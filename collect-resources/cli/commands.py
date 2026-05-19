"""
CLI commands module for Project Look.
Main Click setup defining interface entry points and interactive hooks.
"""

import click
import sys
import re
import json
import os
from typing import Optional, List
from core.api_client import APIClient
from core.cache_manager import CacheManager
from cli.display import display_history
from utils.pdf_engine import generate_pdf


def contains_cjk(text: str) -> bool:
    """Check if text contains any CJK (Chinese, Japanese, Korean) characters.
    Returns True if any character in the CJK Unicode range is found.
    """
    if not text:
        return False
    # CJK Unified Ideographs range
    pattern = re.compile(r"[一-鿿]")
    return bool(pattern.search(text))


class DefaultGroup(click.Group):
    """Run `search` when the first argument is not a subcommand name."""

    default_cmd = "search"

    def parse_args(self, ctx, args):
        if not args:
            return super().parse_args(ctx, args)
        if args[0] in self.commands:
            return super().parse_args(ctx, args)
        if args[0] in ("--help", "-h", "--version"):
            return super().parse_args(ctx, args)
        args = [self.default_cmd, *args]
        return super().parse_args(ctx, args)


@click.group(cls=DefaultGroup)
@click.version_option(version="1.0.0")
def cli():
    """Project Look - CLI tool for discovering open-source learning resources."""
    pass


@cli.command()
@click.argument("query")
@click.option(
    "--source",
    "-s",
    type=click.Choice(["github", "open_library"]),
    help="Limit search to specific source (github or open_library)",
)
@click.option(
    "--include-all",
    "-a",
    is_flag=True,
    help="Include all results, not just reputable ones",
)
@click.option(
    "--refresh", "-r", is_flag=True, help="Force refresh from API, bypassing cache"
)
@click.option(
    "--offline", "-o", is_flag=True, help="Use only cached data, no network requests"
)
@click.option(
    "--export",
    "-e",
    type=click.Path(),
    help="Optional custom export path (file or directory); default is ./exports/<query>.pdf",
)
@click.option(
    "--ignore-lang",
    "-i",
    is_flag=True,
    help="Include non-English resources (default: filter out non-English)",
)
@cli.command()
@click.pass_context
def history(ctx):
    """Display search history."""
    cache_manager = CacheManager()
    try:
        display_history(cache_manager.get_search_history())
    except Exception as e:
        click.echo(f"Error retrieving history: {str(e)}", err=True)
        sys.exit(1)
    finally:
        cache_manager.close()


def get_offline_results(
    cache_manager: CacheManager, query: str, source: Optional[str]
) -> List[dict]:
    """Get results from offline cache."""
    query_id = cache_manager.get_query_id(query)
    if query_id is None:
        click.echo(f"No cached results found for query: {query}")
        return []
    return cache_manager.get_cached_results(query_id, source)


def fetch_from_api(
    api_client: APIClient, query: str, source: Optional[str]
) -> List[dict]:
    """Fetch results from APIs."""
    results = []

    fetchers = {
        "github": [
            {
                "source": "github",
                "title": r["name"],
                "description": r.get("description") or "",
                "url": r["html_url"],
                "reputable": r["stargazers_count"] > 100,
            }
            for r in api_client.search_github(query)
        ],
        "open_library": [
            {
                "source": "open_library",
                "title": r.get("title", "Unknown Title"),
                "description": (r.get("author_name") or [""])[0],
                "url": f"https://openlibrary.org{r.get('key', '')}",
                "reputable": True,
            }
            for r in api_client.search_open_library(query)
        ],
    }

    for src, fetch in fetchers.items():
        if source and source != src:
            continue
        try:
            results.extend(fetch())
        except Exception as e:
            click.echo(f"Warning: Could not fetch from {src}: {str(e)}", err=True)

    return results


def cache_results_to_db(
    cache_manager: CacheManager,
    query_id: int,
    results: List[dict],
    source: Optional[str],
):
    """Cache results to database, grouped by source."""
    sources = [source] if source else ["github", "open_library"]
    for src in sources:
        src_results = [r for r in results if r["source"] == src]
        if src_results:
            cache_manager.cache_results(query_id, src_results, src)


def load_config() -> dict:
    """Load config.json from the project root."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def query_to_filename(query: str, ext: str = ".pdf") -> str:
    """Build a safe filename from a search query."""
    slug = re.sub(r"[-\s]+", "_", re.sub(r"[^\w\s-]", "", query.lower())).strip("_")
    return f"{slug or 'search_results'}{ext}"


def resolve_export_path(custom_export: Optional[str], query: str) -> str:
    """
    Resolve the export file path.

    Without --export: ./exports/<query>.pdf (from config default_export_path).
    With --export: use as a file path, or as a directory with the default filename.
    """
    config = load_config()
    default_dir = config.get("default_export_path", "./exports")
    default_filename = query_to_filename(query)

    if not custom_export:
        os.makedirs(default_dir, exist_ok=True)
        return os.path.join(default_dir, default_filename)

    custom_export = os.path.normpath(custom_export)
    if os.path.splitext(custom_export)[1].lower() in (".pdf", ".txt"):
        os.makedirs(os.path.dirname(custom_export) or ".", exist_ok=True)
        return custom_export

    os.makedirs(custom_export, exist_ok=True)
    return os.path.join(custom_export, default_filename)


def write_export(results: List[dict], query: str, export_path: str) -> None:
    """Write search results to PDF, falling back to plain text on failure."""
    if not results:
        click.echo(f"No results to export.")
        return

    try:
        generate_pdf(results, query, export_path)
        click.echo(f"Results exported to {export_path}")
    except Exception as e:
        click.echo(f"Warning: PDF generation failed: {str(e)}", err=True)
        text_path = (
            export_path[:-4] if export_path.lower().endswith(".pdf") else export_path
        ) + ".txt"
        try:
            save_as_text(results, query, text_path)
            click.echo(f"Results saved as text file: {text_path}")
        except Exception as text_e:
            click.echo(
                f"Warning: Text file generation also failed: {str(text_e)}", err=True
            )


def save_as_text(results: List[dict], query: str, output_path: str):
    """Save results as a plain text file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Search Query: {query}\nTotal Results: {len(results)}\n{'=' * 50}\n\n")
        for i, r in enumerate(results, 1):
            f.write(
                f"{i}. {r['title']} ({r['source']})\n"
                f"   Description: {r['description']}\n"
                f"   URL: {r['url']}\n"
                f"   Reputable: {'Yes' if r['reputable'] else 'No'}\n"
                f"{'-' * 50}\n\n"
            )


if __name__ == "__main__":
    cli()
