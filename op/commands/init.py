import click
from op.commands.config_cmd import init as config_init

@click.command(name="init")
@click.option("--dev", is_flag=True, help="Initialize a .env file in the current directory")
@click.argument("location", required=False, type=click.Path())
@click.pass_context
def init_cmd(ctx, dev, location):
    """Alias for 'op config init'"""
    ctx.forward(config_init)
