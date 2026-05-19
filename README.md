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

### Basic Search
```bash
# Search all sources (default)
look "data structures"

# Search specific source
look "machine learning" --source github

# Include all results (including non-reputable)
look "algorithms" --include-all

# Force refresh from API (bypass cache)
look "react" --refresh

# Offline mode (use cached data only)
look "python" --offline
```

### Export Results
```bash
# Export to PDF
look "data structures" --export ./data_structures.pdf

# Export with specific options
look "machine learning" --source github --export ./ml_github.pdf
```

### View History
```bash
# Show search history
look --history
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
