#!/usr/bin/env python3

from __future__ import annotations

import sys

assert sys.version_info >= (3, 8), "Python < 3.8 is not supported"

import argparse
import binascii
import itertools
import json
import logging
import os
import random
import re
import stat
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from math import ceil
from pathlib import Path
from urllib.parse import urljoin, urlencode # Added urlencode
from urllib.request import Request, urlopen


os_windows = (os.name == "nt")


HEADER = r'''
 ____                       _            _____                    
| __ )  ___ _ __   __ _ ___| | ___   _  |  ___|_ _ _ __ _ __ ___  
|  _ \ / _ \ '_ \ / _` / __| |/ / | | | | |_ / _` | '__| '_ ` _ \ 
| |_) |  __/ | | | (_| \__ \   <| |_| | |  _| (_| | |  | | | | | |
|____/ \___|_| |_|\__, |___/_|\_\\__, | |_|  \__,_|_|  |_| |_| |_|
                  |___/          |___/                            
Multi-sploit farm client
'''[1:]


class Style(Enum):
    BOLD = 1

    FG_BLACK = 30
    FG_RED = 31
    FG_GREEN = 32
    FG_YELLOW = 33
    FG_BLUE = 34
    FG_MAGENTA = 35
    FG_CYAN = 36
    FG_LIGHT_GRAY = 37


BRIGHT_COLORS = [
    Style.FG_RED,
    Style.FG_GREEN,
    Style.FG_BLUE,
    Style.FG_MAGENTA,
    Style.FG_CYAN,
]


def highlight(text, style=None):
    if os_windows:
        return text

    if style is None:
        style = [Style.BOLD, random.choice(BRIGHT_COLORS)]

    return (
        "\033[{}m".format(";".join(str(item.value) for item in style))
        + text
        + "\033[0m"
    )


log_format = "%(asctime)s {} %(message)s".format(
    highlight("%(levelname)s", [Style.FG_YELLOW])
)

logging.basicConfig(
    format=log_format,
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


SCRIPT_EXTENSIONS = {
    ".pl": "perl",
    ".py": "python3",
    ".rb": "ruby",
}


SERVER_TIMEOUT = 5
POST_PERIOD = 5

exit_event = threading.Event()

display_output_lock = threading.RLock()
instance_lock = threading.RLock()


class InvalidSploitError(Exception):
    pass


class APIException(Exception):
    pass


# ------------------------------------------------------------------
# 1. Update parse_args() to accept the new --download flag
# ------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Run multiple sploits automatically",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # We make 'sploit' optional (nargs="?") so it isn't required when downloading
    parser.add_argument(
        "sploit",
        nargs="?",
        help="Sploit file OR directory containing multiple sploits",
    )

    parser.add_argument(
        "-u",
        "--server-url",
        metavar="URL",
        default="http://localhost:5000",
    )

    # Added the new --download flag
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download all saved scripts from the farm server into the local directory",
    )

    parser.add_argument(
        "-a",
        "--alias",
        metavar="ALIAS",
        default=None,
    )

    parser.add_argument(
        "--token",
        metavar="TOKEN",
    )

    parser.add_argument(
        "--interpreter",
        metavar="COMMAND",
    )

    parser.add_argument(
        "--pool-size",
        metavar="N",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--attack-period",
        metavar="N",
        type=float,
        default=120,
    )

    parser.add_argument(
        "-v",
        "--verbose-attacks",
        metavar="N",
        type=int,
        default=1,
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--not-per-team",
        action="store_true",
    )

    group.add_argument(
        "--distribute",
        metavar="K/N",
    )

    return parser.parse_args()


# ------------------------------------------------------------------
# 2. Add the download worker function
# ------------------------------------------------------------------
def download_scripts_from_server(args):
    """
    Fetches all scripts from the server via the API and saves them 
    locally inside their respective challenge folders.
    """
    logger.info("Starting scripts download from %s...", args.server_url)
    
    try:
        # Request all script metadata from the server
        req = Request(urljoin(args.server_url, "/api/scripts/list"))
        if args.token:
            req.add_header("X-Token", args.token)
            
        with urlopen(req, timeout=SERVER_TIMEOUT) as conn:
            if conn.status != 200:
                logger.error("Failed to get scripts list from server. Status: %s", conn.status)
                return
            scripts = json.loads(conn.read().decode())

        if not scripts:
            logger.info("No scripts found on the server to download.")
            return

        for script in scripts:
            chall_name = script['chall_name']
            exp_name = script['exp_name']
            content = script['content']

            # If it's the fallback folder, you can save it directly or keep the directory
            target_dir = Path(chall_name)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = target_dir / exp_name
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Make the file executable locally if it's on a non-Windows machine
            if not os_windows:
                file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)

            logger.info("Downloaded and saved: %s/%s", chall_name, exp_name)

        logger.info("Successfully downloaded %d script(s).", len(scripts))

    except Exception as e:
        logger.critical("Error downloading scripts: %r", e)


