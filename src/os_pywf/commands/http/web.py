import click

from . import cli as main


@main.command()
@click.pass_context
def web(ctx):
    "Web server."
