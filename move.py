"""Data model for a drone move in the fly-in simulation."""

from dataclasses import dataclass

from drone import Drone
from zone import Connection, Zone


@dataclass(frozen=True)
class Move:
    """Represent one scheduled drone movement.

    Attributes:
        drone: Drone assigned to make the move.
        destination: Zone reached by the move.
        connection: Connection used to reach the destination.
    """

    drone: Drone
    destination: Zone
    connection: Connection

    @property
    def cost(self) -> int:
        """Return the entry cost of the destination zone.

        Returns:
            Entry cost for the destination zone.
        """
        return self.destination.entry_cost
