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
    pattern = re.compile(r'[一-鿿]')
    return bool(pattern.search(text))


class DefaultGroup(click.Group):
    """Run `search` when the first argument is not a subcommand name."""

    default_cmd = 'search'

    def parse_args(self, ctx, args):
        if not args:
            return super().parse_args(ctx, args)
        if args[0] in self.commands:
            return super().parse_args(ctx, args)
        if args[0] in ('--help', '-h', '--version'):
            return super().parse_args(ctx, args)
        args = [self.default_cmd, *args]
        return super().parse_args(ctx, args)


@click.group(cls=DefaultGroup)
@click.version_option(version="1.0.0")
def cli():
    """Project Look - CLI tool for discovering open-source learning resources."""
    pass


@cli.command()
@click.argument('query')
@click.option('--source', '-s', type=click.Choice(['github', 'open_library']),
              help='Limit search to specific source (github or open_library)')
@click.option('--include-all', '-a', is_flag=True,
              help='Include all results, not just reputable ones')
@click.option('--refresh', '-r', is_flag=True,
              help='Force refresh from API, bypassing cache')
@click.option('--offline', '-o', is_flag=True,
              help='Use only cached data, no network requests')
@click.option('--export', '-e', type=click.Path(),
              help='Optional custom export path (file or directory); default is ./exports/<query>.pdf')
@click.option('--ignore-lang', '-i', is_flag=True,
              help='Include non-English resources (default: filter out non-English)')
def search(query: str, source: Optional[str], include_all: bool,
           refresh: bool, offline: bool, export: Optional[str], ignore_lang: bool):
    """
    Search for open-source learning resources.

    \b
    Examples:
      python main.py "data structures"
      python main.py "machine learning" --source github
      python main.py "algorithms" --include-all --export results.pdf
    """
    # Initialize components
    api_client = APIClient()
    cache_manager = CacheManager()

    try:
        # Check if we should use offline mode
        if offline:
            click.echo("Running in offline mode...")
            results = get_offline_results(cache_manager, query, source)
        else:
            # Get or create query record
            query_id = cache_manager.get_or_create_query(query)

            # Check cache first unless refresh is requested
            if not refresh:
                cached_results = cache_manager.get_cached_results(query_id, source)
                if cached_results:
                    results = cached_results
                    click.echo("Using cached results...")
                else:
                    # Fetch from API
                    results = fetch_from_api(api_client, query, source)
                    # Cache the results
                    if results:
                        cache_results_to_db(cache_manager, query_id, results, source)
            else:
                # Force refresh
                results = fetch_from_api(api_client, query, source)
                if results:
                    cache_results_to_db(cache_manager, query_id, results, source)

        # Filter results based on language if not ignoring language
        if not ignore_lang:
            results = [r for r in results if not (
                contains_cjk(r['title']) or
                contains_cjk(r.get('description', ''))
            )]

        # Filter results based on reputation if needed
        if not include_all:
            results = [r for r in results if r['reputable']]

        # Display results
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
        history_data = cache_manager.get_search_history()
        display_history(history_data)
    except Exception as e:
        click.echo(f"Error retrieving history: {str(e)}", err=True)
        sys.exit(1)
    finally:
        cache_manager.close()


def get_offline_results(cache_manager: CacheManager, query: str, source: Optional[str]) -> List[dict]:
    """Get results from offline cache."""
    # In offline mode, we need to find the query first
    cursor = cache_manager.connection.cursor()
    cursor.execute(
        "SELECT id FROM queries WHERE search_term = %s",
        (query,)
    )
    result = cursor.fetchone()
    cursor.close()

    if not result:
        click.echo(f"No cached results found for query: {query}")
        return []

    query_id = result[0]
    return cache_manager.get_cached_results(query_id, source)


