from errors import SimulationError
from zone import Connection, Zone


class Drone:

    def __init__(self, drone_id: int, start: Zone) -> None:
        self.id: int = drone_id
        self._zone: Zone | None = start
        self._connection: Connection | None = None
        self._destination: Zone | None = None
        self._delivered_turn: int | None = None

    @property
    def name(self) -> str:
        return f"D{self.id}"

    @property
    def idle(self) -> bool:
        return self._zone is not None and self._delivered_turn is None

    @property
    def in_transit(self) -> bool:
        return self._zone is None

    @property
    def delivered(self) -> bool:
        return self._delivered_turn is not None

    @property
    def delivered_turn(self) -> int | None:
        return self._delivered_turn

    @property
    def zone(self) -> Zone:
        zone = self._zone
        if zone is None:
            raise SimulationError(f"{self.name} is in transit")
        return zone

    @property
    def connection(self) -> Connection:
        connection = self._connection
        if connection is None:
            raise SimulationError(f"{self.name} is not in transit")
        return connection

    @property
    def destination(self) -> Zone:
        destination = self._destination
        if destination is None:
            raise SimulationError(f"{self.name} is not in transit")
        return destination

    def depart(self, connection: Connection, destination: Zone) -> None:
        self._zone = None
        self._connection = connection
        self._destination = destination

    def arrive(self, zone: Zone) -> None:
        self._zone = zone
        self._connection = None
        self._destination = None

    def deliver(self, turn: int) -> None:
        self._delivered_turn = turn
