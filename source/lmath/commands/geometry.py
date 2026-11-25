"""
geometry.py — polygons, angles, similarity, transformations, coordinates, circles, proofs.

Results keep π and radicals exact (area = 25π), with a decimal beside them.
"""
import re

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, show, show_or_approx
from ..registry import command
from ..steps import Steps
from .algebra import pick_var
from .algebra2 import _points

DEG = sp.pi / 180


def exact_trig(f, angle):
    """sin/cos/tan of an exact angle, simplified (radicals when sympy knows them)."""
    return sp.nsimplify(sp.simplify(f(angle)), [sp.sqrt(2), sp.sqrt(3), sp.sqrt(5)]) if False else sp.radsimp(sp.simplify(f(angle)))


# ══════════════════════════════════════════════════════════════════════
#  polygons
# ══════════════════════════════════════════════════════════════════════

_NAMES = {3: "triangle", 4: "square", 5: "pentagon", 6: "hexagon", 7: "heptagon", 8: "octagon",
          9: "nonagon", 10: "decagon", 12: "dodecagon"}


@command("polygon", "Geometry", "polygon <n> side|radius|apothem <value>",
         "Regular polygon: angles, apothem, radius, perimeter and area (exact when possible).",
         examples=("polygon 6 side 5", "polygon 5 radius 10", "polygon 8 apothem 4"))
def polygon(ctx, a):
    w = a.rest.replace("=", " ").split()
    if len(w) < 3:
        w = w + [ctx.ask(p) for p in ("n (number of sides)", "side / radius / apothem", "value")[len(w):]]
    n = int(ctx.number(w[0], "number of sides"))
    if n < 3:
        raise MathError("A polygon needs at least 3 sides.")
    kind = w[1].lower()[0]
    val = ctx.number(w[2], "length")
    t = sp.tan(sp.pi / n)
    sn = sp.sin(sp.pi / n)
    if kind == "s":
        s_ = val
    elif kind == "r":
        s_ = 2 * val * sn
    elif kind == "a":
        s_ = 2 * val * t
    else:
        raise UsageError("Say whether the length is a side, radius, or apothem.")
    s_ = sp.radsimp(sp.simplify(s_))
    ap = sp.radsimp(sp.simplify(s_ / (2 * t)))
    R = sp.radsimp(sp.simplify(s_ / (2 * sn)))
    per = sp.simplify(n * s_)
    area = sp.radsimp(sp.simplify(per * ap / 2))
    interior = sp.Rational((n - 2) * 180, n)
    nice = n in (3, 4, 6, 12)
    def fmt(e):
        return ("= " + show_or_approx(e)) if (nice or sp.sympify(e).is_Rational) else "≈ " + approx(e)
    box(f"Regular {_NAMES.get(n, f'{n}-gon')} (n = {n})", [
        f"Interior angle  = (n−2)·180°/n = {mstr(interior)}°",
        f"Exterior angle  = 360°/n = {mstr(sp.Rational(360, n))}°",
        f"Sum of interior angles = {(n - 2) * 180}°",
        f"Diagonals = n(n−3)/2 = {n * (n - 3) // 2}",
        "",
        f"Side      s {fmt(s_)}",
        f"Apothem   a {fmt(ap)}",
        f"Radius    R {fmt(R)}",
        f"Perimeter P {fmt(per)}",
        f"Area = ½·a·P {fmt(area)}"])


# ══════════════════════════════════════════════════════════════════════
#  angles
# ══════════════════════════════════════════════════════════════════════

@command("angles", "Geometry", "angles <supplementary|complementary|vertical|parallel|triangle> <values>",
         "Angle relationships — with numbers, or with expressions to solve for x.",
         examples=("angles supplementary 110", "angles complementary 3x+10 2x-5", "angles triangle 50 60",
                   "angles parallel 65"))
