"""
quiz.py — practice problems that always have clean answers (built backwards from the answer).

  quiz <topic> [n]        interactive, one problem at a time, checked for you
  worksheet <topic> [n]   a printable list of problems with an answer key (great for teachers)

Answers are checked by meaning, not spelling: 'x=3', '3', and '6/2' are all the same answer.
"""
import random
from fractions import Fraction

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import box
from ..registry import command


def _num(user):
    """A student's typed answer as an exact number, or None."""
    s = user.strip().lower().replace(" ", "")
    for lead in ("x=", "y=", "m=", "n="):
        if s.startswith(lead):
            s = s[len(lead):]
    try:
        v = P.parse(s, {})
        return v if v.is_number else None
    except MathError:
        return None


def _nums(user):
    out = []
    for tok in user.replace(",", " ").replace(" or ", " ").replace("x=", " ").replace("and", " ").split():
        v = _num(tok)
        if v is not None:
            out.append(v)
    return out


def _fmt_poly(*parts):
    return " ".join(parts)


def _gen_linear():
    a = random.choice([2, 3, 4, 5, -2, -3, -4])
    x = random.randint(-10, 10)
    b = random.randint(-15, 15)
    c = a * x + b
    return f"Solve for x:  {a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}", f"x = {x}", lambda u: _num(u) == x


def _quad_text(r1, r2, head="x²"):
    b, c = -(r1 + r2), r1 * r2
    parts = [head]
    if b:
        parts.append(f"{'+' if b > 0 else '-'} {'' if abs(b) == 1 else abs(b)}x")
    if c:
        parts.append(f"{'+' if c > 0 else '-'} {abs(c)}")
    return " ".join(parts)


def _two_roots(lo=-8, hi=8):
    r1 = random.randint(lo, hi)
    r2 = random.randint(lo, hi)
    while r2 == r1:
        r2 = random.randint(lo, hi)
    return sorted([r1, r2])


def _gen_quad():
    r1, r2 = _two_roots()
    return f"Solve:  {_quad_text(r1, r2)} = 0", f"x = {r1}, x = {r2}", lambda u: sorted(set(_nums(u))) == sorted({sp.Integer(r1), sp.Integer(r2)})


def _gen_slope():
    x1, y1 = random.randint(-10, 10), random.randint(-10, 10)
    dx, dy = random.choice([1, 2, 3, -1, -2, -3]), random.choice([1, 2, 3, 4, -1, -2, -3, -4])
    m = sp.Rational(dy, dx)
    return f"Find the slope through ({x1},{y1}) and ({x1 + dx},{y1 + dy})", f"m = {m}", lambda u: _num(u) == m


def _gen_pythag():
    a0, b0, c0 = random.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (6, 8, 10), (9, 12, 15)])
    k = random.choice([1, 1, 1, 2])
    a, b, c = a0 * k, b0 * k, c0 * k
    miss = random.choice("abc")
    if miss == "c":
        return f"Right triangle with legs {a} and {b}. Find the hypotenuse.", str(c), lambda u: _num(u) == c
    if miss == "a":
        return f"Right triangle with leg {b} and hypotenuse {c}. Find the other leg.", str(a), lambda u: _num(u) == a
    return f"Right triangle with leg {a} and hypotenuse {c}. Find the other leg.", str(b), lambda u: _num(u) == b


def _gen_inequality():
    a = random.choice([2, 3, 4, 5, -2, -3, -4])
    xb = random.randint(-10, 10)
    b = random.randint(-15, 15)
    c = a * xb + b
    op = random.choice(["<", ">", "<=", ">="])
    flip = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
    res = flip[op] if a < 0 else op

    def check(u):
        s = u.strip().lower().replace(" ", "").replace("x", "").replace("≤", "<=").replace("≥", ">=")
        for o in ("<=", ">=", "<", ">"):
            if s.startswith(o):
                return o == res and _num(s[len(o):]) == xb
        return False
    return f"Solve for x:  {a}x {'+' if b >= 0 else '-'} {abs(b)} {op} {c}", f"x {res} {xb}", check


def _gen_proportion():
    while True:
        b, d = random.randint(2, 12), random.randint(2, 12)
        ratio = sp.Rational(random.randint(1, 6), random.randint(1, 4))
        a, x = ratio * b, ratio * d
        if a.q <= 4 and x.q <= 4:
            break
    return f"Solve the proportion:  {a}/{b} = x/{d}", f"x = {x}", lambda u: _num(u) == x


def _gen_factor():
    r1, r2 = _two_roots(-9, 9)
    f = lambda r: f"(x - {r})" if r >= 0 else f"(x + {-r})"
    ans = f(r1) + f(r2)
    x = sp.Symbol("x")

    def check(u):
        try:
            e = P.parse(u.replace("=", "-(") + ")" if "=" in u else u, {})
            return sp.expand(e - (x - r1) * (x - r2)) == 0
        except MathError:
            return False
    return f"Factor:  {_quad_text(r1, r2)}", ans, check


