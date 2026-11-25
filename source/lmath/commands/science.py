"""science.py — kinematics (SUVAT), projectile motion, F = ma, chemical equation balancing."""
import itertools
import re

import sympy as sp

from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, show, show_or_approx
from ..registry import command

s_, u_, v_, a_, t_ = sp.symbols("s u v a t", real=True)
G = sp.Rational(49, 5)                      # 9.8 m/s² (override with g=…)

_SUVAT = [
    ("v = u + at", sp.Eq(v_, u_ + a_ * t_)),
    ("s = ut + ½at²", sp.Eq(s_, u_ * t_ + a_ * t_ ** 2 / 2)),
    ("v² = u² + 2as", sp.Eq(v_ ** 2, u_ ** 2 + 2 * a_ * s_)),
    ("s = ½(u + v)t", sp.Eq(s_, (u_ + v_) * t_ / 2)),
    ("s = vt − ½at²", sp.Eq(s_, v_ * t_ - a_ * t_ ** 2 / 2)),
]
_NAMES = {"s": "displacement (m)", "u": "initial velocity (m/s)", "v": "final velocity (m/s)", "a": "acceleration (m/s²)", "t": "time (s)"}


@command("kine", "Science", "kine <any 3 of> s= u= v= a= t=", "Kinematics (SUVAT): give any three and I find the other two.",
         aliases=("kinematics",), examples=("kine u=0 a=9.8 t=3", "kine u=20 v=0 a=-9.8", "kine s=100 u=0 t=5"))
def kine(ctx, a):
    kw = a.kw("s", "u", "v", "a", "t")
    if len(kw) < 3 and ctx.interactive:
        for n in "suvat":
            if n not in kw and len(kw) < 3:
                r = ctx.ask(f"{_NAMES[n]} (blank to skip)")
                if r:
                    kw[n] = r
    if len(kw) != 3:
        raise UsageError("Give exactly three of s, u, v, a, t — for example:  kine u=0 a=9.8 t=3")
    sym = {"s": s_, "u": u_, "v": v_, "a": a_, "t": t_}
    known = {sym[k]: ctx.number(val, k) for k, val in kw.items()}
    unknown = [x for x in sym.values() if x not in known]
    sols = []
    for (l1, e1), (l2, e2) in itertools.combinations(_SUVAT, 2):
        try:
            res = sp.solve([e1.subs(known), e2.subs(known)], unknown, dict=True)
        except Exception:
            continue
        for r in res:
            if len(r) == 2 and all(sp.simplify(e.lhs.subs({**known, **r}) - e.rhs.subs({**known, **r})) == 0 for _, e in _SUVAT):
                full = {**known, **r}
                if full[t_].is_real and full[t_] >= 0 and full not in sols:
                    sols.append(full)
        if sols:
            break
    if not sols:
        raise MathError("Those three values don't fit together (or time would have to be negative). Check the signs.")
    lines = []
    for i, full in enumerate(sols):
        if len(sols) > 1:
            lines.append(f"Solution {i + 1}:")
        for n in "suvat":
            lines.append(f"  {n} = {show_or_approx(sp.simplify(full[sym[n]]))}   ({_NAMES[n]})")
    box("Kinematics (SUVAT)", ["Given: " + ", ".join(f"{k} = {kw[k]}" for k in kw), ""] + lines)


@command("projectile", "Science", "projectile <speed> <angle> [height] [g=9.8]",
         "Projectile motion: components, peak, flight time, range, impact speed.", examples=("projectile 20 45", "projectile 30 60 10"))
def projectile(ctx, a):
    kw = a.kw("g")
    w = a.rest.replace(",", " ").split()
    v0 = ctx.number(w[0] if w else ctx.ask("launch speed (m/s)"), "speed")
    ang = ctx.number(w[1] if len(w) > 1 else ctx.ask("launch angle (degrees)"), "angle")
    h0 = ctx.number(w[2], "height") if len(w) > 2 else sp.Integer(0)
    g = ctx.number(kw["g"], "g") if "g" in kw else G
    th = ang * sp.pi / 180
    vx, vy = sp.simplify(v0 * sp.cos(th)), sp.simplify(v0 * sp.sin(th))
    tpk = vy / g
    hmax = h0 + vy ** 2 / (2 * g)
    tfl = (vy + sp.sqrt(vy ** 2 + 2 * g * h0)) / g
    rng = vx * tfl
    vimp = sp.sqrt(vx ** 2 + (vy - g * tfl) ** 2)
    f = lambda e: show_or_approx(sp.simplify(e), max_len=26)
    box("Projectile motion", [f"v₀ = {mstr(v0)} m/s at {mstr(ang)}°, from height {mstr(h0)} m, g = {approx(g)} m/s²", "",
                              f"Horizontal speed vₓ = {f(vx)} m/s", f"Vertical speed v_y = {f(vy)} m/s (initial)", "",
                              f"Time to peak = {f(tpk)} s", f"Maximum height = {f(hmax)} m", f"Time of flight = {f(tfl)} s",
                              f"Horizontal range = {f(rng)} m", f"Impact speed = {f(vimp)} m/s"])


