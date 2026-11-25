"""
graph.py — plot functions, equations and inequalities.

The graph is an interactive page (assets/grapher.js): drag to pan, scroll to zoom,
hover to trace, intercepts / vertex / intersections are marked with exact labels.
On the desktop it opens in the browser; on the website it appears next to the console.
If no browser is available, a text graph is printed instead.
"""
import math
import os
import re
import webbrowser

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr
from ..paths import asset_path
from ..registry import command
from .algebra import numeric_roots

X, Y = sp.symbols("x y")
_RECIP = {sp.sec: lambda a: 1 / sp.cos(a), sp.csc: lambda a: 1 / sp.sin(a), sp.cot: lambda a: 1 / sp.tan(a)}
_OK_JS = re.compile(r"(?<![\w.])[A-Za-z_][\w.]*")
_ALLOWED_JS = {"x", "y", "Infinity", "NaN", "Math.PI", "Math.E"}


# ══════════════════════════════════════════════════════════════════════
#  SymPy → JavaScript
# ══════════════════════════════════════════════════════════════════════

def to_js(expr):
    """JavaScript source for an expression in x (and y), or None if it can't be translated safely."""
    e = sp.sympify(expr)
    for f, g in _RECIP.items():
        e = e.replace(f, g)
    try:
        code = sp.jscode(e)
    except Exception:
        return None
    for name in _OK_JS.findall(code):
        if name not in _ALLOWED_JS and not name.startswith("Math."):
            return None
    return code


def _lambdify(expr):
    return sp.lambdify(X, expr, "math")


def _samples(expr, lo, hi, n=3000):
    f = _lambdify(expr)
    out = []
    for i in range(n + 1):
        x = lo + (hi - lo) * i / n
        try:
            y = float(f(x))
            out.append([x, y if math.isfinite(y) else None])
        except Exception:
            out.append([x, None])
    return out


# ══════════════════════════════════════════════════════════════════════
#  key points (intercepts, vertex / extrema, intersections)
# ══════════════════════════════════════════════════════════════════════

def real_roots(expr, lo=-50.0, hi=50.0):
    """[(float, exact-or-None)] real roots: exact when the polynomial factors into degree ≤ 2 pieces."""
    expr = sp.together(sp.simplify(expr))
    num = sp.fraction(expr)[0]
    try:
        if num.is_polynomial(X) and num.has(X):
            facs = sp.factor_list(num)[1]
            if all(sp.degree(f, X) <= 2 for f, _ in facs):
                out = []
                for f, _ in facs:
                    for r in sp.solve(f, X):
                        if r.is_real:
                            out.append((float(sp.N(r)), sp.simplify(r)))
                return sorted(set(out), key=lambda t: t[0])
    except Exception:
        pass
    return [(r, None) for r in numeric_roots(expr, X, lo, hi)]


def _label(x, y, xe=None, ye=None):
    xs = mstr(xe) if xe is not None else approx(x, 5)
    ys = mstr(ye) if ye is not None else approx(y, 5)
    if len(xs) > 22 or len(ys) > 22:
        xs, ys = approx(x, 5), approx(y, 5)
    return f"({xs}, {ys})"


def key_points(fns, lo, hi, limit=12):
    """fns = [(expr, label)] → list of point dicts. Never raises; skips anything it can't compute."""
    pts = []
    seen = set()

    def add(x, y, xe, ye, kind):
        k = (round(x, 6), round(y, 6))
        if k in seen or len(pts) >= limit or not (math.isfinite(x) and math.isfinite(y)):
            return
        seen.add(k)
        pts.append({"x": x, "y": y, "label": _label(x, y, xe, ye), "kind": kind})

    for expr, _ in fns:
        try:
            y0 = expr.subs(X, 0)
            if y0.is_real and y0.is_finite:
                add(0.0, float(sp.N(y0)), sp.Integer(0), sp.simplify(y0), "y-intercept")
        except Exception:
            pass
        try:
            for r, re_ in real_roots(expr, lo, hi):
                add(r, 0.0, re_, sp.Integer(0), "x-intercept")
        except Exception:
            pass
        try:
            d1 = sp.diff(expr, X)
            d2 = sp.diff(d1, X)
            quad = expr.is_polynomial(X) and sp.degree(expr, X) == 2
            for r, re_ in real_roots(d1, lo, hi):
                yv = expr.subs(X, re_ if re_ is not None else r)
                s2 = d2.subs(X, re_ if re_ is not None else r)
                kind = "vertex" if quad else ("local min" if s2 > 0 else "local max" if s2 < 0 else "critical point")
                add(r, float(sp.N(yv)), re_, sp.simplify(yv) if re_ is not None else None, kind)
        except Exception:
            pass
    for i in range(len(fns)):
        for j in range(i + 1, len(fns)):
            try:
                diff = sp.simplify(fns[i][0] - fns[j][0])
                if diff == 0:
                    continue
                for r, re_ in real_roots(diff, lo, hi):
                    yv = fns[i][0].subs(X, re_ if re_ is not None else r)
                    add(r, float(sp.N(yv)), re_, sp.simplify(yv) if re_ is not None else None, "intersection")
            except Exception:
                pass
    return pts