def _gen_system():
    x0, y0 = random.randint(-8, 8), random.randint(-8, 8)
    a1, b1 = random.randint(1, 5), random.randint(1, 5) * random.choice([1, -1])
    a2, b2 = random.randint(1, 5), random.randint(1, 5) * random.choice([1, -1])
    while a1 * b2 - a2 * b1 == 0:
        a2, b2 = random.randint(1, 5), random.randint(1, 5) * random.choice([1, -1])
    c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
    eq = lambda a, b, c: f"{'' if a == 1 else a}x {'+' if b >= 0 else '-'} {'' if abs(b) == 1 else abs(b)}y = {c}"

    def check(u):
        t = u.lower().replace("x=", " ").replace("y=", " ").replace("(", " ").replace(")", " ")
        n = _nums(t)
        return len(n) >= 2 and n[0] == x0 and n[1] == y0
    return f"Solve the system:  {eq(a1, b1, c1)}   and   {eq(a2, b2, c2)}", f"x = {x0}, y = {y0}", check


def _gen_sequence():
    a1 = random.randint(-10, 10)
    d = random.choice([1, 2, 3, 4, 5, -1, -2, -3, -4, -5])
    terms = [a1 + i * d for i in range(4)]
    ans = a1 + 4 * d
    return f"What is the next term?  {', '.join(map(str, terms))}, ___", str(ans), lambda u: _num(u) == ans


_SPECIAL = {(0, "sin"): "0", (0, "cos"): "1", (30, "sin"): "1/2", (30, "cos"): "√3/2", (45, "sin"): "√2/2", (45, "cos"): "√2/2",
            (60, "sin"): "√3/2", (60, "cos"): "1/2", (90, "sin"): "1", (90, "cos"): "0"}


def _gen_trig():
    ang, fn = random.choice([0, 30, 45, 60, 90]), random.choice(["sin", "cos"])
    ans = _SPECIAL[(ang, fn)]
    target = P.parse(ans, {})

    def check(u):
        try:
            return sp.simplify(P.parse(u.replace("°", ""), {}) - target) == 0
        except MathError:
            return False
    return f"Find the exact value:  {fn}({ang}°)", ans, check


def _gen_geometry():
    w, h = random.randint(2, 20), random.randint(2, 20)
    if random.choice(["area", "perimeter"]) == "area":
        return f"Find the area of a {w} × {h} rectangle.", str(w * h), lambda u: _num(u) == w * h
    return f"Find the perimeter of a {w} × {h} rectangle.", str(2 * (w + h)), lambda u: _num(u) == 2 * (w + h)


def _gen_exponent():
    b, x = random.choice([2, 3, 4, 5, 10]), random.randint(1, 5)
    return f"Solve for x:  {b}^x = {b ** x}", f"x = {x}", lambda u: _num(u) == x


GENERATORS = {"linear": _gen_linear, "quad": _gen_quad, "slope": _gen_slope, "pythag": _gen_pythag, "inequality": _gen_inequality,
              "proportion": _gen_proportion, "factor": _gen_factor, "system": _gen_system, "sequence": _gen_sequence,
              "trig": _gen_trig, "geometry": _gen_geometry, "exponent": _gen_exponent}


def _setup(a):
    kw = a.kw("seed")
    w = a.rest.split()
    if not w:
        raise UsageError("Pick a topic: " + ", ".join(GENERATORS) + "   e.g.  quiz linear 5")
    topic = w[0].lower()
    if topic not in GENERATORS:
        raise MathError(f"No topic called '{topic}'. Topics: {', '.join(GENERATORS)}")
    n = int(w[1]) if len(w) > 1 and w[1].isdigit() else 5
    if not 1 <= n <= 50:
        raise MathError("Choose between 1 and 50 questions.")
    if "seed" in kw:
        random.seed(int(kw["seed"]))
    return topic, n


@command("quiz", "Practice", "quiz <topic> [n]", "Interactive practice, checked by meaning. Topics: " + ", ".join(GENERATORS),
         examples=("quiz linear 5", "quiz quad", "quiz trig 3"), web=False)
def quiz(ctx, a):
    topic, n = _setup(a)
    if not ctx.interactive:
        raise UsageError("quiz needs a keyboard — try  worksheet " + topic + "  instead.")
    print(f"\n  Quiz: {topic}  ({n} questions) — type your answer, or 'skip'.\n")
    score = 0
    for i in range(1, n + 1):
        prompt, ans, check = GENERATORS[topic]()
        print(f"  Problem {i}: {prompt}")
        u = ctx.ask("your answer")
        if u.lower() == "skip":
            print(f"    Skipped. Answer: {ans}\n")
        elif check(u):
            print("    ✓ Correct!\n")
            score += 1
        else:
            print(f"    ✗ Not quite. Answer: {ans}\n")
    box("Quiz complete", [f"Score: {score}/{n}"])


@command("worksheet", "Practice", "worksheet <topic> [n] [seed=N]", "Make a problem list with an answer key (use seed=N to get the same sheet again).",
         examples=("worksheet quad 8", "worksheet system 6 seed=42"))
def worksheet(ctx, a):
    topic, n = _setup(a)
    probs = [GENERATORS[topic]() for _ in range(n)]
    print(f"\n  Worksheet — {topic}\n")
    for i, (p, _, _) in enumerate(probs, 1):
        print(f"  {i:>2}. {p}")
    print("\n  Answer key")
    print("  " + "   ".join(f"{i}) {ans}" for i, (_, ans, _) in enumerate(probs, 1)))
    print()
