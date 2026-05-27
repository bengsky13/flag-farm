#!/usr/bin/env python3
import sys
import socket
import threading

CHALL_HOST = "127.0.0.1"
CHALL_PORT = 8000

def pipe_stream(source_stream, target_socket):
    try:
        while True:
            data = source_stream.buffer.read(1024)
            if not data:
                break
            target_socket.sendall(data)
    except Exception:
        pass
    finally:
        target_socket.close()

def main():
    # 1. Connect to the actual challenge binary
    try:
        chall_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        chall_sock.connect((CHALL_HOST, CHALL_PORT))
    except Exception as e:
        sys.stderr.write(f"[-] Proxy failed to connect to challenge: {e}\n")
        sys.exit(1)

    # 2. Start a thread to pass data from stdin -> ./chall
    client_to_chall = threading.Thread(target=pipe_stream, args=(sys.stdin, chall_sock))
    client_to_chall.daemon = True
    client_to_chall.start()

    # 3. Use the main thread to pass data from ./chall -> stdout
    try:
        while True:
            data = chall_sock.recv(1024)
            if not data:
                break
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
    except Exception:
        pass
    finally:
        chall_sock.close()

if __name__ == "__main__":
    main()