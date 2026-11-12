import heapq
import itertools
import zlib
from dataclasses import dataclass

from errors import SimulationError
from move import Move
from network import Network
from pathfinder import Pathfinder
from reservation import ReservationTable
from scheduler import Scheduler
from simulation import Simulation
from zone import Connection, Zone, ZoneType

State = tuple[str, int]
Rank = tuple[int, int]


@dataclass(frozen=True)
class Step:
    zone: Zone
    link: Connection
    depart: int
    arrive: int


Successor = tuple[Zone, int, Step | None]
Turn = list[tuple[int, Step]]


class SpaceTimeScheduler(Scheduler):

    BASE_MODES = 3

    def __init__(self, restarts: int = 40) -> None:
        self._restarts = restarts

    def plan(self, simulation: Simulation) -> list[list[Move]]:
        network = simulation.network
        drones = simulation.drones
        finder = Pathfinder(network)
        baseline = finder.find_path(network.start, network.end)
        dist = finder.distances_to(network.end)
        horizon = len(drones) * baseline.cost
        bound = self._lower_bound(network, len(drones), baseline.cost)
        best_turns: list[Turn] | None = None
        best_score: tuple[int, int] | None = None
        for mode in range(self.BASE_MODES + self._restarts):
            routes = self._solve(network, len(drones), dist, horizon, mode)
            turns = self._turns(routes)
            score = (len(turns), sum(r[-1].arrive for r in routes))
            if best_score is None or score < best_score:
                best_score = score
                best_turns = turns
            if best_score[0] <= bound:
                break
        if best_turns is None:
            raise SimulationError("no schedule found")
        return [self._moves(simulation, turn) for turn in best_turns]

    @staticmethod
    def _lower_bound(network: Network, count: int, cost: int) -> int:
        leaving = sum(
            link.max_link_capacity
            for _, link in network.neighbors(network.start)
        )
        arriving = sum(
            link.max_link_capacity
            for _, link in network.neighbors(network.end)
        )
        rate = max(1, min(leaving, arriving))
        return -(-count // rate) + cost - 1

    @staticmethod
    def _moves(simulation: Simulation, turn: Turn) -> list[Move]:
        drones = simulation.drones
        return [
            Move(drones[index], step.zone, step.link)
            for index, step in turn
        ]

    def _solve(
        self,
        network: Network,
        count: int,
        dist: dict[str, int],
        horizon: int,
        mode: int,
    ) -> list[list[Step]]:
        table = ReservationTable()
        routes: list[list[Step]] = []
        for _ in range(count):
            steps = self._search(network, table, dist, horizon, mode)
            self._reserve(table, steps)
            routes.append(steps)
        return routes

    @staticmethod
    def _increment(mode: int, zone: Zone | None) -> Rank:
        if zone is None:
            waits, plain = 1, 0
        else:
            waits = 0
            plain = 0 if zone.zone_type is ZoneType("priority") else 1
        if mode == 0:
            return (plain, waits)
        if mode == 1:
            return (waits, plain)
        if mode == 2:
            return (plain, -waits)
        noise = 0
        if zone is not None:
            noise = zlib.crc32(f"{mode}:{zone.name}".encode()) % 7
        return (noise, waits)

    @staticmethod
    def _successors(
        network: Network,
        table: ReservationTable,
        zone: Zone,
        turn: int,
        horizon: int,
    ) -> list[Successor]:
        result: list[Successor] = []
        depart = turn + 1
        if depart <= horizon and table.zone_free(zone, depart):
            result.append((zone, depart, None))
        for neighbor, link in network.neighbors(zone):
            cost = neighbor.entry_cost
            arrive = depart + cost - 1
            if arrive > horizon:
                continue
            if not table.link_free(link, depart):
                continue
            if cost == 2 and not table.link_free(link, depart + 1):
                continue
            if not table.zone_free(neighbor, arrive):
                continue
            step = Step(neighbor, link, depart, arrive)
            result.append((neighbor, arrive, step))
        return result

    def _search(
        self,
        network: Network,
        table: ReservationTable,
        dist: dict[str, int],
        horizon: int,
        mode: int,
    ) -> list[Step]:
        start = network.start
        end = network.end
        origin: State = (start.name, 0)
        best: dict[State, Rank] = {origin: (0, 0)}
        parent: dict[State, tuple[State, Step | None]] = {}
        counter = itertools.count()
        heap: list[tuple[int, Rank, int, int, Zone]] = [
            (dist[start.name], (0, 0), next(counter), 0, start)
        ]
        while heap:
            _, rank, _, turn, zone = heapq.heappop(heap)
            here: State = (zone.name, turn)
            if rank > best[here]:
                continue
            if zone.name == end.name:
                return self._rebuild(parent, here)
            for nxt, nxt_turn, step in self._successors(
                network, table, zone, turn, horizon
            ):
                remaining = dist.get(nxt.name)
                if remaining is None or nxt_turn + remaining > horizon:
                    continue
                inc = self._increment(
                    mode, nxt if step is not None else None
                )
                new_rank = (rank[0] + inc[0], rank[1] + inc[1])
                key: State = (nxt.name, nxt_turn)
                known = best.get(key)
                if known is None or new_rank < known:
                    best[key] = new_rank
                    parent[key] = (here, step)
                    heapq.heappush(
                        heap,
                        (
                            nxt_turn + remaining,
                            new_rank,
                            next(counter),
                            nxt_turn,
                            nxt,
                        ),
                    )
        raise SimulationError(f"no schedule found within {horizon} turns")

    @staticmethod
    def _rebuild(
        parent: dict[State, tuple[State, Step | None]], goal: State
    ) -> list[Step]:
        steps: list[Step] = []
        cursor = goal
        while cursor in parent:
            previous, step = parent[cursor]
            if step is not None:
                steps.append(step)
            cursor = previous
        steps.reverse()
        return steps

    @staticmethod
    def _reserve(table: ReservationTable, steps: list[Step]) -> None:
        for index, step in enumerate(steps):
            table.reserve_link(step.link, step.depart)
            if step.arrive > step.depart:
                table.reserve_link(step.link, step.depart + 1)
            if index + 1 < len(steps):
                leave = steps[index + 1].depart
                for turn in range(step.arrive, leave):
                    table.reserve_zone(step.zone, turn)

    @staticmethod
    def _turns(routes: list[list[Step]]) -> list[Turn]:
        departing: dict[int, Turn] = {}
        flying: set[int] = set()
        last = 0
        for index, steps in enumerate(routes):
            for step in steps:
                departing.setdefault(step.depart, []).append((index, step))
                if step.arrive > step.depart:
                    flying.add(step.arrive)
                last = max(last, step.arrive)
        turns: list[Turn] = []
        for turn in range(1, last + 1):
            if turn in departing or turn in flying:
                turns.append(departing.get(turn, []))
        return turns
