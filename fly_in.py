import os
import sys

from errors import FlyInError
from map_parser import MapParser
from renderer import Renderer
from simulation import Simulation
from space_time_scheduler import SpaceTimeScheduler

USAGE = "Usage: python3 fly_in.py [--visual] [--no-color] <map_file>"
FLAGS = {"--visual", "--no-color"}


def parse_args(args: list[str]) -> tuple[str, set[str]] | None:
    flags = {arg for arg in args if arg.startswith("--")}
    paths = [arg for arg in args if not arg.startswith("--")]
    if len(paths) != 1 or not flags <= FLAGS:
        return None
    return paths[0], flags


def want_color(flags: set[str]) -> bool:
    if "--no-color" in flags or "NO_COLOR" in os.environ:
        return False
    return "--visual" in flags or sys.stdout.isatty()


def report(simulation: Simulation) -> None:
    print(f"turns: {simulation.turns}", file=sys.stderr)
    print(
        f"drones moved per turn: {simulation.drones_moved_per_turn}",
        file=sys.stderr,
    )
    print(
        f"average turns per drone: "
        f"{simulation.average_turns_per_drone:.2f}",
        file=sys.stderr,
    )
    print(f"total path cost: {simulation.total_cost}", file=sys.stderr)


def main() -> int:
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return 2
    path, flags = parsed
    try:
        network = MapParser().parse(path)
        simulation = Simulation(network)
        plan = SpaceTimeScheduler().plan(simulation)
        results = simulation.run(plan)
        renderer = Renderer(network, want_color(flags))
        if "--visual" in flags:
            print(renderer.legend())
            print()
            for result in results:
                print(renderer.frame(result))
                print()
        else:
            for result in results:
                print(renderer.line(result))
        sys.stdout.flush()
        report(simulation)
    except FlyInError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"Unexpected error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
