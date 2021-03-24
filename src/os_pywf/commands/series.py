import click


@click.command()
@click.pass_context
def cli(ctx, **kwargs):
    "Run as series."
