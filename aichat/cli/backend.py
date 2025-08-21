"""
Backend CLI entry point
"""

import uvicorn
from argparse import Namespace
import sys


def main(args: Namespace = None):
    """Start the backend API server"""
    if args is None:
        # Default arguments for standalone execution
        class Args:
            host = "localhost"
            port = 8765
            reload = False

        args = Args()

    print(f"Starting AI Chat Backend API on {args.host}:{args.port}")

    try:
        # Import the create_app function - will need to update this path after migration
        from aichat.backend.main import create_app

        app = create_app()

        uvicorn.run(
            app, host=args.host, port=args.port, reload=args.reload, log_level="info"
        )
    except ImportError as e:
        print(f"Error importing backend: {e}")
        print("Backend modules may not be migrated yet.")
        return 1
    except Exception as e:
        print(f"Error starting backend: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    sys.exit(main(args))
