import logging
import subprocess
import sys
from pathlib import Path

import click

from op.config import ensure_config

logger = logging.getLogger(__name__)


@click.command()
@click.argument("services", nargs=-1)
def start(services):
    """Start all op services using honcho."""
    ensure_config()

    if not Path("Procfile").exists():
        click.echo("Error: Procfile not found in the current directory.", err=True)
        sys.exit(1)

    try:
        # Run honcho start to manage processes defined in Procfile
        cmd = ["honcho", "start"] + list(services)
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        click.echo("\nStopping services...")
    except subprocess.CalledProcessError as e:
        click.echo(f"Honcho exited with error code {e.returncode}", err=True)
        sys.exit(e.returncode)
    except FileNotFoundError:
        click.echo("Error: 'honcho' command not found. Ensure it is installed.", err=True)
        sys.exit(1)
