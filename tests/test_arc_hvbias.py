import subprocess
import sys

import cothread

from arc_hvbias import __main__, __version__

# def test_execution_debug():
#     cmd = [sys.executable, "-m", "arc_hvbias"]
#     result = subprocess.check_output(cmd)
#     cothread.Sleep(1000)
#     print(result.decode())


def test_cli_version():
    cmd = [sys.executable, "-m", "arc_hvbias", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
