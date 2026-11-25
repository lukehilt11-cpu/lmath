"""
registry.py — the command table and the one dispatcher.

Each command is a small function registered with @command(...). Help text,
the command menu, typo suggestions, and the website's cheat sheet are all
generated from this table, so there is no hand-maintained menu to go stale.
"""
import difflib
import re
from dataclasses import dataclass, field

from . import parse as P
from .errors import Cancelled, MathError, UsageError

GROUP_ORDER = ["Basics", "Algebra", "Algebra 1/2 & Pre-Calc", "Functions & Graphs",
               "Geometry", "Conic Sections", "Trig", "Calculus", "Linear Algebra",
               "Statistics", "Number Theory", "Science", "Finance", "Units", "Practice",
               "Settings"]


@dataclass
class Command:
    name: str
    fn: callable
    group: str
    usage: str
    summary: str
    aliases: tuple = ()
    examples: tuple = ()
    web: bool = True                   # runs in the browser preview?
    hidden: bool = False


COMMANDS = {}          # name or alias -> Command
ORDERED = []           # canonical commands in registration order


def command(name, group, usage, summary, aliases=(), examples=(), web=True, hidden=False):
    def deco(fn):
        cmd = Command(name, fn, group, usage, summary, tuple(aliases), tuple(examples), web, hidden)
        COMMANDS[name] = cmd
        for a in aliases:
            COMMANDS[a] = cmd
        ORDERED.append(cmd)
        return fn
    return deco


# ── argument helper ──────────────────────────────────────────────────────
class Args:
    """What follows the command word, with helpers for prompting and splitting."""

    def __init__(self, ctx, rest: str, cmd: Command = None):
        self.ctx = ctx
        self.rest = rest.strip()
        self.cmd = cmd

    def __bool__(self):
        return bool(self.rest)

    @property
    def words(self):
        return self.rest.split()

    def need(self, prompt: str, default=None) -> str:
        """The whole argument text, asking for it if it was left out."""
        return self.rest if self.rest else self.ctx.ask(prompt, default)

    def word(self, i: int, prompt: str, default=None) -> str:
        w = self.words
        return w[i] if len(w) > i else self.ctx.ask(prompt, default)

    def parts(self, seps="|;") -> list:
        return [p.strip() for p in P.split_top(self.rest, seps)] if self.rest else []

    def kw(self, *names) -> dict:
        """Pull name=value pairs out of the argument text (and remove them from it)."""
        found = {}
        for n in names:
            m = re.search(rf"(?:^|\s){n}\s*=\s*(\S+)", self.rest)
            if m:
                found[n] = m.group(1)
                self.rest = (self.rest[:m.start()] + " " + self.rest[m.end():]).strip()
        return found

    def phrase(self, *keys):
        """Pull 'from A to B' / 'at P' style phrases out of the text. Returns dict key->text."""
        found = {}
        text = self.rest
        positions = []
        for k in keys:
            m = re.search(rf"(?:^|\s)({k})\s+", text)
            if m:
                positions.append((m.start(), m.end(), k))
        positions.sort()
        if not positions:
            return {}, text
        head = text[:positions[0][0]].strip()
        for idx, (s, e, k) in enumerate(positions):
            stop = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
            found[k] = text[e:stop].strip()
        return found, head


# ── dispatch ─────────────────────────────────────────────────────────────
_WORD = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)\s*(.*)$", re.S)


def known_names():
    return set(COMMANDS)


def suggest(word: str):
    return difflib.get_close_matches(word.lower(), list(COMMANDS), n=3, cutoff=0.6)


def run_command(ctx, cmd: Command, rest: str):
    cmd.fn(ctx, Args(ctx, rest, cmd))


def dispatch(ctx, line: str):
    """Run one line of input. Never raises for student mistakes — prints a friendly message."""
    ctx.reserved = set(COMMANDS)
    line = line.strip()
    if not line or line.startswith("#"):
        return
    try:
        _dispatch(ctx, line)
    except Cancelled:
        print("  (cancelled)")
    except UsageError as e:
        print(f"  {e}")
    except MathError as e:
        print(f"  {e}")
    except RecursionError:
        print("  That expression is too deeply nested for me to work with.")
    except (ValueError, ZeroDivisionError, TypeError, OverflowError, ArithmeticError, KeyError, IndexError) as e:
        print(f"  Something went wrong with that input ({type(e).__name__}: {e}).")
        print("  Check the numbers and try again, or type: help")


def _dispatch(ctx, line):
    m = _WORD.match(line)
    word, rest = (m.group(1), m.group(2)) if m else ("", line)
    cmd = COMMANDS.get(word.lower()) if word else None

    # f(x) = ... defines a function, unless the word is really a command
    if ctx.looks_like_def(line) and not (cmd and not re.match(rf"^{word}\s*\(", line)):
        from .commands.functions import do_define
        do_define(ctx, line)
        return

    # name = value assigns a variable
    am = re.match(r"^([A-Za-z_]\w*)\s*=\s*(?!=)(.+)$", line)
    if am and not cmd and not P.split_relation(line):
        from .commands.functions import do_assign
        do_assign(ctx, am.group(1), am.group(2))
        return

    if cmd:
        run_command(ctx, cmd, rest)
        return

    # a bare function name, or a bare word that is clearly not math
    if word and not rest.strip():
        if word in ctx.fn_src:
            print(f"  {word} is a function — use it like {word}(3) or {word}(x), or see it with:  fn {word}")
            return
        if word.isalpha() and len(word) >= 4 and word not in ctx.vars:
            close = suggest(word)
            print(f"  I don't know '{word}'." + (f" Did you mean: {', '.join(close)}?" if close else " Type 'help' to see what I can do."))
            return

    # An unknown first word that looks like a mistyped command (solv x+1=2)
    if word and len(word) >= 3 and word.isalpha() and rest.strip() and not rest.lstrip().startswith(("+", "-", "*", "/", "^", "=", "(", ")", "<", ">")):
        close = suggest(word)
        if close:
            print(f"  I don't know the command '{word}'. Did you mean: {', '.join(close)}?")
            return

    # Not a command: treat it as math the student typed directly.
    from .commands import algebra
    if P.split_relation(line):
        COMMANDS["inequality"].fn(ctx, Args(ctx, line))
        return
    if P.split_equation(line) or ";" in line:
        print("  (treating this as: solve " + line + ")")
        COMMANDS["solve"].fn(ctx, Args(ctx, line))
        return
    try:
        algebra.do_calc(ctx, line)
    except MathError as e:
        close = suggest(word) if word else []
        if close and not rest.strip().startswith(("(", "=")):
            print(f"  I don't know the command '{word}'. Did you mean: {', '.join(close)}?")
        elif close and len(word) > 3:
            print(f"  I don't know the command '{word}'. Did you mean: {', '.join(close)}?")
        else:
            print(f"  {e}")
        print("  Type 'help' to see everything I can do.")


# ── help ─────────────────────────────────────────────────────────────────
def grouped():
    out = {}
    for c in ORDERED:
        if not c.hidden:
            out.setdefault(c.group, []).append(c)
    ordered = [(g, out[g]) for g in GROUP_ORDER if g in out]
    ordered += [(g, v) for g, v in out.items() if g not in GROUP_ORDER]
    return ordered


def catalog(web_only=False):
    """Plain data describing every command (used by the website's cheat sheet)."""
    data = []
    for g, cmds in grouped():
        items = [dict(name=c.name, usage=c.usage, summary=c.summary, examples=list(c.examples))
                 for c in cmds if (c.web or not web_only)]
        if items:
            data.append(dict(group=g, commands=items))
    return data
