import heapq
import itertools

from errors import NoPathError
from network import Network
from path import Path
from zone import Zone, ZoneType

Cost = tuple[int, int]


class Pathfinder:

    def __init__(self, network: Network) -> None:
        self._network = network

    def _edge_cost(self, zone: Zone) -> Cost:
        extra = 0 if zone.zone_type is ZoneType("priority") else 1
        return (zone.entry_cost, extra)

    def find_path(self, start: Zone, end: Zone) -> Path:
        best: dict[str, Cost] = {start.name: (0, 0)}
        previous: dict[str, Zone] = {}
        counter = itertools.count()
        heap: list[tuple[Cost, int, Zone]] = [
            ((0, 0), next(counter), start)
        ]
        while heap:
            cost, _, zone = heapq.heappop(heap)
            if cost > best[zone.name]:
                continue
            if zone.name == end.name:
                break
            for neighbor, _link in self._network.neighbors(zone):
                edge = self._edge_cost(neighbor)
                new_cost = (cost[0] + edge[0], cost[1] + edge[1])
                known = best.get(neighbor.name)
                if known is None or new_cost < known:
                    best[neighbor.name] = new_cost
                    previous[neighbor.name] = zone
                    heapq.heappush(
                        heap, (new_cost, next(counter), neighbor)
                    )
        if end.name not in best:
            raise NoPathError(
                f"no path from '{start.name}' to '{end.name}'"
            )
        return self._rebuild(previous, start, end)

    def _rebuild(
        self, previous: dict[str, Zone], start: Zone, end: Zone
    ) -> Path:
        zones = [end]
        current = end
        while current.name != start.name:
            current = previous[current.name]
            zones.append(current)
        zones.reverse()
        return Path(zones)

    def distances_to(self, end: Zone) -> dict[str, int]:
        best: dict[str, int] = {end.name: 0}
        counter = itertools.count()
        heap: list[tuple[int, int, Zone]] = [(0, next(counter), end)]
        while heap:
            cost, _, zone = heapq.heappop(heap)
            if cost > best[zone.name]:
                continue
            for neighbor, _link in self._network.neighbors(zone):
                new_cost = cost + zone.entry_cost
                known = best.get(neighbor.name)
                if known is None or new_cost < known:
                    best[neighbor.name] = new_cost
                    heapq.heappush(
                        heap, (new_cost, next(counter), neighbor)
                    )
        return best
