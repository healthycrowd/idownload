import click

from . import __version__
from .sources import SOURCES
from .exceptions import ImageDownloadException


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
        kwargs["progressbar"] = click.progressbar
        source.download(**kwargs)

    command.__name__ = source.COMMAND
    for arg in reversed(source.ARGS):
        command = click.argument(arg, nargs=1)(command)
    command = cli.command()(command)
