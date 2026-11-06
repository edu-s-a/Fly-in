import sys

from errors import FlyInError
from parser import MapParser


def main() -> int:
    """Run the program and return the exit status."""
    if len(sys.argv) != 2:
        print("Usage: python3 fly_in.py <map_file>", file=sys.stderr)
        return 2
    try:
        network = MapParser().parse(sys.argv[1])
        # simulation goes here
    except FlyInError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"Unexpected error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