# ══════════════════════════════════════════════════════════════════════
#  turning typed items into series
# ══════════════════════════════════════════════════════════════════════

def _need_vars(e, allowed, text):
    extra = e.free_symbols - allowed
    if extra:
        names = ", ".join(sorted(s.name for s in extra))
        raise MathError(f"I can only graph in x and y, but '{text}' also has {names}. "
                        f"Give {names} a value first (e.g. {sorted(extra, key=str)[0]} = 2).")


def build_series(ctx, items, lo, hi):
    series, fns = [], []
    for raw in items:
        t = raw.strip()
        if not t:
            continue
        if t in ctx.fn_src:                       # a bare function name:  plot f
            t = f"{t}(x)"
        rel = P.split_relation(t)
        if rel and len(rel[1]) == 1:
            l, r = (ctx.expr(p) for p in rel[0])
            op = {"<=": "<=", ">=": ">=", "<": "<", ">": ">"}.get(rel[1][0])
            if op is None:
                raise MathError("Graphing ≠ isn't supported — graph the equation instead.")
            F = sp.expand(l - r)
            _need_vars(F, {X, Y}, t)
            js = to_js(F)
            if js is None:
                raise MathError(f"I can't draw '{t}' as an inequality.")
            series.append({"type": "rel", "js": js, "op": op, "label": mstr(sp.Rel(l, r, {"<=": "<=", ">=": ">=", "<": "<", ">": ">"}[op]))})
            continue
        eq = P.split_equation(t)
        if eq:
            ltxt, rtxt = eq[0].strip(), eq[1].strip()
            l, r = ctx.expr(ltxt), ctx.expr(rtxt)
            F = sp.expand(l - r)
            _need_vars(F, {X, Y}, t)
            if l == Y and not r.has(Y):
                _add_fn(series, fns, r, lo, hi)
            elif r == Y and not l.has(Y):
                _add_fn(series, fns, l, lo, hi)
            elif F.is_polynomial(Y) and sp.degree(F, Y) == 1 and not sp.Poly(F, Y).LC().has(X, Y):
                _add_fn(series, fns, sp.expand(sp.solve(F, Y)[0]), lo, hi)      # a line like 3x + 2y = 6
            elif not F.has(Y):
                roots = [v for v in sp.solve(F, X) if v.is_real]
                if not roots:
                    raise MathError(f"'{t}' has no real x-values to draw.")
                for v in roots:
                    series.append({"type": "vline", "x": float(sp.N(v)), "label": f"x = {mstr(v)}"})
            else:
                js = to_js(F)
                if js is None:
                    raise MathError(f"I can't draw '{t}'.")
                series.append({"type": "implicit", "js": js, "label": mstr(sp.Eq(l, r, evaluate=False))})
            continue
        e = ctx.expr(t)
        _need_vars(e, {X, Y}, t)
        if e.has(Y) and not e.has(X) and e.free_symbols == {Y}:
            raise MathError("Graph y in terms of x, e.g.  plot y = 2x+1  (or use an equation like x^2+y^2=25).")
        if e.has(Y):
            raise MathError("That has both x and y — add an equals sign, e.g.  plot x^2+y^2=25")
        _add_fn(series, fns, e, lo, hi)
    return series, fns


def _add_fn(series, fns, e, lo, hi):
    js = to_js(e)
    s = {"type": "fn", "label": "y = " + mstr(e)}
    if js is not None:
        s["js"] = js
    else:
        span = max(abs(lo), abs(hi)) * 3
        s["samples"] = _samples(e, -span, span)
    series.append(s)
    fns.append((e, s["label"]))


