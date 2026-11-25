"""steps.py — numbered, step-by-step solution boxes."""
from .fmt import box


class Steps:
    """
    Collects numbered steps and prints one box when the `with` block ends.

        with Steps("Solve: 2x+3=11", ctx) as s:
            s.step("Subtract 3 from both sides", "2x = 8")
            s.note("Inverse operation of +3")
            s.result("x = 4")

    When the student has turned steps off (`steps off`), only the results print.
    """

    def __init__(self, title: str, ctx=None, force: bool = False):
        self.title = title
        self.on = force or ctx is None or ctx.settings.get("steps", True)
        self._lines = []
        self._results = []
        self._n = 0

    def step(self, text: str, expr: str = ""):
        self._n += 1
        self._lines.append(f"Step {self._n}: {text}")
        if expr:
            for line in str(expr).split("\n"):
                self._lines.append("        " + line)

    def note(self, text: str):
        self._lines.append(f"  ↳ {text}")

    def gap(self):
        self._lines.append("")

    def result(self, text: str):
        self._results.append(text)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False
        lines = list(self._lines) if self.on else []
        if self._results:
            if lines:
                lines.append("")
            lines += [f"✓ {r}" if i == 0 or len(self._results) == 1 else f"  {r}"
                      for i, r in enumerate(self._results)]
        if lines:
            box(self.title, lines)
        return False
