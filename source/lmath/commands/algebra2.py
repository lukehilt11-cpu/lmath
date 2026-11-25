"""
algebra2.py — Algebra 1 / Algebra 2 / Pre-Calc tools, all exact.

inequality  slope  line  proportion  percent  sequence  series
completesq  quadform  polydiv  synth  remainder  complexnum  binomexp
"""
import re

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, set_str, show
from ..registry import command
from ..steps import Steps
from .algebra import pick_var, quad_formula_str, quadratic_steps

X = sp.Symbol("x")
_SUBS = str.maketrans("0123456789n+-", "₀₁₂₃₄₅₆₇₈₉ₙ₊₋")


def sub(s) -> str:
    return str(s).translate(_SUBS)


# ══════════════════════════════════════════════════════════════════════
#  inequalities
# ══════════════════════════════════════════════════════════════════════

_REL = {"<": sp.StrictLessThan, "<=": sp.LessThan, ">": sp.StrictGreaterThan, ">=": sp.GreaterThan}


def number_line(s) -> list:
    """ASCII number line for a solution set with finite boundary points."""
    pts = set()
    parts = s.args if isinstance(s, sp.Union) else [s]
    for p in parts:
        if isinstance(p, sp.Interval):
            for b in (p.start, p.end):
                if b.is_finite:
                    pts.add(b)
        elif isinstance(p, sp.FiniteSet):
            pts |= set(p.args)
    pts = sorted(pts, key=lambda t: float(sp.N(t)))
    if not pts or len(pts) > 7:
        return []
    gap = 11
    n = len(pts)
    width = gap * (n + 1)
    pos = [gap * (i + 1) for i in range(n)]
    line = [" "] * (width + 1)

    def inside(val):
        try:
            return bool(s.contains(val))
        except Exception:
            return False

    bounds = [-1e9] + [float(sp.N(p)) for p in pts] + [1e9]
    cuts = [0] + pos + [width]
    for i in range(n + 1):
        mid = (bounds[i] + bounds[i + 1]) / 2
        if i == 0:
            mid = bounds[1] - 1
        if i == n:
            mid = bounds[n] + 1
        ch = "━" if inside(sp.Rational(mid).limit_denominator(1000)) else "─"
        for c in range(cuts[i], cuts[i + 1] + 1):
            line[c] = ch
    if line[0] == "━":
        line[0] = "◄"
    if line[width] == "━":
        line[width] = "►"
    labels = [" "] * (width + 6)
    for p, c in zip(pts, pos):
        line[c] = "●" if inside(p) else "○"
        t = mstr(p)
        start = max(0, c - len(t) // 2)
        for k, chh in enumerate(t):
            if start + k < len(labels):
                labels[start + k] = chh
    return ["  " + "".join(line), "  " + "".join(labels).rstrip()]


def _sign_chart(expr, v, op, lines):
    """Critical points and a test value in each interval."""
    num, den = sp.fraction(sp.together(expr))
    crit = set()
    for part in (num, den):
        if part.has(v):
            for r in sp.solveset(part, v, sp.S.Reals):
                crit.add(r)
    crit = sorted(crit, key=lambda t: float(sp.N(t)))
    if not crit:
        return
    lines.append("Critical points (where the expression is 0 or undefined): " + ", ".join(mstr(c) for c in crit))
    edges = [None] + crit + [None]
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if lo is None:
            t = hi - 1 if hi.is_Integer else sp.floor(hi) - 1
        elif hi is None:
            t = lo + 1 if lo.is_Integer else sp.ceiling(lo) + 1
        else:
            t = (lo + hi) / 2
        val = expr.subs(v, t)
        sign = "+" if val > 0 else "-" if val < 0 else "0"
        a = "-∞" if lo is None else mstr(lo)
        b = "∞" if hi is None else mstr(hi)
        lines.append(f"  ({a}, {b}):  test {v.name} = {mstr(t)}  →  {mstr(val)}  ({sign})")


@command("inequality", "Algebra 1/2 & Pre-Calc", "inequality <inequality>",
         "Solve inequalities (linear, compound, absolute value, quadratic, rational) with a number line.",
         aliases=("ineq",), examples=("inequality 2x+3>7", "inequality -3<2x+1<=7", "inequality |2x-1|<5",
                                       "inequality x^2-5x+6<0", "inequality (x+1)/(x-2)>=0"))
def inequality(ctx, a):
    text = a.need("inequality (e.g. 2x+3>7)")
    rel = P.split_relation(text)
    if not rel:
        raise UsageError("That needs an inequality sign (<, >, <=, >=). Example:  inequality 2x+3>7")
    pieces, ops = rel
    if any(o == "!=" for o in ops):
        raise MathError("I can't do ≠ here — use  solve  for the equation, then exclude those values.")
    exprs = [ctx.expr(p) for p in pieces]
    v = pick_var(exprs)
    if v is None:
        raise MathError("There's no variable to solve for.")
    vr = sp.Symbol(v.name, real=True)
    sets, lines = [], []
    shown = f"{' '.join([mstr(exprs[0])] + sum(([('≤' if o == '<=' else '≥' if o == '>=' else o), mstr(e)] for o, e in zip(ops, exprs[1:])), []))}"
    for i, o in enumerate(ops):
        r = _REL[o](exprs[i].subs(v, vr), exprs[i + 1].subs(v, vr))
        if r in (sp.true, sp.false):
            sets.append(sp.S.Reals if r == sp.true else sp.S.EmptySet)
            continue
        sets.append(sp.solve_univariate_inequality(r, vr, relational=False))
    result = sets[0]
    for s_ in sets[1:]:
        result = sp.Intersection(result, s_)

    with Steps(f"Solve: {shown}", ctx) as s:
        s.step("Start with the inequality", shown)
        if len(ops) == 1:
            diff = sp.expand(exprs[0] - exprs[1])
            if diff.is_polynomial(v) and sp.degree(diff, v) == 1 and not diff.has(sp.Abs):
                A, B = diff.coeff(v, 1), diff.coeff(v, 0)
                sym = {"<": "<", "<=": "≤", ">": ">", ">=": "≥"}
                l, r_ = sp.expand(exprs[0]), sp.expand(exprs[1])
                al, bl, ar, br = l.coeff(v, 1), l.coeff(v, 0), r_.coeff(v, 1), r_.coeff(v, 0)
                op = ops[0]
                if ar != 0:
                    s.step(f"Get the {v.name}-terms on one side", f"{mstr((al - ar) * v + bl)} {sym[op]} {mstr(br)}")
                if bl != 0:
                    s.step(f"{'Subtract' if bl > 0 else 'Add'} {mstr(abs(bl))} {'from' if bl > 0 else 'to'} both sides",
                           f"{mstr(A * v)} {sym[op]} {mstr(br - bl)}")
                if A != 1:
                    flip = A < 0
                    new = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}[op] if flip else op
                    s.step(f"Divide both sides by {mstr(A)}" + (" — dividing by a negative flips the sign!" if flip else ""),
                           f"{v.name} {sym[new]} {mstr((br - bl) / A)}")
            elif not diff.has(sp.Abs):
                chart = []
                _sign_chart(sp.together(diff), v, ops[0], chart)
                if chart:
                    s.step("Move everything to one side and find where it changes sign",
                           f"{mstr(diff)} {({'<': '<', '<=': '≤', '>': '>', '>=': '≥'})[ops[0]]} 0")
                    for c in chart:
                        s.note(c.strip()) if c.startswith("  ") else s.note(c)
            else:
                s.step("Split the absolute value into two inequalities and combine the results")
        else:
            s.step("Solve each part and keep only the values that satisfy both")
        s.step("Solution set (interval notation)", set_str(result))
        s.result("Solution: " + _as_inequality(result, v))
        for ln in number_line(result):
            s.result(ln.strip("\n")) if False else None
    for ln in number_line(result):
        print(ln)


