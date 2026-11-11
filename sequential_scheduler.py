from move import Move
from pathfinder import Pathfinder
from scheduler import Scheduler
from simulation import Simulation


class SequentialScheduler(Scheduler):

    def plan(self, simulation: Simulation) -> list[list[Move]]:
        network = simulation.network
        path = Pathfinder(network).find_path(network.start, network.end)
        zones = path.zones
        turns: list[list[Move]] = []
        for drone in simulation.drones:
            for index in range(1, len(zones)):
                source = zones[index - 1]
                destination = zones[index]
                link = network.connection_between(source, destination)
                turns.append([Move(drone, destination, link)])
                if destination.entry_cost == 2:
                    turns.append([])
        return turns
