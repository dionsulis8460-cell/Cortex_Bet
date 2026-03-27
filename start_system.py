"""Compatibility wrapper for the consolidated stack entrypoint."""

from scripts.system_entrypoint import run_system_stack


def main() -> None:
    """Run the official local stack using the consolidated system entrypoint."""
    run_system_stack()

if __name__ == "__main__":
    main()