# ------------------------------------------------------------------
# 3. Update main() to intercept the --download flag immediately
# ------------------------------------------------------------------
def main(args):
    # Quick URL fix formatting
    if "://" not in args.server_url:
        args.server_url = "http://" + args.server_url

    print(highlight(HEADER))

    # If --download is passed, execute downloading process and exit directly
    if args.download:
        download_scripts_from_server(args)
        return

    # Otherwise, validate regular attack arguments and continue normal loop execution
    if not args.sploit:
        logger.critical("Error: Please provide a sploit target file/folder name or run with --download.")
        return

    try:
        fix_args(args)
    except Exception as e:
        logger.critical("%s", e)
        return

    logger.info(
        "connecting to %s",
        args.server_url,
    )

    threading.Thread(
        target=lambda: run_post_loop(args),
        daemon=True,
    ).start()

    pool = ThreadPoolExecutor(
        max_workers=args.pool_size
    )

    config = None
    flag_format = None

    # Sync scripts once to the server right before entering the attack loop
    upload_scripts_to_server(args)

    for attack_no in once_in_a_period(args.attack_period):
        try:
            config = get_config(args)
            flag_format = re.compile(config["FLAG_FORMAT"])
        except Exception as e:
            logger.error("failed fetching config: %r", e)
            if attack_no == 1:
                return
            continue

        teams = get_target_teams(args, config["TEAMS"])
        if not teams:
            logger.error("no teams")
            if attack_no == 1:
                return
            continue

        logger.info(
            "launching attack #%d against %d teams",
            attack_no,
            len(teams),
        )

        divisor = ceil((len(teams) * len(args.sploit_paths)) / args.pool_size)
        max_runtime = max(1, args.attack_period / divisor)
        show_time_limit_info(args, config, max_runtime, attack_no)

        for team_name, team_addr in teams.items():
            pool.submit(
                run_sploit,
                args,
                team_name,
                team_addr,
                attack_no,
                max_runtime,
                flag_format,
            )

def discover_sploits(path):
    path = Path(path)

    if path.is_file():
        return [str(path)]

    if not path.is_dir():
        raise ValueError(f"No such file or directory: {path}")

    sploits = []

    for item in sorted(path.iterdir()):
        if not item.is_file():
            continue

        ext = item.suffix.lower()

        if ext in SCRIPT_EXTENSIONS or os.access(item, os.X_OK):
            sploits.append(str(item))

    if not sploits:
        raise ValueError(f"No sploits found in directory: {path}")

    return sploits


def check_script_source(source, interpreter):
    errors = []

    if not os_windows and not interpreter and source[:2] != "#!":
        errors.append(
            "Please use shebang as first line "
            "(example: #!/usr/bin/env python3)"
        )

    if re.search(r"flush[(=]", source) is None:
        errors.append(
            "Sploit should flush stdout after printing flags"
        )

    return errors


def check_sploit_file(path, args):
    ext = os.path.splitext(path)[1].lower()
    is_script = ext in SCRIPT_EXTENSIONS

    if is_script:
        with open(path, "r", errors="ignore") as f:
            source = f.read()

        errors = check_script_source(source, args.interpreter)

        if errors:
            for msg in errors:
                logger.error("[%s] %s", path, msg)

            raise InvalidSploitError(path)

        if os_windows and args.interpreter is None:
            args.interpreter = SCRIPT_EXTENSIONS[ext]

    if not os_windows:
        file_mode = os.stat(path).st_mode

        if not file_mode & stat.S_IXUSR:
            if is_script:
                logger.info("setting executable bit on %s", path)
                os.chmod(path, file_mode | stat.S_IXUSR)
            else:
                raise InvalidSploitError(
                    f"{path} is not executable"
                )


def fix_args(args):
    if "://" not in args.server_url:
        args.server_url = "http://" + args.server_url

    args.sploit_paths = discover_sploits(args.sploit)

    logger.info(
        "loaded %d sploits",
        len(args.sploit_paths),
    )

    for path in args.sploit_paths:
        check_sploit_file(path, args)

    if args.distribute is not None:
        valid = False

        match = re.fullmatch(r"(\d+)/(\d+)", args.distribute)

        if match:
            k = int(match.group(1))
            n = int(match.group(2))

            if n >= 2 and 1 <= k <= n:
                args.distribute = (k, n)
                valid = True

        if not valid:
            raise ValueError(
                "Wrong syntax for --distribute"
            )