def angles(ctx, a):
    w = a.rest.split()
    if not w:
        w = [ctx.ask("kind (supplementary/complementary/vertical/parallel/triangle)")]
    kind = w[0].lower()
    vals = [ctx.expr(t) for t in w[1:]]
    if not vals:
        vals = [ctx.expr(ctx.ask("angle"))]
    total = {"supplementary": 180, "complementary": 90, "triangle": 180, "linear": 180}.get(kind)
    if total and any(v.free_symbols for v in vals):
        expr = sum(vals) - total
        v = pick_var(vals)
        sol = sp.solve(expr, v)
        if not sol:
            raise MathError("Those can't add up to " + str(total) + "°.")
        with Steps(f"{kind.title()} angles: {' + '.join(mstr(t) for t in vals)} = {total}°", ctx) as s:
            s.step(f"Write the equation (the angles add to {total}°)", f"{' + '.join(mstr(t) for t in vals)} = {total}")
            s.step(f"Solve for {v.name}", f"{v.name} = {mstr(sol[0])}")
            s.step("Find each angle", ",  ".join(f"{mstr(t)} = {mstr(t.subs(v, sol[0]))}°" for t in vals))
            s.result(f"{v.name} = {mstr(sol[0])};  angles: " + ", ".join(f"{mstr(t.subs(v, sol[0]))}°" for t in vals))
        return
    if kind in ("supplementary", "linear"):
        box("Supplementary angles (sum to 180°)", [f"{mstr(vals[0])}° + ? = 180°", f"? = {mstr(180 - vals[0])}°"])
    elif kind == "complementary":
        box("Complementary angles (sum to 90°)", [f"{mstr(vals[0])}° + ? = 90°", f"? = {mstr(90 - vals[0])}°"])
    elif kind == "vertical":
        box("Vertical angles", [f"Vertical angles are equal: ? = {mstr(vals[0])}°",
                                f"The two other angles are each {mstr(180 - vals[0])}° (supplementary)."])
    elif kind in ("parallel", "transversal"):
        x = vals[0]
        box("Parallel lines cut by a transversal", [
            f"Given one angle = {mstr(x)}°", f"Equal ({mstr(x)}°): corresponding, alternate interior, alternate exterior, vertical",
            f"Supplementary ({mstr(180 - x)}°): co-interior (same-side interior), linear pairs"])
    elif kind == "triangle":
        if len(vals) == 2:
            third = 180 - vals[0] - vals[1]
            if third <= 0:
                raise MathError("Those two angles already add to 180° or more — they can't be in a triangle.")
            box("Triangle angle sum", [f"{mstr(vals[0])}° + {mstr(vals[1])}° + ? = 180°", f"? = {mstr(third)}°",
                                       f"Exterior angle at the third vertex = {mstr(180 - third)}°"])
        else:
            raise UsageError("Give two angles to find the third, e.g.  angles triangle 50 60")
    else:
        raise UsageError("Kinds: supplementary, complementary, vertical, parallel, triangle")


# ══════════════════════════════════════════════════════════════════════
#  similarity
# ══════════════════════════════════════════════════════════════════════

def _side_list(ctx, tok):
    out = []
    for t in tok.split(","):
        t = t.strip()
        out.append(None if t in ("_", "?", "x", "") else ctx.number(t, "side"))
    return out


@command("similar", "Geometry", "similar <sides1> <sides2>   (comma lists; _ for unknown)",
         "Similar figures: scale factor, missing sides, perimeter and area ratios.",
         examples=("similar 3,4,5 _,8,_", "similar 6,9 4,_"))
def similar(ctx, a):
    parts = a.parts("|;") if "|" in a.rest or ";" in a.rest else a.rest.split()
    if len(parts) != 2:
        raise UsageError("Give two lists of sides, e.g.  similar 3,4,5 _,8,_  (use _ for an unknown side)")
    s1, s2 = _side_list(ctx, parts[0]), _side_list(ctx, parts[1])
    if len(s1) != len(s2):
        raise MathError("Both figures need the same number of sides.")
    k = None
    for p, q in zip(s1, s2):
        if p is not None and q is not None:
            k = q / p
            break
    if k is None:
        raise MathError("I need at least one pair of corresponding sides that are both known.")
    lines = [f"Scale factor (figure 2 ÷ figure 1) = {mstr(k)}", "ratio of sides = " + mstr(k.p) + " : " + mstr(k.q) if k.is_Rational else ""]
    new1 = [p if p is not None else q / k for p, q in zip(s1, s2)]
    new2 = [q if q is not None else p * k for p, q in zip(s1, s2)]
    lines += ["Figure 1 sides: " + ", ".join(mstr(t) for t in new1), "Figure 2 sides: " + ", ".join(mstr(t) for t in new2),
              f"Perimeter ratio = {mstr(k)}", f"Area ratio = k² = {mstr(k ** 2)}", f"Volume ratio (if 3-D) = k³ = {mstr(k ** 3)}"]
    box("Similar figures", [l for l in lines if l])


