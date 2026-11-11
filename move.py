from dataclasses import dataclass

from drone import Drone
from zone import Connection, Zone


@dataclass(frozen=True)
class Move:
    drone: Drone
    destination: Zone
    connection: Connection

    @property
    def cost(self) -> int:
        return self.destination.entry_cost
