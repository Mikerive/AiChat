"""
Training CLI entry point
"""

from argparse import Namespace
import sys


def main(args: Namespace = None):
    """Start the training pipeline"""
    if args is None:
        # Default arguments for standalone execution
        class Args:
            mode = "serve"

        args = Args()

    print(f"Starting AI Chat Training Pipeline in {args.mode} mode")

    try:
        # Import the training main function - will need to update this path after migration
        if args.mode == "serve":
            from aichat.training.main import main as training_main
        else:
            print(f"Training mode '{args.mode}' not implemented yet")
            return 1

        return training_main()
    except ImportError as e:
        print(f"Error importing training: {e}")
        print("Training modules may not be migrated yet.")
        return 1
    except Exception as e:
        print(f"Error starting training: {e}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["ingest", "train", "serve"],
        default="serve",
        help="Training mode",
    )
    args = parser.parse_args()

    sys.exit(main(args))