def get_config(args):
    req = Request(
        urljoin(args.server_url, "/api/get_config")
    )

    if args.token:
        req.add_header("X-Token", args.token)

    with urlopen(req, timeout=SERVER_TIMEOUT) as conn:
        if conn.status != 200:
            raise APIException(conn.read())

        return json.loads(conn.read().decode())


def upload_scripts_to_server(args):
    """
    Reads local script files passed in the arguments and syncs them to the farm server
    matching the chall_name/exp_name structure.
    """
    for path_str in args.sploit_paths:
        try:
            path = Path(path_str)
            
            # Determine challenge folder name and filename
            if path.parent.name and path.parent.name != '.':
                chall_name = path.parent.name
            else:
                # If path was passed directly as a standalone file (e.g., 'exp1.py')
                chall_name = "standalone_exploits"
                
            exp_name = path.name

            with open(path, "r", errors="ignore") as f:
                content = f.read()

            # Prepare form-encoded payload expected by Flask's request.form
            payload = {
                'chall_name': chall_name,
                'exp_name': exp_name,
                'content': content
            }
            data = urlencode(payload).encode('utf-8')

            req = Request(
                urljoin(args.server_url, "/api/scripts/add"),
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if args.token:
                req.add_header("X-Token", args.token)

            with urlopen(req, timeout=SERVER_TIMEOUT) as conn:
                if conn.status == 200:
                    logger.info("Synchronized script safely to server: %s/%s", chall_name, exp_name)
                else:
                    logger.error("Failed to sync script %s to server, Status: %s", exp_name, conn.status)

        except Exception as e:
            logger.error("Error running server script synchronization for %s: %r", path_str, e)


def post_flags(args, flags):
    data = [
        {
            "flag": item["flag"],
            "sploit": item["sploit"],
            "team": item["team"],
        }
        for item in flags
    ]

    req = Request(
        urljoin(args.server_url, "/api/post_flags")
    )

    req.add_header(
        "Content-Type",
        "application/json",
    )

    if args.token:
        req.add_header("X-Token", args.token)

    with urlopen(
        req,
        data=json.dumps(data).encode(),
        timeout=SERVER_TIMEOUT,
    ) as conn:
        if conn.status != 200:
            raise APIException(conn.read())


class FlagStorage:
    def __init__(self):
        self._flags_seen = set()
        self._queue = []
        self._lock = threading.RLock()

    def add(self, flags, team_name, sploit_name):
        new_flags = set()

        with self._lock:
            for flag in flags:
                if flag not in self._flags_seen:
                    self._flags_seen.add(flag)

                    self._queue.append({
                        "flag": flag,
                        "team": team_name,
                        "sploit": sploit_name,
                    })

                    new_flags.add(flag)

        return new_flags

    def pick_flags(self):
        with self._lock:
            return self._queue[:]

    def mark_as_sent(self, count):
        with self._lock:
            self._queue = self._queue[count:]

    @property
    def queue_size(self):
        with self._lock:
            return len(self._queue)


flag_storage = FlagStorage()


def once_in_a_period(period):
    for i in itertools.count(1):
        start = time.time()

        yield i

        spent = time.time() - start

        if period > spent:
            exit_event.wait(period - spent)

        if exit_event.is_set():
            break


def display_sploit_output(team_name, output_lines):
    if not output_lines:
        return

    prefix = highlight(team_name + ": ")

    with display_output_lock:
        print(
            "\n"
            + "\n".join(
                prefix + line.rstrip()
                for line in output_lines
            )
            + "\n"
        )


class InstanceStorage:
    def __init__(self):
        self.instances = {}
        self._counter = 0

        self.n_completed = 0
        self.n_killed = 0

    def register_start(self, process):
        instance_id = self._counter

        self.instances[instance_id] = process

        self._counter += 1

        return instance_id

    def register_stop(self, instance_id, was_killed):
        self.instances.pop(instance_id, None)

        self.n_completed += 1
        self.n_killed += was_killed


instance_storage = InstanceStorage()


def process_sploit_output(
    stream,
    args,
    team_name,
    flag_format,
    attack_no,
    sploit_name,
):
    output_lines = []
    instance_flags = set()

    while True:
        line = stream.readline()

        if not line:
            break

        line = line.decode(errors="replace")

        output_lines.append(line)

        line_flags = set(flag_format.findall(line))

        if line_flags:
            added = flag_storage.add(
                line_flags,
                team_name,
                sploit_name,
            )

            instance_flags |= added

    if (
        attack_no <= args.verbose_attacks
        and not exit_event.is_set()
    ):
        display_sploit_output(
            team_name,
            output_lines,
        )

        if instance_flags:
            logger.info(
                'got %d flags from "%s"',
                len(instance_flags),
                team_name,
            )

    return instance_flags


def launch_sploit(
    sploit_path,
    args,
    team_name,
    team_addr,
    attack_no,
    flag_format,
):
    env = os.environ.copy()

    env["PYTHONUNBUFFERED"] = "1"

    command = [os.path.abspath(sploit_path)]

    if args.interpreter:
        command = [args.interpreter] + command

    if team_addr is not None:
        command.append(team_addr)

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=0,
        close_fds=(not os_windows),
    )

    future = ThreadPoolExecutor(max_workers=1).submit(
        process_sploit_output,
        proc.stdout,
        args,
        team_name,
        flag_format,
        attack_no,
        sploit_path,
    )

    return (
        proc,
        future,
        instance_storage.register_start(proc),
    )


