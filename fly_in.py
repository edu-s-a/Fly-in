import os
import sys

from errors import FlyInError
from map_parser import MapParser
from renderer import Renderer
from simulation import Simulation
from space_time_scheduler import SpaceTimeScheduler


class Cli:
    FLAGS = {"--visual", "--no-color"}
    USAGE = "Usage: python3 fly_in.py [--visual] [--no-color] <map_file>"

    def parse_args(self, args: list[str]) -> tuple[str, set[str]] | None:
        flags = {arg for arg in args if arg.startswith("--")}
        paths = [arg for arg in args if not arg.startswith("--")]
        if len(paths) != 1 or not flags <= self.FLAGS:
            return None
        return paths[0], flags

    @staticmethod
    def want_color(flags: set[str]) -> bool:
        if "--no-color" in flags or "NO_COLOR" in os.environ:
            return False
        return "--visual" in flags or sys.stdout.isatty()

    @staticmethod
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

    def run(self, args: list[str]) -> int:
        parsed = self.parse_args(args)
        if parsed is None:
            print(self.USAGE, file=sys.stderr)
            return 2
        path, flags = parsed
        try:
            network = MapParser().parse(path)
            simulation = Simulation(network)
            plan = SpaceTimeScheduler().plan(simulation)
            results = simulation.run(plan)
            renderer = Renderer(network, self.want_color(flags))
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
            self.report(simulation)
        except FlyInError as err:
            print(f"Error: {err}", file=sys.stderr)
            return 1
        except Exception as err:
            print(f"Unexpected error: {err}", file=sys.stderr)
            return 1
        return 0


def main() -> int:
    return Cli().run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
