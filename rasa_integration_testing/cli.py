import sys
from typing import Optional, TextIO

import click

COLOR_SUCCESS = "green"
COLOR_ERROR = "red"
COLOR_WARNING = "yellow"
EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def echo(
    message: str, color: Optional[str] = None, output: TextIO = sys.stdout
) -> None:
    if output is sys.stdout and color is not None:
        click.secho(message, file=output, fg=color)
    else:
        click.echo(message, file=output)
