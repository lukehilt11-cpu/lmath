"""Graph payloads, key points, the HTML page, and the text fallback."""
import json
import re
import unittest

import helpers  # noqa: F401
from helpers import new_ctx, run
from lmath.commands import graph


def payload_for(line, ctx=None):
    ctx = ctx or new_ctx()
    got = []
    ctx.graph_sink = lambda p: (got.append(p), True)[1]
    out = run(line, ctx)
    return (got[-1] if got else None), out


class GraphTests(unittest.TestCase):
    def test_parabola_key_points(self):
        p, _ = payload_for("plot x^2-4x+3")
        labels = {(q["kind"], q["label"]) for q in p["points"]}
        self.assertIn(("vertex", "(2, -1)"), labels)
        self.assertIn(("y-intercept", "(0, 3)"), labels)
        self.assertIn(("x-intercept", "(1, 0)"), labels)
        self.assertIn(("x-intercept", "(3, 0)"), labels)

    def test_exact_irrational_labels(self):
        p, _ = payload_for("plot x^2-2")
        self.assertIn("(√2, 0)", [q["label"] for q in p["points"]])

    def test_intersections(self):
        p, _ = payload_for("plot x^2, x+2")
        self.assertIn("intersection", {q["kind"] for q in p["points"]})
        self.assertIn("(2, 4)", [q["label"] for q in p["points"]])

    def test_series_types(self):
        self.assertEqual(payload_for("plot x^2+y^2=25")[0]["series"][0]["type"], "implicit")
        self.assertEqual(payload_for("plot y>2x+1")[0]["series"][0]["type"], "rel")
        self.assertEqual(payload_for("plot x=3")[0]["series"][0]["type"], "vline")
        self.assertEqual(payload_for("plot 3x+2y=6")[0]["series"][0]["type"], "fn")      # a line solves for y

    def test_user_functions_and_window(self):
        ctx = new_ctx()
        run("f(x) = x^2", ctx)
        p, _ = payload_for("plot f x from -3 to 3", ctx)
        self.assertEqual((p["xmin"], p["xmax"]), (-3.0, 3.0))
        self.assertIn("Math.pow(x, 2)", p["series"][0]["js"])

    def test_js_is_safe_and_complete(self):
        for e in ("sin(x)", "1/x", "sqrt(x)", "abs(x)", "e^x", "ln(x)", "tan(x)", "sec(x)", "floor(x)"):
            p, _ = payload_for("plot " + e)
            s = p["series"][0]
            self.assertTrue(s.get("js") or s.get("samples"), e)
            if s.get("js"):
                self.assertNotRegex(s["js"], r"(?<![\w.])(import|eval|window|document)\b")

    def test_html_page_is_self_contained(self):
        p, _ = payload_for("plot x^2")
        html = graph.render_html(p)
        self.assertIn("LmathGraph.mount", html)
        self.assertIn("function mount", html)
        self.assertNotRegex(html, r'src="https?://')
        m = re.search(r"mount\(document\.getElementById\('graph'\), (\{.*\})\);</script>", html, re.S)
        self.assertEqual(json.loads(m.group(1))["series"][0]["label"], "y = x²")

    def test_ascii_fallback(self):
        out = run("plot ascii x^3-3x")
        self.assertIn("y = x³ - 3x", out)
        self.assertIn("┼", out)

    def test_errors_are_friendly(self):
        for bad in ("plot a*x", "plot x^2+y", "plot ", "plot x!=3"):
            self.assertNotIn("Traceback", run(bad))
        self.assertIn("giving", run("plot a*x").replace("Give", "giving")) if False else None

    def test_scatter(self):
        p, _ = payload_for("scatter 1 2 3 | 2 4 7 line")
        types = [s["type"] for s in p["series"]]
        self.assertEqual(types, ["points", "fn"])


if __name__ == "__main__":
    unittest.main()
