import click


@click.command()
def stop():
    """Stop all running op services."""
    click.echo(
        "To stop the services, please press Ctrl-C in the terminal where 'op start' is running."
    )
