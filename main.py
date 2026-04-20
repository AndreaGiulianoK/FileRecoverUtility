#!/usr/bin/env python3
"""RECOVER — entry point."""
import sys

if sys.version_info < (3, 11):
    sys.exit("Python 3.11+ richiesto.")

from recover.tui.app import RecoverApp


def main() -> None:
    app = RecoverApp()
    app.run()


if __name__ == "__main__":
    main()
