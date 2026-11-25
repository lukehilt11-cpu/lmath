"""
calculus.py — derivative, integ, limit, taylor, critical, newton, gd, riemann.

SymPy does the symbolic work; results stay exact, with decimals only beside them.
"""
import math

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, best, box, mstr, pretty_lines, show
from ..registry import command
from ..steps import Steps
from .algebra import numeric_roots, pick_var

X = sp.Symbol("x")


def _expr_var(ctx, a, text=None, hint=None):
    text = text if text is not None else a.need("expression (e.g. x^3+2x)")
    e = ctx.expr(text)
    v = pick_var([e], hint)
    return e, (v if v is not None else X)


@command("deriv", "Calculus", "deriv <expression> [order=2] [at=3] [var=t]",
         "Derivative of an expression (any order), optionally evaluated at a point.",
         aliases=("derivative", "diff"), examples=("deriv x^3+2x", "deriv sin(x)*x^2", "deriv x^4 order=2", "deriv x^2+1 at=3"))
def deriv(ctx, a):
    kw = a.kw("order", "at", "var")
    e, v = _expr_var(ctx, a, hint=kw.get("var"))
    n = int(ctx.number(kw["order"], "order")) if "order" in kw else 1
    if n < 1 or n > 10:
        raise MathError("The order must be between 1 and 10.")
    d = best(sp.diff(e, v, n))
    prime = "′" * n if n <= 3 else f"⁽{n}⁾"
    lines = [f"f(x) = {mstr(e)}"] + [f"f{prime}(x) = " + pretty_lines(d)[0]] if len(pretty_lines(d)) == 1 else \
        [f"f(x) = {mstr(e)}", f"f{prime}(x) ="] + pretty_lines(d)
    if "at" in kw:
        pt = ctx.number(kw["at"], "point")
        lines.append(f"f{prime}({mstr(pt)}) = {show(d.subs(v, pt))}")
    sup = str(n).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
    box(f"d/d{v.name} [{mstr(e)}]" if n == 1 else f"d{sup}/d{v.name}{sup} [{mstr(e)}]", lines)


@command("integ", "Calculus", "integ <expression> [from a to b]",
         "Indefinite or definite integral (exact, with a decimal for definite ones).",
         aliases=("integrate",), examples=("integ x^2+3x", "integ sin(x) from 0 to pi", "integ 1/x from 1 to e",
                                           "integ e^(-x) from 0 to oo"))
def integ(ctx, a):
    found, head = a.phrase("from", "to")
    head = head.rstrip()
    if head.endswith(" dx"):
        head = head[:-3]
    e, v = _expr_var(ctx, a, text=head or a.need("expression"))
    if "from" in found or "to" in found:
        if "from" not in found or "to" not in found:
            raise UsageError("For a definite integral use:  integ <expr> from <a> to <b>")
        lo, hi = ctx.number(found["from"], "lower limit"), ctx.number(found["to"], "upper limit")
        res = sp.integrate(e, (v, lo, hi))
        if res.has(sp.Integral):
            val = sp.Integral(e, (v, lo, hi)).evalf()
            box(f"∫[{mstr(lo)}, {mstr(hi)}] {mstr(e)} d{v.name}", ["No closed form; numerically:", f"≈ {approx(val)}"])
            return
        res = sp.simplify(res)
        lines = []
        anti = sp.integrate(e, v)
        if not anti.has(sp.Integral):
            lines += [f"antiderivative F({v.name}) = {mstr(anti)}", f"F({mstr(hi)}) − F({mstr(lo)}) = {show(res)}"]
        else:
            lines.append(show(res))
        box(f"∫[{mstr(lo)}, {mstr(hi)}] {mstr(e)} d{v.name}", lines)
        return
    res = sp.integrate(e, v)
    if res.has(sp.Integral):
        raise MathError("That has no antiderivative I can write in closed form. Try a definite integral (add 'from a to b') for a numeric value.")
    box(f"∫ {mstr(e)} d{v.name}", pretty_lines(res) if len(pretty_lines(res)) > 1 else [mstr(res) + " + C"])


@command("limit", "Calculus", "limit <expression> at <point> [from left|right]",
         "Limit as x approaches a point (or ∞); shows one-sided limits when they differ.",
         aliases=("lim",), examples=("limit (x^2-1)/(x-1) at 1", "limit sin(x)/x at 0", "limit 1/x at 0 from right",
                                     "limit (1+1/x)^x at oo"))
def limit(ctx, a):
    found, head = a.phrase("at", "from")
    if "at" not in found:
        parts = head.rsplit(None, 1)
        if len(parts) != 2:
            raise UsageError("Use:  limit <expression> at <point>   e.g.  limit sin(x)/x at 0")
        head, found["at"] = parts
    e, v = _expr_var(ctx, a, text=head)
    pt = ctx.number(found["at"], "point")
    side = found.get("from", "").lower()
    lines = [f"lim({v.name}→{mstr(pt)}) {mstr(e)}"]
    if side.startswith(("l", "-")):
        lines.append(f"from the left:  {show(sp.limit(e, v, pt, '-'))}")
    elif side.startswith(("r", "+")):
        lines.append(f"from the right: {show(sp.limit(e, v, pt, '+'))}")
    else:
        L, R = sp.limit(e, v, pt, "-"), sp.limit(e, v, pt, "+")
        if L == R:
            lines.append(f"= {show(L)}")
            if e.has(sp.zoo) or sp.simplify(e.subs(v, pt)).has(sp.nan, sp.zoo) if pt.is_finite else False:
                lines.append(f"(the function itself is undefined at {v.name} = {mstr(pt)}, but the limit exists)")
        else:
            lines += [f"from the left:  {show(L)}", f"from the right: {show(R)}", "The one-sided limits differ, so the limit does not exist."]
    box("Limit", lines)


