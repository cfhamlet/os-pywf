import click

from . import cli as main


@main.command()
@click.pass_context
def proxy(ctx):
    "HTTP proxy."
