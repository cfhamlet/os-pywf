import click
from click_option_group import optgroup

import os_pywf

from . import cli as main


def callback(task):
    pass


@main.command()
@optgroup.group("Curl options", help="Options same as curl.")
@optgroup.option(
    "-0",
    "--http1.0",
    "http10",
    is_flag=True,
    help="Use HTTP 1.0",
)
@optgroup.option(
    "-A",
    "--user-agent",
    default=f"os-pywf/{os_pywf.__version__}",
    show_default=True,
    help="User-Agent to send to server.",
)
@optgroup.option(
    "-b",
    "--cookie",
    default=(None, None),  # issue of click
    type=(click.File(), str),
    help="String or file to read cookies from.",
)
@optgroup.option(
    "-c",
    "--cookie-jar",
    type=click.File(mode="w"),
    help="Write cookies to this file after operation.",
)
@optgroup.option(
    "-d",
    "--data",
    multiple=True,
    help="HTTP POST data.",
)
@optgroup.option(
    "--data-urlencode",
    multiple=True,
    help="HTTP POST data url encoded.",
)
@optgroup.option(
    "-e",
    "--referer",
    help="Referer URL.",
)
@optgroup.option(
    "-F",
    "--form",
    help="Specify HTTP multipart POST data.",
)
@optgroup.option(
    "-H",
    "--header",
    multiple=True,
    help="Custom header to pass to server.",
)
@optgroup.option(
    "-L",
    "--location",
    is_flag=True,
    help="Follow redirects.",
)
@optgroup.option(
    "--max-redirs",
    type=click.INT,
    default=20,
    show_default=True,
    help="Maximum number of redirects allowed.",
)
@optgroup.option(
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
@optgroup.group("Additional options", help="Additional options.")
@optgroup.option(
    "--callback",
    default=f"{callback.__module__}.{callback.__name__}",
    show_default=True,
    help="Callback function invoked when response received.",
)
@optgroup.option(
    "--retry",
    type=click.INT,
    default=0,
    show_default=True,
    help="Retry times when request fail.",
)
@optgroup.option("--parallel", is_flag=True, help="Send requests parallelly.")
@click.argument("urls", nargs=-1)
@click.pass_context
def curl(ctx, **kwargs):
    "HTTP client inspired by curl."
    print(kwargs)

    urls = kwargs.pop("urls", ())
    if not urls:
        click.echo(curl.get_help(ctx))
        ctx.exit(0)
