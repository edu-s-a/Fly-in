from errors import ParseError, NetworkError
from network import Network
from zone import Connection, Zone, ZoneRole, ZoneType


class MapParser:

    _ZONE_KEYWORDS: dict[str, ZoneRole] = {
        "start_hub": ZoneRole.START,
        "end_hub": ZoneRole.END,
        "hub": ZoneRole.REGULAR}
    _ZONE_KEYS: set[str] = {"zone", "color", "max_drones"}
    _CONNECTION_KEYS: set[str] = {"max_link_capacity"}

    def __init__(self) -> None:
        self._connection_keys: set[frozenset[str]] = set()

    def _parse_lines(self, lines: list[str]) -> Network:
        network: Network | None = None
        self._connection_keys = set()
        for line_no, raw in enumerate(lines, start=1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if network is None:
                network = self._parse_header(line, line_no)
                continue
            self._parse_entry(network, line, line_no)
        if network is None:
            raise ParseError("file contains no nb_drones")
        try:
            _ = network.start
            _ = network.end
        except NetworkError as err:
            raise ParseError(str(err)) from None
        return network

    def _parse_entry(self, network: Network, line: str, line_no: int) -> None:
        keyword, sep, value = line.partition(":")
        keyword = keyword.strip()
        value = value.strip()
        if not sep:
            raise ParseError("expected 'keyword: value'", line_no)
        if keyword == "nb_drones":
            raise ParseError("nb_drones defined more than once", line_no)
        if keyword in self._ZONE_KEYWORDS:
            self._parse_zone(
                network, value, self._ZONE_KEYWORDS[keyword], line_no
            )
        elif keyword == "connection":
            self._parse_connection(network, value, line_no)
        else:
            raise ParseError(f"unknown keyword '{keyword}'", line_no)

    def _parse_header(self, line: str, line_no: int) -> Network:
        keyword, sep, value = line.partition(":")
        if not sep or keyword.strip() != "nb_drones":
            raise ParseError("nb_drones must be the first line", line_no)
        nb_drones = self._parse_positive_int(
            value.strip(), "nb_drones", line_no
        )
        return Network(nb_drones)

    def parse(self, path: str) -> Network:
        """Parse a map file into a Network."""
        try:
            with open(path, encoding="utf-8") as file:
                lines = file.read().splitlines()
        except OSError as err:
            raise ParseError(f"cannot read '{path}': {err.strerror}") from err
        except UnicodeDecodeError:
            raise ParseError(f"'{path}' is not valid UTF-8 text") from None
        return self._parse_lines(lines)

    def _parse_int(self, text: str, what: str, line: int) -> int:
        """Convert text to int or raise a ParseError."""
        try:
            return int(text)
        except ValueError:
            raise ParseError(
                f"{what} must be an integer, got '{text}'", line
            ) from None

    def _parse_positive_int(self, text: str, what: str, line: int) -> int:
        """Convert text to a strictly positive int."""
        value = self._parse_int(text, what, line)
        if value <= 0:
            raise ParseError(
                f"{what} must be a positive integer, got '{text}'", line
            )
        return value

    def _split_metadata(self, value: str, line_no: int
                        ) -> tuple[str, dict[str, str]]:
        start = value.find("[")
        if start == -1:
            if "]" in value:
                raise ParseError("unexpected ']'", line_no)
            return value, {}
        if value.count("[") != 1:
            raise ParseError("only one metadata block allowed", line_no)
        if "]" not in value:
            raise ParseError("unclosed '[' in metadata", line_no)
        if value.count("]") != 1 or not value.endswith("]"):
            raise ParseError("unexpected text after metadata block", line_no)
        meta: dict[str, str] = {}
        for token in value[start + 1:-1].split():
            key, sep, val = token.partition("=")
            if not sep or not key or not val or "=" in val:
                raise ParseError(
                    f"invalid metadata entry '{token}', expected key=value",
                    line_no,
                )
            if key in meta:
                raise ParseError(f"duplicate metadata key '{key}'", line_no)
            meta[key] = val
        return value[:start].strip(), meta

    def _parse_zone(
        self, network: Network, value: str, role: ZoneRole, line_no: int
    ) -> None:
        body, meta = self._split_metadata(value, line_no)
        tokens = body.split()
        if len(tokens) != 3:
            raise ParseError("expected '<name> <x> <y>'", line_no)
        name = tokens[0]
        if "-" in name:
            raise ParseError(
                f"zone name '{name}' must not contain '-'", line_no
            )
        x = self._parse_int(tokens[1], "x coordinate", line_no)
        y = self._parse_int(tokens[2], "y coordinate", line_no)
        for key in meta:
            if key not in self._ZONE_KEYS:
                raise ParseError(
                    f"unknown zone metadata key '{key}'", line_no
                )
        zone_type = self._parse_zone_type(meta.get("zone", "normal"), line_no)
        max_drones = 1
        if "max_drones" in meta and role is ZoneRole.REGULAR:
            max_drones = self._parse_positive_int(
                meta["max_drones"], "max_drones", line_no
            )
        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=meta.get("color"),
            max_drones=max_drones,
            role=role,
        )
        try:
            network.add_zone(zone)
        except NetworkError as err:
            raise ParseError(str(err), line_no) from None

    def _parse_zone_type(self, text: str, line_no: int) -> ZoneType:
        try:
            return ZoneType(text)
        except ValueError:
            valid = ", ".join(t.value for t in ZoneType)
            raise ParseError(
                f"invalid zone type '{text}', expected one of: {valid}",
                line_no,
            ) from None

    def _parse_connection(
        self, network: Network, value: str, line_no: int
    ) -> None:
        body, meta = self._split_metadata(value, line_no)
        names = body.split("-")
        if len(body.split()) != 1 or len(names) != 2 or not all(names):
            raise ParseError("expected '<zone1>-<zone2>'", line_no)
        name_1, name_2 = names
        if name_1 == name_2:
            raise ParseError(
                f"connection links zone '{name_1}' to itself", line_no
            )
        try:
            zone_1 = network.get_zone(name_1)
            zone_2 = network.get_zone(name_2)
        except NetworkError as err:
            raise ParseError(str(err), line_no) from None
        for key in meta:
            if key not in self._CONNECTION_KEYS:
                raise ParseError(
                    f"unknown connection metadata key '{key}'", line_no
                )
        capacity = 1
        if "max_link_capacity" in meta:
            capacity = self._parse_positive_int(
                meta["max_link_capacity"], "max_link_capacity", line_no
            )
        pair = frozenset((name_1, name_2))
        if pair in self._connection_keys:
            raise ParseError(
                f"duplicate connection '{name_1}-{name_2}'", line_no
            )
        connection = Connection(
            zone_1=zone_1, zone_2=zone_2, max_link_capacity=capacity
        )
        try:
            network.add_connection(connection)
        except NetworkError as err:
            raise ParseError(str(err), line_no) from None
        self._connection_keys.add(pair)
