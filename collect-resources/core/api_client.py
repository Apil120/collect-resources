"""
API client module for Project Look.
Handles requests to GitHub and Open Library APIs with structured User-Agents and token support.
"""

import requests
from typing import Dict, List, Optional, Any


class APIClient:
    """Handles API requests to GitHub and Open Library."""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.session = requests.Session()
        # Set common headers
        self.session.headers.update({
            'User-Agent': 'ProjectLook/1.0 (https://github.com/project-look)',
            'Accept': 'application/json'
        })

        # Add GitHub token if provided
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}'
            })

    def search_github(self, query: str) -> List[Dict[str, Any]]:
        """
        Search GitHub repositories.

        Args:
            query: Search query string

        Returns:
            List of repository data dictionaries
        """
        url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 30
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('items', [])
        except requests.RequestException as e:
            raise Exception(f"GitHub API error: {str(e)}")

    def search_open_library(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Open Library for books.

        Args:
            query: Search query string

        Returns:
            List of book data dictionaries
        """
        url = "https://openlibrary.org/search.json"
        params = {
            'q': query,
            'limit': 30
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('docs', [])
        except requests.RequestException as e:
            raise Exception(f"Open Library API error: {str(e)}")

    def close(self):
        """Close the session."""
        self.session.close()