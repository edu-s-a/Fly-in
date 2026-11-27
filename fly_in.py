#!/usr/bin/env python3
"""Command-line interface for parsing, scheduling, and running fly-in maps."""

import os
import sys

from errors import FlyInError
from map_parser import MapParser
from renderer import Renderer
from simulation import Simulation, TurnResult
from space_time_scheduler import SpaceTimeScheduler


class Cli:
    """Parse command-line arguments and run a fly-in simulation."""

    FLAGS = {"--visual", "--no-color", "--capacity-info", "--stats"}
    USAGE = (
        "Usage: python3 fly_in.py [--visual] [--no-color] "
        "[--capacity-info] [--stats] <map_file>"
    )

    def __init__(self, args: list[str]) -> None:
        """Initialize the CLI with command-line arguments.

        Args:
            args: Command-line arguments, excluding the program name.
        """
        self._flags: set[str] = {a for a in args if a.startswith("--")}
        self._paths: list[str] = [a for a in args if not a.startswith("--")]

    @property
    def valid(self) -> bool:
        """Check whether the CLI arguments are valid.

        Returns:
            True when exactly one map path is provided and all flags are known;
            otherwise False.
        """
        return len(self._paths) == 1 and self._flags <= self.FLAGS

    def _want_color(self) -> bool:
        """Determine whether colored output should be enabled.

        Returns:
            True when color output is enabled; otherwise False.
        """
        if "--no-color" in self._flags or "NO_COLOR" in os.environ:
            return False
        return "--visual" in self._flags or sys.stdout.isatty()

    def _show(self, renderer: Renderer, results: list[TurnResult]) -> None:
        """Render the simulation turn results.

        Args:
            renderer: Renderer used to format output.
            results: Turn results produced by the simulation.
        """
        visual = "--visual" in self._flags
        info = "--capacity-info" in self._flags
        if visual:
            print(renderer.legend())
            print()
        for result in results:
            print(renderer.frame(result) if visual else renderer.line(result))
            if info:
                for text in renderer.capacity_lines(result):
                    print(text)
            if visual:
                print()

    @staticmethod
    def report(simulation: Simulation) -> None:
        """Print summary statistics for a completed simulation.

        Args:
            simulation: Completed simulation whose statistics will be reported.
        """
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

    def run(self) -> int:
        """Run the command-line workflow and return a process exit code.

        Returns:
            Zero on success, one for simulation or runtime errors, or two for
            invalid command-line arguments.
        """
        if not self.valid:
            print(self.USAGE, file=sys.stderr)
            return 2
        try:
            network = MapParser().parse(self._paths[0])
            simulation = Simulation(network)
            plan = SpaceTimeScheduler().plan(simulation)
            results = simulation.run(plan)
            self._show(Renderer(network, self._want_color()), results)
            sys.stdout.flush()
            if "--stats" in self._flags:
                self.report(simulation)
        except FlyInError as err:
            print(f"Error: {err}", file=sys.stderr)
            return 1
        except Exception as err:
            print(f"Unexpected error: {err}", file=sys.stderr)
            return 1
        return 0


def main() -> int:
    """Serve as the program entry point.

    Returns:
        The exit code returned by the CLI.
    """
    return Cli(sys.argv[1:]).run()


if __name__ == "__main__":
    sys.exit(main())
