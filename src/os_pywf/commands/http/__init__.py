import click


@click.group()
@click.pass_context
def cli(ctx):
    "HTTP tools."
