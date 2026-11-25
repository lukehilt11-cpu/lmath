"""finance.py — interest, time value of money, loan amortization, NPV, IRR.

Money is shown to the cent; rates may be typed as 5%, 0.05 or 5/100.
"""
import math

import sympy as sp

from ..errors import MathError, UsageError
from ..fmt import box
from ..registry import command


def _num(ctx, text, name="value"):
    v = ctx.number(text, name)
    return float(sp.N(v))


def _money(x):
    return f"{x:,.2f}"


def _rate(ctx, text):
    t = text.strip()
    v = float(sp.N(ctx.number(t, "rate")))
    return v if t.endswith("%") or v <= 1 or "/" in t or "." in t else v / 100


@command("interest", "Finance", "interest P= r= t= A= [n=12] [mode=simple|compound]  (leave out the unknown)",
         "Simple or compound interest; solves for whichever of P, r, t, A you leave out.",
         examples=("interest P=1000 r=5% t=3", "interest P=1000 r=0.05 t=3 n=12", "interest P=1000 A=1500 t=5 mode=simple"))
def interest(ctx, a):
    kw = a.kw("P", "r", "t", "A", "n", "mode")
    if len([k for k in "PrtA" if k in kw]) < 3:
        raise UsageError("Give three of P (principal), r (rate), t (years), A (final amount) — e.g.  interest P=1000 r=5% t=3")
    P = _num(ctx, kw["P"]) if "P" in kw else None
    r = _rate(ctx, kw["r"]) if "r" in kw else None
    t = _num(ctx, kw["t"]) if "t" in kw else None
    A = _num(ctx, kw["A"]) if "A" in kw else None
    n = int(_num(ctx, kw.get("n", "1")))
    simple = kw.get("mode", "compound").lower().startswith("s")
    lines = [f"Mode: {'simple' if simple else f'compound, {n}×/year'}"]
    if simple:
        if A is None:
            A = P * (1 + r * t); lines += [f"A = P(1 + rt) = {_money(P)}·(1 + {r:g}·{t:g}) = {_money(A)}", f"Interest earned = {_money(A - P)}"]
        elif P is None:
            P = A / (1 + r * t); lines.append(f"P = A/(1 + rt) = {_money(P)}")
        elif r is None:
            r = (A / P - 1) / t; lines.append(f"r = (A/P − 1)/t = {r * 100:.4g}% per year")
        else:
            t = (A / P - 1) / r; lines.append(f"t = (A/P − 1)/r = {t:.4g} years")
    else:
        if A is None:
            A = P * (1 + r / n) ** (n * t)
            lines += [f"A = P(1 + r/n)^(nt) = {_money(P)}·(1 + {r:g}/{n})^({n}·{t:g})", f"A = {_money(A)}", f"Interest earned = {_money(A - P)}",
                      f"(Continuous compounding, Pe^(rt): {_money(P * math.exp(r * t))})"]
        elif P is None:
            P = A / (1 + r / n) ** (n * t); lines.append(f"P = A/(1 + r/n)^(nt) = {_money(P)}")
        elif r is None:
            r = n * ((A / P) ** (1 / (n * t)) - 1); lines.append(f"r = n[(A/P)^(1/nt) − 1] = {r * 100:.4g}% per year")
        else:
            t = math.log(A / P) / (n * math.log(1 + r / n)); lines.append(f"t = ln(A/P) / (n·ln(1 + r/n)) = {t:.4g} years")
    box("Interest", lines)


@command("tvm", "Finance", "tvm N= IY= PV= PMT= FV=  (leave out the unknown)  [due=yes]",
         "Time value of money (like a financial calculator): N periods, IY % per period, PV, PMT, FV.",
         examples=("tvm N=360 IY=0.5 PV=-200000 FV=0", "tvm N=10 IY=5 PV=-1000 PMT=0"))
