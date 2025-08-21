"""
Frontend CLI entry point
"""

from argparse import Namespace
import sys


def main(args: Namespace = None):
    """Start the GUI frontend"""
    print("Starting AI Chat GUI Frontend")

    try:
        # Import the GUI main function - will need to update this path after migration
        from aichat.frontend.gui import main as gui_main

        return gui_main()
    except ImportError as e:
        print(f"Error importing frontend: {e}")
        print("Frontend modules may not be migrated yet.")
        return 1
    except Exception as e:
        print(f"Error starting frontend: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
