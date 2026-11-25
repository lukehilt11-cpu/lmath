"""
trig.py — trig values (exact at special angles), inverse trig, triangle laws,
the unit circle, angle conversion, and area/volume of common shapes (exact, with π).
"""
import re

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, show
from ..registry import command
from ..steps import Steps

DEG = sp.pi / 180
_QUAD = {1: "I", 2: "II", 3: "III", 4: "IV"}


def parse_angle(ctx, text):
    """→ (radians, degrees). Plain numbers are degrees; π, 'rad', or ° pick the unit explicitly."""
    t = text.strip()
    rad_word = re.search(r"\s*(rad|radians?)\s*$", t, re.I)
    deg_word = re.search(r"\s*(deg|degrees?)\s*$", t, re.I)
    if rad_word:
        t = t[:rad_word.start()]
    if deg_word:
        t = t[:deg_word.start()]
    e = ctx.expr(t)
    if not e.is_number:
        raise MathError("The angle must be a number, like 30, 45°, or π/6.")
    if "°" in t or deg_word or not (rad_word or e.has(sp.pi)):
        if "°" in t:
            rad = e
        else:
            rad = e * DEG
    else:
        rad = e
    return rad, sp.simplify(rad / DEG)


def _val(e) -> str:
    e = sp.simplify(e)
    if e.has(sp.zoo, sp.nan) or e == sp.zoo:
        return "undefined"
    return show(sp.radsimp(e))


def _deg_str(d) -> str:
    d = sp.simplify(d)
    return mstr(d) if d.is_Rational else approx(d)


