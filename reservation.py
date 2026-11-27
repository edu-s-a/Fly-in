"""Track zone and link reservations for scheduled simulation turns."""

from errors import SimulationError
from zone import Connection, Zone


class ReservationTable:
    """Track capacity reservations separately by turn and resource."""

    def __init__(self) -> None:
        """Initialize an empty reservation table."""
        self._zones: dict[tuple[str, int], int] = {}
        self._links: dict[tuple[frozenset[str], int], int] = {}

    @staticmethod
    def _key(link: Connection) -> frozenset[str]:
        """Create an unordered key for a connection.

        Args:
            link: Connection to identify.

        Returns:
            Frozenset containing the connection's endpoint names.
        """
        return frozenset((link.zone_1.name, link.zone_2.name))

    def zone_load(self, zone: Zone, turn: int) -> int:
        """Return the zone reservation count for a turn.

        Args:
            zone: Zone whose load is requested.
            turn: Simulation turn.

        Returns:
            Number of reservations in the zone at the turn.
        """
        return self._zones.get((zone.name, turn), 0)

    def link_load(self, link: Connection, turn: int) -> int:
        """Return the link reservation count for a turn.

        Args:
            link: Connection whose load is requested.
            turn: Simulation turn.

        Returns:
            Number of reservations on the connection at the turn.
        """
        return self._links.get((self._key(link), turn), 0)

    def zone_free(self, zone: Zone, turn: int) -> bool:
        """Check whether a zone has capacity at a turn.

        Args:
            zone: Zone to check.
            turn: Simulation turn.

        Returns:
            True if the zone can accept another reservation.
        """
        capacity = zone.capacity
        return capacity is None or self.zone_load(zone, turn) < capacity

    def link_free(self, link: Connection, turn: int) -> bool:
        """Check whether a connection has capacity at a turn.

        Args:
            link: Connection to check.
            turn: Simulation turn.

        Returns:
            True if the connection can accept another reservation.
        """
        return self.link_load(link, turn) < link.max_link_capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        """Reserve one zone capacity slot for a turn.

        Args:
            zone: Zone to reserve.
            turn: Simulation turn.

        Raises:
            SimulationError: If the zone is already full at the turn.
        """
        if not self.zone_free(zone, turn):
            raise SimulationError(
                f"zone '{zone.name}' already full at turn {turn}"
            )
        key = (zone.name, turn)
        self._zones[key] = self._zones.get(key, 0) + 1

    def reserve_link(self, link: Connection, turn: int) -> None:
        """Reserve one connection capacity slot for a turn.

        Args:
            link: Connection to reserve.
            turn: Simulation turn.

        Raises:
            SimulationError: If the connection is already full at the turn.
        """
        if not self.link_free(link, turn):
            raise SimulationError(
                f"connection '{link.name}' already full at turn {turn}"
            )
        key = (self._key(link), turn)
        self._links[key] = self._links.get(key, 0) + 1