# ══════════════════════════════════════════════════════════════════════
#  output: browser page, website, or text
# ══════════════════════════════════════════════════════════════════════

def render_html(payload) -> str:
    with open(asset_path("graph_template.html"), encoding="utf-8") as f:
        tpl = f.read()
    with open(asset_path("grapher.js"), encoding="utf-8") as f:
        js = f.read()
    with open(asset_path("grapher.css"), encoding="utf-8") as f:
        css = f.read()
    import json
    data = json.dumps(payload).replace("</", "<\\/")
    return (tpl.replace("__TITLE__", payload.get("title", "Graph").replace("<", "&lt;")).replace("__CSS__", css)
            .replace("__JS__", js.replace("</script", "<\\/script")).replace("__DATA__", data))


def desktop_sink(data_dir):
    """Graph sink for the desktop app: write data/graph.html and open it. Returns False if that failed."""
    def sink(payload):
        folder = data_dir or os.getcwd()
        path = os.path.join(folder, "graph.html")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(render_html(payload))
        except OSError as err:
            raise MathError(f"I couldn't save the graph page ({err}).")
        try:
            opened = webbrowser.open("file://" + path.replace("\\", "/") if os.name == "nt" else "file://" + path)
        except Exception:
            opened = False
        if opened:
            print(f"  Graph opened in your browser.   (saved as {path})")
        return bool(opened)
    return sink


def ascii_plot(fns, lo, hi, width=76, height=22, ymin=None, ymax=None):
    marks = "*#@+ox&"
    xs = [lo + (hi - lo) * c / (width - 1) for c in range(width)]
    cols = []
    for expr, _ in fns:
        f = _lambdify(expr)
        col = []
        for x in xs:
            try:
                y = float(f(x))
                col.append(y if math.isfinite(y) else None)
            except Exception:
                col.append(None)
        cols.append(col)
    vals = sorted(y for c in cols for y in c if y is not None)
    if not vals:
        return ["(nothing to draw in that range)"]
    if ymin is None or ymax is None:
        a, b = vals[int(len(vals) * 0.03)], vals[int(len(vals) * 0.97)]
        if b - a < 1e-9:
            a, b = a - 1, b + 1
        pad = (b - a) * 0.1
        ymin, ymax = a - pad, b + pad
    grid = [[" "] * width for _ in range(height)]
    ry = lambda y: int(round((ymax - y) / (ymax - ymin) * (height - 1)))
    if ymin <= 0 <= ymax:
        for c in range(width):
            grid[ry(0)][c] = "─"
    if lo <= 0 <= hi:
        cc = int(round((0 - lo) / (hi - lo) * (width - 1)))
        for r in range(height):
            grid[r][cc] = "┼" if grid[r][cc] == "─" else "│"
    for k, col in enumerate(cols):
        prev = None
        for c, y in enumerate(col):
            if y is None or not (ymin <= y <= ymax):
                prev = None
                continue
            r = ry(y)
            grid[r][c] = marks[k % len(marks)]
            if prev is not None and abs(r - prev) > 1 and abs(r - prev) < height // 2:
                for rr in range(min(r, prev) + 1, max(r, prev)):
                    if grid[rr][c] == " ":
                        grid[rr][c] = marks[k % len(marks)]
            prev = r
    out = []
    for r, row in enumerate(grid):
        label = f"{ymax - (ymax - ymin) * r / (height - 1):8.3g} " if r % 4 == 0 else " " * 9
        out.append(label + "".join(row))
    out.append(" " * 9 + f"{lo:<8.3g}" + " " * (width - 16) + f"{hi:>8.3g}")
    for k, (_, lab) in enumerate(fns):
        out.append(f"   {marks[k % len(marks)]}  {lab}")
    return out


# ══════════════════════════════════════════════════════════════════════
#  commands
# ══════════════════════════════════════════════════════════════════════

def _window(rest):
    lo, hi, ylo, yhi = None, None, None, None
    m = re.search(r"\bx\s+from\s+(\S+)\s+to\s+(\S+)", rest)
    if m:
        lo, hi = m.group(1), m.group(2)
        rest = rest[:m.start()] + rest[m.end():]
    m = re.search(r"\by\s+from\s+(\S+)\s+to\s+(\S+)", rest)
    if m:
        ylo, yhi = m.group(1), m.group(2)
        rest = rest[:m.start()] + rest[m.end():]
    return rest.strip(), lo, hi, ylo, yhi