def _as_inequality(s, v) -> str:
    if s == sp.S.EmptySet:
        return "no solution"
    if s == sp.S.Reals:
        return "all real numbers"
    n = v.name
    if isinstance(s, sp.Interval):
        lo_inf, hi_inf = s.start == -sp.oo, s.end == sp.oo
        if lo_inf:
            return f"{n} {'<' if s.right_open else '≤'} {mstr(s.end)}"
        if hi_inf:
            return f"{n} {'>' if s.left_open else '≥'} {mstr(s.start)}"
        return f"{mstr(s.start)} {'<' if s.left_open else '≤'} {n} {'<' if s.right_open else '≤'} {mstr(s.end)}"
    if isinstance(s, sp.FiniteSet):
        return " or ".join(f"{n} = {mstr(t)}" for t in sorted(s.args, key=lambda q: float(sp.N(q))))
    if isinstance(s, sp.Union):
        return "  or  ".join(_as_inequality(p, v) for p in sorted(s.args, key=lambda q: float(sp.N(q.inf if hasattr(q, 'inf') else min(q.args)))))
    return set_str(s)


# ══════════════════════════════════════════════════════════════════════
#  lines & slope
# ══════════════════════════════════════════════════════════════════════

def standard_form(m, b):
    """y = mx + b → (A, B, C) integers with A ≥ 0:  Ax + By = C."""
    m, b = sp.Rational(m), sp.Rational(b)
    den = sp.ilcm(m.q, b.q)
    A, B, C = -m * den, sp.Integer(den), b * den
    g = sp.igcd(int(A), int(B), int(C)) or 1
    A, B, C = A / g, B / g, C / g
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return int(A), int(B), int(C)


def _std_str(A, B, C):
    x = X
    y = sp.Symbol("y")
    return mstr(sp.Eq(A * x + B * y, C, evaluate=False))


