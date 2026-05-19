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
from cli.display import display_results, display_history
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
def search(
    query: str,
    source: Optional[str],
    include_all: bool,
    refresh: bool,
    offline: bool,
    export: Optional[str],
    ignore_lang: bool,
):
    """Search for open-source learning resources."""
    api_client = create_api_client()
    cache_manager = CacheManager()

    try:
        if offline:
            click.echo("Running in offline mode...")
            results = get_offline_results(cache_manager, query, source)
        else:
            query_id = cache_manager.get_or_create_query(query)
            results = []
            if not refresh:
                cached_results = cache_manager.get_cached_results(query_id, source)
                if cached_results:
                    results = cached_results
                    click.echo("Using cached results...")
            if refresh or not results:
                results = fetch_from_api(api_client, query, source)
                if results:
                    cache_results_to_db(cache_manager, query_id, results, source)

        results = [normalize_result(r) for r in results]

        if not ignore_lang:
            results = [
                r
                for r in results
                if not (
                    contains_cjk(r["title"])
                    or contains_cjk(r.get("description", ""))
                )
            ]

        if not include_all:
            reputable = [r for r in results if r["reputable"]]
            if results and not reputable:
                click.echo(
                    "No reputable results (>100 GitHub stars). "
                    "Use --include-all to see all matches."
                )
            results = reputable

        display_results(results, query)

        export_path = resolve_export_path(export, query)
        write_export(results, query, export_path)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    finally:
        api_client.close()
        cache_manager.close()


@cli.command()
def history():
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
    cursor = cache_manager.connection.cursor()
    cursor.execute(
        "SELECT id FROM queries WHERE search_term = %s",
        (query,),
    )
    row = cursor.fetchone()
    cursor.close()

    if not row:
        click.echo(f"No cached results found for query: {query}")
        return []
    return cache_manager.get_cached_results(row[0], source)


def normalize_result(result: dict) -> dict:
    """Fix legacy cache rows and ensure GitHub entries use owner/repo + full URL."""
    url = (result.get("url") or "").strip()
    title = (result.get("title") or "").strip()

    if result.get("source") == "github" and "github.com/" in url:
        path = url.split("github.com/", 1)[-1].strip("/")
        if path and "/" not in title:
            result["title"] = path
        if not url.startswith("http"):
            result["url"] = f"https://github.com/{path}"

    return result


def create_api_client() -> APIClient:
    """Build API client using github_token from config or GITHUB_TOKEN env."""
    config = load_config()
    token = (config.get("github_token") or os.environ.get("GITHUB_TOKEN") or "").strip()
    return APIClient(github_token=token or None)


def fetch_from_api(
    api_client: APIClient, query: str, source: Optional[str]
) -> List[dict]:
    """Fetch results from APIs."""
    results = []
    sources = (source,) if source else ("github", "open_library")

    for src in sources:
        try:
            if src == "github":
                for r in api_client.search_github(query):
                    full_name = r.get("full_name") or r.get("name", "")
                    html_url = r.get("html_url") or (
                        f"https://github.com/{full_name}" if full_name else ""
                    )
                    results.append(
                        {
                            "source": "github",
                            "title": full_name,
                            "description": r.get("description") or "",
                            "url": html_url,
                            "reputable": r["stargazers_count"] > 100,
                        }
                    )
            elif src == "open_library":
                for r in api_client.search_open_library(query):
                    authors = r.get("author_name") or []
                    key = r.get("key") or ""
                    ol_url = (
                        key
                        if key.startswith("http")
                        else f"https://openlibrary.org{key}"
                    )
                    description = (
                        f"Authors: {', '.join(authors[:3])}"
                        if authors
                        else (r.get("subtitle") or "")
                    )
                    results.append(
                        {
                            "source": "open_library",
                            "title": r.get("title", "Unknown Title"),
                            "description": description,
                            "url": ol_url,
                            "reputable": True,
                        }
                    )
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