@command("plot", "Functions & Graphs", "plot <f, g, …> [x from a to b] [y from c to d] [ascii]",
         "Graph functions, equations (even circles), and inequalities — interactive, with intercepts, vertex and intersections marked.",
         aliases=("graph", "plotgui", "plot_gui"),
         examples=("plot x^2-4x+3", "plot sin(x), cos(x) x from -2pi to 2pi", "plot x^2+y^2=25", "plot y>2x+1", "plot f, g",
                   "plot 1/x y from -10 to 10", "plot ascii x^3-3x"))
def plot(ctx, a):
    text = a.need("what to graph, e.g. x^2-4x+3")
    ascii_mode = bool(re.search(r"(^|\s)ascii(\s|$)", text))
    text = re.sub(r"(^|\s)(ascii|browser|gui)(?=\s|$)", " ", text).strip()
    text, xlo, xhi, ylo, yhi = _window(text)
    lo = float(sp.N(ctx.number(xlo, "x minimum"))) if xlo else -10.0
    hi = float(sp.N(ctx.number(xhi, "x maximum"))) if xhi else 10.0
    if lo >= hi:
        raise MathError("The x-range must go from a smaller number to a bigger one.")
    items = P.split_top(text, ",;")
    if not text or not any(i.strip() for i in items):
        raise UsageError("Tell me what to graph, e.g.  plot x^2-4x+3")
    if len(items) > 8:
        raise MathError("That's a lot of graphs — please plot 8 or fewer at a time.")
    series, fns = build_series(ctx, items, lo, hi)
    payload = {"title": ",  ".join(s.get("label", "") for s in series)[:120], "series": series,
               "points": key_points(fns, lo, hi) if len(fns) <= 4 else []}
    if xlo or xhi:
        payload["xmin"], payload["xmax"] = lo, hi
    if ylo and yhi:
        payload["ymin"], payload["ymax"] = (float(sp.N(ctx.number(ylo, "y minimum"))), float(sp.N(ctx.number(yhi, "y maximum"))))
    sink = ctx.graph_sink
    if not ascii_mode and sink is not None:
        if sink(payload) is not False:
            if payload["points"]:
                print("  Marked:  " + "   ".join(p["label"] for p in payload["points"][:6]) + (" …" if len(payload["points"]) > 6 else ""))
            return
        print("  (I couldn't open a browser, so here's a text graph instead.)")
    if not fns:
        raise MathError("The text graph only handles y = f(x) curves. Use the browser graph for circles and inequalities.")
    yl, yh = (payload.get("ymin"), payload.get("ymax"))
    for line in ascii_plot(fns, lo, hi, ymin=yl, ymax=yh):
        print(line)
    if payload["points"]:
        print("  Marked:  " + "   ".join(p["label"] for p in payload["points"][:6]))


@command("scatter", "Functions & Graphs", "scatter <x values> | <y values> [line]",
         "Scatter plot of data, optionally with the least-squares line.", examples=("scatter 1 2 3 4 5 | 2 4 5 4 6 line",))
def scatter(ctx, a):
    from .stats import _pair, _reg
    want_line = bool(re.search(r"\bline\s*$", a.rest))
    if want_line:
        a.rest = re.sub(r"\s*\bline\s*$", "", a.rest)
    x, y = _pair(a, ctx)
    series = [{"type": "points", "pts": [[float(sp.N(p)), float(sp.N(q))] for p, q in zip(x, y)], "label": "data"}]
    fns, notes = [], []
    if want_line:
        mx, my, sxx, syy, sxy = _reg(x, y)
        if sxx != 0:
            m = sxy / sxx
            b = my - m * mx
            e = m * X + b
            _add_fn(series, fns, e, -10, 10)
            notes.append(f"Best-fit line:  y = {mstr(e)}")
    xs = [float(sp.N(p)) for p in x]
    pad = (max(xs) - min(xs)) * 0.15 or 1
    payload = {"title": "Scatter plot", "series": series, "points": [], "xmin": min(xs) - pad, "xmax": max(xs) + pad}
    if ctx.graph_sink is None or ctx.graph_sink(payload) is False:
        raise MathError("I couldn't open a graph window here. Try the desktop app or the website preview.")
    for n in notes:
        print("  " + n)
