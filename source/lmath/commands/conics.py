"""
conics.py — circles, parabolas, ellipses, hyperbolas, and a general-form identifier.

All results are exact (radicals, fractions, π). `identify` accepts a general-form
equation, completes the square for you, and reports the conic's properties.
"""
import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, show
from ..registry import command
from ..steps import Steps

X, Y = sp.symbols("x y")


def _shift(v, h):
    """(x − h) with the sign written the way a textbook does: (x + 3), (x − 2), or x."""
    if h == 0:
        return v.name
    return f"({v.name} {'-' if h > 0 else '+'} {mstr(abs(h))})"


def _sq(v, h, d=2):
    sup = {2: "²"}[d]
    return f"{_shift(v, h)}{sup}" if h != 0 else f"{v.name}²"


def _over(txt, d):
    """'(x − 1)²' over d, dropping the '/1'."""
    return txt if d == 1 else f"{txt}/{mstr(d)}"


def _gen(expr):
    """General form text:  x² + y² − 4x + 6y − 12 = 0."""
    return mstr(sp.expand(expr)) + " = 0"


def circle_report(h, k, r2, how=None):
    r = sp.sqrt(r2)
    A = sp.expand((X - h) ** 2 + (Y - k) ** 2 - r2)
    lines = [f"Standard form:  {_sq(X, h)} + {_sq(Y, k)} = {mstr(r2)}",
             f"General form:   {_gen(A)}",
             f"Center: ({mstr(h)}, {mstr(k)})",
             f"Radius: {show(r)}      Diameter: {show(2 * r)}",
             f"Circumference = {show(2 * sp.pi * r)}",
             f"Area = {show(sp.pi * r2)}"]
    return lines


def parabola_report(a, b, c, vertical=True):
    h, k = -b / (2 * a), c - b ** 2 / (4 * a)
    p = 1 / (4 * a)
    u, w = (X, Y) if vertical else (Y, X)       # u is the squared variable
    form = f"{w.name} = {mstr(sp.expand(a * u ** 2 + b * u + c))}"
    sq_term = sp.Pow(u - h, 2, evaluate=False)
    body = sq_term if a == 1 else sp.Mul(a, sq_term, evaluate=False)
    vform = f"{w.name} = {mstr(body)}{' + ' + mstr(k) if k > 0 else (' − ' + mstr(-k) if k < 0 else '')}"
    if vertical:
        vertex = (h, k)
        focus, directrix = (h, k + p), f"y = {mstr(k - p)}"
        axis = f"x = {mstr(h)}"
        opens = "up" if a > 0 else "down"
        ints = sp.solve(a * X ** 2 + b * X + c, X)
        xint = "x-intercepts: " + (", ".join(f"({mstr(t)}, 0)" for t in sorted([t for t in ints if t.is_real], key=lambda q: float(sp.N(q)))) or "none")
        yint = f"y-intercept: (0, {mstr(c)})"
    else:
        vertex = (k, h)
        focus, directrix = (k + p, h), f"x = {mstr(k - p)}"
        axis = f"y = {mstr(h)}"
        opens = "right" if a > 0 else "left"
        ints = sp.solve(a * Y ** 2 + b * Y + c, Y)
        yint = "y-intercepts: " + (", ".join(f"(0, {mstr(t)})" for t in sorted([t for t in ints if t.is_real], key=lambda q: float(sp.N(q)))) or "none")
        xint = f"x-intercept: ({mstr(c)}, 0)"
    return [f"Standard form:  {form}", f"Vertex form:    {vform}",
            f"Vertex: ({mstr(vertex[0])}, {mstr(vertex[1])})", f"Opens {opens}",
            f"Axis of symmetry: {axis}", f"Focus: ({mstr(focus[0])}, {mstr(focus[1])})",
            f"Directrix: {directrix}", f"p = 1/(4a) = {mstr(p)}  (distance vertex → focus)", xint, yint]


