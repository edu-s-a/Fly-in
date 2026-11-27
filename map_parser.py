"""Parse Fly-in map files and construct their network representation."""

from errors import ParseError, NetworkError
from network import Network
from zone import Connection, Zone, ZoneRole, ZoneType


class MapParser:
    """Parse map files into network objects.

    Attributes:
        _ZONE_KEYWORDS: Mapping of map keywords to zone roles.
        _ZONE_KEYS: Metadata keys accepted for zone declarations.
        _CONNECTION_KEYS: Metadata keys accepted for connection declarations.
    """

    _ZONE_KEYWORDS: dict[str, ZoneRole] = {
        "start_hub": ZoneRole.START,
        "end_hub": ZoneRole.END,
        "hub": ZoneRole.REGULAR}
    _ZONE_KEYS: set[str] = {"zone", "color", "max_drones"}
    _CONNECTION_KEYS: set[str] = {"max_link_capacity"}

    def __init__(self) -> None:
        """Initialize the parser's connection tracking."""
        self._connection_keys: set[frozenset[str]] = set()

    def parse(self, path: str) -> Network:
        """Parse a map file into a Network.

        Args:
            path: Path to the UTF-8 map file.

        Returns:
            Parsed network representation of the map.

        Raises:
            ParseError: If the file cannot be read or is not valid UTF-8.
        """
        try:
            with open(path, encoding="utf-8") as file:
                lines = file.read().splitlines()
        except OSError as err:
            raise ParseError(f"cannot read '{path}': {err.strerror}") from err
        except UnicodeDecodeError:
            raise ParseError(f"'{path}' is not valid UTF-8 text") from None
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> Network:
        """Parse map-file lines and validate the resulting network.

        Args:
            lines: Lines from the map file.

        Returns:
            Validated network constructed from the lines.

        Raises:
            ParseError: If the file is incomplete or otherwise invalid.
        """
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
        """Parse one non-header line and add its entry to ``network``.

        Args:
            network: Network receiving the parsed entry.
            line: Non-header line to parse.
            line_no: 1-based line number in the map file.

        Raises:
            ParseError: If the line syntax or keyword is invalid.
        """
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
        """Parse the required first line and create a network.

        Args:
            line: First map-file line.
            line_no: 1-based line number in the map file.

        Returns:
            Empty network initialized with the drone count.

        Raises:
            ParseError: If the header is missing or malformed.
        """
        keyword, sep, value = line.partition(":")
        if not sep or keyword.strip() != "nb_drones":
            raise ParseError("nb_drones must be the first line", line_no)
        nb_drones = self._parse_positive_int(
            value.strip(), "nb_drones", line_no
        )
        return Network(nb_drones)

    def _split_metadata(self, value: str, line_no: int
                        ) -> tuple[str, dict[str, str]]:
        """Separate a line's body from optional ``[key=value]`` metadata.

        Args:
            value: Entry value, potentially followed by metadata.
            line_no: 1-based line number in the map file.

        Returns:
            A tuple containing the body and parsed metadata dictionary.

        Raises:
            ParseError: If metadata syntax is malformed or duplicated.
        """
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
        """Parse a zone declaration and add the zone to ``network``.

        Args:
            network: Network receiving the zone.
            value: Zone declaration value.
            role: Role assigned to the declared zone.
            line_no: 1-based line number in the map file.

        Raises:
            ParseError: If the zone declaration or metadata is invalid.
        """
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
        """Convert a zone-type string to its corresponding enum value.

        Args:
            text: Zone type name.
            line_no: 1-based line number in the map file.

        Returns:
            Matching zone type enum value.

        Raises:
            ParseError: If the text is not a recognized zone type.
        """
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
        """Parse a connection declaration and add it to ``network``.

        Args:
            network: Network receiving the connection.
            value: Connection declaration value.
            line_no: 1-based line number in the map file.

        Raises:
            ParseError: If the connection declaration or metadata is invalid.
        """
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

    def _parse_int(self, text: str, what: str, line: int) -> int:
        """Convert text to int or raise a ParseError.

        Args:
            text: Text to convert.
            what: Description of the value being parsed.
            line: 1-based line number in the map file.

        Returns:
            Parsed integer value.

        Raises:
            ParseError: If text is not a valid integer.
        """
        try:
            return int(text)
        except ValueError:
            raise ParseError(
                f"{what} must be an integer, got '{text}'", line
            ) from None

    def _parse_positive_int(self, text: str, what: str, line: int) -> int:
        """Convert text to a strictly positive int.

        Args:
            text: Text to convert.
            what: Description of the value being parsed.
            line: 1-based line number in the map file.

        Returns:
            Parsed positive integer value.

        Raises:
            ParseError: If text is not an integer or is not positive.
        """
        value = self._parse_int(text, what, line)
        if value <= 0:
            raise ParseError(
                f"{what} must be a positive integer, got '{text}'", line
            )
        return value
