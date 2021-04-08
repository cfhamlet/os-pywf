import click
from click_option_group import optgroup

from os_pywf.utils import walk_modules

from . import __version__


class CommandFinder(click.MultiCommand):
    def list_commands(self, ctx):
        ctx.ensure_object(dict)
        return list(self.__find_commnds(**ctx.obj).keys())

    def get_command(self, ctx, name):
        ctx.ensure_object(dict)
        commands = self.__find_commnds(**ctx.obj)
        return commands.get(name, None)

    def __find_commnds(self, **kwargs):
        command_packages = kwargs.get("command_packages", [])
        commands = {}
        for command_package in command_packages:
            for cmd_module in walk_modules(command_package, skip_fail=False):
                if hasattr(cmd_module, "cli") and isinstance(
                    cmd_module.cli, click.Command
                ):
                    name = cmd_module.__name__.split(".")[-1]
                    name = name.replace("_", "-")
                    commands[name] = cmd_module.cli

        return commands


def execute(**kwargs):
    import pywf as wf

    gs = wf.GlobalSettings()

    @click.command(cls=CommandFinder, context_settings=dict(obj=kwargs))
    @click.version_option(version=__version__)
    @optgroup.group("Workflow", help="Workflow global settings.")
    @optgroup.option(
        "--compute-threads",
        default=gs.compute_threads,
        show_default=True,
        type=click.INT,
        help="Number of compute threads.",
    )
    @optgroup.option(
        "--handler-threads",
        default=gs.handler_threads,
        show_default=True,
        type=click.INT,
        help="Number of handler threads.",
    )
    @optgroup.option(
        "--poller-threads",
        default=gs.poller_threads,
        show_default=True,
        type=click.INT,
        help="Number of poller threads.",
    )
    @optgroup.option(
        "--dns-threads",
        default=gs.dns_threads,
        show_default=True,
        type=click.INT,
        help="Number of dns threads.",
    )
    @optgroup.option(
        "--dns-ttl-default",
        default=gs.dns_ttl_default,
        show_default=True,
        type=click.INT,
        help="Default seconds of dns ttl.",
    )
    @optgroup.option(
        "--dns-ttl-min",
        default=gs.dns_ttl_min,
        show_default=True,
        type=click.INT,
        help="Min seconds of dns ttl.",
    )
    @optgroup.option(
        "--max-connections",
        default=gs.endpoint_params.max_connections,
        show_default=True,
        type=click.INT,
        help="Max number of connections.",
    )
    @optgroup.option(
        "--connection-timeout",
        default=gs.endpoint_params.connect_timeout,
        show_default=True,
        type=click.INT,
        help="Connect timeout(ms).",
    )
    @optgroup.option(
        "--response-timeout",
        default=gs.endpoint_params.response_timeout,
        show_default=True,
        type=click.INT,
        help="Response timeout(ms).",
    )
    @optgroup.option(
        "--ssl-connect-timeout",
        default=gs.endpoint_params.ssl_connect_timeout,
        show_default=True,
        type=click.INT,
        help="SSL connect timeout(ms).",
    )
    @click.pass_context
    def cli(ctx, **kgs):
        """Command line tool for os-pywf."""
        for k in (
            "compute_threads",
            "handler_threads",
            "poller_threads",
            "dns_threads",
            "dns_ttl_min",
            "dns_ttl_default",
        ):
            setattr(gs, k, kgs.get(k, getattr(gs, k)))

        for k in (
            "connect_timeout",
            "max_connections",
            "response_timeout",
            "ssl_connect_timeout",
        ):
            setattr(gs.endpoint_params, k, kgs.get(k, getattr(gs.endpoint_params, k)))

        wf.WORKFLOW_library_init(gs)

    cli()