def ellipse_report(h, k, a, b):
    """a = semi-axis along x, b = semi-axis along y."""
    a, b = sp.sympify(a), sp.sympify(b)
    horiz = a >= b
    big, small = (a, b) if horiz else (b, a)
    c = sp.sqrt(big ** 2 - small ** 2)
    e = sp.simplify(c / big)
    if horiz:
        verts = [(h - big, k), (h + big, k)]
        covs = [(h, k - small), (h, k + small)]
        foci = [(h - c, k), (h + c, k)]
    else:
        verts = [(h, k - big), (h, k + big)]
        covs = [(h - small, k), (h + small, k)]
        foci = [(h, k - c), (h, k + c)]
    pt = lambda p: f"({mstr(p[0])}, {mstr(p[1])})"
    std = f"{_over(_sq(X, h), a ** 2)} + {_over(_sq(Y, k), b ** 2)} = 1"
    return [f"Standard form:  {std}", f"Center: ({mstr(h)}, {mstr(k)})",
            f"Major axis: {'horizontal' if horiz else 'vertical'}   (a = {mstr(big)}, b = {mstr(small)})",
            f"Vertices: {pt(verts[0])}, {pt(verts[1])}", f"Co-vertices: {pt(covs[0])}, {pt(covs[1])}",
            f"c² = a² − b² = {mstr(big ** 2 - small ** 2)}  →  c = {show(c)}",
            f"Foci: {pt(foci[0])}, {pt(foci[1])}", f"Eccentricity e = c/a = {show(e)}",
            f"Area = πab = {show(sp.pi * a * b)}"]


def hyperbola_report(h, k, a, b, horizontal=True):
    a, b = sp.sympify(a), sp.sympify(b)
    c = sp.sqrt(a ** 2 + b ** 2)
    e = sp.simplify(c / a)
    pt = lambda p: f"({mstr(p[0])}, {mstr(p[1])})"
    if horizontal:
        std = f"{_over(_sq(X, h), a ** 2)} − {_over(_sq(Y, k), b ** 2)} = 1"
        verts, foci, slope = [(h - a, k), (h + a, k)], [(h - c, k), (h + c, k)], b / a
    else:
        std = f"{_over(_sq(Y, k), a ** 2)} − {_over(_sq(X, h), b ** 2)} = 1"
        verts, foci, slope = [(h, k - a), (h, k + a)], [(h, k - c), (h, k + c)], a / b
    sx = mstr(sp.Mul(slope, (X if horizontal else X) - h, evaluate=False)) if h != 0 else mstr(slope * X)
    asy = (f"y {'-' if k >= 0 else '+'} {mstr(abs(k))} = ±{sx}" if k != 0 else f"y = ±{sx}") if horizontal else \
          (f"y {'-' if k >= 0 else '+'} {mstr(abs(k))} = ±{sx}" if k != 0 else f"y = ±{sx}")
    return [f"Standard form:  {std}", f"Center: ({mstr(h)}, {mstr(k)})", f"Opens: {'left & right' if horizontal else 'up & down'}",
            f"Vertices: {pt(verts[0])}, {pt(verts[1])}", f"c² = a² + b² = {mstr(a ** 2 + b ** 2)}  →  c = {show(c)}",
            f"Foci: {pt(foci[0])}, {pt(foci[1])}", f"Asymptotes: {asy}", f"Eccentricity e = c/a = {show(e)}"]


def _nums(ctx, a, n, labels):
    w = a.rest.replace(",", " ").replace("=", " ").split()
    nums = []
    for t in w:
        try:
            nums.append(ctx.number(t, "number"))
        except MathError:
            break
    while len(nums) < n:
        nums.append(ctx.number(ctx.ask(labels[len(nums)]), "number"))
    return nums


# ══════════════════════════════════════════════════════════════════════
#  commands
# ══════════════════════════════════════════════════════════════════════

@command("circle2", "Conic Sections", "circle2 <h> <k> <r>   or   circle2 <general-form equation>",
         "Circle from center and radius, or from x² + y² + Dx + Ey + F = 0 (completes the square).",
         aliases=("conic_circle", "ccircle"), examples=("circle2 2 -3 5", "circle2 x^2+y^2-4x+6y-12=0"))
def circle2(ctx, a):
    if "=" in a.rest and ("x" in a.rest or "y" in a.rest):
        return identify(ctx, a)
    h, k, r = _nums(ctx, a, 3, ("center h", "center k", "radius r"))
    if r <= 0:
        raise MathError("The radius must be positive.")
    box(f"Circle: center ({mstr(h)}, {mstr(k)}), r = {mstr(r)}", circle_report(h, k, r ** 2))


