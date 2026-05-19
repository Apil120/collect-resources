"""
Display module for Project Look.
Formatting layer wrapping 'rich' layouts for console tables.
"""

from rich.table import Table
from rich.console import Console
from rich import box
from typing import List, Dict, Any


def display_results(results: List[Dict[str, Any]], query: str):
    """
    Display search results in a formatted table.

    Args:
        results: List of result dictionaries
        query: The search query
    """
    console = Console()

    if not results:
        console.print(f"[yellow]No results found for query: {query}[/yellow]")
        return

    # Create table
    table = Table(
        title=f"Search Results for: {query}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("Source", style="cyan", width=12)
    table.add_column("Title", style="green", width=36, overflow="fold")
    table.add_column("Description", style="white", width=40, overflow="fold")
    table.add_column("URL", style="blue", width=52, overflow="fold")
    table.add_column("Reputable", style="yellow", width=10)

    for result in results:
        title = result["title"]
        if len(title) > 36:
            title = title[:33] + "..."

        description = result.get("description") or ""
        if len(description) > 40:
            description = description[:37] + "..."

        url = result.get("url") or ""
        if url:
            # Full repo URL; avoid truncating to https://github.com/<user> only
            url_cell = f"[link={url}]{url}[/link]"
        else:
            url_cell = ""

        reputable = "Yes" if result["reputable"] else "No"

        table.add_row(
            result["source"].title(),
            title,
            description,
            url_cell,
            reputable,
        )

    console.print(table)
    console.print(f"[dim]Found {len(results)} results[/dim]")


def display_history(history: List[Dict[str, Any]]):
    """
    Display search history in a formatted table.

    Args:
        history: List of history dictionaries
    """
    console = Console()

    if not history:
        console.print("[yellow]No search history found[/yellow]")
        return

    # Create table
    table = Table(
        title="Search History",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("Search Term", style="cyan", width=20)
    table.add_column("Sources", style="green", width=20)
    table.add_column("Total Results", style="yellow", width=15)
    table.add_column("Last Updated", style="blue", width=20)

    for item in history:
        table.add_row(
            item['search_term'],
            item['sources'],
            str(item['total_results']),
            item['created_at']
        )

    console.print(table)


def display_error(message: str):
    """
    Display an error message.

    Args:
        message: The error message to display
    """
    console = Console()
    console.print(f"[red]Error: {message}[/red]")


def display_info(message: str):
    """
    Display an info message.

    Args:
        message: The info message to display
    """
    console = Console()
    console.print(f"[blue]{message}[/blue]")


def display_warning(message: str):
    """
    Display a warning message.

    Args:
        message: The warning message to display
    """
    console = Console()
    console.print(f"[yellow]Warning: {message}[/yellow]")