# ══════════════════════════════════════════════════════════════════════
#  transformations
# ══════════════════════════════════════════════════════════════════════

@command("transform", "Geometry", "transform <reflect|rotate|translate|dilate> <x> <y> …",
         "Transform a point: reflect over an axis/line, rotate (about any center), translate, or dilate.",
         examples=("transform reflect 3 -2 x-axis", "transform reflect 3 -2 y=x", "transform rotate 3 -2 90",
                   "transform rotate 3 -2 90 about 1 1", "transform translate 3 -2 4 5", "transform dilate 3 -2 2"))
def transform(ctx, a):
    rest = a.rest.replace("about", " about ")
    w = rest.split()
    if len(w) < 4:
        raise UsageError("Example:  transform rotate 3 -2 90   (kind, x, y, then details)")
    kind = w[0].lower()
    x, y = ctx.number(w[1], "x"), ctx.number(w[2], "y")
    arg = w[3:]
    P_ = f"({mstr(x)}, {mstr(y)})"
    if kind == "reflect":
        line = "".join(arg).lower().replace(" ", "")
        if line in ("x-axis", "xaxis", "y=0"):
            img, rule = (x, -y), "(x, y) → (x, −y)"
        elif line in ("y-axis", "yaxis", "x=0"):
            img, rule = (-x, y), "(x, y) → (−x, y)"
        elif line == "y=x":
            img, rule = (y, x), "(x, y) → (y, x)"
        elif line in ("y=-x", "y=−x"):
            img, rule = (-y, -x), "(x, y) → (−y, −x)"
        elif line.startswith("x="):
            c = ctx.number(line[2:], "line")
            img, rule = (2 * c - x, y), f"(x, y) → ({mstr(2 * c)} − x, y)"
        elif line.startswith("y="):
            c = ctx.number(line[2:], "line")
            img, rule = (x, 2 * c - y), f"(x, y) → (x, {mstr(2 * c)} − y)"
        else:
            raise UsageError("Reflect over: x-axis, y-axis, y=x, y=-x, x=<number>, or y=<number>")
        label = f"over {''.join(arg)}"
    elif kind == "rotate":
        ang = ctx.expr(arg[0]) if arg else ctx.number(ctx.ask("angle in degrees"))
        h, k = sp.Integer(0), sp.Integer(0)
        if "about" in arg:
            i = arg.index("about")
            h, k = ctx.number(arg[i + 1]), ctx.number(arg[i + 2])
        th = ang * DEG
        c, s_ = sp.cos(th), sp.sin(th)
        img = (sp.radsimp(sp.simplify(h + (x - h) * c - (y - k) * s_)), sp.radsimp(sp.simplify(k + (x - h) * s_ + (y - k) * c)))
        rule = {90: "(x, y) → (−y, x)", 180: "(x, y) → (−x, −y)", 270: "(x, y) → (y, −x)", -90: "(x, y) → (y, −x)"}.get(
            int(ang) if ang.is_Integer else None, "x' = x·cosθ − y·sinθ,  y' = x·sinθ + y·cosθ") if (h, k) == (0, 0) else "rotate about the center"
        label = f"{mstr(ang)}° counterclockwise about ({mstr(h)}, {mstr(k)})"
    elif kind == "translate":
        dx, dy = ctx.number(arg[0]), ctx.number(arg[1])
        img, rule, label = (x + dx, y + dy), f"(x, y) → (x {'+' if dx >= 0 else '-'} {mstr(abs(dx))}, y {'+' if dy >= 0 else '-'} {mstr(abs(dy))})", f"by <{mstr(dx)}, {mstr(dy)}>"
    elif kind == "dilate":
        f = ctx.number(arg[0])
        h, k = (ctx.number(arg[1]), ctx.number(arg[2])) if len(arg) >= 3 else (sp.Integer(0), sp.Integer(0))
        img, rule, label = (h + f * (x - h), k + f * (y - k)), f"(x, y) → ({mstr(f)}x, {mstr(f)}y)" if (h, k) == (0, 0) else "dilate about the center", f"by scale factor {mstr(f)} from ({mstr(h)}, {mstr(k)})"
    else:
        raise UsageError("Kinds: reflect, rotate, translate, dilate")
    box(f"{kind.title()} {label}", [f"Rule: {rule}", f"{P_}  →  ({mstr(img[0])}, {mstr(img[1])})"])


