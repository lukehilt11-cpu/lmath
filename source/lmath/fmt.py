"""
fmt.py — turning SymPy results into the exact-first text students see.

  mstr(e)      one-line exact form:   2√3,  3x²/4,  π/6,  1 + 2i
  show(e)      exact form plus a labelled decimal when it is irrational
  approx(e)    just the decimal, e.g. 3.4641
  box(t, ls)   the framed result box every command prints
"""
import re

import sympy as sp
from sympy.printing.precedence import PRECEDENCE
from sympy.printing.str import StrPrinter

_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


class _Printer(StrPrinter):
    """SymPy's string printer, tuned to read like a textbook."""

    def _base(self, b):
        if self._atomic(b):
            return self._print(b)
        return "(" + self._print(b) + ")" if not b.is_Function else self._print(b)

    @staticmethod
    def _atomic(b):
        return b.is_Symbol or (b.is_Integer and b >= 0) or b in (sp.pi, sp.E)

    def _print_Pow(self, expr):
        b, e = expr.base, expr.exp
        if e == sp.S.Half:
            s = self._print(b)
            return "√" + (s if self._atomic(b) else f"({s})")
        if e == sp.Rational(1, 3):
            s = self._print(b)
            return "∛" + (s if self._atomic(b) else f"({s})")
        if e == -1:
            return f"1/{self._base(b)}"
        if e.is_Integer and e > 1:
            if e <= 9:
                return self._base(b) + str(int(e)).translate(_SUP)
            return f"{self._base(b)}^{int(e)}"
        if e.is_Symbol or (e.is_Integer and e > 0):
            return f"{self._base(b)}^{self._print(e)}"
        return f"{self._base(b)}^({self._print(e)})"

    def _print_exp(self, expr):
        a = expr.args[0]
        if a.is_Integer and -9 <= a <= 9 and a not in (0, 1):
            return "e" + str(int(a)).translate(_SUP)
        s = self._print(a)
        return "e^" + (s if (a.is_Symbol or (a.is_Integer and a >= 0)) else f"({s})")

    def _print_Pi(self, expr):
        return "π"

    def _print_Exp1(self, expr):
        return "e"

    def _print_ImaginaryUnit(self, expr):
        return "i"

    def _print_Infinity(self, expr):
        return "∞"

    def _print_NegativeInfinity(self, expr):
        return "-∞"

    def _print_Abs(self, expr):
        return "|" + self._print(expr.args[0]) + "|"

    def _print_Relational(self, expr):
        ops = {"==": "=", "<=": "≤", ">=": "≥", "!=": "≠"}
        op = ops.get(expr.rel_op, expr.rel_op)
        return f"{self._print(expr.lhs)} {op} {self._print(expr.rhs)}"

    def _print_Equality(self, expr):
        return f"{self._print(expr.lhs)} = {self._print(expr.rhs)}"

    def _print_log(self, expr):
        return "ln(" + self._print(expr.args[0]) + ")"


_printer = _Printer({"order": "lex"})
_num_printer = _Printer({"order": None})
_FUNC_NEXT = re.compile(r"^[A-Za-z]{2,}\(")


def _implicit(s: str) -> str:
    """Drop the * between factors where juxtaposition is unambiguous: 2*x → 2x."""
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch == "*" and out:
            left = out[-1]
            right = s[i + 1:]
            ok_left = left.isalnum() or left in ")π²³⁴⁵⁶⁷⁸⁹"
            ok_right = bool(right) and (right[0].isalpha() or right[0] in "π√∛(|")
            if ok_left and ok_right and not _FUNC_NEXT.match(right):
                i += 1
                continue
            out.append("·")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def mstr(e) -> str:
    """Exact, one-line, student-readable string for any SymPy object (or number)."""
    if isinstance(e, (list, tuple)):
        return ", ".join(mstr(x) for x in e)
    e = sp.sympify(e)
    if isinstance(e, (sp.Interval, sp.Union, sp.FiniteSet)) or e in (sp.S.Reals, sp.S.EmptySet):
        return set_str(e)
    return _implicit((_printer if e.free_symbols else _num_printer).doprint(e))