def line_lines(m, b, point=None):
    """Every form of a non-vertical line y = mx + b."""
    A, B, C = standard_form(m, b)
    lines = [f"Slope-intercept:  y = {mstr(sp.expand(m * X + b))}",
             f"Standard form:    {_std_str(A, B, C)}"]
    if point is not None:
        x1, y1 = point
        lines.insert(0, f"Point-slope:      y {'-' if y1 >= 0 else '+'} {mstr(abs(y1))} = {mstr(m)}(x {'-' if x1 >= 0 else '+'} {mstr(abs(x1))})")
    lines.append(f"y-intercept:      (0, {mstr(b)})")
    lines.append(f"x-intercept:      " + (f"({mstr(-b / m)}, 0)" if m != 0 else ("none (horizontal line)" if b != 0 else "every point")))
    return lines


def _points(ctx, text):
    pairs = re.findall(r"\(([^()]*?),([^()]*?)\)", text)
    if len(pairs) >= 2:
        return [ctx.number(t, "coordinate") for t in (pairs[0][0], pairs[0][1], pairs[1][0], pairs[1][1])]
    words = text.replace(",", " ").split()
    if len(words) < 4:
        words = words + [ctx.ask(n) for n in ("x1", "y1", "x2", "y2")[len(words):]]
    return [ctx.number(w, "coordinate") for w in words[:4]]


@command("slope", "Algebra 1/2 & Pre-Calc", "slope <x1> <y1> <x2> <y2>   or   slope (x1,y1) (x2,y2)",
         "Slope between two points, the line's equation in every form, distance and midpoint.",
         examples=("slope 1 2 3 8", "slope (0,3) (4,-1)", "slope 2 5 2 9"))
def slope(ctx, a):
    x1, y1, x2, y2 = _points(ctx, a.rest)
    dx, dy = x2 - x1, y2 - y1
    lines = [f"Points: ({mstr(x1)}, {mstr(y1)}) and ({mstr(x2)}, {mstr(y2)})",
             f"rise = {mstr(y2)} − {mstr(y1) if y1 >= 0 else '(' + mstr(y1) + ')'} = {mstr(dy)}",
             f"run  = {mstr(x2)} − {mstr(x1) if x1 >= 0 else '(' + mstr(x1) + ')'} = {mstr(dx)}"]
    if dx == 0 and dy == 0:
        raise MathError("Those are the same point — there's no line to measure.")
    if dx == 0:
        lines += ["slope m = undefined (vertical line)", f"Equation: x = {mstr(x1)}"]
    else:
        m = dy / dx
        b = y1 - m * x1
        kind = "rising" if m > 0 else "falling" if m < 0 else "horizontal"
        lines += [f"slope m = rise/run = {mstr(m)}   ({kind})", ""] + line_lines(m, b, (x1, y1))
        lines += ["", f"A parallel line has slope {mstr(m)}"]
        lines.append(f"A perpendicular line has slope {mstr(-1 / m) if m != 0 else 'undefined'}")
    d = sp.sqrt(dx ** 2 + dy ** 2)
    lines += ["", f"Distance = {show(d)}", f"Midpoint = ({mstr((x1 + x2) / 2)}, {mstr((y1 + y2) / 2)})"]
    box("Slope", lines)


@command("line", "Algebra 1/2 & Pre-Calc", "line <m> <b>   or   line <equation>",
         "All forms of a line from a slope and intercept, or from an equation.",
         examples=("line 2 -3", "line y=2x+3", "line 2x+3y=6"))
def line(ctx, a):
    text = a.need("slope and intercept, or an equation")
    eq = P.split_equation(text)
    y = sp.Symbol("y")
    if eq:
        e = ctx.expr(eq[0]) - ctx.expr(eq[1])
        if not e.has(y) and e.has(X):
            box("Line", [f"Vertical line  x = {mstr(sp.solve(e, X)[0])}", "slope: undefined"])
            return
        sol = sp.solve(e, y)
        if not sol:
            raise MathError("I couldn't solve that for y — is it a line?")
        yy = sp.expand(sol[0])
        if sp.degree(yy, X) > 1:
            raise MathError("That isn't a straight line (it has x² or higher).")
        m, b = yy.coeff(X, 1), yy.coeff(X, 0)
    else:
        w = text.replace(",", " ").split()
        if len(w) < 2:
            raise UsageError("Give a slope and a y-intercept, e.g.  line 2 -3")
        m, b = ctx.number(w[0], "slope"), ctx.number(w[1], "intercept")
    box("Line", line_lines(m, b))


# ══════════════════════════════════════════════════════════════════════
#  proportions & percents
# ══════════════════════════════════════════════════════════════════════

@command("proportion", "Algebra 1/2 & Pre-Calc", "proportion <a/b = c/d>",
         "Solve a proportion by cross-multiplying.", examples=("proportion 3/4 = x/20", "proportion 5/x = 15/6"))
