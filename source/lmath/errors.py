"""errors.py — exceptions that carry student-friendly messages."""


class MathError(Exception):
    """Something the student can fix: bad input, no solution, etc."""


class UsageError(MathError):
    """A command was called with missing or malformed arguments."""


class Cancelled(MathError):
    """The student cancelled an interactive prompt (Ctrl-C / end of input)."""
