import requests
import logging

from models import FlagStatus, SubmitResult

logger = logging.getLogger(__name__)

RESPONSES = {
    FlagStatus.QUEUED: ['timeout', 'game not started', 'try again later', 'game over', 'is not up',
                        'no such flag'],
    FlagStatus.ACCEPTED: ['submitted successfully'],
    FlagStatus.REJECTED: ['bad', 'wrong', 'expired', 'unknown', 'your own',
                          'too old', 'not in database', 'already submitted', 'invalid flag'],
}
TIMEOUT = 5


def submit_flags(flags, config):
    for listflag in flags:
        r = requests.post(config['SYSTEM_URL'],
                        headers={'Authorization': "Bearer "+config['SYSTEM_TOKEN']},
                        json={"flag":listflag.flag}, timeout=TIMEOUT)
        response = r.json()['message'].strip()
        if response == 'Flag submitted successfully':
            found_status = FlagStatus.ACCEPTED
        else:
            found_status = FlagStatus.REJECTED

        yield SubmitResult(listflag.flag, found_status, response)