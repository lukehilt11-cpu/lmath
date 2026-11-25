"""numtheory.py — primes, factoring, gcd/lcm with working, modular arithmetic, base conversion."""
import sympy as sp

from ..errors import MathError, UsageError
from ..fmt import box
from ..registry import command


def _int(ctx, text, what="number"):
    v = ctx.number(text, what)
    if not v.is_Integer:
        raise MathError(f"The {what} must be a whole number.")
    return int(v)


def _ints(ctx, a, n, labels):
    w = a.rest.replace(",", " ").split()
    out = [_int(ctx, t) for t in w[:n]]
    while len(out) < n:
        out.append(_int(ctx, ctx.ask(labels[len(out)])))
    return out


def _fstr(n):
    return " × ".join(f"{p}^{e}" if e > 1 else str(p) for p, e in sorted(sp.factorint(n).items()))


@command("prime", "Number Theory", "prime <n>", "Is n prime? Shows factors, next and previous primes.", aliases=("isprime",), examples=("prime 97", "prime 1001"))
def prime(ctx, a):
    n = _int(ctx, a.need("n"))
    p = sp.isprime(n)
    lines = [f"n = {n}", f"Prime: {'YES' if p else 'NO'}"]
    if not p and n > 3:
        lines.append(f"Factors: {_fstr(n)}")
    lines.append(f"Next prime: {sp.nextprime(n)}")
    if n > 2:
        lines.append(f"Previous prime: {sp.prevprime(n)}")
    box(f"Prime: {n}", lines)


@command("primes", "Number Theory", "primes <limit>", "All primes up to a limit.", aliases=("prime_list",), examples=("primes 50",))
def primes(ctx, a):
    lim = _int(ctx, a.need("limit"), "limit")
    if lim > 2_000_000:
        raise MathError("Please use a limit of 2,000,000 or less.")
    ps = list(sp.primerange(2, lim + 1))
    box(f"Primes ≤ {lim}", [f"Count: {len(ps)}", ", ".join(map(str, ps[:80])) + (" …" if len(ps) > 80 else "")])


@command("factorize", "Number Theory", "factorize <n>", "Prime factorization, with the division steps.", aliases=("pfactor",), examples=("factorize 360", "factorize 1001"))
def factorize(ctx, a):
    n = _int(ctx, a.need("n"))
    if n < 2:
        raise MathError("Use a whole number of 2 or more.")
    lines, rem, d = [f"Factorizing {n}:"], n, 2
    while d * d <= rem:
        while rem % d == 0:
            lines.append(f"  {rem} ÷ {d} = {rem // d}")
            rem //= d
        d += 1 if d == 2 else 2
        if d > 2_000_000:
            break
    if rem > 1:
        lines.append(f"  {rem} is prime")
    box(f"Factorize: {n}", lines + [f"{n} = {_fstr(n)}", f"Number of divisors: {sp.divisor_count(n)}"])


@command("divisors", "Number Theory", "divisors <n>", "All divisors of n.", examples=("divisors 36",))
def divisors(ctx, a):
    n = _int(ctx, a.need("n"))
    ds = sp.divisors(n)
    box(f"Divisors of {n}", [f"{len(ds)} divisors: " + ", ".join(map(str, ds)), f"Sum of divisors = {sum(ds)}"])


@command("gcd", "Number Theory", "gcd <a> <b> [c …]", "Greatest common divisor with the Euclidean algorithm shown.", examples=("gcd 48 18",))
def gcd(ctx, a):
    nums = [_int(ctx, t) for t in a.need("numbers").replace(",", " ").split()]
    if len(nums) < 2:
        raise UsageError("Give two or more whole numbers.")
    lines = []
    g = nums[0]
    for b in nums[1:]:
        x, y = abs(g), abs(b)
        while y:
            lines.append(f"  {x} = {x // y}·{y} + {x % y}")
            x, y = y, x % y
        g = x
    box("GCD", lines + [f"gcd({', '.join(map(str, nums))}) = {g}"])