def proportion(ctx, a):
    text = a.need("proportion (e.g. 3/4 = x/20)")
    if text.lower().startswith("percent"):
        return percent(ctx, type(a)(ctx, text[7:]))
    eq = P.split_equation(text)
    if not eq:
        raise UsageError("A proportion needs an = sign, e.g.  proportion 3/4 = x/20")
    l, r = ctx.expr(eq[0]), ctx.expr(eq[1])
    v = pick_var([l, r])
    if v is None:
        raise MathError("There's no unknown in that proportion.")
    ln, ld = sp.fraction(sp.together(l))
    rn, rd = sp.fraction(sp.together(r))
    with Steps(f"Proportion: {mstr(l)} = {mstr(r)}", ctx) as s:
        s.step("Cross-multiply:  a/b = c/d  →  a·d = b·c", f"{mstr(ln * rd)} = {mstr(ld * rn)}")
        sol = sp.solve(sp.Eq(ln * rd, ld * rn), v)
        if not sol:
            s.result("No solution")
            return
        s.step(f"Solve for {v.name}", f"{v.name} = {mstr(sol[0])}")
        s.step("Check", f"{mstr(l.subs(v, sol[0]))} = {mstr(r.subs(v, sol[0]))}  ✓")
        s.result(f"{v.name} = {show(sol[0])}")


@command("percent", "Algebra 1/2 & Pre-Calc", "percent <35 of 80 | 28 is what percent of 80 | 28 is 35% of what | change 50 to 65>",
         "Percent problems, solved and explained.",
         examples=("percent 35 of 80", "percent 28 is what percent of 80", "percent 28 is 35% of what", "percent change 50 to 65"))
def percent(ctx, a):
    t = a.need("percent problem").strip().lower().replace("%", "")
    n = r"(-?[\d./]+)"
    m = re.match(rf"change\s+(?:from\s+)?{n}\s+to\s+{n}$", t)
    if m:
        old, new = ctx.number(m.group(1)), ctx.number(m.group(2))
        ch = (new - old) / old * 100
        box("Percent change", [f"change = new − old = {mstr(new - old)}",
                               f"percent change = change ÷ old × 100 = {mstr(new - old)}/{mstr(old)} × 100",
                               f"= {show(ch)}%  ({'increase' if ch > 0 else 'decrease' if ch < 0 else 'no change'})"])
        return
    m = re.match(rf"{n}\s+is\s+what\s+(?:percent|pct)?\s*of\s+{n}$", t)
    if m:
        part, whole = ctx.number(m.group(1)), ctx.number(m.group(2))
        box("Percent", [f"part ÷ whole × 100 = {mstr(part)}/{mstr(whole)} × 100", f"= {show(part / whole * 100)}%"])
        return
    m = re.match(rf"{n}\s+is\s+{n}\s*(?:percent|pct)?\s+of\s+what$", t)
    if m:
        part, pc = ctx.number(m.group(1)), ctx.number(m.group(2))
        box("Percent", [f"part ÷ (percent ÷ 100) = {mstr(part)} ÷ {mstr(pc / 100)}", f"whole = {show(part / (pc / 100))}"])
        return
    m = re.match(rf"{n}\s*(?:percent|pct)?\s+of\s+{n}$", t)
    if m:
        pc, whole = ctx.number(m.group(1)), ctx.number(m.group(2))
        box("Percent", [f"{mstr(pc)}% of {mstr(whole)} = {mstr(pc / 100)} × {mstr(whole)}", f"= {show(pc / 100 * whole)}"])
        return
    raise UsageError("Try one of:  percent 35 of 80   |   percent 28 is what percent of 80   |   percent 28 is 35% of what   |   percent change 50 to 65")


# ══════════════════════════════════════════════════════════════════════
#  sequences & series
# ══════════════════════════════════════════════════════════════════════

def _terms(f, n, limit=10):
    return ", ".join(mstr(f(i)) for i in range(1, min(n, limit) + 1)) + (", …" if n > limit else "")


@command("sequence", "Algebra 1/2 & Pre-Calc", "sequence arith <a1> <d> [n]  |  sequence geo <a1> <r> [n]  |  sequence <t1> <t2> <t3> …",
         "Arithmetic and geometric sequences: formula, terms, and the nth term (or detect the pattern from terms).",
         examples=("sequence arith 3 4 20", "sequence geo 2 3 8", "sequence 2 5 8 11", "sequence 3 6 12 24"))
