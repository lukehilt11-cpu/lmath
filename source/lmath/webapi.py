"""
webapi.py — the entry point the website calls (through Pyodide) to run lmath in the browser.

    run("solve 2x+3=11")  →  '{"out": "...", "graph": null}'
"""
import contextlib
import io
import json
import re

from . import __version__
from . import commands  # noqa: F401  (registers every command)
from .registry import COMMANDS, catalog, dispatch
from .session import Context

_ctx = None
_graphs = []


def _get():
    global _ctx
    if _ctx is None:
        _ctx = Context(data_dir=None, interactive=False)
        _ctx.graph_sink = lambda payload: (_graphs.append(payload), True)[1]
    return _ctx


def run(line: str) -> str:
    ctx = _get()
    _graphs.clear()
    buf = io.StringIO()
    m = re.match(r"^\s*([A-Za-z_]\w*)", line)
    cmd = COMMANDS.get(m.group(1).lower()) if m else None
    with contextlib.redirect_stdout(buf):
        if cmd is not None and not cmd.web:
            print(f"  '{cmd.name}' needs the desktop app (it isn't available in the browser preview).")
        else:
            dispatch(ctx, line)
    return json.dumps({"out": buf.getvalue(), "graph": _graphs[-1] if _graphs else None})


def catalog_json() -> str:
    return json.dumps({"version": __version__, "groups": catalog(web_only=True)})


def version() -> str:
    return __version__
