"""Custom exceptions for the Fly-in project."""


class FlyInError(Exception):
    """Base class for every error raised by this project."""


class ParseError(FlyInError):
    """Raised when a map file is invalid.

    Attributes:
        line: 1-based line number of the problem, or None when the
            error is not tied to a specific line.
        reason: Human-readable description of the problem.
    """

    def __init__(self, reason: str, line: int | None = None) -> None:
        """Build the error and its final message.

        Args:
            reason: What went wrong.
            line: Line number, or None for file-level errors.
        """
        self.line: int | None = line
        self.reason: str = reason
        super().__init__(self._format())

    def _format(self) -> str:
        """Return the message shown to the user."""
        if self.line is None:
            return self.reason
        return f"line {self.line}: {self.reason}"


class NetworkError(FlyInError):
    pass
