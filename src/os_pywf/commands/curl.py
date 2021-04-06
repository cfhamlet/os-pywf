import logging
import signal
import sys
import time
from typing import Type, Union

import click
import pywf
import requests
from click_option_group import optgroup
from requests.models import DEFAULT_REDIRECT_LIMIT

import os_pywf
from os_pywf.exceptions import Failure
from os_pywf.http.client import HTTP_10, HTTP_11, Session
from os_pywf.utils import LogLevel, init_logging, kv_from_string, load_obj

logger = logging.getLogger(__name__)

pywf_settings = pywf.get_global_settings()


def callback(
    task: pywf.HttpTask, request: requests.PreparedRequest, response: requests.Response
):
    logger.info(f"{request.method} {request.url} {response}")


def errback(task: pywf.HttpTask, request: requests.PreparedRequest, failure: Failure):
    logger.error(f"{request.method} {request.url} {failure}")


def startup(runner: Union[pywf.SeriesWork, Type[pywf.SubTask]]):
    ctx = runner.get_context()
    if ctx is None:
        runner.set_context({"start_time": time.time()})
    logger.debug("start")


def cleanup(runner: Union[pywf.SeriesWork, Type[pywf.SubTask]]):
    ctx = runner.get_context()
    msg = "finish"
    if ctx and isinstance(ctx, dict) and "start_time" in ctx:
        cost = time.time() - ctx["start_time"]
        msg += f" cost:{cost:.5f}"
    logger.debug(msg)


@click.command()
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
    "--max-filesize",
    type=click.INT,
    default=None,
    show_default=True,
    help="Maximum data size (in bytes) to download.",
)
@optgroup.option(
    "--max-redirs",
    type=click.INT,
    default=DEFAULT_REDIRECT_LIMIT,
    show_default=True,
    help="Maximum number of redirects allowed.",
)
@optgroup.option("--no-keepalive", is_flag=True, help="Disable keepalive.")
@optgroup.option(
    "--retry",
    type=click.INT,
    default=0,
    show_default=True,
    help="Maximum retries when request fail.",
)
@optgroup.option(
    "--retry-delay",
    type=click.FLOAT,
    default=0,
    show_default=True,
    help="Time between two retries(s).",
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
    "--send-timeout",
    type=click.FLOAT,
    default=-1,
    show_default=True,
    help="Send request timeout(s).",
)
@optgroup.option(
    "--receive-timeout",
    type=click.FLOAT,
    default=-1,
    show_default=True,
    help="Receive response timeout(s).",
)
@optgroup.option(
    "--startup",
    default=f"{startup.__module__}.{startup.__name__}",
    show_default=True,
    help="Function invoked when startup.",
)
@optgroup.option(
    "--cleanup",
    default=f"{cleanup.__module__}.{cleanup.__name__}",
    show_default=True,
    help="Function invoked when cleanup.",
)
@optgroup.option(
    "--callback",
    default=f"{callback.__module__}.{callback.__name__}",
    show_default=True,
    help="Function invoked when response received.",
)
@optgroup.option(
    "--errback",
    default=f"{errback.__module__}.{errback.__name__}",
    show_default=True,
    help="Function invoked when request fail.",
)
@optgroup.option("--parallel", is_flag=True, help="Send requests parallelly.")
@optgroup.option(
    "--log-level",
    default="INFO",
    show_default=True,
    type=click.Choice([l.name.upper() for l in LogLevel], case_sensitive=False),
    help="Log level.",
)
@optgroup.option("--debug", is_flag=True, help="Enable debug mode.")
@click.argument("urls", nargs=-1)
@click.pass_context
def cli(ctx, **kwargs):
    "HTTP client inspired by curl."

    if not kwargs.get("urls", ()):
        click.echo(cli.get_help(ctx))
        ctx.exit(0)

    debug = kwargs.get("debug", False)

    loglevel = "DEBUG" if debug else kwargs.get("log_level", "INFO").upper()
    init_logging(loglevel)

    if debug:
        logger.debug(kwargs)

    for k in ("debug", "log_level"):
        kwargs.pop(k, None)

    sys.path.insert(0, ".")
    funcs = dict.fromkeys(("cleanup", "startup", "callback", "errback"))
    for name in funcs:
        if kwargs.get(name, None):
            f = load_obj(kwargs.pop(name))
            funcs[name] = f

    runner = None
    append = None
    parallel = kwargs.pop("parallel", False)
    if parallel:
        runner = pywf.create_parallel_work(None)
        append = runner.add_series
    else:
        runner = pywf.create_series_work(pywf.create_empty_task(), None)
        append = runner.push_back

    timeout = (kwargs.pop("send_timeout", -1), kwargs.pop("receive_timeout", -1))

    headers = {}

    for kv in kwargs.pop("header"):
        k, v = kv_from_string(kv)
        headers[k] = v

    referer = kwargs.pop("referer")
    if referer:
        headers["Referer"] = referer

    headers["User-Agent"] = kwargs.pop("user_agent")

    method = kwargs.pop("request")
    version = HTTP_10 if kwargs.pop("http10") else HTTP_11
    no_keepalive = not kwargs.pop("no_keepalive")
    retry = kwargs.pop("retry")
    retry_delay = kwargs.pop("retry_delay")
    max_redirs = kwargs.pop("max_redirs")
    location = kwargs.pop("location")
    max_size = kwargs.pop("max_filesize")
    urls = kwargs.pop("urls", ())

    with Session(
        version=version,
        headers=headers,
        timeout=timeout,
        disable_keepalive=no_keepalive,
        max_retries=retry,
        retry_delay=retry_delay,
        allow_redirects=location,
        max_redirects=max_redirs,
        max_size=max_size,
        callback=funcs["callback"],
        errback=funcs["errback"],
    ) as session:

        for url in urls:
            o = session.request(
                url,
                method=method,
            )
            if parallel:
                o = pywf.create_series_work(o, None)
            append(o)

        def _cancel(signum, frame):
            logger.debug(f"receive signal {signal.Signals(signum).name}")
            session.cancel()

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, _cancel)

        def _cleanup(task):
            if session.cancel():
                cancel.set()
            if funcs["cleanup"]:
                funcs["cleanup"](runner)

        runner.set_callback(_cleanup)

        if funcs["startup"]:
            funcs["startup"](runner)
        runner.start()
        session.wait_cancel()
    pywf.wait_finish()