def run_sploit(
    args,
    team_name,
    team_addr,
    attack_no,
    max_runtime,
    flag_format,
):
    for sploit_path in args.sploit_paths:
        try:
            with instance_lock:
                if exit_event.is_set():
                    return

                proc, future, instance_id = launch_sploit(
                    sploit_path,
                    args,
                    team_name,
                    team_addr,
                    attack_no,
                    flag_format,
                )

        except Exception as e:
            logger.error(
                "failed to launch %s: %r",
                sploit_path,
                e,
            )
            continue

        try:
            try:
                proc.wait(timeout=max_runtime)
                was_killed = False

            except subprocess.TimeoutExpired:
                was_killed = True

                logger.warning(
                    '[%s] timeout: %s',
                    team_name,
                    os.path.basename(sploit_path),
                )

                proc.kill()

            instance_flags = future.result(timeout=5)

            with instance_lock:
                instance_storage.register_stop(
                    instance_id,
                    was_killed,
                )

            if instance_flags:
                logger.info(
                    '[%s] success using %s (%d flags)',
                    team_name,
                    sploit_path,
                    len(instance_flags),
                )

                return

            else:
                logger.info(
                    '[%s] no flags from %s',
                    team_name,
                    sploit_path,
                )

        except Exception as e:
            logger.error(
                "error running %s against %s: %r",
                sploit_path,
                team_name,
                e,
            )

    logger.warning(
        '[%s %s] all sploits failed',
        team_name,
        team_addr
    )


def get_target_teams(args, teams):
    if args.not_per_team:
        return {"*": None}

    if args.distribute:
        k, n = args.distribute

        teams = {
            name: addr
            for name, addr in teams.items()
            if binascii.crc32(addr.encode()) % n == k - 1
        }

    return teams


def show_time_limit_info(
    args,
    config,
    max_runtime,
    attack_no,
):
    if attack_no == 1:
        min_attack_period = (
            config["FLAG_LIFETIME"]
            - config["SUBMIT_PERIOD"]
            - POST_PERIOD
        )

        if args.attack_period >= min_attack_period:
            logger.warning(
                "attack period may be too large"
            )

    logger.info(
        "time limit per instance: %.1f sec",
        max_runtime,
    )

    with instance_lock:
        if instance_storage.n_completed > 0:
            pct = (
                float(instance_storage.n_killed)
                / instance_storage.n_completed
            ) * 100

            logger.info(
                "%.1f%% instances timed out",
                pct,
            )


def run_post_loop(args):
    try:
        for _ in once_in_a_period(POST_PERIOD):
            flags_to_post = flag_storage.pick_flags()

            if not flags_to_post:
                continue

            try:
                post_flags(args, flags_to_post)

                flag_storage.mark_as_sent(
                    len(flags_to_post)
                )

                logger.info(
                    "posted %d flags (%d queued)",
                    len(flags_to_post),
                    flag_storage.queue_size,
                )

            except Exception as e:
                logger.error(
                    "failed posting flags: %r",
                    e,
                )

    except Exception as e:
        logger.critical(
            "post loop crashed: %r",
            e,
        )

        shutdown()


def shutdown():
    exit_event.set()

    with instance_lock:
        for proc in list(
            instance_storage.instances.values()
        ):
            try:
                proc.kill()
            except Exception:
                pass

if __name__ == "__main__":
    try:
        main(parse_args())

    except KeyboardInterrupt:
        logger.info("Ctrl+C received")

    finally:
        shutdown()