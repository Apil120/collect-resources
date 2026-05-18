"""
Main entry point for Project Look application.
"""

import sys
from cli.commands import cli

def main():
    """Entry point for the application."""
    try:
        cli()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        # raise e
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()