def sequence(ctx, a):
    w = a.rest.replace(",", " ").split()
    if not w:
        w = a.ctx.ask("kind (arith/geo) or list of terms").replace(",", " ").split()
    n_sym = sp.Symbol("n")
    kind = w[0].lower()
    if kind in ("arith", "arithmetic", "geo", "geometric"):
        if len(w) < 3:
            w += [ctx.ask("a1" if len(w) == 1 else ("d" if kind.startswith("a") else "r"))] * (3 - len(w))
        a1, k = ctx.number(w[1], "first term"), ctx.number(w[2], "common difference/ratio")
        n = int(ctx.number(w[3], "n")) if len(w) > 3 else 10
        arith = kind.startswith("a")
    else:
        vals = [ctx.number(t, "term") for t in w]
        if len(vals) < 3:
            raise UsageError("Give at least 3 terms, e.g.  sequence 2 5 8 11")
        d = vals[1] - vals[0]
        if all(vals[i + 1] - vals[i] == d for i in range(len(vals) - 1)):
            arith, a1, k, n = True, vals[0], d, len(vals) + 3
        elif vals[0] != 0 and all(vals[i] != 0 for i in vals and range(len(vals))) and \
                all(sp.simplify(vals[i + 1] / vals[i] - vals[1] / vals[0]) == 0 for i in range(len(vals) - 1)):
            arith, a1, k, n = False, vals[0], vals[1] / vals[0], len(vals) + 3
        else:
            box("Sequence", ["Not arithmetic (no common difference) and not geometric (no common ratio).",
                             "Differences: " + ", ".join(mstr(vals[i + 1] - vals[i]) for i in range(len(vals) - 1))])
            return
    if arith:
        f = lambda i: a1 + (i - 1) * k
        explicit = sp.expand(a1 + (n_sym - 1) * k)
        lines = ["Arithmetic sequence", f"first term a₁ = {mstr(a1)},   common difference d = {mstr(k)}",
                 f"Explicit:  aₙ = a₁ + (n − 1)d = {mstr(a1)} + (n − 1)({mstr(k)}) = {mstr(explicit)}",
                 f"Recursive: a₁ = {mstr(a1)},  aₙ = aₙ₋₁ {'+' if k >= 0 else '-'} {mstr(abs(k))}"]
    else:
        f = lambda i: a1 * k ** (i - 1)
        lines = ["Geometric sequence", f"first term a₁ = {mstr(a1)},   common ratio r = {mstr(k)}",
                 f"Explicit:  aₙ = a₁·rⁿ⁻¹ = {mstr(a1)}·({mstr(k)})ⁿ⁻¹",
                 f"Recursive: a₁ = {mstr(a1)},  aₙ = {mstr(k)}·aₙ₋₁"]
    lines += ["", f"First terms: {_terms(f, n)}", f"a{sub(n)} = {show(f(n))}"]
    box("Sequence", lines)


@command("series", "Algebra 1/2 & Pre-Calc", "series arith <a1> <d> <n>  |  series geo <a1> <r> <n>  |  series geo_inf <a1> <r>",
         "Sum of a sequence: arithmetic, geometric, or an infinite geometric series.",
         examples=("series arith 3 4 20", "series geo 2 3 8", "series geo_inf 1 1/2"))
def series(ctx, a):
    w = a.rest.replace(",", " ").split()
    if len(w) < 3:
        raise UsageError("Examples:  series arith 3 4 20   |   series geo 2 3 8   |   series geo_inf 1 1/2")
    kind = w[0].lower()
    a1, k = ctx.number(w[1], "first term"), ctx.number(w[2], "d or r")
    if kind in ("geo_inf", "inf", "infinite"):
        if abs(k) >= 1:
            box("Infinite geometric series", [f"r = {mstr(k)}, and |r| ≥ 1, so the series diverges (no finite sum)."])
        else:
            box("Infinite geometric series", ["Converges because |r| < 1.", "S = a₁ / (1 − r)",
                                               f"S = {mstr(a1)} / (1 − {mstr(k) if k >= 0 else '(' + mstr(k) + ')'}) = {show(a1 / (1 - k))}"])
        return
    if len(w) < 4:
        raise UsageError("Also tell me how many terms n, e.g.  series arith 3 4 20")
    n = int(ctx.number(w[3], "n"))
    if kind.startswith("a"):
        an = a1 + (n - 1) * k
        S = sp.Rational(n, 2) * (a1 + an)
        box("Arithmetic series", ["Sₙ = n/2 · (a₁ + aₙ)", f"aₙ = a₁ + (n − 1)d = {mstr(an)}",
                                   f"S{sub(n)} = {n}/2 · ({mstr(a1)} + {mstr(an)}) = {show(S)}"])
    else:
        if k == 1:
            S = a1 * n
        else:
            S = a1 * (1 - k ** n) / (1 - k)
        box("Geometric series", ["Sₙ = a₁(1 − rⁿ) / (1 − r)" if k != 1 else "r = 1, so Sₙ = n·a₁",
                                  f"S{sub(n)} = {mstr(a1)}(1 − {mstr(k)}^{n}) / (1 − {mstr(k)}) = {show(S)}"])


# ══════════════════════════════════════════════════════════════════════
#  completing the square, quadratic formula
# ══════════════════════════════════════════════════════════════════════

@command("completesq", "Algebra 1/2 & Pre-Calc", "completesq <quadratic expression or equation>",
         "Complete the square: vertex form, vertex, and solutions if it's an equation.",
         aliases=("completesquare",), examples=("completesq x^2+6x+5", "completesq 2x^2-8x+3=0"))
