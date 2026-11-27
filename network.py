"""Network model for zones and connections in the fly-in map."""

from zone import Zone, Connection, ZoneRole
from errors import NetworkError


class Network:
    """Store zones and connections that make up a fly-in network.

    Attributes:
        nb_drones: Number of drones in the simulation.
    """

    def __init__(self, nb_drones: int) -> None:
        """Initialize an empty network.

        Args:
            nb_drones: Number of drones in the simulation.
        """
        self.nb_drones: int = nb_drones
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._adjacency: dict[str, list[Connection]] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the network.

        Args:
            zone: Zone to add.

        Raises:
            NetworkError: If the zone name or start/end role is duplicated.
        """
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
        """Add a connection between two zones.

        Args:
            connection: Connection to add.

        Raises:
            NetworkError: If either endpoint zone is not in the network.
        """
        for end_zone in (connection.zone_1, connection.zone_2):
            if end_zone.name not in self._adjacency:
                raise NetworkError(f"unknown zone: '{end_zone.name}'")
        self._connections.append(connection)
        self._adjacency[connection.zone_1.name].append(connection)
        self._adjacency[connection.zone_2.name].append(connection)

    def get_zone(self, name: str) -> Zone:
        """Return a zone by name.

        Args:
            name: Name of the zone to find.

        Returns:
            Zone with the requested name.

        Raises:
            NetworkError: If no zone has the requested name.
        """
        try:
            return self._zones[name]
        except KeyError:
            raise NetworkError(f"unknown zone name: '{name}'") from None

    def connections_of(self, zone: Zone) -> list[Connection]:
        """Return connections attached to a zone.

        Args:
            zone: Zone whose connections are requested.

        Returns:
            Connections attached to the zone.

        Raises:
            NetworkError: If the zone is not in the network.
        """
        try:
            return self._adjacency[zone.name]
        except KeyError:
            raise NetworkError(f"unknown zone: '{zone.name}'") from None

    def neighbors(self, zone: Zone) -> list[tuple[Zone, Connection]]:
        """Return passable neighboring zones and their connections.

        Args:
            zone: Zone for which neighbors are requested.

        Returns:
            Neighbor-zone and connection pairs.

        Raises:
            NetworkError: If the zone is not in the network.
        """
        result: list[tuple[Zone, Connection]] = []
        for connection in self.connections_of(zone):
            neighbor = connection.other(zone)
            if not neighbor.is_passable:
                continue
            result.append((neighbor, connection))
        return result

    @property
    def start(self) -> Zone:
        """Return the network's start zone.

        Returns:
            Configured start zone.

        Raises:
            NetworkError: If the network has no start zone.
        """
        local_start = self._start
        if local_start is None:
            raise NetworkError("network has no start zone")
        return local_start

    @property
    def end(self) -> Zone:
        """Return the network's end zone.

        Returns:
            Configured end zone.

        Raises:
            NetworkError: If the network has no end zone.
        """
        local_end = self._end
        if local_end is None:
            raise NetworkError("network has no end zone")
        return local_end

    @property
    def zones(self) -> tuple[Zone, ...]:
        """Return all zones in insertion order.

        Returns:
            Tuple containing every zone in the network.
        """
        return tuple(self._zones.values())

    @property
    def connections(self) -> tuple[Connection, ...]:
        """Return all connections in insertion order.

        Returns:
            Tuple containing every connection in the network.
        """
        return tuple(self._connections)
