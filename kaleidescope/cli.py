import click
import uvicorn
from kaleidescope.config import load_config
import logging


@click.group()
def cli():
    pass


@cli.command()
@click.option("--host", default=None, help="Bind socket to this host.")
@click.option("--port", default=None, type=int, help="Bind socket to this port.")
@click.option("--reload", is_flag=True, help="Enable auto-reload.")
def serve(host, port, reload):
    """Run the Kaleidescope API server."""
    config = load_config()

    server_host = host if host else config.host
    server_port = port if port else config.port

    # Configure logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    uvicorn.run(
        "kaleidescope.main:app",
        host=server_host,
        port=server_port,
        reload=reload,
        log_config=log_config,
    )


if __name__ == "__main__":
    cli()