def completesq(ctx, a):
    text = a.need("quadratic (e.g. x^2+6x+5)")
    eq = P.split_equation(text)
    e = ctx.expr(eq[0]) - ctx.expr(eq[1]) if eq else ctx.expr(text)
    v = pick_var([e])
    if v is None or not e.is_polynomial(v) or sp.degree(e, v) != 2:
        raise MathError("I need a quadratic (highest power 2), like x^2+6x+5.")
    p = sp.Poly(sp.expand(e), v)
    A, B, C = p.coeff_monomial(v ** 2), p.coeff_monomial(v), p.coeff_monomial(1)
    h = B / (2 * A)
    k = C - B ** 2 / (4 * A)
    with Steps(f"Complete the square: {mstr(sp.expand(e))}{' = 0' if eq else ''}", ctx) as s:
        s.step("Start with  ax² + bx + c", f"a = {mstr(A)},  b = {mstr(B)},  c = {mstr(C)}")
        if A != 1:
            s.step(f"Factor {mstr(A)} out of the x-terms", f"{mstr(A)}({mstr(v ** 2 + (B / A) * v)}) + {mstr(C)}")
        s.step("Take half of the x-coefficient and square it", f"({mstr(B / A)} ÷ 2)² = ({mstr(h)})² = {mstr(h ** 2)}")
        add = A * h ** 2
        s.step("Add and subtract that inside, so the value doesn't change",
               f"{mstr(A) + '(' if A != 1 else ''}{mstr(v ** 2 + (B / A) * v + h ** 2)}{')' if A != 1 else ''} + {mstr(C)} − {mstr(add)}")
        form = sp.Mul(A, sp.Pow(v + h, 2, evaluate=False), evaluate=False) if A != 1 else sp.Pow(v + h, 2, evaluate=False)
        vertex_form = f"{mstr(form)} {'+' if k >= 0 else '-'} {mstr(abs(k))}" if k != 0 else mstr(form)
        s.step("Write as a perfect square", vertex_form)
        s.result(f"Vertex form:  y = {vertex_form}")
        s.result(f"Vertex: ({mstr(-h)}, {mstr(k)})   ({'opens up, minimum' if A > 0 else 'opens down, maximum'})")
        if eq:
            s.step("Solve for x:  take the square root of both sides")
            s.result(quad_formula_str(*[int(t * sp.ilcm(*[sp.Rational(q).q for q in (A, B, C)])) for t in (A, B, C)], var=v.name))


@command("quadform", "Algebra 1/2 & Pre-Calc", "quadform <a> <b> <c>",
         "The quadratic formula, one step at a time, for ax² + bx + c = 0.", examples=("quadform 2 3 -1", "quadform 1 -4 13"))
def quadform(ctx, a):
    w = a.rest.replace(",", " ").split()
    vals = [ctx.number(t, "coefficient") for t in w[:3]]
    while len(vals) < 3:
        vals.append(ctx.number(ctx.ask("abc"[len(vals)]), "coefficient"))
    A, B, C = vals
    if A == 0:
        raise MathError("a can't be 0 — then it isn't a quadratic.")
    quadratic_steps(ctx, A, B, C, X, f"Quadratic formula: {mstr(A * X ** 2 + B * X + C)} = 0", factor_first=False)


# ══════════════════════════════════════════════════════════════════════
#  polynomial division
# ══════════════════════════════════════════════════════════════════════

def _split_two(a, what="two polynomials"):
    parts = a.parts("|;") if a.rest else []
    if len(parts) == 1 and " by " in parts[0]:
        parts = [t.strip() for t in parts[0].split(" by ")]
    if len(parts) != 2:
        ws = a.rest.split()
        if len(ws) == 2:
            parts = ws
        else:
            raise UsageError(f"Give {what} separated by |   e.g.  polydiv x^3-2x^2+x-3 | x-1")
    return parts


@command("polydiv", "Algebra 1/2 & Pre-Calc", "polydiv <dividend> | <divisor>",
         "Polynomial long division, step by step.", aliases=("longdiv",),
         examples=("polydiv x^3-2x^2+x-3 | x-1", "polydiv 6x^3+x^2-5x+2 | 2x+1"))
def polydiv(ctx, a):
    n_txt, d_txt = _split_two(a)
    num, den = ctx.expr(n_txt), ctx.expr(d_txt)
    v = pick_var([num, den])
    if v is None:
        raise MathError("These aren't polynomials in a variable.")
    N, D = sp.Poly(num, v), sp.Poly(den, v)
    if D.is_zero:
        raise MathError("Can't divide by 0.")
    rem, quo = N, sp.Integer(0)
    with Steps(f"Divide: ({mstr(num)}) ÷ ({mstr(den)})", ctx) as s:
        while not rem.is_zero and rem.degree() >= D.degree():
            t = sp.together(rem.LC() / D.LC()) * v ** (rem.degree() - D.degree())
            prod = sp.Poly(sp.expand(t * den), v)
            s.step(f"Divide leading terms:  {mstr(rem.LC() * v ** rem.degree())} ÷ {mstr(D.LC() * v ** D.degree())} = {mstr(t)}")
            s.note(f"Multiply:  {mstr(t)}·({mstr(den)}) = {mstr(prod.as_expr())}")
            rem = rem - prod
            s.note(f"Subtract:  remainder so far = {mstr(rem.as_expr())}")
            quo += t
        q, r = sp.expand(quo), rem.as_expr()
        s.result(f"Quotient:  {mstr(q)}")
        s.result(f"Remainder: {mstr(r)}")
        s.result(f"{mstr(num)} = ({mstr(den)})({mstr(q)})" + _plus(r))


