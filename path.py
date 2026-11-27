"""Data model for ordered paths through a fly-in network."""

from zone import Zone


class Path:
    """Represent an ordered route through a sequence of zones.

    Attributes:
        zones: Ordered tuple of zones in the path.
        names: Ordered names of the zones in the path.
        moves: Number of connections required to follow the path.
        cost: Total entry cost of zones visited after the start.
    """

    def __init__(self, zones: list[Zone]) -> None:
        """Initialize a path from an ordered list of zones.

        Args:
            zones: Zones in route order, starting with the start zone.
        """
        self._zones: tuple[Zone, ...] = tuple(zones)

    @property
    def zones(self) -> tuple[Zone, ...]:
        """Return the zones in route order.

        Returns:
            Ordered tuple of zones.
        """
        return self._zones

    @property
    def names(self) -> list[str]:
        """Return the names of zones in route order.

        Returns:
            Ordered list of zone names.
        """
        return [zone.name for zone in self._zones]

    @property
    def moves(self) -> int:
        """Return the number of moves needed to follow the path.

        Returns:
            Number of connections between consecutive zones.
        """
        return len(self._zones) - 1

    @property
    def cost(self) -> int:
        """Calculate the path's total entry cost.

        Returns:
            Sum of entry costs for zones after the starting zone.
        """
        return sum(zone.entry_cost for zone in self._zones[1:])
