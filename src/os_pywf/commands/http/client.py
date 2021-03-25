import click

import os_pywf

from . import cli as main


def callback(task):
    pass


@main.command()
@click.option(
    "-0",
    "--http1.0",
    "http10",
    is_flag=True,
    help="Use HTTP 1.0",
)
@click.option(
    "-A",
    "--user-agent",
    default=f"os-pywf/{os_pywf.__version__}",
    show_default=True,
    help="User-Agent to send to server.",
)
@click.option(
    "-b",
    "--cookie",
    default=(None, None),  # issue of click
    type=(click.File(), str),
    help="String or file to read cookies from.",
)
@click.option(
    "--callback",
    default=f"{callback.__module__}.{callback.__name__}",
    show_default=True,
    help="Callback function invoked when response received.",
)
@click.option(
    "-c",
    "--cookie-jar",
    type=click.File(mode="w"),
    help="Write cookies to this file after operation.",
)
@click.option(
    "-d",
    "--data",
    multiple=True,
    help="HTTP POST data.",
)
@click.option(
    "--data-urlencode",
    multiple=True,
    help="HTTP POST data url encoded.",
)
@click.option(
    "-e",
    "--referer",
    help="Referer URL.",
)
@click.option(
    "-F",
    "--form",
    help="Specify HTTP multipart POST data.",
)
@click.option(
    "-H",
    "--header",
    multiple=True,
    help="Custom header to pass to server.",
)
@click.option(
    "-L",
    "--location",
    is_flag=True,
    help="Follow redirects.",
)
@click.option(
    "--max-redirs",
    type=click.INT,
    default=20,
    show_default=True,
    help="Maximum number of redirects allowed.",
)
@click.option(
    "--retry",
    type=click.INT,
    default=0,
    show_default=True,
    help="Retry times when request fail.",
)
@click.option(
    "-X",
    "--request",
    default="GET",
    show_default=True,
    type=click.Choice(
        ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
        case_sensitive=False,
    ),
    help="Request method.",
)
@click.argument("urls", nargs=-1)
@click.pass_context
def client(ctx, **kwargs):
    "HTTP client inspired by curl."

    urls = kwargs.pop("urls", ())
    if not urls:
        click.echo(client.get_help(ctx))
        ctx.exit(0)
