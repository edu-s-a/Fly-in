"""Execute drone movement plans and report turn-by-turn simulation results."""

from dataclasses import dataclass, field

from drone import Drone
from errors import SimulationError
from move import Move
from network import Network
from zone import Connection, Zone, ZoneRole


@dataclass(frozen=True)
class TurnResult:
    """Store the state snapshot and usage information for one turn.

    Attributes:
        turn: One-based simulation turn number.
        tokens: Compact textual representations of drone positions.
        zone_usage: Zone names mapped to used and available capacities.
        link_usage: Connection names mapped to used and total capacities.
    """

    turn: int
    tokens: tuple[str, ...]
    zone_usage: dict[str, tuple[int, int | None]] = field(
        default_factory=dict, compare=False
    )
    link_usage: dict[str, tuple[int, int]] = field(
        default_factory=dict, compare=False
    )

    @property
    def line(self) -> str:
        """Return the turn's compact representation as a line.

        Returns:
            Space-separated position tokens.
        """
        return " ".join(self.tokens)


class Simulation:
    """Manage drones and execute a movement plan against a network."""

    def __init__(self, network: Network) -> None:
        """Initialize a simulation for a network.

        Args:
            network: Network and drone count used to build the simulation.
        """
        self._network = network
        self._drones: tuple[Drone, ...] = tuple(
            Drone(number, network.start)
            for number in range(1, network.nb_drones + 1)
        )
        self._turn: int = 0
        self._results: list[TurnResult] = []
        self._total_cost: int = 0

    @property
    def network(self) -> Network:
        """Return the simulated network.

        Returns:
            Network used by this simulation.
        """
        return self._network

    @property
    def drones(self) -> tuple[Drone, ...]:
        """Return all drones in the simulation.

        Returns:
            Ordered tuple of drones.
        """
        return self._drones

    @property
    def turns(self) -> int:
        """Return the number of completed turns.

        Returns:
            Current turn count.
        """
        return self._turn

    @property
    def results(self) -> tuple[TurnResult, ...]:
        """Return snapshots for all completed turns.

        Returns:
            Ordered tuple of turn results.
        """
        return tuple(self._results)

    @property
    def finished(self) -> bool:
        """Check whether every drone has been delivered.

        Returns:
            True if all drones have finished; otherwise False.
        """
        return all(drone.delivered for drone in self._drones)

    @property
    def total_cost(self) -> int:
        """Return the total movement cost incurred.

        Returns:
            Sum of movement costs from completed turns.
        """
        return self._total_cost

    @property
    def drones_moved_per_turn(self) -> list[int]:
        """Return the number of position tokens generated in each turn.

        Returns:
            Drone movement counts ordered by turn.
        """
        return [len(result.tokens) for result in self._results]

    @property
    def delivery_turns(self) -> list[int]:
        """Return delivery turns for delivered drones.

        Returns:
            Ordered list of available delivery turn numbers.
        """
        turns: list[int] = []
        for drone in self._drones:
            turn = drone.delivered_turn
            if turn is not None:
                turns.append(turn)
        return turns

    @property
    def average_turns_per_drone(self) -> float:
        """Return the average delivery turn across delivered drones.

        Returns:
            Mean delivery turn, or 0.0 if no drone has been delivered.
        """
        turns = self.delivery_turns
        if not turns:
            return 0.0
        return sum(turns) / len(turns)

    def run(self, plan: list[list[Move]]) -> list[TurnResult]:
        """Execute a complete movement plan.

        Args:
            plan: Movement lists ordered by turn.

        Returns:
            Turn results produced by the plan.

        Raises:
            SimulationError: If the plan leaves drones undelivered.
        """
        results = [self.step(moves) for moves in plan]
        if not self.finished:
            left = sum(1 for d in self._drones if not d.delivered)
            raise SimulationError(
                f"plan ended with {left} drone(s) not delivered"
            )
        return results

    def step(self, moves: list[Move]) -> TurnResult:
        """Validate and apply one turn of a movement plan.

        Args:
            moves: Moves to apply during this turn.

        Returns:
            Snapshot describing the completed turn.

        Raises:
            SimulationError: If the simulation is finished or the turn is
                invalid.
        """
        if self.finished:
            raise SimulationError("simulation already finished")
        forced = [drone for drone in self._drones if drone.in_transit]
        if not moves and not forced:
            raise SimulationError("deadlock: no drone can move")
        self._check_moves(moves)
        instant = [move for move in moves if move.cost == 1]
        slow = [move for move in moves if move.cost == 2]
        self._check_zone_capacity(moves, instant, forced)
        links = self._check_link_capacity(moves, forced)
        return self._apply(instant, slow, forced, links)

    def _owns(self, drone: Drone) -> bool:
        """Check whether a drone belongs to this simulation.

        Args:
            drone: Drone to verify.

        Returns:
            True if the drone belongs to this simulation.
        """
        index = drone.id - 1
        return 0 <= index < len(self._drones) and (
            self._drones[index] is drone
        )

    def _check_moves(self, moves: list[Move]) -> None:
        """Validate all proposed moves for ownership, routing, and state.

        Args:
            moves: Proposed moves to validate.

        Raises:
            SimulationError: If a move is invalid or duplicates a drone turn.
        """
        seen: set[int] = set()
        for move in moves:
            drone = move.drone
            if not self._owns(drone):
                raise SimulationError(
                    f"{drone.name} does not belong to this simulation"
                )
            if drone.delivered:
                raise SimulationError(
                    f"{drone.name} has already been delivered"
                )
            if drone.in_transit:
                raise SimulationError(
                    f"{drone.name} is in transit and cannot be moved"
                )
            if drone.id in seen:
                raise SimulationError(
                    f"{drone.name} moves more than once in a turn"
                )
            seen.add(drone.id)
            source = drone.zone
            link = move.connection
            dest = move.destination
            if link not in self._network.connections_of(source):
                raise SimulationError(
                    f"{drone.name} is not at an endpoint of "
                    f"connection '{link.name}'"
                )
            if link.other(source).name != dest.name:
                raise SimulationError(
                    f"connection '{link.name}' does not lead to "
                    f"'{dest.name}'"
                )
            if not dest.is_passable:
                raise SimulationError(f"zone '{dest.name}' is blocked")
            if move.cost not in (1, 2):
                raise SimulationError(
                    f"unsupported movement cost {move.cost}"
                )

    def _check_zone_capacity(
        self, moves: list[Move], instant: list[Move], forced: list[Drone]
    ) -> None:
        """Validate predicted zone occupancy for the current turn.

        Args:
            moves: All departing moves.
            instant: Moves that arrive immediately.
            forced: Drones that remain in transit.

        Raises:
            SimulationError: If a zone exceeds its capacity.
        """
        count: dict[str, int] = {}
        for drone in self._drones:
            if drone.idle:
                name = drone.zone.name
                count[name] = count.get(name, 0) + 1
        for move in moves:
            count[move.drone.zone.name] -= 1
        for move in instant:
            name = move.destination.name
            count[name] = count.get(name, 0) + 1
        for drone in forced:
            name = drone.destination.name
            count[name] = count.get(name, 0) + 1
        for name, occupants in count.items():
            capacity = self._network.get_zone(name).capacity
            if capacity is not None and occupants > capacity:
                raise SimulationError(
                    f"zone '{name}' over capacity ({occupants}/{capacity})"
                )

    def _check_link_capacity(
        self, moves: list[Move], forced: list[Drone]
    ) -> dict[str, tuple[int, int]]:
        """Validate and summarize connection usage for the current turn.

        Args:
            moves: Departing moves.
            forced: Drones already traveling.

        Returns:
            Connection names mapped to current usage and capacity.

        Raises:
            SimulationError: If a connection exceeds its capacity.
        """
        links = [move.connection for move in moves]
        links += [drone.connection for drone in forced]
        usage: dict[frozenset[str], int] = {}
        seen: dict[frozenset[str], Connection] = {}
        for link in links:
            key = frozenset((link.zone_1.name, link.zone_2.name))
            usage[key] = usage.get(key, 0) + 1
            seen[key] = link
        report: dict[str, tuple[int, int]] = {}
        for key, used in usage.items():
            link = seen[key]
            if used > link.max_link_capacity:
                raise SimulationError(
                    f"connection '{link.name}' over capacity "
                    f"({used}/{link.max_link_capacity})"
                )
            report[link.name] = (used, link.max_link_capacity)
        return report

    def _zone_usage(self) -> dict[str, tuple[int, int | None]]:
        """Build a report of drones currently occupying each zone.

        Returns:
            Mapping of occupied zone names to usage and capacity.
        """
        count: dict[str, int] = {}
        for drone in self._drones:
            if not drone.in_transit:
                name = drone.zone.name
                count[name] = count.get(name, 0) + 1
        usage: dict[str, tuple[int, int | None]] = {}
        for zone in self._network.zones:
            if zone.name in count:
                usage[zone.name] = (count[zone.name], zone.capacity)
        return usage

    def _apply(
        self,
        instant: list[Move],
        slow: list[Move],
        forced: list[Drone],
        links: dict[str, tuple[int, int]],
    ) -> TurnResult:
        """Apply validated moves and create the turn result.

        Args:
            instant: Moves that arrive this turn.
            slow: Moves that begin in transit this turn.
            forced: Drones that arrive after prior slow moves.
            links: Connection usage report for this turn.

        Returns:
            Turn snapshot created after applying all moves.
        """
        turn = self._turn + 1
        entries: list[tuple[int, str]] = []
        for drone in forced:
            dest = drone.destination
            drone.arrive(dest)
            self._deliver_if_end(drone, dest, turn)
            entries.append((drone.id, f"{drone.name}-{dest.name}"))
        for move in instant:
            move.drone.arrive(move.destination)
            self._deliver_if_end(move.drone, move.destination, turn)
            entries.append(
                (move.drone.id, f"{move.drone.name}-{move.destination.name}")
            )
        for move in slow:
            move.drone.depart(move.connection, move.destination)
            entries.append(
                (move.drone.id, f"{move.drone.name}-{move.connection.name}")
            )
        entries.sort()
        self._total_cost += sum(move.cost for move in instant + slow)
        self._turn = turn
        result = TurnResult(
            turn,
            tuple(token for _, token in entries),
            self._zone_usage(),
            links,
        )
        self._results.append(result)
        return result

    @staticmethod
    def _deliver_if_end(drone: Drone, zone: Zone, turn: int) -> None:
        """Mark a drone delivered if it arrives at the end zone.

        Args:
            drone: Drone that arrived.
            zone: Zone reached by the drone.
            turn: Current turn number.
        """
        if zone.role is ZoneRole.END:
            drone.deliver(turn)
