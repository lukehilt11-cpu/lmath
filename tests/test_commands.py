"""Every command family: run real input, check the exact answer appears."""
import unittest

import helpers  # noqa: F401
from helpers import new_ctx, run

CASES = [
    # basics / algebra
    ("calc 3/4 + 5/6", ["19/12"]),
    ("calc sqrt(48)", ["4√3"]),
    ("calc 2^10", ["1024"]),
    ("calc 100*1.07^5", ["140.25517307"]),
    ("calc 7/16", ["7/16"]),
    ("3/4+5/6", ["19/12"]),
    ("solve 2x+3=11", ["x = 4"]),
    ("2x+3=11", ["x = 4"]),
    ("solve 2(x+1)=3x-5", ["x = 7"]),
    ("solve x/2+1/3=5", ["x = 28/3"]),
    ("solve x^2-5x+6=0", ["x = 2  or  x = 3"]),
    ("solve 2x^2+3x-1=0", ["(-3 ± √17)/4"]),
    ("solve x^2+4=0", ["±2i"]),
    ("solve x^2-4x+13=0", ["2 ± 3i"]),
    ("solve |2x-1|=5", ["x = -2", "x = 3"]),
    ("solve 3x+2=3x+5", ["No solution"]),
    ("solve 3(x+1)=3x+3", ["All real numbers"]),
    ("solve x^3-6x^2+11x-6=0", ["x = 1", "x = 2", "x = 3"]),
    ("solve sqrt(x+2)=x", ["x = 2"]),
    ("solve (x+1)/(x-2)=3", ["x = 7/2"]),
    ("solve 2^x=32", ["x = 5"]),
    ("solve ln(x)=2", ["e²"]),
    ("solve sin(x)=1/2", ["π/6", "5π/6"]),
    ("solve y=2x+1 for x", ["x = (y - 1)/2"]),
    ("solve x+y=7; x-y=1", ["x = 4", "y = 3"]),
    ("system 2x+3y=6 ; x-y=1", ["x = 9/5", "y = 4/5"]),
    ("system x+y+z=6; 2x-y+z=3; x+2y-z=2", ["x = 1", "y = 2", "z = 3"]),
    ("system y=x^2 ; y=x+2", ["(2, 4)", "(-1, 1)"]),
    ("factor x^2-5x+6", ["(x - 2)(x - 3)"]),
    ("factor 6x^2+11x-10", ["(3x - 2)(2x + 5)"]),
    ("factor x^2-49", ["(x - 7)(x + 7)"]),
    ("factor 2x^3-8x", ["2x(x - 2)(x + 2)"]),
    ("factor x^2+x+1", ["prime"]),
    ("expand (x+2)^3", ["x³ + 6x² + 12x + 8"]),
    ("simplify sqrt(12x^3)", ["2x√(3x)"]),
    ("simplify (x^2-1)/(x-1)", ["x + 1", "x ≠ 1"]),
    ("simplify 2sqrt(18)+sqrt(8)", ["8√2"]),
    ("poly_gcd x^2-1 | x^2-x", ["x - 1"]),
    # algebra 1/2
    ("inequality 2x+3>7", ["x > 2", "(2, ∞)"]),
    ("inequality -2x+4>=10", ["x ≤ -3"]),
    ("inequality -3<2x+1<=7", ["-2 < x ≤ 3", "(-2, 3]"]),
    ("inequality |2x-1|<5", ["(-2, 3)"]),
    ("inequality x^2-5x+6<0", ["(2, 3)"]),
    ("inequality (x+1)/(x-2)>=0", ["(-∞, -1] ∪ (2, ∞)"]),
    ("slope (0,3) (4,-1)", ["= -1", "y = -x + 3"]),
    ("slope 2 5 2 9", ["undefined", "x = 2"]),
    ("line 2x+3y=6", ["y = -2x/3 + 2"]),
    ("proportion 3/4 = x/20", ["x = 15"]),
    ("percent 35 of 80", ["28"]),
    ("percent change 50 to 65", ["30"]),
    ("sequence 2 5 8 11", ["3n - 1"]),
    ("sequence geo 2 3 5", ["162"]),
    ("series arith 3 4 20", ["820"]),
    ("series geo_inf 1 1/2", ["2"]),
    ("completesq x^2+6x+5", ["(x + 3)²", "(-3, -4)"]),
    ("quadform 1 -4 13", ["2 ± 3i"]),
    ("polydiv x^3-2x^2+x-3 | x-1", ["Quotient:  x² - x", "Remainder: -3"]),
    ("synth x^3-2x^2+x-3 1", ["Remainder: -3"]),
    ("remainder x^3-2x^2+x-3 1", ["-3"]),
    ("complexnum mul 3+2i 1-4i", ["11 - 10i"]),
    ("complexnum div 3+2i 1-4i", ["-5/17 + 14i/17"]),
    ("complexnum modulus 3+4i", ["= 5"]),
    ("binomexp x 2 5", ["x⁵ + 10x⁴ + 40x³ + 80x² + 80x + 32"]),
    # geometry & conics
    ("polygon 6 side 5", ["Interior angle  = (n−2)·180°/n = 120°", "75√3/2"]),
    ("angles complementary 3x+10 2x-5", ["x = 17"]),
    ("angles triangle 50 60", ["70°"]),
    ("similar 3,4,5 _,8,_", ["Scale factor (figure 2 ÷ figure 1) = 2", "Area ratio = k² = 4"]),
    ("transform rotate 3 -2 90", ["(2, 3)"]),
    ("transform reflect 3 -2 y=x", ["(-2, 3)"]),
    ("midpoint (1,2) (7,8)", ["(4, 5)"]),
    ("distance 1 2 4 6", ["= 5"]),
    ("circlegeo arc 60 6", ["2π"]),
    ("circlegeo tangent 5 13", ["= 12"]),
    ("circle2 x^2+y^2-4x+6y-12=0", ["(x - 2)² + (y + 3)² = 25", "Center: (2, -3)"]),
    ("parabola 1 -4 3", ["Vertex: (2, -1)", "Focus: (2, -3/4)"]),
    ("identify 4x^2+9y^2-16x+18y-11=0", ["Ellipse", "Foci"]),
    ("identify x^2-4y^2-2x-8y-7=0", ["Hyperbola", "Asymptotes"]),
    ("identify y^2-6y-8x+1=0", ["Parabola"]),
    ("ellipsec 0 0 5 3", ["Foci: (-4, 0), (4, 0)", "15π"]),
    ("hyperbolac 0 0 3 4", ["Foci: (-5, 0), (5, 0)", "y = ±4x/3"]),
    # trig
    ("trig 30", ["sin(30°) = 1/2", "cos(30°) = √3/2"]),
    ("trig 90", ["tan(90°) = undefined"]),
    ("trig pi/6", ["30°"]),
    ("itrig asin 1/2", ["π/6", "30°"]),
    ("coslaw a=5 b=7 C=60", ["√39"]),
    ("coslaw a=3 b=4 c=5", ["C = 90°"]),
    ("sinlaw a=5 A=30 B=45", ["5√2"]),
    ("sinlaw a=10 A=30 b=15", ["Triangle 1", "Triangle 2"]),
    ("ucircle 150", ["(-√3/2, 1/2)"]),
    ("d2r 150", ["5π/6"]),
    ("circle 5", ["10π", "25π"]),
    ("triangle 13 14 15", ["= 84"]),
    ("cone 3 4", ["Slant height ℓ = √(r² + h²) = 5"]),
    ("pyth 3 4 _", ["c = 5", "triple"]),
    ("pyth 5 5 _", ["5√2"]),
    # calculus
    ("deriv x^3+2x", ["3x² + 2"]),
    ("deriv x^4 order=2", ["12x²"]),
    ("integ x^2+3x", ["x³/3 + 3x²/2 + C"]),
    ("integ sin(x) from 0 to pi", ["= 2"]),
    ("limit (x^2-1)/(x-1) at 1", ["= 2"]),
    ("limit 1/x at 0", ["does not exist"]),
    ("critical x^3-3x", ["local maximum", "local minimum"]),
    ("taylor e^x order 3", ["x³/6"]),
    ("newton x^2-2 1", ["1.41421356"]),
    ("riemann x^2 from 0 to 2 n=4", ["Exact integral = 8/3"]),
    # linear algebra
    ("det [[1,2],[3,4]]", ["= -2"]),
    ("inv [[4,7],[2,6]]", ["3/5", "-7/10"]),
    ("eig [[2,1],[1,2]]", ["λ = 1", "λ = 3"]),
    ("dot 1 2 3 | 4 5 6", ["= 32"]),
    ("cross 1 2 3 | 4 5 6", ["[-3, 6, -3]"]),
    ("rref 1 2 3; 4 5 6; 7 8 10", ["Rank = 3"]),
    ("mul [[1,2],[3,4]] | [[0,1],[1,0]]", ["2  1", "4  3"]),
    # stats
    ("describe 3 5 7 7 10 12", ["Mean     = 22/3", "Median   = 7", "Mode     = 7"]),
    ("linreg 1 2 3 | 3 5 7", ["y = 2x + 1"]),
    ("corr 1 2 3 4 | 2 4 6 8", ["r = 1"]),
    ("binom 10 3 1/2", ["15/128"]),
    ("comb 10 3", ["120"]),
    ("ev 1 2 3 | 1/2 1/3 1/6", ["5/3"]),
    ("normal cdf 0", ["0.5"]),
    # number theory / science / units / finance
    ("prime 97", ["YES"]),
    ("factorize 360", ["2^3 × 3^2 × 5"]),
    ("gcd 48 18", ["= 6"]),
    ("lcm 4 6 10", ["= 60"]),
    ("modexp 7 128 13", ["≡ 3"]),
    ("baseconv 255 10 16", ["FF"]),
    ("totient 36", ["= 12"]),
    ("kine u=0 a=9.8 t=3", ["s = 441/10"]),
    ("force m=5 a=2", ["F = 5 × 2 = 10 N"]),
    ("balance H2 + O2 -> H2O", ["2H2 + O2 → 2H2O"]),
    ("balance C3H8 + O2 -> CO2 + H2O", ["C3H8 + 5O2 → 3CO2 + 4H2O"]),
    ("units 5 ft cm", ["152.4 cm"]),
    ("units 98.6 F C", ["37"]),
    ("units 60 mph m/s", ["26.8224"]),
    ("interest P=1000 r=5% t=3 n=12", ["1,161.47"]),
    ("amortize 20000 5% 2", ["877.43"]),
    ("irr -1000 300 400 500 600", ["IRR = 24.88"]),
    # practice
    ("worksheet quad 3 seed=1", ["Answer key"]),
]


