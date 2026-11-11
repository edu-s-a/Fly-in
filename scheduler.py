from abc import ABC, abstractmethod

from move import Move
from simulation import Simulation


class Scheduler(ABC):

    @abstractmethod
    def plan(self, simulation: Simulation) -> list[list[Move]]:
        ...
