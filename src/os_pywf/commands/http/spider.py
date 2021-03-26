import click

from . import cli as main


@main.command()
@click.pass_context
def spider(ctx):
    "Web spider."