def tvm(ctx, a):
    kw = a.kw("N", "IY", "PV", "PMT", "FV", "due")
    keys = [k for k in ("N", "IY", "PV", "PMT", "FV") if k in kw]
    if len(keys) != 4:
        raise UsageError("Give four of N, IY (%), PV, PMT, FV and leave out the unknown.")
    due = kw.get("due", "no").lower().startswith(("y", "t", "1"))
    v = {k: _num(ctx, kw[k], k) for k in keys}
    target = next(k for k in ("N", "IY", "PV", "PMT", "FV") if k not in v)
    N, IY, PV, PMT, FV = (v.get(k) for k in ("N", "IY", "PV", "PMT", "FV"))
    k = 1 if due else 0

    def fv(N, i, PV, PMT):
        if abs(i) < 1e-12:
            return -PV - PMT * N
        f = (1 + i) ** N
        return -PV * f - PMT * (1 + i * k) * (f - 1) / i

    if target == "FV":
        FV = fv(N, IY / 100, PV, PMT)
    elif target == "PV":
        i = IY / 100
        PV = -(FV + PMT * N) if abs(i) < 1e-12 else -(FV + PMT * (1 + i * k) * ((1 + i) ** N - 1) / i) / (1 + i) ** N
    elif target == "PMT":
        i = IY / 100
        PMT = -(FV + PV * N) / N if abs(i) < 1e-12 else -(FV + PV * (1 + i) ** N) * i / ((1 + i * k) * ((1 + i) ** N - 1))
    elif target == "N":
        i = IY / 100
        if abs(i) < 1e-12:
            N = -(FV + PV) / PMT if PMT else float("nan")
        else:
            c = PMT * (1 + i * k) / i
            num, den = -FV + c, PV + c
            if den == 0 or num / den <= 0:
                raise MathError("No number of periods fits those values — check the signs (money in vs. out).")
            N = math.log(num / den) / math.log(1 + i)
    else:
        lo, hi = 1e-9, 5.0
        f = lambda i: fv(N, i, PV, PMT) - FV
        if f(lo) * f(hi) > 0:
            raise MathError("I couldn't find a rate that fits — check the signs (money in vs. out).")
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(lo) * f(mid) <= 0:
                hi = mid
            else:
                lo = mid
        IY = (lo + hi) / 2 * 100
    box("Time value of money", [f"Mode: {'annuity due (payments at start)' if due else 'ordinary annuity (payments at end)'}", "",
                                f"N   = {N:,.6g} periods", f"I/Y = {IY:.6g}% per period", f"PV  = {_money(PV)}", f"PMT = {_money(PMT)}", f"FV  = {_money(FV)}",
                                "", f"→ {target} was the unknown"])


@command("amortize", "Finance", "amortize <principal> <annual rate> <years> [periods per year]",
         "Loan payment and an amortization schedule.", examples=("amortize 200000 6% 30", "amortize 20000 0.05 5"))
def amortize(ctx, a):
    w = a.rest.replace(",", "").split()
    if len(w) < 3:
        w += [ctx.ask(p) for p in ("loan amount", "annual rate (e.g. 6%)", "years")[len(w):]]
    P_, r, years = _num(ctx, w[0]), _rate(ctx, w[1]), _num(ctx, w[2])
    ppy = int(_num(ctx, w[3])) if len(w) > 3 else 12
    i, N = r / ppy, int(round(years * ppy))
    if N < 1:
        raise MathError("The loan needs at least one payment.")
    pmt = P_ / N if abs(i) < 1e-12 else P_ * i / (1 - (1 + i) ** -N)
    lines = [f"Loan: {_money(P_)} at {r * 100:g}% for {years:g} years ({N} payments)", f"Payment: {_money(pmt)} per period",
             f"Total paid: {_money(pmt * N)}", f"Total interest: {_money(pmt * N - P_)}", ""]
    bal = P_
    lines.append(f"{'Pmt':>5} {'Interest':>12} {'Principal':>12} {'Balance':>14}")
    for k in range(1, N + 1):
        ip = bal * i
        pp = pmt - ip
        bal -= pp
        if N <= 24 or k % ppy == 0 or k == N or k <= 3:
            lines.append(f"{k:>5} {ip:>12,.2f} {pp:>12,.2f} {max(bal, 0):>14,.2f}")
    box("Loan amortization", lines)


@command("npv", "Finance", "npv <rate> | <cash flows>", "Net present value (cash flow 0 is today).", examples=("npv 8% | -1000 300 400 500 600",))
def npv(ctx, a):
    parts = a.parts("|;")
    if len(parts) != 2:
        raise UsageError("Example:  npv 8% | -1000 300 400 500 600")
    r = _rate(ctx, parts[0])
    cfs = [_num(ctx, t) for t in parts[1].replace(",", " ").split()]
    lines, tot = [], 0.0
    for t, cf in enumerate(cfs):
        pv = cf / (1 + r) ** t
        tot += pv
        lines.append(f"  t={t}:  {cf:>12,.2f}  →  PV {pv:>12,.2f}")
    box(f"NPV at {r * 100:g}%", lines + ["", f"NPV = {_money(tot)}", "Accept the project (NPV > 0)." if tot > 0 else "Reject the project (NPV ≤ 0)."])


@command("irr", "Finance", "irr <cash flows>", "Internal rate of return.", examples=("irr -1000 300 400 500 600",))
def irr(ctx, a):
    cfs = [_num(ctx, t) for t in a.need("cash flows (first is usually negative)").replace(",", " ").split()]
    f = lambda r: sum(c / (1 + r) ** t for t, c in enumerate(cfs))
    grid = [-0.99 + k * 0.01 for k in range(0, 2000)]
    root = None
    for x0, x1 in zip(grid, grid[1:]):
        if f(x0) * f(x1) <= 0:
            lo, hi = x0, x1
            for _ in range(100):
                mid = (lo + hi) / 2
                if f(lo) * f(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            root = (lo + hi) / 2
            break
    if root is None:
        raise MathError("I couldn't find an IRR — the cash flows need to change sign (money out, then money in).")
    box("Internal rate of return", [f"IRR = {root * 100:.4f}% per period", f"Check: NPV at that rate ≈ {f(root):.2e}"])
