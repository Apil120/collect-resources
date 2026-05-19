"""
Cache manager module for Project Look.
Handles MySQL connection pooling, schema generation, and query filtering.
"""

import json
import mysql.connector
from mysql.connector import Error
from typing import List,  Optional, Dict, Any


class CacheManager:
    """Manages local MySQL cache for search results."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.connection = None
        self._load_config()
        self._init_db()

    def _load_config(self):
        """Load database configuration from config.json."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            mysql_config = config.get('mysql', {})
            self.db_config = {
                'host': mysql_config.get('host', 'localhost'),
                'port': mysql_config.get('port', 3306),
                'user': mysql_config.get('user', 'root'),
                'password': mysql_config.get('password', ''),
                'database': mysql_config.get('database', 'project_look'),
                'autocommit': True
            }
        except FileNotFoundError:
            # Default configuration if config.json not found
            self.db_config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': 'root',
                'database': 'project_look',
                'autocommit': True
            }
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file: {self.config_path}")

    def _init_db(self):
        """Initialize the database with required tables."""

        try:
            self.connection = mysql.connector.connect(**self.db_config)
            cursor = self.connection.cursor()

            # Create queries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    search_term VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create resources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    query_id INT,
                    source VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    url VARCHAR(512) NOT NULL,
                    reputable BOOLEAN NOT NULL,
                    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
                )
            """)

            # Align older schemas that used shorter column types
            cursor.execute(
                "ALTER TABLE resources MODIFY description TEXT"
            )

            self.connection.commit()
            cursor.close()
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def get_or_create_query(self, search_term: str) -> int:
        """
        Get or create a query record and return its ID.

        Args:
            search_term: The search term to look up or create

        Returns:
            The query ID
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM queries WHERE search_term = %s",
            (search_term,)
        )
        result = cursor.fetchone()

        if result:
            query_id = result[0]
            cursor.close()
            return query_id
        else:
            cursor.execute(
                "INSERT INTO queries (search_term) VALUES (%s)",
                (search_term,)
            )
            self.connection.commit()
            query_id = cursor.lastrowid
            cursor.close()
            return query_id

    def get_cached_results(self, query_id: int, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get cached results for a query.

        Args:
            query_id: The query ID
            source: Optional source filter ('github' or 'open_library')

        Returns:
            List of resource dictionaries
        """
        cursor = self.connection.cursor()
        if source:
            cursor.execute(
                """
                SELECT source, title, description, url, reputable
                FROM resources
                WHERE query_id = %s AND source = %s
                """,
                (query_id, source)
            )
        else:
            cursor.execute(
                """
                SELECT source, title, description, url, reputable
                FROM resources
                WHERE query_id = %s
                """,
                (query_id,)
            )

        results = []
        for row in cursor.fetchall():
            results.append({
                'source': row[0],
                'title': row[1],
                'description': row[2] or '',
                'url': row[3],
                'reputable': bool(row[4])
            })
        cursor.close()
        return results

    def cache_results(self, query_id: int, results: List[Dict[str, Any]], source: str):
        """
        Cache results for a query.

        Args:
            query_id: The query ID
            results: List of resource dictionaries to cache
            source: Source of the results ('github' or 'open_library')
        """
        cursor = self.connection.cursor()
        # Clear existing results for this query and source
        cursor.execute(
            "DELETE FROM resources WHERE query_id = %s AND source = %s",
            (query_id, source)
        )

        # Insert new results
        for result in results:
            title = (result['title'] or '')[:255]
            description = (result.get('description') or '')[:65535]
            url = (result['url'] or '')[:512]
            cursor.execute(
                """
                INSERT INTO resources (query_id, source, title, description, url, reputable)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    query_id,
                    source,
                    title,
                    description,
                    url,
                    result['reputable']
                )
            )

        self.connection.commit()
        cursor.close()

    def get_search_history(self) -> List[Dict[str, Any]]:
        """
        Get search history with source information and result counts.

        Returns:
            List of search history entries
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT
                q.search_term,
                q.created_at,
                GROUP_CONCAT(DISTINCT r.source) as sources,
                COUNT(r.id) as total_results
            FROM queries q
            LEFT JOIN resources r ON q.id = r.query_id
            GROUP BY q.id
            ORDER BY q.created_at DESC
            """
        )

        history = []
        for row in cursor.fetchall():
            history.append({
                'search_term': row[0],
                'created_at': row[1],
                'sources': row[2] or '',
                'total_results': row[3]
            })
        cursor.close()
        return history

    def clear_cache(self):
        """Clear all cached data."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM resources")
        cursor.execute("DELETE FROM queries")
        self.connection.commit()
        cursor.close()

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()