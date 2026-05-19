# Collect Resources - CLI Tool for Open-Source Learning Resources

A command-line interface (CLI) application that aggregates, caches, and exports high-quality open-source learning resources (books, projects, and courses) from GitHub and Open Library.

## Features

- **Multi-Source Search**: Search across GitHub repositories and Open Library books
- **Intelligent Caching**: Local caching for offline use and reduced API calls
- **Smart Filtering**: Automatic reputation scoring based on GitHub stars
- **Error Handling**: Graceful handling of API failures and rate limits
- **Interactive Recovery**: Prompt for retry/switch/abort when sources fail
- **Export Functionality**: Generate PDF reports with clickable links
- **History Tracking**: Browse previous searches

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Apil120/collect-resources.git
   cd collect-resources
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. (Optional) Get a GitHub Personal Access Token for higher rate limits:
   - Go to GitHub Settings → Developer settings → Personal Access Tokens
   - Generate a token with `public_repo` scope
   - Add it to `config.json` or set the `GITHUB_TOKEN` environment variable

## Usage

Run commands from the `collect-resources` directory (where `main.py` lives). Search is the default command, so you can pass a query directly without typing `search`.

### Global options

| Flag | Short | Description |
|------|-------|-------------|
| `--help` | | Show help for the CLI or a subcommand |
| `--version` | | Show the application version (1.0.0) |

```bash
python main.py --help
python main.py --version
python main.py search --help
```

### Search flags

Use these with a search query: `python main.py "<search term>" [flags]`

| Flag | Short | Description |
|------|-------|-------------|
| `--source` | `-s` | Limit search to one source: `github` or `open_library` |
| `--include-all` | `-a` | Include all results, not only reputable ones (GitHub: ≤100 stars) |
| `--refresh` | `-r` | Force a fresh API fetch and bypass the cache |
| `--offline` | `-o` | Use only cached data; no network requests |
| `--export` | `-e` | Optional custom export path (file or directory); every search also writes to `./exports` by default |
| `--ignore-lang` | `-i` | Include non-English resources (default: CJK titles/descriptions are filtered out) |

The search term is a required positional argument (quote phrases with spaces).

### Commands

| Command | Description |
|---------|-------------|
| *(default)* / `search` | Search for learning resources |
| `history` | Show previous searches stored in the local cache |

### Basic search

```bash
# Search all sources (default)
python main.py "data structures"

# Same as above, with explicit subcommand
python main.py search "data structures"

# Search a specific source
python main.py "machine learning" --source github
python main.py "algorithms" -s open_library

# Include all results (including non-reputable)
python main.py "algorithms" --include-all
python main.py "algorithms" -a

# Force refresh from API (bypass cache)
python main.py "react" --refresh
python main.py "react" -r

# Offline mode (cached data only)
python main.py "python" --offline
python main.py "python" -o

# Include non-English resources
python main.py "数据结构" --ignore-lang
python main.py "数据结构" -i
```

### Export results

Every search automatically exports results to `./exports/<query>.pdf` (or `.txt` if PDF generation fails). The `exports/` directory is always created.

```bash
# Default export: ./exports/data_structures.pdf
python main.py "data structures"

# Custom file path
python main.py "machine learning" --export ../reports/ml.pdf

# Custom directory (uses default filename derived from the query)
python main.py "algorithms" --export ./my-reports/
```

### View history

```bash
python main.py history
```

## Configuration

Create or edit `config.json` in the project root:

```json
{
  "github_token": "your_github_token_here",
  "default_export_path": "./exports",
  "cache_duration_hours": 24
}
```

## Project Structure

```
project_look/
├── core/
│   ├── __init__.py
│   ├── api_client.py          # API client for GitHub and Open Library
│   └── cache_manager.py       # SQLite cache management
├── cli/
│   ├── __init__.py
│   ├── commands.py            # Main CLI commands
│   └── display.py             # Output formatting
├── utils/
│   └── pdf_engine.py          # PDF generation
├── config.json                # User configuration
├── main.py                    # Application entry point
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## API Rate Limits

- GitHub API: Unauthenticated requests are limited to 60 requests per hour
- With a GitHub Personal Access Token: 5,000 requests per hour
- Open Library API: No known rate limits for basic usage

The application automatically falls back to cached data when rate limits are exceeded.

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request