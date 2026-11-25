"""
algebra.py — calc, solve, factor, expand, simplify, system, poly_gcd.

These are the tools students lean on most, so they all read input through
the shared parser (2x+3, (x+1)(x-1), 0.5x, √12 ...) and keep answers exact.
"""
import math

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, is_exact_irrational, mstr, pretty_lines, show
from ..registry import command
from ..steps import Steps

X = sp.Symbol("x")


# ══════════════════════════════════════════════════════════════════════
#  shared helpers
# ══════════════════════════════════════════════════════════════════════

def pick_var(exprs, hint=None):
    """Choose the variable to work on: an explicit hint, the only one, or x."""
    if hint:
        name = hint.strip()
        if not name.isidentifier():
            raise MathError(f"'{hint}' isn't a variable name.")
        return sp.Symbol(name)
    free = P.free_vars(*exprs)
    if not free:
        return None
    if len(free) == 1:
        return free[0]
    if X in free:
        return X
    names = ", ".join(s.name for s in free)
    raise MathError(f"I see several variables ({names}). Say which one, e.g.  ... for {free[0].name}")


def radical_parts(n: int):
    """n = k²·m with m square-free → (k, m)."""
    k, m = 1, 1
    for p, e in sp.factorint(int(n)).items():
        k *= p ** (e // 2)
        m *= p ** (e % 2)
    return k, m


def quad_formula_str(a, b, c, var="x") -> str:
    """Exact roots of ax²+bx+c as a single reduced string:  x = (5 ± √13)/6."""
    a, b, c = sp.Integer(a), sp.Integer(b), sp.Integer(c)
    D = int(b * b - 4 * a * c)
    num_b, den = int(-b), int(2 * a)
    if D == 0:
        r = sp.Rational(num_b, den)
        return f"{var} = {mstr(r)}"
    k, m = radical_parts(abs(D))
    if D > 0 and m == 1:
        r1, r2 = sorted([sp.Rational(num_b + k, den), sp.Rational(num_b - k, den)])
        return f"{var} = {mstr(r1)}  or  {var} = {mstr(r2)}"
    g = math.gcd(math.gcd(abs(num_b), k), abs(den)) or 1
    num_b, k, den = num_b // g, k // g, den // g
    if den < 0:
        num_b, den = -num_b, -den
    rad = (str(k) if k > 1 else "") + ("i" if D < 0 else "") + (("√" + str(m)) if m > 1 else "")
    num = f"{num_b} ± {rad}" if num_b else f"±{rad}"
    if den == 1:
        return f"{var} = {num}"
    return f"{var} = ({num})/{den}" if num_b else f"{var} = {num}/{den}"


def fmt_solution(v, val) -> str:
    if val.free_symbols:
        val = min([val, sp.factor(val), sp.together(val)], key=lambda c: (sp.count_ops(c), len(mstr(c))))
    if isinstance(val, sp.Float) or (val.has(sp.Float)):
        return f"{v.name} ≈ {approx(val)}"
    if val.is_real is False or val.has(sp.I):
        return f"{v.name} = {mstr(val)}"
    return f"{v.name} = {show(val)}"


def numeric_roots(expr, v, lo=-50.0, hi=50.0, n=4000):
    """Last-resort real roots by scanning for sign changes then bisecting."""
    try:
        f = sp.lambdify(v, expr, "math")
    except Exception:
        return []
    roots, prev_x, prev_y = [], None, None
    for i in range(n + 1):
        x0 = lo + (hi - lo) * i / n
        try:
            y0 = float(f(x0))
        except Exception:
            prev_x = prev_y = None
            continue
        if not math.isfinite(y0):
            prev_x = prev_y = None
            continue
        if y0 == 0.0:
            roots.append(x0)
        elif prev_y is not None and prev_y * y0 < 0:
            a, b, fa = prev_x, x0, prev_y
            for _ in range(80):
                mid = (a + b) / 2
                try:
                    fm = float(f(mid))
                except Exception:
                    break
                if fa * fm <= 0:
                    b = mid
                else:
                    a, fa = mid, fm
            if abs(f((a + b) / 2)) < 1e-6:
                roots.append((a + b) / 2)
        prev_x, prev_y = x0, y0
    out = []
    for r in roots:
        if not out or abs(r - out[-1]) > 1e-6:
            out.append(r)
    return out


def _holds(lhs, rhs, v, val) -> bool:
    try:
        d = (lhs - rhs).subs(v, val)
        d = sp.simplify(d)
        if d == 0:
            return True
        n = complex(sp.N(d, 20))
        return abs(n) < 1e-9 and math.isfinite(abs(n))
    except Exception:
        return False


def solve_equation(lhs, rhs, v):
    """
    Returns (kind, solutions, rejected, note) where kind is 'all', 'none' or 'some'.
    `rejected` lists candidates that failed the check in the original equation.
    """
    expr = sp.simplify(lhs - rhs)
    if expr == 0:
        return "all", [], [], ""
    if not expr.has(v):
        return "none", [], [], ""
    note = ""
    rejected = []
    if expr.has(sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot):
        s = sp.solveset(expr, v, sp.Interval.Ropen(0, 2 * sp.pi))
        note = "solutions in [0, 2π); add 2πk (k any integer) for all solutions"
        sols = list(s.args) if isinstance(s, sp.FiniteSet) else []
        if isinstance(s, sp.ConditionSet) or (not sols and s != sp.S.EmptySet):
            sols = [sp.Float(r) for r in numeric_roots(expr, v, 0, 2 * math.pi)]
        return ("some" if sols else "none"), sorted(sols, key=lambda a: float(sp.N(a))), [], note
    if expr.has(sp.Abs):
        vr = sp.Symbol(v.name, real=True)
        s = sp.solveset(expr.subs(v, vr), vr, sp.S.Reals)
        if s == sp.S.Reals:
            return "all", [], [], ""
        if isinstance(s, sp.FiniteSet):
            sols = sorted(s.args, key=lambda a: float(sp.N(a)))
            return ("some" if sols else "none"), sols, [], ""
        if s == sp.S.EmptySet:
            return "none", [], [], ""
    try:
        cands = sp.solve(expr, v)
    except (NotImplementedError, Exception):
        cands = []
    if any(c.has(sp.CRootOf) or len(mstr(c)) > 40 for c in cands if not isinstance(c, dict)):
        try:
            cands = [sp.N(c, 12) for c in cands]
            note = "no simple exact form — decimal approximations"
        except Exception:
            pass
    sols = []
    for c in cands:
        if isinstance(c, dict):
            continue
        if c.has(sp.nan, sp.zoo, sp.oo):
            continue
        if _holds(lhs, rhs, v, c):
            sols.append(c)
        else:
            rejected.append(c)
    if not sols and not rejected:
        nums = numeric_roots(expr, v)
        if nums:
            return "some", [sp.Float(r, 8) for r in nums], [], "numeric (no exact form found)"
    def key(a):
        try:
            c = complex(sp.N(a))
            return (abs(c.imag) > 1e-12, c.real, c.imag)
        except Exception:
            return (True, 0, 0)
    return ("some" if sols else "none"), sorted(sols, key=key), rejected, note


# ══════════════════════════════════════════════════════════════════════
#  step-by-step solvers
# ══════════════════════════════════════════════════════════════════════

def _eqs(l, r):
    return mstr(sp.Eq(l, r, evaluate=False))


def linear_steps(ctx, lhs, rhs, v, title):
    with Steps(title, ctx) as s:
        s.step("Start with the equation", _eqs(lhs, rhs))
        l, r = sp.expand(lhs), sp.expand(rhs)
        if l != lhs or r != rhs:
            s.step("Distribute and combine like terms on each side", _eqs(l, r))
        al, bl = l.coeff(v, 1), l.coeff(v, 0)
        ar, br = r.coeff(v, 1), r.coeff(v, 0)
        if ar != 0:
            s.step(f"Move the {v.name}-terms to the left (subtract {mstr(ar * v)} from both sides)",
                   _eqs((al - ar) * v + bl, br))
        coef = al - ar
        if coef == 0:
            s.result("All real numbers (the sides are always equal)" if bl == br else "No solution (the sides can never be equal)")
            return
        if bl != 0:
            verb = "Subtract" if bl > 0 else "Add"
            s.step(f"{verb} {mstr(abs(bl))} {'from' if bl > 0 else 'to'} both sides", _eqs(coef * v, br - bl))
        sol = (br - bl) / coef
        if coef != 1:
            s.step(f"Divide both sides by {mstr(coef)}", _eqs(v, sol))
        s.step("Check by substituting back", f"{mstr(lhs.subs(v, sol))} = {mstr(rhs.subs(v, sol))}  ✓")
        s.result(fmt_solution(v, sol))


def quadratic_steps(ctx, a, b, c, v, title, factor_first=True):
    """Quadratic formula / factoring with every step shown. a, b, c may be rationals."""
    poly = a * v ** 2 + b * v + c
    with Steps(title, ctx) as s:
        s.step("Write in standard form  ax² + bx + c = 0", f"{mstr(poly)} = 0")
        den = sp.ilcm(*[sp.Rational(t).q for t in (a, b, c)])
        if den != 1:
            a, b, c = a * den, b * den, c * den
            poly = a * v ** 2 + b * v + c
            s.step(f"Multiply every term by {den} to clear the fractions", f"{mstr(poly)} = 0")
        g = sp.igcd(int(a), int(b), int(c))
        if g not in (0, 1):
            a, b, c = a / g, b / g, c / g
            poly = a * v ** 2 + b * v + c
            s.step(f"Divide every term by {g}", f"{mstr(poly)} = 0")
        a, b, c = int(a), int(b), int(c)
        s.step("Identify the coefficients", f"a = {a},  b = {b},  c = {c}")
        D = b * b - 4 * a * c
        s.step("Find the discriminant  D = b² − 4ac", f"D = ({b})² − 4({a})({c}) = {D}")
        if D > 0:
            s.note("D > 0: two real solutions" + (" (a perfect square, so they are rational)" if sp.sqrt(D).is_Integer else ""))
        elif D == 0:
            s.note("D = 0: one repeated real solution")
        else:
            s.note("D < 0: no real solutions — two complex solutions")
        f = sp.factor(poly)
        if factor_first and D >= 0 and sp.sqrt(D).is_Integer and f.is_Mul or (D == 0 and f.is_Pow):
            s.step("This factors, so factor it", f"{ordered_factor_str(poly)} = 0")
            s.step("Set each factor equal to 0 (zero-product property)")
            for r in sorted(set(sp.solve(poly, v))):
                s.note(f"{v.name} = {mstr(r)}")
        else:
            s.step("Use the quadratic formula  x = (−b ± √D) / 2a",
                   f"x = ({-b} ± √({D})) / {2 * a}" if D < 0 else f"x = ({-b} ± √{D}) / {2 * a}")
            if D > 0 and radical_parts(D)[0] > 1:
                k, m = radical_parts(D)
                s.step(f"Simplify the radical:  √{D} = {k}√{m}")
            elif D < 0:
                k, m = radical_parts(-D)
                s.step(f"Simplify:  √({D}) = {k if k > 1 else ''}i{'√' + str(m) if m > 1 else ''}")
        s.result(quad_formula_str(a, b, c, v.name))
        approx_vals = [r for r in sp.solve(poly, v) if is_exact_irrational(r) and r.is_real]
        if approx_vals:
            s.result("   or   ".join(f"{v.name} ≈ {approx(r)}" for r in approx_vals))


def abs_steps(ctx, inner, rhs, v, title):
    with Steps(title, ctx) as s:
        s.step("Start with the equation", f"|{mstr(inner)}| = {mstr(rhs)}")
        if rhs < 0:
            s.note("An absolute value is never negative.")
            s.result("No solution")
            return
        if rhs == 0:
            s.step("The only way |A| = 0 is A = 0", f"{mstr(inner)} = 0")
            sol = sp.solve(inner, v)
            s.result(", ".join(fmt_solution(v, r) for r in sol))
            return
        s.step("Split into two cases:  A = c  or  A = −c")
        s.note(f"Case 1: {mstr(inner)} = {mstr(rhs)}")
        s.note(f"Case 2: {mstr(inner)} = {mstr(-rhs)}")
        sols = []
        for label, target in (("Case 1", rhs), ("Case 2", -rhs)):
            r = sp.solve(sp.Eq(inner, target), v)
            sols += r
            s.step(f"Solve {label}", ",  ".join(fmt_solution(v, t) for t in r))
        s.step("Check both in the original equation",
               "  ".join(f"|{mstr(inner.subs(v, t))}| = {mstr(rhs)} ✓" for t in sols))
        s.result("   or   ".join(fmt_solution(v, t) for t in sols))


def general_steps(ctx, lhs, rhs, v, title, kind, sols, rejected, note):
    with Steps(title, ctx) as s:
        s.step("Start with the equation", _eqs(lhs, rhs))
        expr = sp.simplify(lhs - rhs)
        if rhs != 0:
            s.step("Move everything to one side", f"{mstr(expr)} = 0")
        if expr.is_polynomial(v) and sp.degree(expr, v) >= 3:
            fl = sp.factor(expr)
            if fl != expr:
                s.step("Factor, then set each factor equal to 0", f"{ordered_factor_str(expr)} = 0")
        if rejected:
            s.step("Check each candidate in the original equation")
            for r in rejected:
                s.note(f"{v.name} = {mstr(r)} does not work — extraneous, so reject it")
        if note:
            s.note(note)
        if kind == "all":
            s.result("All real numbers")
        elif kind == "none":
            s.result("No solution")
        else:
            joiner = "   or   " if len(sols) <= 3 else ",   "
            s.result(joiner.join(fmt_solution(v, r) for r in sols))


# ══════════════════════════════════════════════════════════════════════
#  calc
# ══════════════════════════════════════════════════════════════════════

def do_calc(ctx, text):
    e = ctx.expr(text)
    if isinstance(e, sp.Basic) and e.is_Relational:
        raise MathError("That's an equation or inequality — try:  solve " + text)
    if e.free_symbols:
        try:
            s = sp.simplify(e)
            e = s if sp.count_ops(s) <= sp.count_ops(e) else e
        except Exception:
            pass
    ctx.set_ans(e) if e.is_number else None
    print("  = " + show(e))


@command("calc", "Basics", "calc <expression>   (or just type the expression)",
         "Exact arithmetic: fractions, radicals, π, with a decimal beside it.",
         aliases=("eval",), examples=("calc 3/4 + 5/6", "calc sqrt(48)", "calc 2^10", "calc sin(30°)"))
def calc(ctx, a):
    do_calc(ctx, a.need("expression"))


# ══════════════════════════════════════════════════════════════════════
#  solve
# ══════════════════════════════════════════════════════════════════════

def _split_system(text):
    pieces = [p.strip() for p in P.split_top(text.replace(" and ", ";"), ";,") if p.strip()]
    return pieces if len(pieces) > 1 and all(P.split_equation(p) for p in pieces) else None


@command("solve", "Algebra", "solve <equation> [for <variable>]",
         "Solve linear, quadratic, absolute value, polynomial, rational, exponential, trig and more — with steps.",
         examples=("solve 2x+3=11", "solve x^2-5x+6=0", "solve |2x-1|=5", "solve 2^x=32",
                   "solve x+y=7; x-y=1", "solve a*x+b=c for x"))
def solve(ctx, a):
    text = a.need("equation (e.g. 2x+3=11)")
    found, head = a.phrase("for")
    system_parts = _split_system(head)
    if system_parts:
        return do_system(ctx, system_parts)
    eq = P.split_equation(head)
    if eq:
        lhs, rhs = ctx.expr(eq[0]), ctx.expr(eq[1])
    else:
        lhs, rhs = ctx.expr(head), sp.Integer(0)
    v = pick_var([lhs, rhs], found.get("for"))
    title = f"Solve: {mstr(sp.Eq(lhs, rhs, evaluate=False)) if eq else mstr(lhs) + ' = 0'}"
    if v is None:
        ok = sp.simplify(lhs - rhs) == 0
        box(title, ["True — both sides are equal." if ok else "False — the two sides are not equal."])
        return
    if v not in lhs.free_symbols | rhs.free_symbols:
        raise MathError(f"There's no {v.name} in that equation.")
    if len((lhs - rhs).free_symbols) > 1 and not found.get("for"):
        print(f"  (solving for {v.name}; add  'for <letter>'  to solve for a different variable)")

    # exact step-by-step paths for the classic cases
    diff = sp.expand(lhs - rhs)
    try:
        poly = sp.Poly(diff, v) if diff.is_polynomial(v) else None
    except sp.PolynomialError:
        poly = None
    others = diff.free_symbols - {v}
    if poly is not None and not others:
        deg = poly.degree()
        if deg == 1:
            linear_steps(ctx, lhs, rhs, v, title)
            return
        if deg == 2:
            a2, b1, c0 = (poly.coeff_monomial(v ** 2), poly.coeff_monomial(v), poly.coeff_monomial(1))
            if all(t.is_Rational for t in (a2, b1, c0)):
                quadratic_steps(ctx, a2, b1, c0, v, title)
                return
    for ab, other in ((lhs, rhs), (rhs, lhs)):
        if isinstance(ab, sp.Abs) and not other.has(v) and ab.args[0].is_polynomial(v) \
                and sp.degree(ab.args[0], v) == 1 and other.is_number and other.is_real:
            abs_steps(ctx, ab.args[0], other, v, title)
            return

    if sp.expand(lhs - rhs).is_number:            # the variable cancelled out (3x+2 = 3x+5)
        linear_steps(ctx, lhs, rhs, v, title)
        return
    kind, sols, rejected, note = solve_equation(lhs, rhs, v)
    general_steps(ctx, lhs, rhs, v, title, kind, sols, rejected, note)
    if kind == "none" and not rejected and (lhs - rhs).has(v):
        print(f"  Tip: graph it to see what's happening:  plot {mstr(lhs)}, {mstr(rhs)}")


# ══════════════════════════════════════════════════════════════════════
#  systems
# ══════════════════════════════════════════════════════════════════════

def _linear_row(expr_l, expr_r, vs):
    d = sp.expand(expr_l - expr_r)
    if not d.is_polynomial(*vs) or sp.Poly(d, *vs).total_degree() > 1:
        return None
    return [d.coeff(v) for v in vs] + [-d.subs({v: 0 for v in vs})]


def _eq_line(a, b, c, vs):
    return mstr(sp.Eq(a * vs[0] + b * vs[1], c, evaluate=False))


def system_2x2(ctx, rows, vs, title):
    (a1, b1, c1), (a2, b2, c2) = rows
    x, y = vs
    D = a1 * b2 - a2 * b1
    with Steps(title, ctx) as s:
        s.step("Write both equations", f"(1)  {_eq_line(a1, b1, c1, vs)}\n(2)  {_eq_line(a2, b2, c2, vs)}")
        if D == 0:
            if a1 * c2 - a2 * c1 == 0 and b1 * c2 - b2 * c1 == 0:
                s.note("The equations describe the same line.")
                s.result("Infinitely many solutions (dependent system)")
            else:
                s.note("The lines have the same slope but different intercepts — they never meet.")
                s.result("No solution (inconsistent system)")
            return
        s.step(f"Eliminate {y.name}: multiply (1) by {mstr(b2)} and (2) by {mstr(b1)}",
               f"(1)  {_eq_line(a1 * b2, b1 * b2, c1 * b2, vs)}\n(2)  {_eq_line(a2 * b1, b1 * b2, c2 * b1, vs)}")
        s.step("Subtract the equations", f"{mstr(sp.Eq(D * x, c1 * b2 - c2 * b1, evaluate=False))}")
        xs = sp.Rational(c1 * b2 - c2 * b1) / D
        s.step(f"Divide by {mstr(D)}", f"{x.name} = {mstr(xs)}")
        if b1 != 0:
            ys = (c1 - a1 * xs) / b1
            s.step(f"Substitute into (1) and solve for {y.name}",
                   f"{mstr(a1 * xs)} {'+' if b1 >= 0 else '−'} {mstr(abs(b1))}{y.name} = {mstr(c1)}   →   {y.name} = {mstr(ys)}")
        else:
            ys = (c2 - a2 * xs) / b2
            s.step(f"Substitute into (2) and solve for {y.name}", f"{y.name} = {mstr(ys)}")
        ok1 = a1 * xs + b1 * ys == c1
        ok2 = a2 * xs + b2 * ys == c2
        s.step("Check in both equations",
               f"(1) {mstr(a1 * xs + b1 * ys)} = {mstr(c1)} {'✓' if ok1 else '✗'}    (2) {mstr(a2 * xs + b2 * ys)} = {mstr(c2)} {'✓' if ok2 else '✗'}")
        s.result(f"{x.name} = {mstr(xs)},   {y.name} = {mstr(ys)}")
        s.result(f"Point of intersection: ({mstr(xs)}, {mstr(ys)})")


def do_system(ctx, pieces):
    eqs = []
    for p in pieces:
        l, r = P.split_equation(p)
        eqs.append((ctx.expr(l), ctx.expr(r)))
    vs = P.free_vars(*[e for pair in eqs for e in pair])
    title = "System: " + ";  ".join(_eqs(l, r) for l, r in eqs)
    if not vs:
        raise MathError("There are no variables to solve for.")
    if len(vs) > len(eqs):
        raise MathError(f"There are {len(vs)} unknowns ({', '.join(v.name for v in vs)}) but only {len(eqs)} equations — I need one equation per unknown.")
    rows = [_linear_row(l, r, vs) for l, r in eqs]
    if len(eqs) == 2 and len(vs) == 2 and all(rows):
        system_2x2(ctx, rows, vs, title)
        return
    if all(rows) and len(vs) == len(eqs):
        M = sp.Matrix(rows)
        rref, piv = M.rref()
        with Steps(title, ctx) as s:
            s.step("Write the augmented matrix", mstr_matrix(M))
            s.step("Row-reduce to reduced row echelon form", mstr_matrix(rref))
            if len(piv) < len(vs) or (len(piv) == len(vs) and len(vs) in piv):
                s.result("No solution (inconsistent)" if len(vs) in piv else "Infinitely many solutions")
            else:
                for i, v in enumerate(vs):
                    s.result(f"{v.name} = {mstr(rref[i, len(vs)])}")
        return
    sols = sp.solve([sp.Eq(l, r) for l, r in eqs], vs, dict=True)
    with Steps(title, ctx) as s:
        s.step("Solve one equation for a variable, substitute into the other (substitution)")
        if not sols:
            s.result("No solution")
        for sol in sols:
            s.result(",  ".join(f"{v.name} = {show(sol[v])}" for v in vs if v in sol))
        if sols:
            s.result("as points: " + "   ".join("(" + ", ".join(mstr(sol[v]) for v in vs if v in sol) + ")" for sol in sols))


def mstr_matrix(M) -> str:
    rows = [[mstr(M[i, j]) for j in range(M.cols)] for i in range(M.rows)]
    w = [max(len(rows[i][j]) for i in range(M.rows)) for j in range(M.cols)]
    return "\n".join("[ " + "  ".join(r[j].rjust(w[j]) for j in range(M.cols)) + " ]" for r in rows)


@command("system", "Algebra", "system <eq1> ; <eq2> [; <eq3>]",
         "Solve a system of equations (elimination steps for 2×2, row reduction for bigger).",
         examples=("system 2x+3y=6 ; x-y=1", "system y=x^2 ; y=x+2", "system x+y+z=6; 2x-y+z=3; x+2y-z=2"))
def system(ctx, a):
    text = a.need("equations separated by ;  (e.g. 2x+3y=6 ; x-y=1)")
    parts = [p.strip() for p in P.split_top(text.replace("|", ";").replace(" and ", ";"), ";,") if p.strip()]
    if len(parts) < 2:
        raise UsageError("Give two or more equations separated by ;   e.g.  system 2x+3y=6 ; x-y=1")
    do_system(ctx, parts)


# ══════════════════════════════════════════════════════════════════════
#  factor / expand / simplify
# ══════════════════════════════════════════════════════════════════════

def ordered_factor_str(e) -> str:
    """Completely factored text with linear factors ascending by root: (x − 2)(x − 3)."""
    coeff, facs = sp.factor_list(sp.factor(e))

    def key(item):
        base, _ = item
        try:
            p = sp.Poly(base)
            if p.degree() == 1 and len(p.gens) == 1:
                root = float(sp.N(-p.coeff_monomial(1) / p.LC()))
                return (0, abs(root), -root)
            return (1, p.degree())
        except Exception:
            return (2, 0)
    out = []
    for base, mult in sorted(facs, key=key):
        text = f"({mstr(base)})" if base.is_Add else mstr(base)
        out.append(text + (str(int(mult)).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")) if mult > 1 else ""))
    body = "".join(out)
    if coeff == 1:
        return body or "1"
    if coeff == -1:
        return "-" + body
    c = mstr(coeff)
    return (f"({c})" if "/" in c else c) + body


def _is_square(n):
    n = sp.Integer(n)
    return n >= 0 and sp.sqrt(n).is_Integer


def factor_quadratic_steps(s, e, v):
    """Narrate the factoring of a quadratic with integer coefficients (after any GCF)."""
    p = sp.Poly(e, v)
    a, b, c = (int(p.coeff_monomial(v ** 2)), int(p.coeff_monomial(v)), int(p.coeff_monomial(1)))
    if b == 0 and a > 0 and c < 0 and _is_square(a) and _is_square(-c):
        ra, rc = int(sp.sqrt(a)), int(sp.sqrt(-c))
        s.step("Difference of squares:  A² − B² = (A − B)(A + B)",
               f"{mstr(e)} = {mstr(sp.Pow(ra * v, 2, evaluate=False))} − {rc}²")
        return
    D = b * b - 4 * a * c
    if D == 0 and a > 0 and _is_square(a):
        ra = int(sp.sqrt(a))
        rc = int(sp.sqrt(c)) if c >= 0 else 0
        s.step("Perfect-square trinomial:  A² ± 2AB + B² = (A ± B)²",
               f"{mstr(sp.Pow(ra * v, 2, evaluate=False))} {'+' if b >= 0 else '−'} 2·{mstr(ra * v)}·{rc} + {rc}²")
        return
    if a == 1:
        for m in range(-abs(c) - 1, abs(c) + 2):
            if m != 0 and c % m == 0 and m + c // m == b:
                s.step(f"Find two numbers that multiply to c = {c} and add to b = {b}",
                       f"{m} and {c // m}   ({m}·{c // m} = {c},  {m}+{c // m} = {b})")
                return
    else:
        ac = a * c
        for m in range(-abs(ac) - 1, abs(ac) + 2):
            if m != 0 and ac % m == 0 and m + ac // m == b:
                n = ac // m
                s.step(f"AC method: find two numbers that multiply to ac = {ac} and add to b = {b}",
                       f"{m} and {n}")
                g1 = sp.factor(a * v ** 2 + m * v)
                g2 = sp.factor(n * v + c)
                s.step("Split the middle term and group",
                       f"{mstr(a * v ** 2)} {'+' if m >= 0 else '−'} {mstr(abs(m) * v)} {'+' if n >= 0 else '−'} {mstr(abs(n) * v)} {'+' if c >= 0 else '−'} {abs(c)}")
                s.step("Factor each group", f"{mstr(g1)} + {mstr(g2)}")
                return


@command("factor", "Algebra", "factor <expression>",
         "Factor completely (GCF, difference of squares, trinomials, cubes, …) and show how.",
         examples=("factor x^2-5x+6", "factor 6x^2+11x-10", "factor x^2-49", "factor 2x^3-8x", "factor x^3-8"))
def factor(ctx, a):
    e = ctx.expr(a.need("expression to factor"))
    v = pick_var([e])
    f = sp.factor(e)
    title = f"Factor: {mstr(e)}"
    if v is None or f == e or (f.is_Add and f == e):
        extra = []
        if v is not None and e.is_polynomial(v) and sp.degree(e, v) == 2:
            p = sp.Poly(e, v)
            a2, b1, c0 = (p.coeff_monomial(v ** 2), p.coeff_monomial(v), p.coeff_monomial(1))
            D = b1 ** 2 - 4 * a2 * c0
            extra.append(f"Discriminant = {mstr(D)}")
            if D > 0:
                r1, r2 = sp.solve(e, v)
                r1, r2 = sorted([r1, r2], key=lambda t: float(sp.N(t)))
                extra.append(f"Over the real numbers:  {mstr(a2) + '·' if a2 != 1 else ''}({mstr(v - r1)})({mstr(v - r2)})")
            elif D < 0:
                extra.append("No real roots, so it can't be factored using real numbers.")
        box(title, ["Already fully factored over the integers (it is prime)."] + extra)
        return
    with Steps(title, ctx) as s:
        rest = e
        g = sp.gcd_terms(e)
        gcf = sp.Mul(*[t for t in sp.Mul.make_args(sp.factor_terms(e)) if not t.is_Add]) if sp.factor_terms(e).is_Mul else 1
        if v is not None and e.is_polynomial(v) and gcf not in (1, -1) and not sp.expand(gcf).is_Add:
            rest = sp.expand(e / gcf)
            s.step("Factor out the greatest common factor (GCF)", f"{mstr(e)} = {mstr(gcf)}({mstr(rest)})")
        if v is not None and rest.is_polynomial(v):
            d = sp.degree(rest, v)
            if d == 2 and not (rest.free_symbols - {v}) and all(sp.Poly(rest, v).coeffs()[i].is_Integer for i in range(len(sp.Poly(rest, v).coeffs()))):
                factor_quadratic_steps(s, rest, v)
            elif d == 3 and not (rest.free_symbols - {v}):
                p = sp.Poly(rest, v)
                if p.coeff_monomial(v ** 2) == 0 and p.coeff_monomial(v) == 0:
                    s.step("Sum/difference of cubes:  A³ ± B³ = (A ± B)(A² ∓ AB + B²)")
        fs = ordered_factor_str(e)
        s.step("Write the completely factored form", fs)
        s.step("Check by multiplying back out", f"{mstr(sp.expand(f))}  ✓")
        s.result(fs)


@command("expand", "Algebra", "expand <expression>", "Multiply out brackets.",
         examples=("expand (x+2)^3", "expand (2x-1)(x+4)"))
def expand(ctx, a):
    e = ctx.expr(a.need("expression"))
    box(f"Expand: {mstr(e) if False else a.rest}", [mstr(sp.expand(e))])


def tidy_radicals(e):
    """Pull perfect powers out of radicals: √(12x³) → 2x√(3x), ∛(54x⁴) → 3x∛(2x)."""
    x_pos = {s: sp.Symbol(s.name, positive=True) for s in e.free_symbols}
    back = {v: k for k, v in x_pos.items()}
    work = sp.powsimp(sp.expand_power_base(e.subs(x_pos), force=True), force=True)

    def one(term):
        sign = -1 if term.could_extract_minus_sign() else 1
        term = sign * term
        items = dict(term.as_powers_dict())
        q = 1
        for ex in items.values():
            if ex.is_Rational and not ex.is_Integer:
                q = sp.ilcm(q, ex.q)
        if q == 1:
            return sign * term.xreplace(back)
        out, inside = sp.Integer(1), sp.Integer(1)
        for base, ex in items.items():
            base = back.get(base, base)
            if not ex.is_Rational:
                out *= base ** ex
                continue
            n, r = divmod(ex * q, q)
            out *= base ** n
            if r:
                inside *= base ** r
        if inside == 1:
            return sign * out
        return sp.Mul(*sp.Mul.make_args(sign * out), sp.Pow(inside, sp.Rational(1, q), evaluate=False), evaluate=False)

    terms = sp.Add.make_args(sp.expand(work))
    new = [one(t) for t in terms]
    return sp.Add(*new, evaluate=False) if len(new) > 1 else new[0]


def _has_fractional_power(e):
    return any(p.exp.is_Rational and not p.exp.is_Integer for p in e.atoms(sp.Pow))


def _restrictions(e, v):
    den = sp.fraction(sp.together(e))[1]
    if den.is_number or v is None:
        return []
    try:
        return [r for r in sp.solve(den, v) if r.is_real]
    except Exception:
        return []


@command("simplify", "Algebra", "simplify <expression>",
         "Simplify polynomials, fractions, and radicals (√12x³ → 2x√(3x)).",
         examples=("simplify sqrt(12x^3)", "simplify (x^2-1)/(x-1)", "simplify 3x^2+x-x+2x^2", "simplify 2sqrt(18)+sqrt(8)"))
def simplify(ctx, a):
    text = a.need("expression")
    e = ctx.expr(text)
    v = pick_var([e]) if e.free_symbols else None
    lines = []
    if _has_fractional_power(e):
        r = tidy_radicals(e)
        lines += pretty_lines(r) if False else [mstr(r)]
        if not e.free_symbols and is_exact_irrational(e):
            lines[-1] += "  ≈ " + approx(e)
    else:
        cands = [e, sp.simplify(e), sp.cancel(e), sp.factor(e)]
        r = min(cands, key=lambda c: (sp.count_ops(c), len(mstr(c))))
        lines += pretty_lines(r)
        if v is not None:
            bad = _restrictions(e, v)
            if bad and sp.simplify(e - r) == 0:
                lines.append("(for " + ", ".join(f"{v.name} ≠ {mstr(b)}" for b in bad) + ")")
    box(f"Simplify: {text}", lines)


@command("poly_gcd", "Algebra", "poly_gcd <poly1> | <poly2>",
         "Greatest common divisor of two polynomials.", examples=("poly_gcd x^2-1 | x^2-x",))
def poly_gcd(ctx, a):
    parts = a.parts("|;,") if a else [ctx.ask("polynomial 1"), ctx.ask("polynomial 2")]
    if len(parts) != 2:
        raise UsageError("Give two polynomials separated by |   e.g.  poly_gcd x^2-1 | x^2-x")
    p, q = ctx.expr(parts[0]), ctx.expr(parts[1])
    g = sp.gcd(p, q)
    box("Polynomial GCD", [f"gcd = {mstr(g)}", f"{mstr(p)} = {mstr(sp.factor(p))}", f"{mstr(q)} = {mstr(sp.factor(q))}"])
