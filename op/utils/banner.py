from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import logging

from op.config import Config

console = Console()
logger = logging.getLogger(__name__)


def display_banner(config: Config, title: str = "Kaleidescope") -> None:
    logger.debug(f"Displaying banner for {title}")
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="cyan", justify="right")
    table.add_column("Value", style="white")

    table.add_row("API URL:", config.kaleidescope_api_url)
    table.add_row("UI URL:", config.kaleidescope_ui_url)
    table.add_row("Index Name:", config.index_name)
    table.add_row("Data Dir:", config.data_dir)
    table.add_row("Meilisearch:", config.meilisearch_host)

    panel = Panel(
        table,
        title=f"[bold green]{title} Configuration",
        border_style="green",
        padding=(1, 2),
    )

    console.print(panel)


def display_indexer_banner(comfyui_path: str, index_name: str, meilisearch_host: str) -> None:
    logger.debug("Displaying indexer banner")
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="cyan", justify="right")
    table.add_column("Value", style="white")

    table.add_row("Input Path:", comfyui_path)
    table.add_row("Index Name:", index_name)
    table.add_row("Meilisearch:", meilisearch_host)

    panel = Panel(
        table,
        title="[bold blue]Indexer Configuration",
        border_style="blue",
        padding=(1, 2),
    )

    console.print(panel)


def display_success(message: str) -> None:
    logger.info(f"Success: {message}")
    console.print(f"[bold green]✓[/bold green] {message}")


def display_error(message: str) -> None:
    logger.error(message)
    console.print(f"[bold red]✗[/bold red] {message}")


def display_info(message: str) -> None:
    logger.info(message)
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def display_warning(message: str) -> None:
    logger.warning(message)
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")
