"""
parse.py — one place that turns what a student types into a SymPy object.

Everything in lmath reads input through here, so every command accepts the
same natural notation:

    2x+3      3x^2y      (x+1)(x-1)     2(x+1)      x(x+1)
    1/2       0.25       35%            30°         √12        √(x+1)
    |2x-1|    π          e^x            3+2i        sin(30°)

Decimals become exact fractions (0.25 → 1/4), so results stay exact.
"""
import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr,
    rationalize, standard_transformations,
)

from .errors import MathError

_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application, convert_xor, rationalize,
)


def _log(x, base=None):
    """log(x) is base 10 (as in Algebra 2); log(x, b) is base b; ln(x) is natural."""
    return sp.log(x, 10 if base is None else base)


def _root(x, n=2):
    return sp.root(x, n)


FUNCS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "sec": sp.sec, "csc": sp.csc, "cot": sp.cot,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "sqrt": sp.sqrt, "cbrt": sp.cbrt, "root": _root,
    "exp": sp.exp, "ln": sp.log, "log": _log,
    "abs": sp.Abs, "Abs": sp.Abs, "sign": sp.sign,
    "floor": sp.floor, "ceil": sp.ceiling, "ceiling": sp.ceiling,
    "factorial": sp.factorial, "binomial": sp.binomial,
    "gcd": sp.gcd, "lcm": sp.lcm, "min": sp.Min, "max": sp.Max,
    "Min": sp.Min, "Max": sp.Max,
    "re": sp.re, "im": sp.im, "conjugate": sp.conjugate, "arg": sp.arg,
}

CONSTS = {"pi": sp.pi, "e": sp.E, "i": sp.I, "oo": sp.oo, "inf": sp.oo}

GREEK = {n: sp.Symbol(n) for n in
         ("alpha", "beta", "gamma", "delta", "theta", "phi", "psi",
          "omega", "mu", "sigma", "rho", "tau", "epsilon")}

# Names the transformer's generated code refers to.
_GLOBALS = {
    "__builtins__": {},
    "Symbol": sp.Symbol, "Function": sp.Function, "Integer": sp.Integer,
    "Float": sp.Float, "Rational": sp.Rational, "Number": sp.Number,
    "Mul": sp.Mul, "Pow": sp.Pow, "Add": sp.Add, "Basic": sp.Basic,
    "Tuple": sp.Tuple, "Dummy": sp.Dummy,
}

RESERVED = set(FUNCS) | set(CONSTS) | set(GREEK) | {"x", "y", "z", "t"}
_FUNC_WORDS = "sin|cos|tan|sec|csc|cot|ln|log|sqrt|exp|abs"

_UNI = {"−": "-", "–": "-", "×": "*", "·": "*", "÷": "/", "π": "pi",
        "²": "**2", "³": "**3", "⁴": "**4", "≤": "<=", "≥": ">=", "≠": "!=",
        "“": '"', "”": '"', "’": "'"}


def base_namespace() -> dict:
    ns = {}
    ns.update(GREEK)
    ns.update(FUNCS)
    ns.update(CONSTS)
    return ns


def _abs_bars(s: str) -> str:
    """|a| → Abs(a). Bars alternate open/close, which covers everything but nesting."""
    if "|" not in s:
        return s
    out, opened = [], False
    for ch in s:
        if ch == "|":
            out.append(")" if opened else "Abs(")
            opened = not opened
        else:
            out.append(ch)
    if opened:
        raise MathError("Unbalanced | bars — an absolute value needs one on each side.")
    return "".join(out)


def prep(s: str) -> str:
    """Normalise typed notation into something SymPy's parser understands."""
    s = s.strip()
    if "__" in s or "import" in s:
        raise MathError("That doesn't look like math I can read.")
    for a, b in _UNI.items():
        s = s.replace(a, b)
    s = _abs_bars(s)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", s)
    s = re.sub(r"(\d+(?:\.\d+)?|\))\s*°", r"(\1*pi/180)", s)
    s = re.sub(r"√\s*\(", "sqrt(", s)
    s = re.sub(r"√\s*([A-Za-z0-9.]+)", r"sqrt(\1)", s)
    # 3sin(x) works already; x sin(x) typed as xsin(x) needs a hand.
    s = re.sub(rf"(?<![A-Za-z])(?!a(?:sin|cos|tan)\()([A-Za-z0-9])({_FUNC_WORDS})\(", r"\1*\2(", s)
    return s


def _friendly(s: str, err: Exception) -> MathError:
    if s.count("(") != s.count(")"):
        return MathError(f"Check your parentheses in '{s}' — they don't match up.")
    if re.search(r"[+\-*/^]\s*$", s) or re.match(r"^\s*[*/^]", s):
        return MathError(f"'{s}' looks unfinished — there's an operator with nothing after it.")
    return MathError(f"I couldn't read '{s}' as math. Try writing it like 2x+3, x^2-4, or (x+1)/(x-2).")


def parse(s: str, ns: dict = None):
    """Parse an expression string into SymPy using namespace `ns` (variables, functions)."""
    raw = s
    s = prep(s)
    if not s:
        raise MathError("Nothing to read — type an expression first.")
    local = base_namespace()
    if ns:
        local.update(ns)
    try:
        return parse_expr(s, local_dict=local, global_dict=dict(_GLOBALS),
                          transformations=_TRANSFORMS)
    except MathError:
        raise
    except Exception as err:  # SyntaxError, TokenError, TypeError, NameError, ...
        raise _friendly(raw.strip(), err) from None


_REL = re.compile(r"(<=|>=|!=|<|>)")


def split_equation(s: str):
    """Split 'lhs = rhs' on the single '='; returns None if there isn't one."""
    s = s.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=")
    for i, ch in enumerate(s):
        if ch == "=":
            prev = s[i - 1] if i else ""
            nxt = s[i + 1] if i + 1 < len(s) else ""
            if prev in "<>!=" or nxt == "=":
                continue
            return s[:i], s[i + 1:]
    return None


def split_relation(s: str):
    """Split an inequality into (pieces, ops): '-3 < 2x+1 <= 7' → (['-3','2x+1','7'], ['<','<='])."""
    s = s.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=")
    parts = _REL.split(s)
    if len(parts) < 3:
        return None
    return [p.strip() for p in parts[0::2]], parts[1::2]


def split_top(s: str, seps=",") -> list:
    """Split on separators that sit outside any brackets: 'f(1,2), x+1' → ['f(1,2)', ' x+1']."""
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch in seps and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [p for p in out]


def free_vars(*exprs) -> list:
    syms = set()
    for e in exprs:
        syms |= sp.sympify(e).free_symbols
    return sorted(syms, key=lambda v: v.name)
