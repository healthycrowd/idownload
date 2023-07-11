import click

from . import __version__
from .sources import SOURCES
from .exceptions import SourceAccessException


@click.group(
    help="Downloads images and stores metadata about them in a JSON file.",
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
)
@click.version_option(version=__version__)
def cli(**kwargs):
    pass


for source in SOURCES:

    def command(**kwargs):
        kwargs["_progressbar"] = click.progressbar
        try:
            source.download(**kwargs)
        except SourceAccessException as e:
            click.echo(str(e), err=True)

    command.__name__ = source.COMMAND
    for arg in reversed(source.ARGS):
        command = click.argument(arg, nargs=1)(command)
    command = cli.command()(command)

    command = click.option(
        "--with-attr/--no-with-attr",
        default=False,
        help="""
Attempt to attribute to the image to a person or organization and use that name for source_name.
        """,
    )(command)


__all__ = ("cli",)