@command("taylor", "Calculus", "taylor <expression> [at a] [order n]",
         "Taylor/Maclaurin polynomial.", aliases=("series_expand",), examples=("taylor e^x order 5", "taylor sin(x) at 0 order 7", "taylor ln(x) at 1 order 4"))
def taylor(ctx, a):
    found, head = a.phrase("at", "order")
    e, v = _expr_var(ctx, a, text=head)
    pt = ctx.number(found["at"], "center") if "at" in found else sp.Integer(0)
    n = int(ctx.number(found["order"], "order")) if "order" in found else 6
    poly = sp.series(e, v, pt, n + 1).removeO()
    box(f"Taylor polynomial of degree {n} about {v.name} = {mstr(pt)}", [f"f(x) = {mstr(e)}", f"P{n}(x) = {mstr(sp.expand(poly))}" if pt == 0 else f"P{n}(x) = {mstr(poly)}"])


@command("critical", "Calculus", "critical <expression>",
         "Critical points, local max/min, inflection points, and where the function increases or decreases.",
         aliases=("critical_points",), examples=("critical x^3-3x", "critical x^4-8x^2"))
def critical(ctx, a):
    e, v = _expr_var(ctx, a)
    vr = sp.Symbol(v.name, real=True)
    f = e.subs(v, vr)
    d1, d2 = sp.diff(f, vr), sp.diff(f, vr, 2)
    cps = sp.solveset(d1, vr, sp.S.Reals)
    pts = sorted(cps.args, key=lambda t: float(sp.N(t))) if isinstance(cps, sp.FiniteSet) else []
    if not isinstance(cps, sp.FiniteSet):
        pts = [sp.Float(r, 8) for r in numeric_roots(d1, vr)]
    lines = [f"f(x) = {mstr(e)}", f"f′(x) = {mstr(sp.simplify(d1))}", f"f″(x) = {mstr(sp.simplify(d2))}", ""]
    if not pts:
        lines.append("No critical points (f′ is never 0).")
    for p in pts:
        val, second = sp.simplify(f.subs(vr, p)), sp.simplify(d2.subs(vr, p))
        if second > 0:
            kind = "local minimum"
        elif second < 0:
            kind = "local maximum"
        else:
            left, right = d1.subs(vr, p - sp.Rational(1, 100)), d1.subs(vr, p + sp.Rational(1, 100))
            kind = "local min" if left < 0 < right else "local max" if left > 0 > right else "neither (flat inflection)"
        lines.append(f"x = {mstr(p)}  →  f = {show(val)}   ({kind})")
    infl = sp.solveset(d2, vr, sp.S.Reals)
    if isinstance(infl, sp.FiniteSet) and infl.args:
        ip = sorted(infl.args, key=lambda t: float(sp.N(t)))
        keep = []
        for p in ip:
            l_, r_ = d2.subs(vr, p - sp.Rational(1, 100)), d2.subs(vr, p + sp.Rational(1, 100))
            if l_ * r_ < 0:
                keep.append(p)
        if keep:
            lines += ["", "Inflection points: " + ",  ".join(f"({mstr(p)}, {show(sp.simplify(f.subs(vr, p)))})" for p in keep)]
    if pts and len(pts) <= 6:
        edges = [None] + pts + [None]
        lines.append("")
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            t = (hi - 1) if lo is None else (lo + 1) if hi is None else (lo + hi) / 2
            lines.append(f"({'-∞' if lo is None else mstr(lo)}, {'∞' if hi is None else mstr(hi)}): " + ("increasing" if d1.subs(vr, t) > 0 else "decreasing"))
    box("Critical points", lines)


def _lambdify(e, v):
    return sp.lambdify(v, e, "math")


@command("newton", "Calculus", "newton <expression> <x0>",
         "Newton's method for a root, with each iteration shown.", aliases=("newton_method",),
         examples=("newton x^2-2 1", "newton cos(x)-x 1"))