class CommandTests(unittest.TestCase):
    pass


def _make(line, wants):
    def t(self):
        out = run(line)
        for w in wants:
            self.assertIn(w, out, f"\n--- {line!r} printed:\n{out}")
    return t


for i, (line, wants) in enumerate(CASES):
    setattr(CommandTests, f"test_{i:03d}_" + "".join(c if c.isalnum() else "_" for c in line)[:40], _make(line, wants))


class ErrorMessageTests(unittest.TestCase):
    """Student mistakes must give a plain-English message, never a traceback."""

    def test_no_tracebacks(self):
        bad = ["solve", "solve 2x+", "solve x^2+y^2=1 for q", "factor", "inequality 2x+3", "slope 1 2", "integ", "limit sin(x)/x",
               "inv [[1,2],[2,4]]", "det [[1,2,3],[4,5,6]]", "polygon 2 side 5", "units 5 kg m", "balance H2 -> O3 + He", "normal cdf",
               "binom 5 9 0.5", "plot", "plot 1/", "describe", "worksheet nope", "tvm N=5", "kine u=1", "pyth 3 4 5"]
        for line in bad:
            out = run(line)
            self.assertNotIn("Traceback", out, line)
            self.assertTrue(out.strip(), f"{line!r} printed nothing")

    def test_singular_matrix_message(self):
        self.assertIn("singular", run("inv [[1,2],[2,4]]"))


if __name__ == "__main__":
    unittest.main()