def _sort_key(s):
    if isinstance(s, sp.Interval):
        return float(sp.N(s.start)) if s.start.is_finite else -1e18
    if isinstance(s, sp.FiniteSet):
        return min(float(sp.N(v)) for v in s.args)
    return 0.0


def set_str(s) -> str:
    """Interval notation for solution sets: (3, ∞), [-2, 5), {1, 2}."""
    if s == sp.S.EmptySet:
        return "∅"
    if s == sp.S.Reals:
        return "(-∞, ∞)"
    if isinstance(s, sp.Interval):
        l = "(" if s.left_open else "["
        r = ")" if s.right_open else "]"
        return f"{l}{mstr(s.start)}, {mstr(s.end)}{r}"
    if isinstance(s, sp.Union):
        return " ∪ ".join(set_str(p) for p in sorted(s.args, key=_sort_key))
    if isinstance(s, sp.FiniteSet):
        items = sorted(s.args, key=lambda v: float(sp.N(v)) if v.is_real else 0.0)
        return "{" + ", ".join(mstr(a) for a in items) + "}"
    return str(s)


def is_exact_irrational(e) -> bool:
    e = sp.sympify(e)
    return bool(e.is_number and e.is_finite is not False and not e.is_Rational and not isinstance(e, sp.Float) and not e.has(sp.I))


def approx(e, digits: int = 6) -> str:
    """Decimal approximation with up to `digits` significant digits, no trailing zeros."""
    e = sp.sympify(e)
    try:
        v = complex(sp.N(e, 15))
    except (TypeError, ValueError):
        return str(e)

    def one(x):
        s = f"{x:.{digits}g}"
        return "0" if s in ("-0", "0") else s

    if abs(v.imag) < 1e-12:
        return one(v.real)
    sign = "+" if v.imag >= 0 else "-"
    return f"{one(v.real)} {sign} {one(abs(v.imag))}i"


def show(e, digits: int = 6) -> str:
    """Exact form, with '≈ decimal' appended when the value is irrational."""
    e = sp.sympify(e)
    if isinstance(e, sp.Float):
        return approx(e, digits)
    if e.is_Rational and not e.is_Integer and e.q > 100 and set(str(e.q)) <= {"0", "1"} and str(e.q).startswith("1"):
        # a denominator like 100000000 means the number came from decimals (1.07^5) — show it as a decimal
        return str(sp.Float(e, 30)).rstrip("0").rstrip(".")
    s = mstr(e)
    if is_exact_irrational(e):
        a = approx(e, digits)
        if a != s:
            return f"{s}  ≈ {a}"
    return s


def show_or_approx(e, digits: int = 6, max_len: int = 38) -> str:
    """Like show(), but falls back to the decimal alone when the exact form is unwieldy."""
    e = sp.sympify(e)
    if e.is_number and len(mstr(e)) > max_len:
        return "≈ " + approx(e, digits)
    return show(e, digits)


def best(e):
    """The shortest of a few equivalent forms (simplified / factored / combined)."""
    e = sp.sympify(e)
    cands = [e]
    for fn in (sp.simplify, sp.factor, lambda z: sp.cancel(sp.together(z))):
        try:
            cands.append(fn(e))
        except Exception:
            pass
    return min(cands, key=lambda c: (sp.count_ops(c), len(mstr(c))))


def pretty_lines(e) -> list:
    """One line normally; a stacked-fraction layout only when the one-liner would be very long."""
    e = sp.sympify(e)
    one = mstr(e)
    if len(one) > 60 or e.has(sp.Integral, sp.Sum):
        try:
            return sp.pretty(e, use_unicode=True, wrap_line=False).split("\n")
        except Exception:
            pass
    return [one]


def box(title: str, lines) -> None:
    """Print a framed result box. `lines` may contain multi-line strings."""
    flat = []
    for l in lines:
        flat.extend(str(l).split("\n"))
    w = max([len(title)] + [len(l) for l in flat])
    print("┌" + "─" * (w + 2) + "┐")
    print("│ " + title.ljust(w) + " │")
    print("├" + "─" * (w + 2) + "┤")
    for l in flat:
        print("│ " + l.ljust(w) + " │")
    print("└" + "─" * (w + 2) + "┘")


def note(text: str) -> None:
    print("  " + text)
