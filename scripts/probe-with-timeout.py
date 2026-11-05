#!/usr/bin/env python3
"""Run one read-only resolver with discarded output and process-group cleanup.

POSIX process groups cover ordinary CLI descendants, not children that explicitly
escape into another session. No command arguments or child output are logged.
"""
import os
import signal
import subprocess
import sys
import time


class Interrupted(Exception):
    def __init__(self, signum):
        self.signum = signum


def signal_group(group, signum):
    try:
        os.killpg(group, signum)
        return True
    except ProcessLookupError:
        return False


def main():
    if len(sys.argv) < 3 or not sys.argv[1].isdigit():
        return 125
    seconds = int(sys.argv[1])
    if not 1 <= seconds <= 60:
        return 125
    process = None
    code = 125
    cancellation = None
    cleaning = False

    def interrupted(signum, _frame):
        nonlocal cancellation
        if cancellation is None:
            cancellation = signum
        if not cleaning:
            raise Interrupted(signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        process = subprocess.Popen(
            sys.argv[2:], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            code = process.wait(timeout=seconds)
            if code < 0:
                code = 128 - code
        except subprocess.TimeoutExpired:
            code = 124
    except Interrupted as error:
        code = 128 + error.signum
    except OSError:
        code = 125
    finally:
        # Cleanup must not depend on the launcher remaining alive. Also remove
        # background helpers left by a launcher that returned normally.
        # Record late/repeated cancellation without aborting termination.
        cleaning = True
        if process is not None:
            if signal_group(process.pid, signal.SIGTERM):
                time.sleep(1)
                signal_group(process.pid, signal.SIGKILL)
            process.wait()
    return 128 + cancellation if cancellation is not None else code


if __name__ == "__main__":
    sys.exit(main())