# ══════════════════════════════════════════════════════════════════════
#  coordinates
# ══════════════════════════════════════════════════════════════════════

@command("midpoint", "Geometry", "midpoint <x1> <y1> <x2> <y2>", "Midpoint of a segment.",
         examples=("midpoint 1 2 7 8", "midpoint (1,2) (7,8)"))
def midpoint(ctx, a):
    x1, y1, x2, y2 = _points(ctx, a.rest)
    box("Midpoint", ["M = ((x₁ + x₂)/2, (y₁ + y₂)/2)", f"M = (({mstr(x1)} + {mstr(x2)})/2, ({mstr(y1)} + {mstr(y2)})/2)",
                     f"M = ({mstr((x1 + x2) / 2)}, {mstr((y1 + y2) / 2)})"])


@command("distance", "Geometry", "distance <x1> <y1> <x2> <y2>", "Distance between two points (exact radical).",
         examples=("distance 1 2 4 6", "distance (0,0) (3,5)"))
def distance(ctx, a):
    x1, y1, x2, y2 = _points(ctx, a.rest)
    dx, dy = x2 - x1, y2 - y1
    box("Distance", ["d = √((x₂ − x₁)² + (y₂ − y₁)²)", f"d = √(({mstr(dx)})² + ({mstr(dy)})²) = √{mstr(dx ** 2 + dy ** 2)}",
                     f"d = {show(sp.sqrt(dx ** 2 + dy ** 2))}"])


@command("section", "Geometry", "section <x1> <y1> <x2> <y2> <m> <n>",
         "Point that divides a segment in the ratio m : n.", examples=("section 0 0 10 5 2 3",))
def section(ctx, a):
    w = a.rest.replace("(", " ").replace(")", " ").replace(",", " ").split()
    if len(w) < 6:
        raise UsageError("Example:  section 0 0 10 5 2 3   (two points, then the ratio m n)")
    x1, y1, x2, y2, m, n = (ctx.number(t, "number") for t in w[:6])
    if m + n == 0:
        raise MathError("m + n can't be 0.")
    px, py = (n * x1 + m * x2) / (m + n), (n * y1 + m * y2) / (m + n)
    box("Section formula", [f"P divides the segment in the ratio {mstr(m)} : {mstr(n)}",
                            "P = ((n·x₁ + m·x₂)/(m+n), (n·y₁ + m·y₂)/(m+n))", f"P = ({mstr(px)}, {mstr(py)})"])


# ══════════════════════════════════════════════════════════════════════
#  circle geometry
# ══════════════════════════════════════════════════════════════════════

@command("circlegeo", "Geometry", "circlegeo <arc|sector|chord|inscribed|tangent> <values>",
         "Circle geometry: arc length, sector area, chords, inscribed angles, tangents.",
         examples=("circlegeo arc 60 6", "circlegeo sector 90 4", "circlegeo chord 5 3", "circlegeo inscribed 40",
                   "circlegeo tangent 5 13"))
