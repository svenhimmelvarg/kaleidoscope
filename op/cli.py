import click
import logging

from op import __version__
from op.commands.serve import serve as serve_cmd
from op.commands.indexer import indexer as indexer_cmd
from op.commands.prompt import prompt as prompt_cmd
from op.commands.config_cmd import init as init_cmd, config as config_group
from op.commands.ingest import ingest as ingest_cmd
from op.commands.supervisor import supervisor as supervisor_cmd
from op.commands.start import start as start_cmd
from op.commands.stop import stop as stop_cmd
from op.workflow import workflow_invoke, workflow_get


@click.group()
@click.version_option(version=__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(level=logging.CRITICAL)


cli.add_command(init_cmd)
cli.add_command(serve_cmd)
cli.add_command(indexer_cmd)
cli.add_command(prompt_cmd)
cli.add_command(config_group)
cli.add_command(ingest_cmd)
cli.add_command(supervisor_cmd)
cli.add_command(start_cmd)
cli.add_command(stop_cmd)
cli.add_command(workflow_invoke)
cli.add_command(workflow_get)


def main():
    cli()
