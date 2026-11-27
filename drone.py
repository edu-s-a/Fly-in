"""Drone state and movement tracking for the fly-in simulation."""

from errors import SimulationError
from zone import Connection, Zone


class Drone:
    """Represent a drone and its current state in the simulation.

    Attributes:
        id: Unique identifier for the drone.
        name: Human-readable identifier, such as "D1".
    """

    def __init__(self, drone_id: int, start: Zone) -> None:
        """Initialize a drone at a starting zone.

        Args:
            drone_id: Unique identifier for the drone.
            start: Zone where the drone starts.
        """
        self.id: int = drone_id
        self._zone: Zone | None = start
        self._connection: Connection | None = None
        self._destination: Zone | None = None
        self._delivered_turn: int | None = None

    @property
    def name(self) -> str:
        """Return the drone's display name.

        Returns:
            Display name in the form "D" followed by the drone ID.
        """
        return f"D{self.id}"

    @property
    def idle(self) -> bool:
        """Check whether the drone is idle at a zone.

        Returns:
            True if the drone is at a zone and not yet delivered.
        """
        return self._zone is not None and self._delivered_turn is None

    @property
    def in_transit(self) -> bool:
        """Check whether the drone is traveling between zones.

        Returns:
            True if the drone is currently in transit.
        """
        return self._zone is None

    @property
    def delivered(self) -> bool:
        """Check whether the drone has been delivered.

        Returns:
            True if the drone has a delivery turn.
        """
        return self._delivered_turn is not None

    @property
    def delivered_turn(self) -> int | None:
        """Return the turn on which the drone was delivered.

        Returns:
            Delivery turn number, or None if the drone has not been delivered.
        """
        return self._delivered_turn

    @property
    def zone(self) -> Zone:
        """Return the zone where the drone is currently located.

        Returns:
            The drone's current zone.

        Raises:
            SimulationError: If the drone is in transit.
        """
        zone = self._zone
        if zone is None:
            raise SimulationError(f"{self.name} is in transit")
        return zone

    @property
    def connection(self) -> Connection:
        """Return the connection used for the drone's journey.

        Returns:
            The connection the drone is currently traveling through.

        Raises:
            SimulationError: If the drone is not in transit.
        """
        connection = self._connection
        if connection is None:
            raise SimulationError(f"{self.name} is not in transit")
        return connection

    @property
    def destination(self) -> Zone:
        """Return the drone's destination zone.

        Returns:
            The zone to which the drone is traveling.

        Raises:
            SimulationError: If the drone is not in transit.
        """
        destination = self._destination
        if destination is None:
            raise SimulationError(f"{self.name} is not in transit")
        return destination

    def depart(self, connection: Connection, destination: Zone) -> None:
        """Set the drone as departed from its current zone.

        Args:
            connection: Connection used to travel.
            destination: Zone that the drone is traveling toward.
        """
        self._zone = None
        self._connection = connection
        self._destination = destination

    def arrive(self, zone: Zone) -> None:
        """Place the drone at an arrived zone.

        Args:
            zone: Zone reached by the drone.
        """
        self._zone = zone
        self._connection = None
        self._destination = None

    def deliver(self, turn: int) -> None:
        """Mark the drone as delivered on a turn.

        Args:
            turn: Turn number when delivery occurred.
        """
        self._delivered_turn = turn
