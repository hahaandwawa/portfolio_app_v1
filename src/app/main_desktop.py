#!/usr/bin/env python3
"""Desktop application entry point.

This is the main entry point for the local desktop application.
Run with: python -m app.main_desktop
"""

import sys
import logging

from app.config.logging_config import setup_logging


def main() -> None:
    """Launch the desktop application."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Investment Management App (Desktop)")

    try:
        # Import and run desktop app
        from app.ui.app import DesktopApp

        app = DesktopApp()
        app.run()

    except ImportError as e:
        # Handle missing dependencies
        logger.error(f"Missing dependency: {e}")
        print(f"\nError: Missing required dependency.")
        print(f"Please ensure all dependencies are installed:")
        print(f"  pip install -e '.[desktop]'\n")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Application error: {e}")
        print(f"\nApplication error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
