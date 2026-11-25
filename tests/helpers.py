"""Shared test helpers: run lmath lines exactly like the prompt does and capture the output."""
import contextlib
import io
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "source")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import lmath.commands  # noqa: E402,F401
from lmath.registry import dispatch  # noqa: E402
from lmath.session import Context  # noqa: E402


def new_ctx(**kw):
    ctx = Context(data_dir=None, interactive=False)
    ctx.graph_sink = None
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


def run(line, ctx=None):
    """Run one line and return everything it printed."""
    ctx = ctx or new_ctx()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        dispatch(ctx, line)
    return buf.getvalue()