def fetch_from_api(api_client: APIClient, query: str, source: Optional[str]) -> List[dict]:
    """Fetch results from APIs."""
    results = []

    if not source or source == 'github':
        try:
            github_results = api_client.search_github(query)
            for repo in github_results:
                results.append({
                    'source': 'github',
                    'title': repo['name'],
                    'description': repo.get('description', '') or '',
                    'url': repo['html_url'],
                    'reputable': repo['stargazers_count'] > 100
                })
        except Exception as e:
            click.echo(f"Warning: Could not fetch from GitHub: {str(e)}", err=True)

    if not source or source == 'open_library':
        try:
            ol_results = api_client.search_open_library(query)
            for book in ol_results:
                results.append({
                    'source': 'open_library',
                    'title': book.get('title', 'Unknown Title'),
                    'description': book.get('author_name', [''])[0] if book.get('author_name') else '',
                    'url': f"https://openlibrary.org{book.get('key', '')}",
                    'reputable': True  # Open Library books are automatically reputable
                })
        except Exception as e:
            click.echo(f"Warning: Could not fetch from Open Library: {str(e)}", err=True)

    return results


def cache_results_to_db(cache_manager: CacheManager, query_id: int, results: List[dict], source: Optional[str]):
    """Cache results to database."""
    if source:
        # Cache results for specific source
        source_results = [r for r in results if r['source'] == source]
        if source_results:
            cache_manager.cache_results(query_id, source_results, source)
    else:
        # Cache results by source
        github_results = [r for r in results if r['source'] == 'github']
        ol_results = [r for r in results if r['source'] == 'open_library']

        if github_results:
            cache_manager.cache_results(query_id, github_results, 'github')
        if ol_results:
            cache_manager.cache_results(query_id, ol_results, 'open_library')


def load_config() -> dict:
    """Load config.json from the project root."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def query_to_filename(query: str, ext: str = '.pdf') -> str:
    """Build a safe filename from a search query."""
    slug = re.sub(r'[^\w\s-]', '', query.lower())
    slug = re.sub(r'[-\s]+', '_', slug).strip('_')
    return f'{slug or "search_results"}{ext}'


def resolve_export_path(custom_export: Optional[str], query: str) -> str:
    """
    Resolve the export file path.

    Without --export: ./exports/<query>.pdf (from config default_export_path).
    With --export: use the given path as a file, or as a directory for the default filename.
    """
    config = load_config()
    default_export_dir = config.get('default_export_path', './exports')
    default_filename = query_to_filename(query)

    os.makedirs(default_export_dir, exist_ok=True)

    if not custom_export:
        return os.path.join(default_export_dir, default_filename)

    custom_export = os.path.normpath(custom_export)
    _, ext = os.path.splitext(custom_export)

    if ext.lower() in ('.pdf', '.txt'):
        parent = os.path.dirname(custom_export)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return custom_export

    os.makedirs(custom_export, exist_ok=True)
    return os.path.join(custom_export, default_filename)


def write_export(results: List[dict], query: str, export_path: str) -> None:
    """Write search results to PDF, falling back to plain text on failure."""
    export_dir = os.path.dirname(os.path.abspath(export_path)) or '.'
    os.makedirs(export_dir, exist_ok=True)

    if not results:
        click.echo(f"No results to export (directory ready: {export_dir})")
        return

    try:
        generate_pdf(results, query, export_path)
        click.echo(f"Results exported to {export_path}")
    except Exception as e:
        click.echo(f"Warning: PDF generation failed: {str(e)}", err=True)
        try:
            if export_path.lower().endswith('.pdf'):
                text_path = export_path[:-4] + '.txt'
            else:
                text_path = export_path + '.txt'
            save_as_text(results, query, text_path)
            click.echo(f"Results saved as text file: {text_path}")
        except Exception as text_e:
            click.echo(f"Warning: Text file generation also failed: {str(text_e)}", err=True)


def save_as_text(results: List[dict], query: str, output_path: str):
    """Save results as a plain text file."""
    import os
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f'Search Query: {query}\n')
        f.write(f'Total Results: {len(results)}\n')
        f.write('=' * 50 + '\n\n')

        for i, result in enumerate(results, 1):
            f.write(f'{i}. {result["title"]} ({result["source"]})\n')
            f.write(f'   Description: {result["description"]}\n')
            f.write(f'   URL: {result["url"]}\n')
            f.write(f'   Reputable: {"Yes" if result["reputable"] else "No"}\n')
            f.write('-' * 50 + '\n\n')



if __name__ == '__main__':
    cli()