def _quadrant(rad):
    deg = float(sp.N(sp.simplify(rad / DEG))) % 360
    if deg == 0 or deg == 90 or deg == 180 or deg == 270:
        return "on an axis"
    return "Quadrant " + _QUAD[int(deg // 90) + 1]


def _reference(deg):
    d = float(sp.N(deg)) % 360
    if d % 90 == 0:
        return None
    return sp.nsimplify(min(d % 180, 180 - d % 180)) if d % 180 != 0 else 0


@command("trig", "Trig", "trig <angle>      (degrees by default; use π, ° or 'rad' for radians)",
         "All six trig values, exact at special angles, plus quadrant and reference angle.",
         aliases=("trig_eval",), examples=("trig 30", "trig 135", "trig pi/6", "trig 2pi/3", "trig 1 rad"))
def trig(ctx, a):
    rad, deg = parse_angle(ctx, a.need("angle (e.g. 30, 45°, pi/6)"))
    funcs = [("sin", sp.sin), ("cos", sp.cos), ("tan", sp.tan), ("csc", sp.csc), ("sec", sp.sec), ("cot", sp.cot)]
    lines = [f"Angle: {_deg_str(deg)}°  =  {show(rad)} rad", _quadrant(rad)]
    ref = None
    try:
        d = deg % 360
        if d.is_Rational and d % 90 != 0:
            ref = min(d % 180, 180 - d % 180)
            lines.append(f"Reference angle: {mstr(ref)}°")
        if deg.is_Rational and (deg < 0 or deg >= 360):
            lines.append(f"Coterminal angle in [0°, 360°): {mstr(d)}°")
    except Exception:
        pass
    lines.append("")
    for name, f in funcs:
        lines.append(f"{name}({_deg_str(deg)}°) = {_val(f(rad))}")
    box("Trig values", lines)


@command("itrig", "Trig", "itrig <asin|acos|atan> <value>",
         "Inverse trig: the principal angle, exact in radians and degrees when possible.",
         aliases=("inv_trig",), examples=("itrig asin 1/2", "itrig acos -sqrt(3)/2", "itrig atan 1"))
def itrig(ctx, a):
    w = a.rest.split(None, 1)
    if not w:
        raise UsageError("Example:  itrig asin 1/2")
    if w[0].lower().lstrip("a").startswith(("sin", "cos", "tan")) or w[0].lower() in ("asin", "acos", "atan", "arcsin", "arccos", "arctan"):
        fn, val = w[0].lower(), w[1] if len(w) > 1 else ctx.ask("value")
    else:                                                          # value first, then function
        val, fn = w[0], (w[1].lower() if len(w) > 1 else ctx.ask("function (asin/acos/atan)"))
    fn = fn.replace("arc", "a")
    table = {"asin": (sp.asin, "[−90°, 90°]"), "acos": (sp.acos, "[0°, 180°]"), "atan": (sp.atan, "(−90°, 90°)")}
    if fn not in table:
        raise UsageError("Use asin, acos, or atan.")
    v = ctx.number(val, "value")
    if fn in ("asin", "acos") and abs(v) > 1:
        raise MathError(f"{fn} only accepts values from −1 to 1.")
    r = sp.simplify(table[fn][0](v))
    box(f"{fn}({mstr(v)})", [f"= {show(r)} rad", f"= {_deg_str(r / DEG)}°", f"(principal value, range {table[fn][1]})"])


def _triangle_inputs(ctx, a, names):
    kw = a.kw(*names)
    return {k: ctx.number(v, k) for k, v in kw.items()}


@command("coslaw", "Trig", "coslaw a=5 b=7 C=60      or      coslaw a=3 b=4 c=5",
         "Law of cosines: a missing side from two sides and the angle between them, or the angles from three sides.",
         aliases=("law_of_cosines",), examples=("coslaw a=5 b=7 C=60", "coslaw a=3 b=4 c=5"))
def coslaw(ctx, a):
    v = _triangle_inputs(ctx, a, ("a", "b", "c", "A", "B", "C"))
    sides = {k: v[k] for k in "abc" if k in v}
    angs = {k: v[k] for k in "ABC" if k in v}
    with Steps("Law of cosines", ctx) as s:
        if len(sides) == 2 and len(angs) == 1:
            ang = next(iter(angs))
            need = ang.lower()
            if need in sides:
                raise MathError(f"The angle {ang} must be the one between the two given sides (opposite side {need}).")
            p, q = [sides[k] for k in "abc" if k in sides]
            theta = angs[ang]
            n1, n2 = [k for k in "abc" if k != need]
            s.step(f"Use the law of cosines:  {need}² = {n1}² + {n2}² − 2·{n1}·{n2}·cos {ang}")
            c2 = sp.simplify(p ** 2 + q ** 2 - 2 * p * q * sp.cos(theta * DEG))
            s.step("Substitute", f"{need}² = {mstr(p)}² + {mstr(q)}² − 2({mstr(p)})({mstr(q)})cos({mstr(theta)}°) = {mstr(c2)}")
            s.result(f"{need} = {show(sp.sqrt(c2))}")
        elif len(sides) == 3:
            A_, B_, C_ = sides["a"], sides["b"], sides["c"]
            if A_ + B_ <= C_ or A_ + C_ <= B_ or B_ + C_ <= A_:
                raise MathError("Those three sides can't make a triangle (the two shorter ones must add to more than the longest).")
            for ang, (x, y, z) in (("A", (B_, C_, A_)), ("B", (A_, C_, B_)), ("C", (A_, B_, C_))):
                cosv = sp.simplify((x ** 2 + y ** 2 - z ** 2) / (2 * x * y))
                th = sp.acos(cosv)
                s.step(f"cos {ang} = ({mstr(x)}² + {mstr(y)}² − {mstr(z)}²) / (2·{mstr(x)}·{mstr(y)}) = {mstr(cosv)}",
                       f"{ang} = {_deg_str(sp.simplify(th / DEG))}°")
            s.result("Angles: " + ",  ".join(f"{ang} = {_deg_str(sp.simplify(sp.acos(sp.simplify((x ** 2 + y ** 2 - z ** 2) / (2 * x * y))) / DEG))}°"
                                            for ang, (x, y, z) in (("A", (B_, C_, A_)), ("B", (A_, C_, B_)), ("C", (A_, B_, C_)))))
        else:
            raise UsageError("Give two sides and the angle between them (coslaw a=5 b=7 C=60), or all three sides (coslaw a=3 b=4 c=5).")


@command("sinlaw", "Trig", "sinlaw a=5 A=30 B=45     or     sinlaw a=5 A=30 b=8",
         "Law of sines: missing sides/angles from AAS, ASA, or SSA (shows both triangles in the ambiguous case).",
         aliases=("law_of_sines",), examples=("sinlaw a=5 A=30 B=45", "sinlaw a=5 A=30 b=8", "sinlaw a=10 A=30 b=15"))
def sinlaw(ctx, a):
    v = _triangle_inputs(ctx, a, ("a", "b", "c", "A", "B", "C"))
    sides = {k: v[k] for k in "abc" if k in v}
    angs = {k: v[k] for k in "ABC" if k in v}
    pair = next((k for k in "abc" if k in sides and k.upper() in angs), None)
    sn = lambda d: sp.sin(d * DEG)
    out = []

    def finish(A_, B_, C_, a_, b_, c_, title):
        lines = [f"Angles: A = {_deg_str(A_)}°,  B = {_deg_str(B_)}°,  C = {_deg_str(C_)}°",
                 f"Sides:  a = {show(a_)},  b = {show(b_)},  c = {show(c_)}"]
        return title, lines

    if len(angs) >= 2 and sides:
        k0 = next(iter(angs))
        missing = [k for k in "ABC" if k not in angs]
        if missing:
            angs[missing[0]] = 180 - sum(angs.values())
        if min(angs.values()) <= 0:
            raise MathError("Those angles add to 180° or more.")
        ref_side = next(k for k in "abc" if k in sides)
        ratio = sides[ref_side] / sn(angs[ref_side.upper()])
        full = {k: sp.radsimp(sp.simplify(ratio * sn(angs[k.upper()]))) for k in "abc"}
        out.append(finish(angs["A"], angs["B"], angs["C"], full["a"], full["b"], full["c"], "Triangle"))
    elif pair and len(sides) >= 2:
        other = next(k for k in "abc" if k in sides and k != pair)
        sinO = sp.simplify(sides[other] * sn(angs[pair.upper()]) / sides[pair])
        if sinO > 1:
            raise MathError("No triangle: that side is too short to reach (sin of the other angle would be more than 1).")
        O1 = sp.simplify(sp.asin(sinO) / DEG)
        candidates = [O1]
        if O1 != 90 and angs[pair.upper()] + (180 - O1) < 180:
            candidates.append(180 - O1)
        ratio = sides[pair] / sn(angs[pair.upper()])
        for idx, O in enumerate(candidates):
            third = 180 - angs[pair.upper()] - O
            if third <= 0:
                continue
            ang_map = {pair.upper(): angs[pair.upper()], other.upper(): O}
            last = next(k for k in "ABC" if k not in ang_map)
            ang_map[last] = third
            full = {k: (sides[k] if k in sides else sp.radsimp(sp.simplify(ratio * sn(ang_map[k.upper()])))) for k in "abc"}
            out.append(finish(ang_map["A"], ang_map["B"], ang_map["C"], full["a"], full["b"], full["c"],
                              f"Triangle {idx + 1}" if len(candidates) > 1 else "Triangle"))
        if len(out) > 1:
            out.append(("Note", ["This is the ambiguous case (SSA): two different triangles fit the information."]))
    else:
        raise UsageError("Give an angle with its opposite side (a=5 A=30) plus one more angle or side.")
    for title, lines in out:
        box(f"Law of sines — {title}" if title != "Note" else "Law of sines", lines)


@command("ucircle", "Trig", "ucircle <angle>", "A point on the unit circle: (cos θ, sin θ), exact.",
         aliases=("unit_circle",), examples=("ucircle 150", "ucircle 5pi/4"))
def ucircle(ctx, a):
    rad, deg = parse_angle(ctx, a.need("angle (e.g. 150, 5pi/4)"))
    c, s_ = sp.radsimp(sp.simplify(sp.cos(rad))), sp.radsimp(sp.simplify(sp.sin(rad)))
    lines = [f"θ = {_deg_str(deg)}° = {show(rad)} rad", f"(cos θ, sin θ) = ({mstr(c)}, {mstr(s_)})" + (f"   ≈ ({approx(c)}, {approx(s_)})" if not (c.is_Rational and s_.is_Rational) else ""), _quadrant(rad)]
    if deg.is_Rational and deg % 90 != 0:
        lines.append(f"Reference angle: {mstr(min((deg % 360) % 180, 180 - (deg % 360) % 180))}°")
    lines.append(f"tan θ = {_val(sp.tan(rad))}")
    box("Unit circle", lines)


@command("d2r", "Trig", "d2r <degrees>", "Degrees → radians (exact, in terms of π).", aliases=("degrees_to_radians",),
         examples=("d2r 150",))
def d2r(ctx, a):
    d = ctx.number(a.need("degrees"), "angle")
    box("Degrees → radians", [f"{mstr(d)}° × π/180 = {show(d * DEG)} rad"])


@command("r2d", "Trig", "r2d <radians>", "Radians → degrees.", aliases=("radians_to_degrees",), examples=("r2d 5pi/6", "r2d 2"))
def r2d(ctx, a):
    r = ctx.number(a.need("radians"), "angle")
    box("Radians → degrees", [f"{mstr(r)} rad × 180/π = {_deg_str(sp.simplify(r / DEG))}°"])


# ══════════════════════════════════════════════════════════════════════
#  shapes
# ══════════════════════════════════════════════════════════════════════

def _vals(ctx, a, n, labels, kws=()):
    kw = a.kw(*kws) if kws else {}
    w = a.rest.replace(",", " ").split()
    nums = [ctx.number(t, "number") for t in w]
    while len(nums) < n and not kw:
        nums.append(ctx.number(ctx.ask(labels[len(nums)]), "number"))
    return nums, {k: ctx.number(v, k) for k, v in kw.items()}


@command("circle", "Trig", "circle <radius>   or   circle d=<diameter>",
         "Circle: circumference and area (exact, in terms of π).", examples=("circle 5", "circle d=10", "circle 3/2"))
def circle(ctx, a):
    nums, kw = _vals(ctx, a, 1, ("radius",), ("r", "d"))
    r = kw.get("r") or (kw["d"] / 2 if "d" in kw else nums[0])
    if r <= 0:
        raise MathError("The radius must be positive.")
    box("Circle", [f"Radius:        {mstr(r)}", f"Diameter:      {mstr(2 * r)}",
                   f"Circumference: 2πr = {show(2 * sp.pi * r)}", f"Area:          πr² = {show(sp.pi * r ** 2)}"])


@command("triangle", "Trig", "triangle <base> <height>   or   triangle <a> <b> <c>",
         "Triangle area (base × height, or Heron's formula from three sides), perimeter, and type.",
         examples=("triangle 6 4", "triangle 13 14 15", "triangle 3 4 5"))
def triangle(ctx, a):
    nums, _ = _vals(ctx, a, 2, ("base", "height"))
    if len(nums) == 2:
        b, h = nums
        box("Triangle", [f"Area = ½·b·h = ½·{mstr(b)}·{mstr(h)} = {show(b * h / 2)}"])
        return
    x, y, z = sorted(nums[:3])
    if x + y <= z:
        raise MathError("Those sides can't make a triangle (the two shorter ones must add to more than the longest).")
    s = sp.Rational(x + y + z) / 2 if all(sp.sympify(t).is_Rational for t in (x, y, z)) else (x + y + z) / 2
    area = sp.radsimp(sp.simplify(sp.sqrt(s * (s - x) * (s - y) * (s - z))))
    c2, ab = z ** 2, x ** 2 + y ** 2
    kind = "right" if sp.simplify(c2 - ab) == 0 else "acute" if c2 < ab else "obtuse"
    eq = "scalene" if len({x, y, z}) == 3 else "isosceles" if len({x, y, z}) == 2 else "equilateral"
    box("Triangle", [f"Sides {mstr(x)}, {mstr(y)}, {mstr(z)}  →  {eq}, {kind}", f"Perimeter = {mstr(x + y + z)}",
                     f"Semi-perimeter s = {mstr(s)}", f"Heron: Area = √(s(s−a)(s−b)(s−c)) = {show(area)}"])


@command("rect", "Trig", "rect <width> <height>", "Rectangle: area, perimeter, diagonal.", aliases=("rectangle",),
         examples=("rect 6 8",))
def rect(ctx, a):
    (w, h), _ = _vals(ctx, a, 2, ("width", "height"))
    box("Rectangle", [f"Area = w·h = {mstr(w * h)}", f"Perimeter = 2(w + h) = {mstr(2 * (w + h))}",
                      f"Diagonal = √(w² + h²) = {show(sp.sqrt(w ** 2 + h ** 2))}"])


@command("sphere", "Trig", "sphere <radius>", "Sphere volume and surface area (exact).", examples=("sphere 3",))
def sphere(ctx, a):
    (r,), _ = _vals(ctx, a, 1, ("radius",))
    box("Sphere", [f"Volume = 4/3·πr³ = {show(sp.Rational(4, 3) * sp.pi * r ** 3)}", f"Surface area = 4πr² = {show(4 * sp.pi * r ** 2)}"])


@command("cylinder", "Trig", "cylinder <radius> <height>", "Cylinder volume and surface area (exact).", examples=("cylinder 3 10",))
def cylinder(ctx, a):
    (r, h), _ = _vals(ctx, a, 2, ("radius", "height"))
    box("Cylinder", [f"Volume = πr²h = {show(sp.pi * r ** 2 * h)}", f"Lateral area = 2πrh = {show(2 * sp.pi * r * h)}",
                     f"Total surface area = 2πr(r + h) = {show(2 * sp.pi * r * (r + h))}"])


@command("cone", "Trig", "cone <radius> <height>", "Cone volume, slant height, and surface area (exact).", examples=("cone 3 4",))
def cone(ctx, a):
    (r, h), _ = _vals(ctx, a, 2, ("radius", "height"))
    sl = sp.sqrt(r ** 2 + h ** 2)
    box("Cone", [f"Slant height ℓ = √(r² + h²) = {show(sl)}", f"Volume = ⅓πr²h = {show(sp.pi * r ** 2 * h / 3)}",
                 f"Lateral area = πrℓ = {show(sp.pi * r * sl)}", f"Total surface area = πr(r + ℓ) = {show(sp.pi * r * (r + sl))}"])


@command("pyth", "Trig", "pyth <a> <b> <c>   (use _ for the unknown side)",
         "Pythagorean theorem: find the missing side exactly (c is the hypotenuse).",
         aliases=("pythagorean",), examples=("pyth 3 4 _", "pyth _ 12 13", "pyth 5 5 _"))
def pyth(ctx, a):
    kw = a.kw("a", "b", "c")
    w = a.rest.replace(",", " ").split()
    vals = {"a": None, "b": None, "c": None}
    for k, t in zip("abc", w):
        vals[k] = None if t in ("_", "?", "x") else ctx.number(t, "side")
    for k, t in kw.items():
        vals[k] = ctx.number(t, "side")
    missing = [k for k, v in vals.items() if v is None]
    if len(missing) != 1:
        raise UsageError("Give two sides and mark the unknown with _ , e.g.  pyth 3 4 _")
    m = missing[0]
    A_, B_, C_ = vals["a"], vals["b"], vals["c"]
    if m == "c":
        sq, expr = A_ ** 2 + B_ ** 2, f"c² = {mstr(A_)}² + {mstr(B_)}² = {mstr(A_ ** 2 + B_ ** 2)}"
    elif m == "a":
        sq, expr = C_ ** 2 - B_ ** 2, f"a² = {mstr(C_)}² − {mstr(B_)}² = {mstr(C_ ** 2 - B_ ** 2)}"
    else:
        sq, expr = C_ ** 2 - A_ ** 2, f"b² = {mstr(C_)}² − {mstr(A_)}² = {mstr(C_ ** 2 - A_ ** 2)}"
    if sq <= 0:
        raise MathError("The hypotenuse must be the longest side.")
    root = sp.sqrt(sq)
    lines = ["a² + b² = c²", expr, f"{m} = {show(root)}"]
    if root.is_Integer and all(sp.sympify(t).is_Integer for t in (A_, B_, C_) if t is not None):
        lines.append("A Pythagorean triple!")
    box("Pythagorean theorem", lines)
