"""Keep the machine from idling to sleep during a long run (08 §2.1)."""

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager


@contextmanager
def keep_awake():
    """caffeinate -i for this process; a machine without it gets a warning and the run goes on."""
    process = None
    path = shutil.which("caffeinate")
    try:
        if path:
            process = subprocess.Popen([path, "-i", "-w", str(os.getpid())])
    except OSError:
        path = None
    if not path:
        print("warning: caffeinate is unavailable; the machine may sleep during this run", file=sys.stderr)
    try:
        yield
    finally:
        if process:
            process.terminate()