@command("parabola", "Conic Sections", "parabola <a> <b> <c>   or   parabola y = ax²+bx+c   (or x = …y²…)",
         "Parabola: vertex, focus, directrix, axis, intercepts.", aliases=("conic_parabola",),
         examples=("parabola 1 -4 3", "parabola y=2x^2-8x+3", "parabola x=y^2-4y"))
def parabola(ctx, a):
    eq = P.split_equation(a.rest)
    if eq:
        lhs, rhs = eq[0].strip(), ctx.expr(eq[1])
        vertical = lhs == "y"
        if lhs not in ("x", "y"):
            return identify(ctx, a)
        u = X if vertical else Y
        poly = sp.Poly(sp.expand(rhs), u)
        if poly.degree() != 2:
            raise MathError(f"The right side must be a quadratic in {u.name}.")
        A_, B_, C_ = (poly.coeff_monomial(u ** 2), poly.coeff_monomial(u), poly.coeff_monomial(1))
    else:
        A_, B_, C_ = _nums(ctx, a, 3, ("a", "b", "c"))
        vertical = True
    if A_ == 0:
        raise MathError("a can't be 0 — that would be a line, not a parabola.")
    box("Parabola", parabola_report(A_, B_, C_, vertical))


@command("ellipsec", "Conic Sections", "ellipsec <h> <k> <a> <b>",
         "Ellipse from center and semi-axes a (horizontal) and b (vertical): foci, vertices, eccentricity.",
         aliases=("conic_ellipse", "ellipse"), examples=("ellipsec 0 0 5 3", "ellipsec 1 -2 2 4"))
def ellipsec(ctx, a):
    h, k, aa, bb = _nums(ctx, a, 4, ("center h", "center k", "a (x semi-axis)", "b (y semi-axis)"))
    if aa <= 0 or bb <= 0:
        raise MathError("Both semi-axes must be positive.")
    box("Ellipse", ellipse_report(h, k, aa, bb))


@command("hyperbolac", "Conic Sections", "hyperbolac <h> <k> <a> <b> [v]",
         "Hyperbola from center, a and b (add 'v' for one that opens up and down): vertices, foci, asymptotes.",
         aliases=("conic_hyperbola", "hyperbola"), examples=("hyperbolac 0 0 3 4", "hyperbolac 0 0 3 4 v"))
def hyperbolac(ctx, a):
    vertical = a.rest.rstrip().lower().endswith(" v") or a.rest.strip().lower() in ("v",)
    if vertical:
        a.rest = a.rest.rstrip()[:-1]
    h, k, aa, bb = _nums(ctx, a, 4, ("center h", "center k", "a", "b"))
    if aa <= 0 or bb <= 0:
        raise MathError("a and b must be positive.")
    box("Hyperbola", hyperbola_report(h, k, aa, bb, horizontal=not vertical))


@command("identify", "Conic Sections", "identify <general-form equation>   or   identify <A> <C> <D> <E> <F>",
         "Classify a conic from Ax²+Cy²+Dx+Ey+F=0, complete the square, and list its properties.",
         aliases=("conic_identify", "conic"),
         examples=("identify x^2+y^2-4x+6y-12=0", "identify 4x^2+9y^2-16x+18y-11=0", "identify x^2-4y^2-2x-8y-7=0",
                   "identify y^2-6y-8x+1=0"))
