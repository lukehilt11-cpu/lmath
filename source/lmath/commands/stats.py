"""
stats.py — descriptive statistics, regression, probability. Exact fractions where it makes sense.

Data goes in as numbers separated by spaces or commas:  describe 3 5 7 7 10
Two data sets are separated by |:                       linreg 1 2 3 4 | 2 4 5 8
"""
import math
import re
from collections import Counter

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, show
from ..registry import command


def parse_data(ctx, text, label="data"):
    t = (text or "").strip().strip("[]()")
    if not t:
        t = ctx.ask(label + " (numbers separated by spaces)")
    items = [x for x in re.split(r"[,\s]+", t.strip("[]() ,")) if x]
    if not items:
        raise MathError("I didn't find any numbers.")
    return [ctx.number(x, "data value") for x in items]


def _pair(a, ctx):
    parts = a.parts("|;") if a.rest else []
    if len(parts) != 2:
        raise UsageError("Give two lists of numbers separated by |   e.g.  corr 1 2 3 4 | 2 4 5 8")
    x, y = parse_data(ctx, parts[0], "x values"), parse_data(ctx, parts[1], "y values")
    if len(x) != len(y):
        raise MathError(f"The lists need the same length (x has {len(x)}, y has {len(y)}).")
    if len(x) < 2:
        raise MathError("Need at least 2 data points.")
    return x, y


