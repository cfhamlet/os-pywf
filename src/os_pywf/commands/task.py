import click


@click.group()
@click.pass_context
def cli(ctx):
    "Run built-in task."


@cli.command()
@click.pass_context
def http_client(ctx):
    "HTTP client task."


@cli.command()
@click.pass_context
def http_server(ctx):
    "HTTP server task."


@cli.command()
@click.pass_context
def redis(ctx):
    "Redis client task."