def identify(ctx, a):
    text = a.need("equation (e.g. x^2+y^2-4x+6y-12=0) or A C D E F")
    eq = P.split_equation(text)
    if eq:
        e = sp.expand(ctx.expr(eq[0]) - ctx.expr(eq[1]))
    else:
        nums = [ctx.number(t, "coefficient") for t in text.replace(",", " ").split()]
        if len(nums) != 5:
            raise UsageError("Give an equation, or five numbers A C D E F for Ax²+Cy²+Dx+Ey+F=0.")
        A_, C_, D_, E_, F_ = nums
        e = A_ * X ** 2 + C_ * Y ** 2 + D_ * X + E_ * Y + F_
    if not e.free_symbols <= {X, Y}:
        raise MathError("Use only x and y in a conic equation.")
    p = sp.Poly(e, X, Y)
    if p.total_degree() != 2:
        raise MathError("A conic has x² and/or y² terms (degree 2).")
    A_, B_, C_ = p.coeff_monomial(X ** 2), p.coeff_monomial(X * Y), p.coeff_monomial(Y ** 2)
    D_, E_, F_ = p.coeff_monomial(X), p.coeff_monomial(Y), p.coeff_monomial(1)
    disc = B_ ** 2 - 4 * A_ * C_
    head = [f"General form: {_gen(e)}", f"A = {mstr(A_)}, B = {mstr(B_)}, C = {mstr(C_)}, D = {mstr(D_)}, E = {mstr(E_)}, F = {mstr(F_)}",
            f"B² − 4AC = {mstr(disc)}"]
    if B_ != 0:
        kind = "parabola" if disc == 0 else "ellipse (or circle)" if disc < 0 else "hyperbola"
        box("Conic identification", head + [f"→ This is a {kind} that is rotated (it has an xy term)."])
        return
    with Steps("Conic identification", ctx) as s:
        s.step("Read the coefficients of x² and y²", f"A = {mstr(A_)},  C = {mstr(C_)}")
        out = []
        if A_ == 0 and C_ == 0:
            raise MathError("That's a line, not a conic.")
        if A_ == 0 or C_ == 0:                                     # parabola
            if A_ != 0:
                if E_ == 0:
                    s.result("Degenerate: parallel lines, one line, or no graph (no y term).")
                    return
                s.step("Only x is squared → a parabola that opens up or down", f"solve for y:  y = {mstr(sp.expand(-(A_ * X ** 2 + D_ * X + F_) / E_))}")
                out = parabola_report(-A_ / E_, -D_ / E_, -F_ / E_, True)
            else:
                if D_ == 0:
                    s.result("Degenerate: parallel lines, one line, or no graph (no x term).")
                    return
                s.step("Only y is squared → a parabola that opens left or right", f"solve for x:  x = {mstr(sp.expand(-(C_ * Y ** 2 + E_ * Y + F_) / D_))}")
                out = parabola_report(-C_ / D_, -E_ / D_, -F_ / D_, False)
            s.result("Parabola")
        else:
            h = -D_ / (2 * A_)
            k = -E_ / (2 * C_)
            R = -F_ + D_ ** 2 / (4 * A_) + E_ ** 2 / (4 * C_)
            def grp(c, inner):
                return f"({inner})" if c in (1, -1) and False else (f"{mstr(abs(c)) if abs(c) != 1 else ''}({inner})")

            def join(parts):
                txt = ""
                for c, inner in parts:
                    sign = "-" if c < 0 else "+"
                    txt += (("-" if c < 0 else "") if not txt else f" {sign} ") + grp(c, inner)
                return txt
            s.step("Group x-terms and y-terms and complete the square for each",
                   f"{join([(A_, mstr(X ** 2 + (D_ / A_) * X)), (C_, mstr(Y ** 2 + (E_ / C_) * Y))])} = {mstr(-F_)}")
            s.step("Add the squares to both sides",
                   f"{join([(A_, _sq(X, h)), (C_, _sq(Y, k))]).replace('(' + _sq(X, h) + ')', _sq(X, h)).replace('(' + _sq(Y, k) + ')', _sq(Y, k))} = {mstr(R)}")
            if R == 0:
                s.result("Degenerate: " + ("a single point" if A_ * C_ > 0 else "two intersecting lines") + f" through ({mstr(h)}, {mstr(k)})")
                return
            a2, b2 = R / A_, R / C_
            if A_ * C_ > 0:
                std_txt = f"{_over(_sq(X, h), a2)} + {_over(_sq(Y, k), b2)} = 1"
            elif a2 > 0:
                std_txt = f"{_over(_sq(X, h), a2)} − {_over(_sq(Y, k), -b2)} = 1"
            else:
                std_txt = f"{_over(_sq(Y, k), b2)} − {_over(_sq(X, h), -a2)} = 1"
            s.step("Divide by the right side to get 1", std_txt)
            if A_ * C_ > 0:
                if a2 < 0:
                    s.result("No graph (the right side is negative).")
                    return
                if a2 == b2:
                    s.result("Circle")
                    out = circle_report(h, k, a2)
                else:
                    s.result("Ellipse")
                    out = ellipse_report(h, k, sp.sqrt(a2), sp.sqrt(b2))
            else:
                s.result("Hyperbola")
                if a2 > 0:
                    out = hyperbola_report(h, k, sp.sqrt(a2), sp.sqrt(-b2), True)
                else:
                    out = hyperbola_report(h, k, sp.sqrt(b2), sp.sqrt(-a2), False)
    box("Properties", out)