@command("lcm", "Number Theory", "lcm <a> <b> [c …]", "Least common multiple.", examples=("lcm 4 6 10",))
def lcm(ctx, a):
    nums = [_int(ctx, t) for t in a.need("numbers").replace(",", " ").split()]
    if len(nums) < 2:
        raise UsageError("Give two or more whole numbers.")
    lines, cur = [], nums[0]
    for b in nums[1:]:
        g = sp.igcd(cur, b)
        new = abs(cur * b) // g
        lines.append(f"  lcm({cur}, {b}) = {cur}×{b} ÷ gcd = {cur * b} ÷ {g} = {new}")
        cur = new
    box("LCM", lines + [f"LCM = {cur}"])


@command("gcd_ext", "Number Theory", "gcd_ext <a> <b>", "Extended Euclid: Bézout's identity and the modular inverse.", aliases=("bezout",), examples=("gcd_ext 240 46",))
def gcd_ext(ctx, a):
    x, y = _ints(ctx, a, 2, ("a", "b"))
    s, t, g = sp.gcdex(x, y)
    lines = [f"gcd({x}, {y}) = {g}", f"Bézout:  {x}·({s}) + {y}·({t}) = {g}"]
    if g == 1 and y > 1:
        lines.append(f"Modular inverse: {x}⁻¹ ≡ {int(s) % y}  (mod {y})")
    box(f"Extended GCD({x}, {y})", lines)


@command("modexp", "Number Theory", "modexp <base> <exp> <mod>", "Modular exponentiation by square-and-multiply.", aliases=("powmod",), examples=("modexp 7 128 13",))
def modexp(ctx, a):
    b, e, m = _ints(ctx, a, 3, ("base", "exponent", "modulus"))
    if m < 1 or e < 0:
        raise MathError("Use a positive modulus and a non-negative exponent.")
    lines, result, base, ex = [f"{b}^{e} mod {m}", f"exponent in binary: {bin(e)[2:]}"], 1, b % m, e
    while ex:
        bit = ex & 1
        lines.append(f"  bit {bit}: base = {base}" + (f",  result = {result}·{base} mod {m} = {result * base % m}" if bit else ""))
        if bit:
            result = result * base % m
        base = base * base % m
        ex >>= 1
    box("Modular exponentiation", lines + [f"{b}^{e} ≡ {result} (mod {m})"])


@command("baseconv", "Number Theory", "baseconv <number> <from-base> <to-base>", "Convert between bases 2–36, showing the work.",
         aliases=("base_convert",), examples=("baseconv 255 10 16", "baseconv 1011 2 10", "baseconv FF 16 2"))
def baseconv(ctx, a):
    w = a.rest.split()
    if len(w) < 3:
        w += [ctx.ask(p) for p in ("number", "from base", "to base")[len(w):]]
    num, fb, tb = w[0].upper(), int(w[1]), int(w[2])
    if not (2 <= fb <= 36 and 2 <= tb <= 36):
        raise MathError("Bases must be between 2 and 36.")
    D = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if any(ch not in D[:fb] for ch in num):
        raise MathError(f"'{num}' has digits that aren't valid in base {fb}.")
    dec = int(num, fb)
    lines = [f"{num} (base {fb}) → decimal:"]
    for i, ch in enumerate(reversed(num)):
        lines.append(f"  {ch} × {fb}^{i} = {D.index(ch) * fb ** i}")
    lines.append(f"  total = {dec}")
    out, n = [], dec
    if dec == 0:
        out = ["0"]
    else:
        lines.append(f"decimal → base {tb}:")
        while n:
            lines.append(f"  {n} ÷ {tb} = {n // tb} remainder {n % tb} ({D[n % tb]})")
            out.append(D[n % tb])
            n //= tb
    box(f"Base {fb} → base {tb}", lines + [f"{num} (base {fb}) = {''.join(reversed(out))} (base {tb})"])


@command("totient", "Number Theory", "totient <n>", "Euler's totient φ(n).", aliases=("phi",), examples=("totient 36",))
def totient(ctx, a):
    n = _int(ctx, a.need("n"))
    if n < 1:
        raise MathError("Use a positive whole number.")
    box(f"φ({n})", [f"{n} = {_fstr(n)}" if n > 1 else "φ(1) = 1", "φ(n) = n·∏(1 − 1/p) over the primes p dividing n", f"φ({n}) = {sp.totient(n)}"])
