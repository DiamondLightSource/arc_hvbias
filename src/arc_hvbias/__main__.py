from argparse import ArgumentParser

from . import __version__
from .keithley import Keithley

__all__ = ["main"]


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(args)

    k = Keithley()


# test with: pipenv run python -m arc_hvbias
if __name__ == "__main__":
    main()