def circlegeo(ctx, a):
    w = a.rest.split()
    if not w:
        w = [ctx.ask("kind (arc/sector/chord/inscribed/tangent)")]
    kind = w[0].lower()
    v = [ctx.number(t, "number") for t in w[1:]]
    need = {"arc": 2, "sector": 2, "chord": 2, "tangent": 2, "inscribed": 1}.get(kind)
    if need is None:
        raise UsageError("Kinds: arc, sector, chord, inscribed, tangent")
    while len(v) < need:
        v.append(ctx.number(ctx.ask({"arc": "angle° then radius", "sector": "angle° then radius", "chord": "radius then distance from center",
                                     "tangent": "radius then distance from center to external point", "inscribed": "intercepted arc°"}[kind]), "number"))
    if kind == "arc":
        th, r = v
        box("Arc length", [f"s = (θ/360°)·2πr = ({mstr(th)}/360)·2π·{mstr(r)}", f"s = {show(th / 360 * 2 * sp.pi * r)}",
                           f"(the full circumference is {show(2 * sp.pi * r)})"])
    elif kind == "sector":
        th, r = v
        box("Sector area", [f"A = (θ/360°)·πr² = ({mstr(th)}/360)·π·{mstr(r)}²", f"A = {show(th / 360 * sp.pi * r ** 2)}",
                            f"(the full circle is {show(sp.pi * r ** 2)})"])
    elif kind == "chord":
        r, d = v
        if abs(d) > r:
            raise MathError("The chord's distance from the center can't be bigger than the radius.")
        box("Chord length", [f"half-chord = √(r² − d²) = √({mstr(r)}² − {mstr(d)}²) = {show(sp.sqrt(r ** 2 - d ** 2))}",
                             f"chord = 2·√(r² − d²) = {show(2 * sp.sqrt(r ** 2 - d ** 2))}"])
    elif kind == "inscribed":
        arc = v[0]
        box("Inscribed angle", [f"inscribed angle = ½ · intercepted arc = ½ · {mstr(arc)}° = {mstr(arc / 2)}°",
                                f"The central angle on the same arc is {mstr(arc)}°."])
    else:
        r, d = v
        if d <= r:
            raise MathError("The point must be outside the circle (distance > radius).")
        box("Tangent length", ["A tangent is perpendicular to the radius, so  t² + r² = d²",
                               f"t = √(d² − r²) = √({mstr(d)}² − {mstr(r)}²) = {show(sp.sqrt(d ** 2 - r ** 2))}"])


# ══════════════════════════════════════════════════════════════════════
#  two-column proofs
# ══════════════════════════════════════════════════════════════════════

@command("proof", "Geometry", "proof <statement :: reason ; statement :: reason ; …>",
         "Lay out a two-column proof (type it inline, or run `proof` alone to enter it line by line).",
         examples=("proof AB ≅ CD :: Given ; AB = CD :: Definition of congruence",))
def proof(ctx, a):
    pairs = []
    if a.rest:
        for chunk in a.rest.split(";"):
            if "::" in chunk:
                st, rs = chunk.split("::", 1)
            elif "|" in chunk:
                st, rs = chunk.split("|", 1)
            else:
                raise UsageError("Write each line as  statement :: reason  and separate lines with ;")
            pairs.append((st.strip(), rs.strip()))
    else:
        if not ctx.interactive:
            raise UsageError("Write the proof inline:  proof statement :: reason ; statement :: reason")
        print("  Enter each line. Leave the statement blank to finish.")
        while True:
            st = ctx.ask(f"statement {len(pairs) + 1}")
            if not st:
                break
            pairs.append((st, ctx.ask("reason")))
    if not pairs:
        raise MathError("There's nothing in the proof yet.")
    w1 = max(len("Statements"), max(len(f"{i + 1}. {s}") for i, (s, _) in enumerate(pairs)))
    w2 = max(len("Reasons"), max(len(r) for _, r in pairs))
    lines = [f"{'Statements'.ljust(w1)} │ Reasons", "─" * w1 + "─┼─" + "─" * w2]
    lines += [f"{(str(i + 1) + '. ' + s).ljust(w1)} │ {r}" for i, (s, r) in enumerate(pairs)]
    box("Two-column proof", lines)
