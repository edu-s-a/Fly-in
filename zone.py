"""Zone and connection models used to represent the fly-in network."""

from dataclasses import dataclass
from enum import Enum

from errors import NetworkError


class ZoneType(Enum):
    """Define movement behavior for a zone."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int | None:
        """Return the entry cost associated with this zone type.

        Returns:
            Entry cost of one or two turns, or None for blocked zones.
        """
        if self is ZoneType.BLOCKED:
            return None
        if self is ZoneType.RESTRICTED:
            return 2
        return 1


class ZoneRole(Enum):
    """Define the role of a zone in the network."""

    REGULAR = "regular"
    START = "start"
    END = "end"


@dataclass(frozen=True)
class Zone:
    """Represent a location in the network.

    Attributes:
        name: Unique zone name.
        x: Horizontal coordinate.
        y: Vertical coordinate.
        zone_type: Movement and passability behavior.
        color: Optional display color name.
        max_drones: Maximum occupants for regular zones.
        role: Start, end, or regular role.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    role: ZoneRole = ZoneRole.REGULAR

    @property
    def is_passable(self) -> bool:
        """Check whether drones may enter the zone.

        Returns:
            True unless the zone is blocked.
        """
        return self.zone_type is not ZoneType.BLOCKED

    @property
    def entry_cost(self) -> int:
        """Return the cost required to enter the zone.

        Returns:
            One or two moves, depending on the zone type.

        Raises:
            NetworkError: If the zone is blocked.
        """
        cost = self.zone_type.cost
        if cost is None:
            raise NetworkError(f"zone '{self.name}' is blocked")
        return cost

    @property
    def capacity(self) -> int | None:
        """Return the zone's drone capacity.

        Returns:
            Maximum regular-zone occupancy, or None for start and end zones.
        """
        if self.role in (ZoneRole.START, ZoneRole.END):
            return None
        return self.max_drones


@dataclass(frozen=True)
class Connection:
    """Represent a bidirectional link between two zones.

    Attributes:
        zone_1: One endpoint zone.
        zone_2: Other endpoint zone.
        max_link_capacity: Maximum drones using the link per turn.
    """

    zone_1: Zone
    zone_2: Zone
    max_link_capacity: int = 1

    @property
    def name(self) -> str:
        """Return the connection's display name.

        Returns:
            Endpoint names joined by a hyphen.
        """
        return f"{self.zone_1.name}-{self.zone_2.name}"

    @property
    def key(self) -> frozenset[str]:
        """Return an unordered endpoint key for the connection.

        Returns:
            Frozenset containing both endpoint names.
        """
        return frozenset((self.zone_1.name, self.zone_2.name))

    def other(self, zone: Zone) -> Zone:
        """Return the endpoint opposite to a given zone.

        Args:
            zone: One endpoint of the connection.

        Returns:
            The opposite endpoint zone.

        Raises:
            NetworkError: If zone is not an endpoint of this connection.
        """
        if zone.name == self.zone_1.name:
            return self.zone_2
        if zone.name == self.zone_2.name:
            return self.zone_1
        raise NetworkError(
            f"zone '{zone.name}' is not an endpoint of '{self.name}'"
        )