def _plus(r) -> str:
    """' + 3' / ' − 3' / '' for a remainder term."""
    r = sp.sympify(r)
    if r == 0:
        return ""
    return f" + {mstr(r)}" if r > 0 else f" - {mstr(-r)}"


def _synth_rows(coeffs, root):
    row, carry = [], 0
    for c in coeffs:
        carry = c + carry * root
        row.append(carry)
    return row


@command("synth", "Algebra 1/2 & Pre-Calc", "synth <polynomial> <root>",
         "Synthetic division by (x − root).", aliases=("synthetic",), examples=("synth x^3-2x^2+x-3 1", "synth 2x^3-3x^2+4 -1/2"))
def synth(ctx, a):
    text = a.need("polynomial and root, e.g. x^3-2x^2+x-3 1")
    parts = text.rsplit(None, 1)
    if len(parts) != 2:
        raise UsageError("Give a polynomial then the root, e.g.  synth x^3-2x^2+x-3 1")
    poly = ctx.expr(parts[0])
    r = ctx.number(parts[1], "root")
    v = pick_var([poly])
    P_ = sp.Poly(poly, v)
    coeffs = P_.all_coeffs()
    out = _synth_rows(coeffs, r)
    bring = [0] + [out[i] * r for i in range(len(out) - 1)]
    w = max(len(mstr(t)) for t in coeffs + out + bring) + 2
    fmt = lambda row: "".join(mstr(t).rjust(w) for t in row)
    table = [f"{mstr(r).rjust(w)} │{fmt(coeffs)}", f"{' ' * w} │{fmt([''] + [mstr(t) for t in bring[1:]]) if False else ''.join((mstr(t) if i else '').rjust(w) for i, t in enumerate(bring))}",
             f"{' ' * w} └{'─' * (w * len(coeffs))}", f"{' ' * w}  {fmt(out)}"]
    q = sum(c * v ** (len(out) - 2 - i) for i, c in enumerate(out[:-1]))
    box(f"Synthetic division by (x − {mstr(r)})", table + ["",
        f"Quotient:  {mstr(sp.expand(q))}", f"Remainder: {mstr(out[-1])}",
        f"{mstr(poly)} = ({mstr(v - r)})({mstr(sp.expand(q))})" + _plus(out[-1])]
        + (["So (x − " + mstr(r) + ") is a factor and x = " + mstr(r) + " is a root."] if out[-1] == 0 else []))


@command("remainder", "Algebra 1/2 & Pre-Calc", "remainder <polynomial> <a>",
         "Remainder theorem: the remainder dividing by (x − a) is f(a).", examples=("remainder x^3-2x^2+x-3 1",))
def remainder(ctx, a):
    text = a.need("polynomial and value, e.g. x^3-2x^2+x-3 1")
    parts = text.rsplit(None, 1)
    if len(parts) != 2:
        raise UsageError("Give a polynomial then a value, e.g.  remainder x^3-2x^2+x-3 1")
    poly = ctx.expr(parts[0])
    r = ctx.number(parts[1], "value")
    v = pick_var([poly])
    val = poly.subs(v, r)
    box("Remainder theorem", [f"f({mstr(r)}) = {mstr(val)}",
                              f"The remainder when dividing by ({mstr(v - r)}) is {mstr(val)}.",
                              f"(x − {mstr(r)}) {'IS' if val == 0 else 'is NOT'} a factor."])


# ══════════════════════════════════════════════════════════════════════
#  complex numbers
# ══════════════════════════════════════════════════════════════════════

def _cplx(z) -> str:
    z = sp.expand(z)
    re_, im_ = sp.re(z), sp.im(z)
    if im_ == 0:
        return mstr(re_)
    if re_ == 0:
        return mstr(im_ * sp.I)
    return f"{mstr(re_)} {'+' if im_ > 0 else '-'} {mstr(abs(im_) * sp.I)}"


@command("complexnum", "Algebra 1/2 & Pre-Calc", "complexnum <add|sub|mul|div|power|modulus|conj> <z1> [z2|n]",
         "Complex-number arithmetic in a + bi form, with modulus and polar angle.", aliases=("complex",),
         examples=("complexnum add 3+2i 1-4i", "complexnum mul 3+2i 1-4i", "complexnum div 3+2i 1-4i",
                   "complexnum power 1+i 8", "complexnum modulus 3+4i"))
