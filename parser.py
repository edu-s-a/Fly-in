from errors import ParseError


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
