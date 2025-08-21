"""
Main CLI entry point
"""

import sys
import argparse
from typing import Optional


def main(argv: Optional[list] = None):
    """Main CLI entry point"""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="aichat",
        description="AI Chat - AI-powered chat application with voice cloning",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backend command
    backend_parser = subparsers.add_parser("backend", help="Start backend API server")
    backend_parser.add_argument("--host", default="localhost", help="Host to bind to")
    backend_parser.add_argument(
        "--port", type=int, default=8765, help="Port to bind to"
    )
    backend_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload"
    )

    # Frontend command
    frontend_parser = subparsers.add_parser("frontend", help="Start GUI frontend")

    # Training command
    training_parser = subparsers.add_parser("training", help="Start training pipeline")
    training_parser.add_argument(
        "--mode", choices=["ingest", "train", "serve"], help="Training mode"
    )

    args = parser.parse_args(argv)

    if args.command == "backend":
        from .backend import main as backend_main

        return backend_main(args)
    elif args.command == "frontend":
        from .frontend import main as frontend_main

        return frontend_main(args)
    elif args.command == "training":
        from .training import main as training_main

        return training_main(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
