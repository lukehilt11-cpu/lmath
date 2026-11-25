"""
session.py — the Context: everything one student session remembers.

Variables (r = 5), user functions (f(x) = 3x+1), settings (steps on/off),
and how to talk to the student (prompts, graph output). Variables and
functions are saved to the data folder so they survive closing the program.
"""
import json
import os
import re

import sympy as sp

from . import parse as P
from .errors import Cancelled, MathError, UsageError

_FN_DEF = re.compile(r"^\s*(?:def\s+)?([A-Za-z_]\w*)\s*\(([^()]*)\)\s*=\s*(.+?)\s*$")
_VAR_DEF = re.compile(r"^\s*(?:set\s+)?([A-Za-z_]\w*)\s*(?:=|\s)\s*(.+?)\s*$")
_IDENT = re.compile(r"^[A-Za-z_]\w*$")


class Context:
    def __init__(self, data_dir=None, interactive=False, input_fn=input):
        self.data_dir = data_dir
        self.interactive = interactive
        self.input_fn = input_fn
        self.vars = {}                 # name -> SymPy value
        self.fn_src = {}               # name -> "f(x) = 3x+1"
        self.settings = {"steps": True}
        self.reserved = set()          # command names (filled in by the registry)
        self.graph_sink = None         # callable(payload) set by the front-end
        self.last_data = None          # rows for `export`
        self.ans = None
        self._ns_cache = None
        if data_dir:
            self.load()

    # ── namespace: what names an expression may use ──────────────────────
    def namespace(self) -> dict:
        if self._ns_cache is not None:
            return self._ns_cache
        ns = dict(self.vars)
        for name, src in self.fn_src.items():
            m = _FN_DEF.match(src)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            syms = [sp.Symbol(p) for p in params]
            body = P.parse(m.group(3), {**ns, **{p: s for p, s in zip(params, syms)}})
            ns[name] = sp.Lambda(tuple(syms), body)
        if self.ans is not None:
            ns["ans"] = self.ans
        self._ns_cache = ns
        return ns

    def _dirty(self):
        self._ns_cache = None

    def expr(self, text: str):
        e = P.parse(text, self.namespace())
        if isinstance(e, sp.Basic) and e.has(sp.Lambda):
            names = ", ".join(n for n in self.fn_src if re.search(rf"\b{n}\b", text)) or "that name"
            raise MathError(f"{names} is a function — use it like {names.split(', ')[0]}(3) or {names.split(', ')[0]}(x).")
        return e

    def number(self, text: str, what: str = "value"):
        """Parse something that must be a plain number (exact), e.g. a radius."""
        v = self.expr(text)
        if not v.is_number:
            raise MathError(f"The {what} must be a number, but '{text}' has a variable in it.")
        return v

    def set_ans(self, value):
        self.ans = value
        self._dirty()

    # ── variables ────────────────────────────────────────────────────────
    def set_var(self, name: str, text: str):
        if not _IDENT.match(name):
            raise MathError(f"'{name}' isn't a valid variable name (use letters, digits, _).")
        if name in P.RESERVED or name in self.reserved:
            if name in ("x", "y", "z", "t"):
                raise MathError(f"'{name}' is kept free for algebra, so it can't hold a number. "
                                "Try another name like a, r, or rate.")
            raise MathError(f"'{name}' is already a built-in name. Pick a different variable name.")
        if name in self.fn_src:
            raise MathError(f"'{name}' is already a function. Delete it first with: delfn {name}")
        value = self.expr(text)
        self.vars[name] = value
        self._dirty()
        self.save()
        return value

    def del_var(self, name: str) -> bool:
        ok = self.vars.pop(name, None) is not None
        self._dirty()
        self.save()
        return ok

    # ── functions ────────────────────────────────────────────────────────
    @staticmethod
    def looks_like_def(line: str) -> bool:
        m = _FN_DEF.match(line)
        return bool(m) and "==" not in line

    def define_function(self, line: str):
        m = _FN_DEF.match(line)
        if not m:
            raise UsageError("Define a function like this:  f(x) = 3x+1")
        name, params_s, body = m.groups()
        params = [p.strip() for p in params_s.split(",") if p.strip()]
        if not params or not all(_IDENT.match(p) for p in params):
            raise MathError("Function inputs must be names, like f(x) or h(x, y).")
        if name in P.RESERVED or name in self.reserved:
            raise MathError(f"'{name}' is a built-in name, so it can't be a function. Try f, g, or h.")
        if name in self.vars:
            raise MathError(f"'{name}' is already a variable. Remove it first with: unset {name}")
        old = self.fn_src.get(name)
        self.fn_src[name] = f"{name}({', '.join(params)}) = {body}"
        self._dirty()
        try:
            self.namespace()                        # validates the body right now
        except MathError:
            if old is None:
                del self.fn_src[name]
            else:
                self.fn_src[name] = old
            self._dirty()
            raise
        self.save()
        return name, params, body, old is not None

    def del_function(self, name: str) -> bool:
        ok = self.fn_src.pop(name, None) is not None
        self._dirty()
        self.save()
        return ok

    # ── talking to the student ───────────────────────────────────────────
    def ask(self, label: str, default=None) -> str:
        if not self.interactive:
            raise UsageError(f"I need a value for '{label}'. Type 'help' to see how to use this command.")
        suffix = f" [{default}]" if default is not None else ""
        try:
            raw = self.input_fn(f"  {label}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise Cancelled("cancelled") from None
        if not raw and default is not None:
            return str(default)
        return raw

    # ── saving ───────────────────────────────────────────────────────────
    def _state_file(self):
        return os.path.join(self.data_dir, "state.json") if self.data_dir else None

    def save(self):
        path = self._state_file()
        if not path:
            return
        data = {"functions": self.fn_src,
                "variables": {k: str(v) for k, v in self.vars.items()},
                "settings": self.settings}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def load(self):
        path = self._state_file()
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.settings.update(data.get("settings", {}))
            for name, text in data.get("variables", {}).items():
                try:
                    self.vars[name] = P.parse(text, {})
                except MathError:
                    pass
            for name, src in data.get("functions", {}).items():
                self.fn_src[name] = src
            self._dirty()
            try:
                self.namespace()
            except MathError:
                self.fn_src.clear()
                self._dirty()
        except (OSError, ValueError):
            pass

    def reset(self):
        self.vars.clear()
        self.fn_src.clear()
        self.ans = None
        self._dirty()
        self.save()
