"""Parser, formatter, and session behaviour."""
import unittest

import sympy as sp

import helpers  # noqa: F401
from helpers import new_ctx, run
from lmath import fmt, parse
from lmath.errors import MathError


class ParseTests(unittest.TestCase):
    def p(self, s):
        return parse.parse(s)

    def test_implicit_multiplication(self):
        x = sp.Symbol("x")
        self.assertEqual(self.p("2x+3"), 2 * x + 3)
        self.assertEqual(self.p("2(x+1)"), 2 * x + 2)
        self.assertEqual(sp.expand(self.p("x(x+1)")), x ** 2 + x)
        self.assertEqual(sp.expand(self.p("(x+1)(x-1)")), x ** 2 - 1)

    def test_decimals_stay_exact(self):
        self.assertEqual(self.p("0.25"), sp.Rational(1, 4))
        self.assertEqual(self.p("0.5x+1/3"), sp.Symbol("x") / 2 + sp.Rational(1, 3))

    def test_special_notation(self):
        self.assertEqual(self.p("35%"), sp.Rational(7, 20))
        self.assertEqual(self.p("√12"), 2 * sp.sqrt(3))
        self.assertEqual(self.p("sin(30°)"), sp.Rational(1, 2))
        self.assertEqual(self.p("|−3|"), 3)
        self.assertEqual(self.p("π"), sp.pi)
        self.assertEqual(self.p("2^-1"), sp.Rational(1, 2))

    def test_log_conventions(self):
        self.assertEqual(self.p("log(100)"), 2)
        self.assertEqual(self.p("ln(e)"), 1)

    def test_bad_input_is_friendly(self):
        for bad in ("2x+", "((x+1)", "x^^2"):
            with self.assertRaises(MathError):
                self.p(bad)
        with self.assertRaises(MathError):
            self.p("__import__('os')")

    def test_split_helpers(self):
        self.assertEqual(parse.split_equation("2x+3=11"), ("2x+3", "11"))
        self.assertIsNone(parse.split_equation("x<=3"))
        self.assertEqual(parse.split_relation("-3<2x+1<=7"), (["-3", "2x+1", "7"], ["<", "<="]))
        self.assertEqual(parse.split_top("f(1,2), x+1"), ["f(1,2)", " x+1"])


class FormatTests(unittest.TestCase):
    def test_exact_strings(self):
        cases = {"2*sqrt(3)": "2√3", "x**2/4": "x²/4", "pi/6": "π/6", "3+2*I": "3 + 2i", "Abs(x)": "|x|",
                 "sqrt(x+1)": "√(x + 1)", "1/x": "1/x", "-x+3": "-x + 3"}
        for src, want in cases.items():
            self.assertEqual(fmt.mstr(sp.sympify(src)), want)

    def test_show_adds_decimal_only_for_irrationals(self):
        self.assertEqual(fmt.show(sp.Rational(3, 4)), "3/4")
        self.assertEqual(fmt.show(sp.sqrt(2)), "√2  ≈ 1.41421")
        self.assertEqual(fmt.show(sp.oo), "∞")

    def test_sets(self):
        self.assertEqual(fmt.set_str(sp.Interval.open(3, sp.oo)), "(3, ∞)")
        self.assertEqual(fmt.set_str(sp.Interval(-2, 5)), "[-2, 5]")


class SessionTests(unittest.TestCase):
    def test_variables_and_functions(self):
        ctx = new_ctx()
        run("r = 5", ctx)
        self.assertIn("25π", run("circle r", ctx))
        run("f(x) = 3x+1", ctx)
        self.assertIn("= 10", run("f(3)", ctx))
        run("g(x) = f(x)^2", ctx)
        self.assertIn("= 100", run("g(3)", ctx))
        self.assertIn("= 3x + 1", run("f(x)", ctx).replace("= 3x + 1", "= 3x + 1"))
        run("f(x) = x+1", ctx)
        self.assertIn("= 16", run("g(3)", ctx))          # g follows the new f

    def test_cannot_shadow_algebra_letters(self):
        out = run("x = 5")
        self.assertIn("kept free for algebra", out)

    def test_typo_help(self):
        self.assertIn("Did you mean: solve", run("solv x+1=2"))

    def test_persistence(self):
        import tempfile
        from lmath.session import Context
        with tempfile.TemporaryDirectory() as d:
            c1 = Context(data_dir=d)
            c1.set_var("rate", "3/100")
            c1.define_function("f(x) = 2x")
            c2 = Context(data_dir=d)
            self.assertEqual(c2.vars["rate"], sp.Rational(3, 100))
            self.assertIn("f", c2.fn_src)


if __name__ == "__main__":
    unittest.main()
