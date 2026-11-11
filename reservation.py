from errors import SimulationError
from zone import Connection, Zone


class ReservationTable:

    def __init__(self) -> None:
        self._zones: dict[tuple[str, int], int] = {}
        self._links: dict[tuple[frozenset[str], int], int] = {}

    @staticmethod
    def _key(link: Connection) -> frozenset[str]:
        return frozenset((link.zone_1.name, link.zone_2.name))

    def zone_load(self, zone: Zone, turn: int) -> int:
        return self._zones.get((zone.name, turn), 0)

    def link_load(self, link: Connection, turn: int) -> int:
        return self._links.get((self._key(link), turn), 0)

    def zone_free(self, zone: Zone, turn: int) -> bool:
        capacity = zone.capacity
        return capacity is None or self.zone_load(zone, turn) < capacity

    def link_free(self, link: Connection, turn: int) -> bool:
        return self.link_load(link, turn) < link.max_link_capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        if not self.zone_free(zone, turn):
            raise SimulationError(
                f"zone '{zone.name}' already full at turn {turn}"
            )
        key = (zone.name, turn)
        self._zones[key] = self._zones.get(key, 0) + 1

    def reserve_link(self, link: Connection, turn: int) -> None:
        if not self.link_free(link, turn):
            raise SimulationError(
                f"connection '{link.name}' already full at turn {turn}"
            )
        key = (self._key(link), turn)
        self._links[key] = self._links.get(key, 0) + 1