def _median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def quartiles(v):
    """Median-of-halves quartiles (the textbook method; the median is excluded when n is odd)."""
    v = sorted(v)
    n = len(v)
    lower, upper = v[:n // 2], v[(n + 1) // 2:]
    if not lower:
        return v[0], _median(v), v[-1]
    return _median(lower), _median(v), _median(upper)


@command("describe", "Statistics", "describe <numbers>", "Mean, median, mode, spread, quartiles, outliers, standard deviation.",
         aliases=("stats",), examples=("describe 3 5 7 7 10 12", "describe 88, 92, 79, 95, 85"))
def describe(ctx, a):
    d = sorted(parse_data(ctx, a.rest))
    n = len(d)
    mean = sum(d) / n
    q1, med, q3 = quartiles(d)
    iqr = q3 - q1
    cnt = Counter(d)
    top = max(cnt.values())
    modes = [k for k, c in cnt.items() if c == top] if top > 1 else []
    ss = sum((x - mean) ** 2 for x in d)
    pvar = ss / n
    lines = [f"Data (sorted): {', '.join(mstr(x) for x in d)}", f"n = {n}      sum = {mstr(sum(d))}",
             f"Mean     = {show(mean)}", f"Median   = {show(med)}",
             "Mode     = " + (", ".join(mstr(m) for m in sorted(modes)) if modes else "none (no value repeats)"),
             f"Min = {mstr(d[0])}   Max = {mstr(d[-1])}   Range = {mstr(d[-1] - d[0])}",
             f"Q1 = {show(q1)}   Q3 = {show(q3)}   IQR = {show(iqr)}",
             f"Five-number summary: {mstr(d[0])}, {mstr(q1)}, {mstr(med)}, {mstr(q3)}, {mstr(d[-1])}"]
    lo, hi = q1 - sp.Rational(3, 2) * iqr, q3 + sp.Rational(3, 2) * iqr
    out = [x for x in d if x < lo or x > hi]
    lines.append("Outliers (1.5×IQR rule): " + (", ".join(mstr(x) for x in out) if out else "none") + f"   [fences {show(lo)} and {show(hi)}]")
    lines += ["", f"Population variance σ² = {show(pvar)}", f"Population std dev  σ  = {show(sp.sqrt(pvar))}"]
    if n > 1:
        svar = ss / (n - 1)
        lines += [f"Sample variance     s² = {show(svar)}", f"Sample std dev      s  = {show(sp.sqrt(svar))}"]
    ctx.last_data = [["n", "mean", "median", "min", "max", "sigma", "s"],
                     [n, approx(mean), approx(med), approx(d[0]), approx(d[-1]), approx(sp.sqrt(pvar)), approx(sp.sqrt(ss / (n - 1))) if n > 1 else ""]]
    box("Descriptive statistics", lines)


def _reg(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return mx, my, sxx, syy, sxy


@command("corr", "Statistics", "corr <x values> | <y values>", "Pearson correlation coefficient r.", aliases=("correlation",),
         examples=("corr 1 2 3 4 5 | 2 4 5 4 6",))
def corr(ctx, a):
    x, y = _pair(a, ctx)
    mx, my, sxx, syy, sxy = _reg(x, y)
    if sxx == 0 or syy == 0:
        raise MathError("One of the lists never changes, so the correlation isn't defined.")
    r = sp.radsimp(sxy / sp.sqrt(sxx * syy))
    rv = abs(float(sp.N(r)))
    strength = "very strong" if rv >= 0.9 else "strong" if rv >= 0.7 else "moderate" if rv >= 0.4 else "weak"
    box("Pearson correlation", [f"r = {show(r)}", f"r² = {show(sp.simplify(r ** 2))}",
                                f"{strength} {'positive' if r > 0 else 'negative' if r < 0 else ''} linear relationship".replace("  ", " ")])


@command("linreg", "Statistics", "linreg <x values> | <y values> [predict=<x>]",
         "Least-squares line y = mx + b (exact fractions), r, r², and an optional prediction.",
         aliases=("linear_regression",), examples=("linreg 1 2 3 4 5 | 2 4 5 4 6", "linreg 1 2 3 | 3 5 7 predict=10"))
def linreg(ctx, a):
    kw = a.kw("predict")
    x, y = _pair(a, ctx)
    mx, my, sxx, syy, sxy = _reg(x, y)
    if sxx == 0:
        raise MathError("All the x-values are the same, so no line can be fit.")
    m = sxy / sxx
    b = my - m * mx
    X = sp.Symbol("x")
    lines = [f"Slope m = Sxy/Sxx = {show(m)}", f"Intercept b = ȳ − m·x̄ = {show(b)}", f"Line:  y = {mstr(m * X + b)}"]
    if syy != 0:
        r = sxy / sp.sqrt(sxx * syy)
        lines += [f"r = {show(sp.radsimp(r))}", f"R² = {show(sp.simplify(r ** 2))}"]
    if "predict" in kw:
        v = ctx.number(kw["predict"], "x value")
        lines.append(f"Prediction at x = {mstr(v)}:  y = {show(m * v + b)}")
    ctx.last_data = [["x", "y", "fitted"]] + [[mstr(p), mstr(q), approx(m * p + b)] for p, q in zip(x, y)]
    box("Linear regression", lines)


# ── normal distribution ───────────────────────────────────────────────
def _cdf(x, mu=0.0, sigma=1.0):
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def _inv_cdf(p):
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@command("normal", "Statistics", "normal <pdf|cdf|between|z|inv> <values> [mu sigma]",
         "Normal distribution: density, P(X ≤ x), P(a < X < b), z-scores, and inverse look-ups.",
         aliases=("normal_cdf", "normal_pdf"),
         examples=("normal cdf 1.5", "normal cdf 85 mu=70 sigma=10", "normal between 60 80 mu=70 sigma=10", "normal z 85 mu=70 sigma=10", "normal inv 0.975"))
def normal(ctx, a):
    kw = a.kw("mu", "sigma")
    w = a.rest.split()
    if not w:
        raise UsageError("Examples:  normal cdf 1.5   |   normal between 60 80 mu=70 sigma=10")
    kind = w[0].lower()
    nums = [float(sp.N(ctx.number(t, "number"))) for t in w[1:]]
    mu = float(sp.N(ctx.number(kw.get("mu", "0"), "mean")))
    sg = float(sp.N(ctx.number(kw.get("sigma", "1"), "standard deviation")))
    if sg <= 0:
        raise MathError("The standard deviation must be positive.")
    head = f"N(μ={mu:g}, σ={sg:g})"
    if kind == "pdf" and nums:
        x = nums[0]
        box(f"Normal density — {head}", [f"f({x:g}) = {math.exp(-0.5 * ((x - mu) / sg) ** 2) / (sg * math.sqrt(2 * math.pi)):.6g}"])
    elif kind == "cdf" and nums:
        x = nums[0]
        p = _cdf(x, mu, sg)
        box(f"Normal CDF — {head}", [f"z = (x − μ)/σ = {(x - mu) / sg:.4g}", f"P(X ≤ {x:g}) = {p:.6g}   ({p * 100:.4g}%)", f"P(X > {x:g}) = {1 - p:.6g}"])
    elif kind in ("between", "range") and len(nums) >= 2:
        lo, hi = sorted(nums[:2])
        p = _cdf(hi, mu, sg) - _cdf(lo, mu, sg)
        box(f"Normal — {head}", [f"z-scores: {(lo - mu) / sg:.4g} and {(hi - mu) / sg:.4g}", f"P({lo:g} < X < {hi:g}) = {p:.6g}   ({p * 100:.4g}%)"])
    elif kind == "z" and nums:
        box("z-score", [f"z = (x − μ)/σ = ({nums[0]:g} − {mu:g})/{sg:g} = {show(sp.nsimplify((nums[0] - mu) / sg, rational=True))}"])
    elif kind == "inv" and nums:
        p = nums[0]
        if not 0 < p < 1:
            raise MathError("The probability must be strictly between 0 and 1.")
        z = _inv_cdf(p)
        box(f"Inverse normal — {head}", [f"z = {z:.5g}", f"x = μ + zσ = {mu + z * sg:.6g}   (P(X ≤ x) = {p:g})"])
    else:
        raise UsageError("Kinds: pdf x | cdf x | between a b | z x | inv p   (add mu=… sigma=… if not the standard normal)")


@command("binom", "Statistics", "binom <n> <k> <p>", "Binomial probability P(X = k), cumulative values, mean and standard deviation (exact).",
         aliases=("binomial",), examples=("binom 10 3 1/2", "binom 20 5 0.3"))
def binom(ctx, a):
    w = a.rest.replace(",", " ").split()
    vals = [ctx.number(t, "number") for t in w[:3]]
    while len(vals) < 3:
        vals.append(ctx.number(ctx.ask(("n", "k", "p")[len(vals)]), "number"))
    n, k, p = int(vals[0]), int(vals[1]), vals[2]
    if not (0 <= p <= 1) or not (0 <= k <= n):
        raise MathError("Need 0 ≤ k ≤ n and 0 ≤ p ≤ 1.")
    pm = lambda j: sp.binomial(n, j) * p ** j * (1 - p) ** (n - j)
    eq = pm(k)
    le = sum(pm(j) for j in range(k + 1))
    box(f"Binomial: n = {n}, k = {k}, p = {mstr(p)}", [
        f"P(X = {k}) = C({n},{k})·p^{k}·(1−p)^{n - k} = {show(sp.nsimplify(eq) if eq.is_Rational else eq)}",
        f"P(X ≤ {k}) = {approx(le)}", f"P(X ≥ {k}) = {approx(1 - le + eq)}",
        f"Mean = np = {mstr(n * p)}      Std dev = √(npq) = {show(sp.sqrt(n * p * (1 - p)))}"])


@command("poisson", "Statistics", "poisson <k> <λ>", "Poisson probability P(X = k).", examples=("poisson 3 2.5",))
def poisson(ctx, a):
    w = a.rest.replace(",", " ").split()
    k = int(ctx.number(w[0] if w else ctx.ask("k"), "k"))
    lam = ctx.number(w[1] if len(w) > 1 else ctx.ask("λ (average rate)"), "λ")
    pr = sp.exp(-lam) * lam ** k / sp.factorial(k)
    box(f"Poisson: k = {k}, λ = {mstr(lam)}", [f"P(X = {k}) = e^(−λ)·λ^k / k! = {show(pr)}", f"Mean = Variance = {mstr(lam)}"])


@command("bayes", "Statistics", "bayes <P(A)> <P(B|A)> <P(B)>", "Bayes' theorem: P(A|B) = P(B|A)·P(A) / P(B).",
         examples=("bayes 0.01 0.9 0.05", "bayes 1/100 9/10 1/20"))
def bayes(ctx, a):
    w = a.rest.replace(",", " ").split()
    v = [ctx.number(t, "probability") for t in w[:3]]
    while len(v) < 3:
        v.append(ctx.number(ctx.ask(("P(A)", "P(B|A)", "P(B)")[len(v)]), "probability"))
    pa, pba, pb = v
    if pb == 0:
        raise MathError("P(B) can't be 0.")
    r = pba * pa / pb
    box("Bayes' theorem", [f"P(A) = {mstr(pa)}   P(B|A) = {mstr(pba)}   P(B) = {mstr(pb)}",
                           f"P(A|B) = P(B|A)·P(A) / P(B) = ({mstr(pba)})({mstr(pa)}) / ({mstr(pb)})", f"P(A|B) = {show(r)}   ({approx(r * 100)}%)"])


@command("ztest", "Statistics", "ztest <x̄> <μ> <σ> <n> [alpha=0.05] [tail=two|left|right]",
         "One-sample z-test with a p-value and decision.", aliases=("z_test",), examples=("ztest 52 50 8 36", "ztest 52 50 8 36 tail=right alpha=0.01"))
def ztest(ctx, a):
    kw = a.kw("alpha", "tail")
    w = a.rest.replace(",", " ").split()
    v = [float(sp.N(ctx.number(t, "number"))) for t in w[:4]]
    while len(v) < 4:
        v.append(float(sp.N(ctx.number(ctx.ask(("sample mean x̄", "population mean μ", "population σ", "sample size n")[len(v)]), "number"))))
    xb, mu, sg, n = v
    alpha = float(sp.N(ctx.number(kw.get("alpha", "0.05"), "alpha")))
    tail = kw.get("tail", "two").lower()
    z = (xb - mu) / (sg / math.sqrt(n))
    p = 2 * (1 - _cdf(abs(z))) if tail.startswith("t") else (1 - _cdf(z) if tail.startswith("r") else _cdf(z))
    box("One-sample z-test", [f"z = (x̄ − μ)/(σ/√n) = {z:.4f}", f"p-value ({'two-tailed' if tail.startswith('t') else tail + '-tailed'}) = {p:.5g}",
                              f"α = {alpha:g}  →  " + ("Reject H₀" if p < alpha else "Fail to reject H₀")])


@command("comb", "Statistics", "comb <n> <r>", "Combinations C(n,r), permutations P(n,r), and n!.", aliases=("combinations", "perm"),
         examples=("comb 10 3", "comb 52 5"))
def comb(ctx, a):
    w = a.rest.replace(",", " ").split()
    n = int(ctx.number(w[0] if w else ctx.ask("n"), "n"))
    r = int(ctx.number(w[1] if len(w) > 1 else ctx.ask("r"), "r"))
    if n < 0 or r < 0 or r > n:
        raise MathError("Need 0 ≤ r ≤ n.")
    box(f"Counting: n = {n}, r = {r}", [f"C({n},{r}) = n!/(r!(n−r)!) = {math.comb(n, r):,}", f"P({n},{r}) = n!/(n−r)! = {math.perm(n, r):,}",
                                        f"{n}! = {math.factorial(n):,}" if n <= 25 else f"{n}! has {len(str(math.factorial(n)))} digits"])


@command("ev", "Statistics", "ev <values> | <probabilities>", "Expected value, variance, and standard deviation of a distribution.",
         aliases=("expected_value",), examples=("ev 1 2 3 | 1/2 1/3 1/6", "ev 0 10 100 | 0.8 0.15 0.05"))
def ev(ctx, a):
    vals, probs = _pair(a, ctx)
    if sum(probs) != 1:
        raise MathError(f"The probabilities add up to {mstr(sum(probs))}, but they must add to 1.")
    mean = sum(v * p for v, p in zip(vals, probs))
    var = sum(p * (v - mean) ** 2 for v, p in zip(vals, probs))
    box("Expected value", [f"E[X] = Σ x·P(x) = {show(mean)}", f"Var[X] = Σ P(x)(x − μ)² = {show(var)}", f"Std dev = {show(sp.sqrt(var))}"])