def newton(ctx, a):
    parts = a.need("expression and starting guess, e.g. x^2-2 1").rsplit(None, 1)
    if len(parts) != 2:
        raise UsageError("Give an expression then a starting guess, e.g.  newton x^2-2 1")
    e, v = _expr_var(ctx, a, text=parts[0])
    x0 = float(sp.N(ctx.number(parts[1], "starting guess")))
    f, df = _lambdify(e, v), _lambdify(sp.diff(e, v), v)
    xi = x0
    rows = [f"n = 0   x = {xi:.10g}"]
    for n in range(1, 41):
        try:
            d = df(xi)
            if abs(d) < 1e-14:
                rows.append("The slope is 0 here — Newton's method can't continue. Try a different guess.")
                break
            new = xi - f(xi) / d
        except (ZeroDivisionError, ValueError, OverflowError):
            rows.append("Landed where the function isn't defined — try a different guess.")
            break
        rows.append(f"n = {n}   x = {new:.10g}   f(x) = {f(new):.3g}")
        done = abs(new - xi) < 1e-12
        xi = new
        if done:
            break
    if len(rows) > 12:
        rows = rows[:6] + ["   …"] + rows[-4:]
    box(f"Newton's method: {mstr(e)} = 0", rows + ["", f"Root ≈ {xi:.10g}"])


@command("gd", "Calculus", "gd <expression> <x0> [lr=0.1] [steps=100]",
         "Gradient descent toward a minimum.", aliases=("gradient_descent",), examples=("gd (x-3)^2+1 0", "gd x^4-3x^2+x 2 lr=0.01 steps=500"))
def gd(ctx, a):
    kw = a.kw("lr", "steps")
    parts = a.need("expression and starting point").rsplit(None, 1)
    if len(parts) != 2:
        raise UsageError("Give an expression then a starting point, e.g.  gd (x-3)^2+1 0")
    e, v = _expr_var(ctx, a, text=parts[0])
    lr = float(sp.N(ctx.number(kw.get("lr", "0.1"), "learning rate")))
    steps = int(ctx.number(kw.get("steps", "100"), "steps"))
    f, df = _lambdify(e, v), _lambdify(sp.diff(e, v), v)
    xi = float(sp.N(ctx.number(parts[1], "start")))
    for _ in range(steps):
        try:
            xi -= lr * df(xi)
        except OverflowError:
            raise MathError("It blew up — try a smaller learning rate (lr=0.01).")
        if not math.isfinite(xi):
            raise MathError("It blew up — try a smaller learning rate (lr=0.01).")
    box("Gradient descent", [f"f(x) = {mstr(e)}", f"start x = {parts[1]},  learning rate = {lr},  steps = {steps}",
                             f"result: x ≈ {xi:.8g}", f"f(x) ≈ {f(xi):.8g}"])


@command("riemann", "Calculus", "riemann <expression> from a to b [n=4] [method=left|right|mid|trap]",
         "Riemann (and trapezoid) sums, compared with the exact integral.",
         examples=("riemann x^2 from 0 to 2 n=4", "riemann x^2 from 0 to 2 n=4 method=right", "riemann sin(x) from 0 to pi n=100 method=trap"))
def riemann(ctx, a):
    kw = a.kw("n", "method")
    found, head = a.phrase("from", "to")
    if "from" not in found or "to" not in found:
        raise UsageError("Use:  riemann <expr> from <a> to <b> n=<count>")
    e, v = _expr_var(ctx, a, text=head)
    lo, hi = ctx.number(found["from"], "lower"), ctx.number(found["to"], "upper")
    n = int(ctx.number(kw.get("n", "4"), "n"))
    method = kw.get("method", "mid").lower()
    if n < 1 or n > 100000:
        raise MathError("n must be between 1 and 100000.")
    h = (hi - lo) / n
    exact_mode = n <= 40
    pts = []
    for i in range(n):
        if method.startswith("l"):
            x_i = lo + i * h
        elif method.startswith("r"):
            x_i = lo + (i + 1) * h
        elif method.startswith("t"):
            x_i = None
        else:
            x_i = lo + (i + sp.Rational(1, 2)) * h
        pts.append(x_i)
    if method.startswith("t"):
        xs = [lo + i * h for i in range(n + 1)]
        vals = [e.subs(v, t) if exact_mode else float(sp.N(e.subs(v, t))) for t in xs]
        total = h / 2 * (vals[0] + 2 * sum(vals[1:-1]) + vals[-1]) if n > 1 else h / 2 * (vals[0] + vals[-1])
        name = "Trapezoid"
    else:
        if exact_mode:
            vals = [e.subs(v, t) for t in pts]
            total = h * sum(vals)
        else:
            f = _lambdify(e, v)
            hf = float(sp.N(h))
            total = hf * sum(f(float(sp.N(t))) for t in pts)
        name = {"l": "Left", "r": "Right", "m": "Midpoint"}.get(method[0], "Midpoint")
    total = sp.Float(total) if isinstance(total, float) else sp.simplify(total)
    true = sp.integrate(e, (v, lo, hi))
    lines = [f"{name} sum with n = {n},  Δx = {mstr(h)}"]
    if exact_mode and n <= 8 and not method.startswith("t"):
        lines += [f"  {v.name} = {mstr(t)}  →  f = {show(e.subs(v, t))}" for t in pts]
    lines.append(f"Sum = {show(total)}")
    if not true.has(sp.Integral):
        lines += [f"Exact integral = {show(true)}", f"Error ≈ {approx(abs(sp.N(total - true)))}"]
    box(f"Riemann: ∫[{mstr(lo)}, {mstr(hi)}] {mstr(e)} d{v.name}", lines)
