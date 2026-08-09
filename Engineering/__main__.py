"""
Entry point for the Engineering Toolkit CLI.
"""

from __future__ import annotations

import sys

from rich.console import Console

from Engineering.cli.app import app
from Engineering.cli.errors import translate_exception

console = Console()


def main() -> None:
    try:
        app()
    except SystemExit:
        raise
    except Exception as exc:
        code = translate_exception(exc, verbose=False)
        sys.exit(code)


if __name__ == "__main__":
    main()