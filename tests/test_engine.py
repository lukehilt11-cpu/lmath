"""The real program: piped input through engine.py, and the browser entry point."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import helpers  # noqa: F401
from helpers import SRC

ENGINE = os.path.join(SRC, "engine.py")


def engine(stdin="", args=()):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", LMATH_DATA=tempfile.mkdtemp(prefix="lmath-test-"))
    r = subprocess.run([sys.executable, ENGINE, *args], input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=120, env=env)
    return r.returncode, r.stdout, r.stderr


class EngineTests(unittest.TestCase):
    def test_version(self):
        code, out, _ = engine(args=["--version"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("lmath 4."))

    def test_one_shot(self):
        code, out, err = engine(args=["-c", "solve 2x+3=11"])
        self.assertEqual(code, 0, err)
        self.assertIn("x = 4", out)

    def test_piped_session_keeps_state(self):
        code, out, err = engine("r = 5\ncircle r\nf(x)=2x+1\nf(3)\n")
        self.assertEqual(code, 0, err)
        self.assertIn("25π", out)
        self.assertIn("= 7", out)
        self.assertEqual(err.strip(), "")

    def test_no_traceback_on_garbage(self):
        code, out, err = engine("))((\n???\nsolve\nsolve x^2\n@@\n")
        self.assertEqual(code, 0)
        self.assertNotIn("Traceback", out + err)

    def test_help_lists_every_group(self):
        _, out, _ = engine("help\n")
        for word in ("Algebra", "Geometry", "Calculus", "Statistics", "Functions & Graphs"):
            self.assertIn(word, out)


class WebApiTests(unittest.TestCase):
    def test_run_and_graph(self):
        from lmath import webapi
        r = json.loads(webapi.run("solve 2x+3=11"))
        self.assertIn("x = 4", r["out"])
        self.assertIsNone(r["graph"])
        g = json.loads(webapi.run("plot x^2-1"))
        self.assertEqual(g["graph"]["series"][0]["type"], "fn")

    def test_desktop_only_commands_are_blocked_politely(self):
        from lmath import webapi
        self.assertIn("desktop app", json.loads(webapi.run("quiz linear"))["out"])

    def test_catalog_has_examples(self):
        from lmath import webapi
        cat = json.loads(webapi.catalog_json())
        self.assertTrue(cat["version"].startswith("4."))
        count = sum(len(g["commands"]) for g in cat["groups"])
        self.assertGreater(count, 80)

    def test_every_catalog_example_runs_without_traceback(self):
        from lmath import webapi
        cat = json.loads(webapi.catalog_json())
        for g in cat["groups"]:
            for c in g["commands"]:
                for ex in c["examples"]:
                    out = json.loads(webapi.run(ex))["out"]
                    self.assertNotIn("Traceback", out, ex)
                    self.assertNotIn("Something went wrong", out, ex)


if __name__ == "__main__":
    unittest.main()
