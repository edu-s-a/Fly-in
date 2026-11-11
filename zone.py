from dataclasses import dataclass
from enum import Enum

from errors import NetworkError


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int | None:
        if self is ZoneType.BLOCKED:
            return None
        if self is ZoneType.RESTRICTED:
            return 2
        return 1


class ZoneRole(Enum):
    REGULAR = "regular"
    START = "start"
    END = "end"


@dataclass(frozen=True)
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    role: ZoneRole = ZoneRole.REGULAR

    @property
    def is_passable(self) -> bool:
        return self.zone_type is not ZoneType.BLOCKED

    @property
    def entry_cost(self) -> int:
        cost = self.zone_type.cost
        if cost is None:
            raise NetworkError(f"zone '{self.name}' is blocked")
        return cost

    @property
    def capacity(self) -> int | None:
        if self.role in (ZoneRole.START, ZoneRole.END):
            return None
        return self.max_drones


@dataclass(frozen=True)
class Connection:
    zone_1: Zone
    zone_2: Zone
    max_link_capacity: int = 1

    @property
    def name(self) -> str:
        return f"{self.zone_1.name}-{self.zone_2.name}"

    @property
    def key(self) -> frozenset[str]:
        return frozenset((self.zone_1.name, self.zone_2.name))

    def other(self, zone: Zone) -> Zone:
        if zone.name == self.zone_1.name:
            return self.zone_2
        if zone.name == self.zone_2.name:
            return self.zone_1
        raise NetworkError(
            f"zone '{zone.name}' is not an endpoint of '{self.name}'"
        )
