"""
CLI commands module for Project Look.
Main Click setup defining interface entry points and interactive hooks.
"""

import click
import sys
import re
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


@click.group()
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
              help='Export results to PDF at specified path')
@click.option('--ignore-lang', '-i', is_flag=True,
              help='Include non-English resources (default: filter out non-English)')
def search(query: str, source: Optional[str], include_all: bool,
           refresh: bool, offline: bool, export: Optional[str], ignore_lang: bool):
    """
    Search for open-source learning resources.

    \b
    Examples:
      look "data structures"
      look "machine learning" --source github
      look "algorithms" --include-all --export results.pdf
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

        # Export to PDF if requested
        if export:
            try:
                generate_pdf(results, query, export)
                click.echo(f"Results exported to {export}")
            except Exception as e:
                click.echo(f"Warning: PDF generation failed: {str(e)}", err=True)
                # Fallback to text file
                if export.lower().endswith('.pdf'):
                    text_path = export[:-4] + '.txt'
                else:
                    text_path = export + '.txt'
                save_as_text(results, query, text_path)
                click.echo(f"Results saved as text file: {text_path}")

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