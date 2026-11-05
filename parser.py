from enum import Enum, auto
from dataclasses import dataclass


class ZoneType(Enum):
    """Zone types allowed in a map file."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def is_passable(self) -> bool:
        """Return False only for blocked zones."""
        return self is not ZoneType.BLOCKED

    @property
    def cost(self) -> int:
        """Return the turns needed to enter a zone of this type."""
        if self is ZoneType.BLOCKED:
            raise ValueError("blocked zones cannot be entered")
        if self is ZoneType.RESTRICTED:
            return 2
        return 1


class ZoneRole(Enum):
    """Semantic role assigned to a zone in a map."""

    START = auto()
    END = auto()
    REGULAR = auto()


@dataclass(frozen=True)
class Zone:
    """A single location on the map, with optional metadata."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    role: ZoneRole = ZoneRole.REGULAR

    @property
    def capacity(self) -> int | None:
        """Return the number of drones the zone can hold when it is regular. Else unlimited."""
        if self.role is ZoneRole.REGULAR:
            return self.max_drones
        return None

    @property
    def entry_cost(self) -> int:
        """Return the travel cost needed to enter this zone."""
        return self.zone_type.cost

    @property
    def is_passable(self) -> bool:
        """Return whether this zone can be traversed."""
        return self.zone_type.is_passable


@dataclass(frozen=True)
class Connection:
    """Bidirectional link between two zones.

    Zones are kept in the order they appear in the map file.
    """

    zone_1: Zone
    zone_2: Zone
    max_link_capacity: int = 1

    @property
    def key(self) -> frozenset[str]:
        """Return the unordered pair of zone names (for lookups)."""
        return frozenset((self.zone_1.name, self.zone_2.name))

    @property
    def name(self) -> str:
        """Return the connection name as written in the map file."""
        return f"{self.zone_1.name}-{self.zone_2.name}"

    def other(self, zone: Zone) -> Zone:
        """Return the other zone connected to this link."""
        if zone.name == self.zone_1:
            return self.zone_2
        if zone.name == self.zone_2:
            return self.zone_1
        raise ValueError(
            f"zone '{zone.name}' is not part of connection '{self.name}'")