def complexnum(ctx, a):
    w = a.rest.split(None, 1)
    if not w:
        raise UsageError("Example:  complexnum add 3+2i 1-4i")
    op = w[0].lower()
    rest = w[1] if len(w) > 1 else ""
    toks = [t.strip() for t in rest.split("|")] if "|" in rest else rest.split()
    z1 = ctx.expr(toks[0]) if toks else None
    if z1 is None:
        raise UsageError("Give a complex number, e.g. 3+2i (no spaces).")
    lines = []
    if op in ("add", "sub", "mul", "div"):
        if len(toks) < 2:
            raise UsageError("This needs two complex numbers, e.g.  complexnum add 3+2i 1-4i")
        z2 = ctx.expr(toks[1])
        sym = {"add": "+", "sub": "-", "mul": "·", "div": "÷"}[op]
        lines.append(f"({_cplx(z1)}) {sym} ({_cplx(z2)})")
        if op == "add":
            res = z1 + z2
        elif op == "sub":
            res = z1 - z2
        elif op == "mul":
            res = z1 * z2
            lines.append(f"FOIL:  {mstr(sp.expand(z1 * z2, complex=False))}   (using i² = −1)")
        else:
            if z2 == 0:
                raise MathError("Can't divide by 0.")
            conj = sp.conjugate(z2)
            res = sp.simplify(z1 / z2)
            lines.append(f"Multiply top and bottom by the conjugate ({_cplx(conj)}):")
            lines.append(f"  ({_cplx(sp.expand(z1 * conj))}) / ({mstr(sp.expand(z2 * conj))})")
        lines.append(f"= {_cplx(sp.simplify(res))}")
    elif op in ("power", "pow"):
        n = int(ctx.number(toks[1] if len(toks) > 1 else ctx.ask("power n"), "power"))
        lines += [f"({_cplx(z1)})^{n}", f"= {_cplx(sp.expand(z1 ** n))}"]
    elif op in ("modulus", "mod", "abs", "conj", "conjugate", "polar"):
        pass
    else:
        raise UsageError("Operations: add, sub, mul, div, power, modulus, conj")
    if op in ("modulus", "mod", "abs", "conj", "conjugate", "polar") or True:
        zz = z1 if op not in ("add", "sub", "mul", "div", "power", "pow") else None
        if zz is not None:
            r = sp.simplify(sp.Abs(zz))
            lines += [f"conjugate = {_cplx(sp.conjugate(zz))}",
                      f"modulus |z| = √({mstr(sp.re(zz) ** 2)} + {mstr(sp.im(zz) ** 2)}) = {show(r)}",
                      f"angle θ = {show(sp.arg(zz))} rad = " + (mstr(sp.arg(zz) * 180 / sp.pi) if (sp.arg(zz) * 180 / sp.pi).is_Rational else approx(sp.arg(zz) * 180 / sp.pi)) + "°"]
    box("Complex numbers", lines)


# ══════════════════════════════════════════════════════════════════════
#  binomial expansion
# ══════════════════════════════════════════════════════════════════════

@command("binomexp", "Algebra 1/2 & Pre-Calc", "binomexp <a> <b> <n> [term k]",
         "Expand (a + b)ⁿ using the binomial theorem, or find just the kth term.",
         aliases=("binomial_exp",), examples=("binomexp x 2 5", "binomexp 2x y 4", "binomexp x 3 10 term 4"))
def binomexp(ctx, a):
    m = re.search(r"\bterm\s+(\d+)\s*$", a.rest)
    term = int(m.group(1)) if m else None
    rest = a.rest[:m.start()].strip() if m else a.rest
    w = rest.split()
    if len(w) < 3:
        raise UsageError("Give a, b, and n, e.g.  binomexp x 2 5   (that's (x + 2)⁵)")
    A, B, n = ctx.expr(w[0]), ctx.expr(w[1]), int(ctx.number(w[2], "n"))
    if n < 0 or n > 30:
        raise MathError("Use a whole-number exponent from 0 to 30.")
    terms = [sp.binomial(n, k) * A ** (n - k) * B ** k for k in range(n + 1)]
    pascal = [sp.binomial(n, k) for k in range(n + 1)]
    lines = [f"({mstr(A)} + {mstr(B)}){str(n).translate(str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹'))}",
             f"Pascal's row {n}: {'  '.join(map(str, pascal))}",
             "General term:  C(n,k)·a^(n−k)·b^k"]
    if term is not None:
        if not 1 <= term <= n + 1:
            raise MathError(f"There are {n + 1} terms — pick a term from 1 to {n + 1}.")
        k = term - 1
        lines += [f"Term {term} (k = {k}):  C({n},{k})·({mstr(A)})^{n - k}·({mstr(B)})^{k}",
                  f"= {mstr(pascal[k])}·{mstr(A ** (n - k))}·{mstr(B ** k)}", f"= {mstr(sp.expand(terms[k]))}"]
    else:
        lines += ["", "Terms: " + " + ".join(mstr(sp.expand(t)) for t in terms).replace("+ -", "− "),
                  "", "Expanded: " + mstr(sp.expand((A + B) ** n))]
    box("Binomial expansion", lines)
