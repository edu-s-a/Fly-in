"""Find cost-aware routes and distances within a fly-in network."""

import heapq
import itertools

from errors import NoPathError
from network import Network
from path import Path
from zone import Zone, ZoneType

Cost = tuple[int, int]


class Pathfinder:
    """Find routes through a network using prioritized path costs."""

    def __init__(self, network: Network) -> None:
        """Initialize the pathfinder with a network.

        Args:
            network: Network in which routes will be found.
        """
        self._network = network

    def _edge_cost(self, zone: Zone) -> Cost:
        """Calculate the cost pair associated with entering a zone.

        Args:
            zone: Zone being entered.

        Returns:
            Entry cost and priority-penalty pair.
        """
        extra = 0 if zone.zone_type is ZoneType("priority") else 1
        return (zone.entry_cost, extra)

    def find_path(self, start: Zone, end: Zone) -> Path:
        """Find the lowest-cost path between two zones.

        Args:
            start: Zone at the beginning of the route.
            end: Destination zone.

        Returns:
            Reconstructed path from start to end.

        Raises:
            NoPathError: If no route connects the two zones.
        """
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
        """Reconstruct a path from Dijkstra predecessor data.

        Args:
            previous: Mapping of zone names to predecessor zones.
            start: Zone at the beginning of the route.
            end: Destination zone.

        Returns:
            Ordered path from start to end.
        """
        zones = [end]
        current = end
        while current.name != start.name:
            current = previous[current.name]
            zones.append(current)
        zones.reverse()
        return Path(zones)

    def distances_to(self, end: Zone) -> dict[str, int]:
        """Compute the minimum cost from every reachable zone to end.

        Args:
            end: Destination zone used as the distance search origin.

        Returns:
            Mapping of zone names to their minimum entry cost to reach end.
        """
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
