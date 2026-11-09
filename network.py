from zone import Zone, Connection, ZoneRole
from errors import NetworkError


class Network:
    def __init__(self, nb_drones: int) -> None:
        self.nb_drones: int = nb_drones
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._adjacency: dict[str, list[Connection]] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        if zone.name in self._zones:
            raise NetworkError(f"duplicate zone: '{zone.name}'")
        if zone.role is ZoneRole.START and self._start is not None:
            raise NetworkError("network already has a start zone")
        if zone.role is ZoneRole.END and self._end is not None:
            raise NetworkError("network already has an end zone")
        self._zones[zone.name] = zone
        if zone.role is ZoneRole.START:
            self._start = zone
        elif zone.role is ZoneRole.END:
            self._end = zone
        self._adjacency[zone.name] = []

    def add_connection(self, connection: Connection) -> None:
        for end_zone in (connection.zone_1, connection.zone_2):
            if end_zone.name not in self._adjacency:
                raise NetworkError(f"unknown zone: '{end_zone.name}'")
        self._connections.append(connection)
        self._adjacency[connection.zone_1.name].append(connection)
        self._adjacency[connection.zone_2.name].append(connection)

    def get_zone(self, name: str) -> Zone:
        try:
            return self._zones[name]
        except KeyError:
            raise NetworkError(f"unknown zone name: '{name}'") from None

    def connections_of(self, zone: Zone) -> list[Connection]:
        try:
            return self._adjacency[zone.name]
        except KeyError:
            raise NetworkError(f"unknown zone: '{zone.name}'") from None

    def neighbors(self, zone: Zone) -> list[tuple[Zone, Connection]]:
        result: list[tuple[Zone, Connection]] = []
        for connection in self.connections_of(zone):
            neighbor = connection.other(zone)
            if not neighbor.is_passable:
                continue
            result.append((neighbor, connection))
        return result

    @property
    def start(self) -> Zone:
        local_start = self._start
        if local_start is None:
            raise NetworkError("network has no start zone")
        return local_start

    @property
    def end(self) -> Zone:
        local_end = self._end
        if local_end is None:
            raise NetworkError("network has no end zone")
        return local_end

    @property
    def zones(self) -> tuple[Zone, ...]:
        return tuple(self._zones.values())

    @property
    def connections(self) -> tuple[Connection, ...]:
        return tuple(self._connections)
