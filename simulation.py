from dataclasses import dataclass

from drone import Drone
from errors import SimulationError
from move import Move
from network import Network
from zone import Connection, Zone, ZoneRole


@dataclass(frozen=True)
class TurnResult:
    turn: int
    tokens: tuple[str, ...]

    @property
    def line(self) -> str:
        return " ".join(self.tokens)


class Simulation:

    def __init__(self, network: Network) -> None:
        self._network = network
        self._drones: tuple[Drone, ...] = tuple(
            Drone(number, network.start)
            for number in range(1, network.nb_drones + 1)
        )
        self._turn: int = 0
        self._results: list[TurnResult] = []
        self._total_cost: int = 0

    @property
    def drones(self) -> tuple[Drone, ...]:
        return self._drones

    @property
    def turns(self) -> int:
        return self._turn

    @property
    def results(self) -> tuple[TurnResult, ...]:
        return tuple(self._results)

    @property
    def finished(self) -> bool:
        return all(drone.delivered for drone in self._drones)

    @property
    def total_cost(self) -> int:
        return self._total_cost

    @property
    def drones_moved_per_turn(self) -> list[int]:
        return [len(result.tokens) for result in self._results]

    @property
    def delivery_turns(self) -> list[int]:
        turns: list[int] = []
        for drone in self._drones:
            turn = drone.delivered_turn
            if turn is not None:
                turns.append(turn)
        return turns

    @property
    def average_turns_per_drone(self) -> float:
        turns = self.delivery_turns
        if not turns:
            return 0.0
        return sum(turns) / len(turns)

    def run(self, plan: list[list[Move]]) -> list[TurnResult]:
        results = [self.step(moves) for moves in plan]
        if not self.finished:
            left = sum(1 for d in self._drones if not d.delivered)
            raise SimulationError(
                f"plan ended with {left} drone(s) not delivered"
            )
        return results

    def step(self, moves: list[Move]) -> TurnResult:
        if self.finished:
            raise SimulationError("simulation already finished")
        forced = [drone for drone in self._drones if drone.in_transit]
        if not moves and not forced:
            raise SimulationError("deadlock: no drone can move")
        self._check_moves(moves)
        instant = [move for move in moves if move.cost == 1]
        slow = [move for move in moves if move.cost == 2]
        self._check_zone_capacity(moves, instant, forced)
        self._check_link_capacity(moves, forced)
        return self._apply(instant, slow, forced)

    def _owns(self, drone: Drone) -> bool:
        index = drone.id - 1
        return 0 <= index < len(self._drones) and (
            self._drones[index] is drone
        )

    def _check_moves(self, moves: list[Move]) -> None:
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
    ) -> None:
        links = [move.connection for move in moves]
        links += [drone.connection for drone in forced]
        usage: dict[frozenset[str], int] = {}
        seen: dict[frozenset[str], Connection] = {}
        for link in links:
            key = frozenset((link.zone_1.name, link.zone_2.name))
            usage[key] = usage.get(key, 0) + 1
            seen[key] = link
        for key, used in usage.items():
            link = seen[key]
            if used > link.max_link_capacity:
                raise SimulationError(
                    f"connection '{link.name}' over capacity "
                    f"({used}/{link.max_link_capacity})"
                )

    def _apply(
        self, instant: list[Move], slow: list[Move], forced: list[Drone]
    ) -> TurnResult:
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
        result = TurnResult(turn, tuple(token for _, token in entries))
        self._results.append(result)
        return result

    @staticmethod
    def _deliver_if_end(drone: Drone, zone: Zone, turn: int) -> None:
        if zone.role is ZoneRole.END:
            drone.deliver(turn)

    @property
    def network(self) -> Network:
        return self._network
