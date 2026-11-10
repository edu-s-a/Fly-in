from zone import Zone


class Path:

    def __init__(self, zones: list[Zone]) -> None:
        self._zones: tuple[Zone, ...] = tuple(zones)

    @property
    def zones(self) -> tuple[Zone, ...]:
        return self._zones

    @property
    def names(self) -> list[str]:
        return [zone.name for zone in self._zones]

    @property
    def moves(self) -> int:
        return len(self._zones) - 1

    @property
    def cost(self) -> int:
        return sum(zone.entry_cost for zone in self._zones[1:])