@command("force", "Science", "force F= m= a=   (leave out the unknown)", "Newton's second law F = ma.", aliases=("newton_force",),
         examples=("force m=5 a=2", "force F=20 m=4"))
def force(ctx, a):
    kw = a.kw("F", "m", "a")
    if len(kw) != 2:
        raise UsageError("Give two of F, m, a — for example:  force m=5 a=2")
    v = {k: ctx.number(x, k) for k, x in kw.items()}
    if "F" not in v:
        box("F = ma", [f"F = {mstr(v['m'])} × {mstr(v['a'])} = {show(v['m'] * v['a'])} N"])
    elif "m" not in v:
        if v["a"] == 0:
            raise MathError("a can't be 0 when finding the mass.")
        box("F = ma", [f"m = F/a = {mstr(v['F'])} / {mstr(v['a'])} = {show(v['F'] / v['a'])} kg"])
    else:
        if v["m"] == 0:
            raise MathError("m can't be 0 when finding the acceleration.")
        box("F = ma", [f"a = F/m = {mstr(v['F'])} / {mstr(v['m'])} = {show(v['F'] / v['m'])} m/s²"])


# ── chemistry ────────────────────────────────────────────────────────────
def _parse_formula(f):
    def parse(s, i=0):
        counts = {}
        while i < len(s):
            ch = s[i]
            if ch in "([":
                sub, i = parse(s, i + 1)
                m = re.match(r"\d+", s[i:])
                mult = int(m.group()) if m else 1
                i += len(m.group()) if m else 0
                for k, c in sub.items():
                    counts[k] = counts.get(k, 0) + c * mult
            elif ch in ")]":
                return counts, i + 1
            elif ch.isupper():
                m = re.match(r"[A-Z][a-z]?", s[i:])
                el = m.group()
                i += len(el)
                n = re.match(r"\d+", s[i:])
                counts[el] = counts.get(el, 0) + (int(n.group()) if n else 1)
                i += len(n.group()) if n else 0
            else:
                i += 1
        return counts, i
    return parse(f)[0]


@command("balance", "Science", "balance <reactants -> products>", "Balance a chemical equation.",
         aliases=("chem",), examples=("balance H2 + O2 -> H2O", "balance Fe + O2 -> Fe2O3", "balance C3H8 + O2 -> CO2 + H2O", "balance Ca(OH)2 + H3PO4 -> Ca3(PO4)2 + H2O"))
def balance(ctx, a):
    eq = a.need("equation, e.g. H2 + O2 -> H2O")
    m = re.split(r"\s*(?:->|→|=>|=)\s*", eq, maxsplit=1)
    if len(m) != 2:
        raise UsageError("Use an arrow:  H2 + O2 -> H2O")
    split = lambda s: [c.strip() for c in re.split(r"\s*\+\s*", s.strip()) if c.strip()]
    react, prod = split(m[0]), split(m[1])
    comps = react + prod
    parsed = [_parse_formula(c) for c in comps]
    els = sorted({e for p in parsed for e in p})
    if not els or not react or not prod:
        raise MathError("I couldn't read that equation — check the formulas (capital letters start each element).")
    M = sp.Matrix([[(-1 if i >= len(react) else 1) * p.get(e, 0) for i, p in enumerate(parsed)] for e in els])
    ns = M.nullspace()
    if len(ns) != 1:
        raise MathError("I can't find a single way to balance that — check the formulas." if not ns else "That equation can be balanced several independent ways; check it's a single reaction.")
    v = ns[0]
    v = v * sp.ilcm(*[sp.Rational(x).q for x in v])
    v = v / sp.igcd(*[int(x) for x in v])
    if any(x <= 0 for x in v) and all(x <= 0 for x in v):
        v = -v
    if any(x <= 0 for x in v):
        raise MathError("There's no balanced version with positive coefficients — check the formulas.")
    co = [int(x) for x in v]
    term = lambda c, f: f if c == 1 else f"{c}{f}"
    left = " + ".join(term(co[i], comps[i]) for i in range(len(react)))
    right = " + ".join(term(co[len(react) + i], comps[len(react) + i]) for i in range(len(prod)))
    ver = [f"  {e}: {sum(co[i] * parsed[i].get(e, 0) for i in range(len(react)))} = {sum(co[len(react) + i] * parsed[len(react) + i].get(e, 0) for i in range(len(prod)))}  ✓" for e in els]
    box("Chemical equation balancer", [f"Balanced: {left} → {right}", f"Coefficients: {' : '.join(map(str, co))}", "", "Atom count (left = right):"] + ver)
