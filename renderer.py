from network import Network
from simulation import TurnResult
from zone import Zone, ZoneRole

RESET = "\033[0m"
UNLIMITED = (ZoneRole.START, ZoneRole.END)


class Renderer:

    NAMED: dict[str, str] = {
        "black": "30", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "purple": "35", "cyan": "36",
        "white": "37", "gray": "90", "grey": "90",
        "orange": "38;5;208", "pink": "38;5;213", "brown": "38;5;94",
    }
    PALETTE: list[int] = [196, 202, 208, 214, 220, 118, 49, 45, 33, 99, 171]

    def __init__(self, network: Network, enabled: bool) -> None:
        self._network = network
        self._enabled = enabled
        self._where: dict[int, str] = {
            number: network.start.name
            for number in range(1, network.nb_drones + 1)
        }
        self._flying: dict[int, str] = {}

    def paint(self, text: str, code: str) -> str:
        if not self._enabled or not code:
            return text
        return f"\033[{code}m{text}{RESET}"

    def _code(self, color: str | None) -> str:
        if color is None:
            return ""
        key = color.lower()
        if key in self.NAMED:
            return self.NAMED[key]
        index = sum(ord(char) for char in key) % len(self.PALETTE)
        return f"38;5;{self.PALETTE[index]}"

    def zone_text(self, zone: Zone, width: int = 0) -> str:
        code = self._code(zone.color)
        if code and zone.role in UNLIMITED:
            code = "1;" + code
        return self.paint(zone.name.ljust(width), code)

    def _split(self, token: str) -> tuple[int, list[Zone]]:
        head, _, rest = token.partition("-")
        zones = [self._network.get_zone(name) for name in rest.split("-")]
        return int(head[1:]), zones

    @staticmethod
    def _target(zones: list[Zone]) -> Zone:
        if len(zones) == 1:
            return zones[0]
        for zone in zones:
            if zone.entry_cost == 2:
                return zone
        return zones[-1]

    def line(self, result: TurnResult) -> str:
        parts: list[str] = []
        for token in result.tokens:
            _, zones = self._split(token)
            target = self._target(zones)
            parts.append(self.paint(token, self._code(target.color)))
        return " ".join(parts)

    def legend(self) -> str:
        zones = self._network.zones
        width = max(len(zone.name) for zone in zones)
        lines = [self.paint("Map", "1")]
        for zone in zones:
            notes = [zone.zone_type.value]
            if zone.role is ZoneRole.START:
                notes.append("start")
            elif zone.role is ZoneRole.END:
                notes.append("end")
            elif zone.max_drones > 1:
                notes.append(f"max_drones={zone.max_drones}")
            lines.append(
                f"  {self.zone_text(zone, width)}  {', '.join(notes)}"
            )
        return "\n".join(lines)

    def frame(self, result: TurnResult) -> str:
        self._update(result)
        head = self.paint(f"Turn {result.turn}", "1")
        lines = [head, f"  {self.line(result)}"]
        return "\n".join(lines + self._occupancy())

    def _update(self, result: TurnResult) -> None:
        for token in result.tokens:
            number, zones = self._split(token)
            if len(zones) == 1:
                self._where[number] = zones[0].name
                self._flying.pop(number, None)
            else:
                self._where.pop(number, None)
                self._flying[number] = token.partition("-")[2]

    def _occupancy(self) -> list[str]:
        groups: dict[str, list[int]] = {}
        for number, name in sorted(self._where.items()):
            groups.setdefault(name, []).append(number)
        lines: list[str] = []
        for zone in self._network.zones:
            ids = groups.get(zone.name)
            if not ids:
                continue
            load = f"{len(ids)}"
            if zone.role not in UNLIMITED:
                load += f"/{zone.max_drones}"
            drones = " ".join(f"D{number}" for number in ids)
            lines.append(f"    {self.zone_text(zone)} [{load}]: {drones}")
        if self._flying:
            items = sorted(self._flying.items())
            flying = " ".join(f"D{n}({link})" for n, link in items)
            lines.append(f"    in flight: {flying}")
        return lines
