"""functions.py — variables and user-defined functions: r = 5, f(x) = 3x+1, table, fns."""
import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import box, mstr, show
from ..registry import command

X = sp.Symbol("x")


def do_define(ctx, line):
    name, params, body, replaced = ctx.define_function(line)
    print(f"  {'Updated' if replaced else 'Defined'}  {name}({', '.join(params)}) = {body}")
    shown = [f"{name}({', '.join(params)}) = {mstr(ctx.expr(body))}"]
    if len(params) == 1:
        try:
            shown.append(f"  try:  {name}(2)  →  {show(ctx.expr(f'{name}(2)'))}")
        except MathError:
            pass
    print("  " + "\n  ".join(shown))


def do_assign(ctx, name, text):
    value = ctx.set_var(name, text)
    print(f"  {name} = {show(value)}")


@command("def", "Functions & Graphs", "f(x) = <expression>",
         "Define your own function, then use it anywhere: f(3), f(x)+1, f(g(2)), plot f.",
         aliases=("define",), examples=("f(x) = 3x+1", "g(x) = x^2-4", "h(x, y) = x^2+y^2", "p(x) = f(x)+g(x)"))
def define(ctx, a):
    do_define(ctx, a.need("definition, e.g. f(x) = 3x+1"))


@command("set", "Functions & Graphs", "set <name> <value>   (or:  r = 5)",
         "Store a number to reuse in later commands.", examples=("set r 5", "rate = 3/100", "circle r"))
def set_(ctx, a):
    w = a.rest.replace("=", " ").split(None, 1)
    if len(w) < 2:
        raise UsageError("Use:  set <name> <value>   e.g.  set r 5")
    do_assign(ctx, w[0], w[1])


@command("vars", "Functions & Graphs", "vars", "Show your saved variables.")
def vars_(ctx, a):
    if not ctx.vars:
        print("  (no variables yet — try:  r = 5)")
    for k, v in ctx.vars.items():
        print(f"  {k} = {show(v)}")


@command("unset", "Functions & Graphs", "unset <name>", "Remove a saved variable.", aliases=("delvar",))
def unset(ctx, a):
    name = a.word(0, "variable name")
    print(f"  Removed {name}." if ctx.del_var(name) else f"  There's no variable called {name}.")


@command("get", "Functions & Graphs", "get <f(3) | name>",
         "Evaluate a function call or look up a variable.", examples=("get f(3)", "get f(g(2))", "get h(2,4)"))
def get(ctx, a):
    text = a.need("what to evaluate, e.g. f(3)")
    if text in ctx.vars:
        print(f"  {text} = {show(ctx.vars[text])}")
        return
    e = ctx.expr(text)
    print(f"  {text} = {show(e)}")


@command("fns", "Functions & Graphs", "fns", "List your saved functions.")
def fns(ctx, a):
    if not ctx.fn_src:
        print("  (no functions yet — try:  f(x) = 3x+1)")
        return
    box("Your functions", list(ctx.fn_src.values()))


@command("fn", "Functions & Graphs", "fn <name>", "Look closely at one function.")
def fn(ctx, a):
    name = a.word(0, "function name")
    if name not in ctx.fn_src:
        raise MathError(f"There's no function called {name}. Saved: {', '.join(ctx.fn_src) or 'none'}")
    lam = ctx.namespace()[name]
    params = lam.args[0]
    lines = [ctx.fn_src[name], f"simplified: {name}({', '.join(map(str, params))}) = {mstr(sp.simplify(lam.args[1]))}"]
    if len(params) == 1:
        lines.append(f"{name}(0) = {show(lam(0))}   {name}(1) = {show(lam(1))}   {name}(2) = {show(lam(2))}")
    box(f"Function {name}", lines)


@command("delfn", "Functions & Graphs", "delfn <name>", "Delete a saved function.")
def delfn(ctx, a):
    name = a.word(0, "function name")
    print(f"  Deleted {name}." if ctx.del_function(name) else f"  There's no function called {name}.")


@command("table", "Functions & Graphs", "table <f or expression> <start> <stop> <step>",
         "Make a value table for a function.", examples=("table f 0 10 2", "table x^2-3x -3 3 1"))
def table(ctx, a):
    words = a.words
    if len(words) < 4:
        name = a.word(0, "function or expression")
        start, stop, step = ctx.ask("start", "-5"), ctx.ask("stop", "5"), ctx.ask("step", "1")
    else:
        name, start, stop, step = " ".join(words[:-3]), words[-3], words[-2], words[-1]
    start, stop, step = (ctx.number(t, "number") for t in (start, stop, step))
    if step == 0 or (stop - start) / step < 0:
        raise MathError("The step must move from the start toward the stop (and not be 0).")
    if (stop - start) / step > 200:
        raise MathError("That's more than 200 rows — use a bigger step.")
    expr = ctx.expr(name if name not in ctx.fn_src else f"{name}(x)")
    v = X if expr.has(X) or not expr.free_symbols else sorted(expr.free_symbols, key=str)[0]
    rows, t = [], start
    while (t <= stop) if step > 0 else (t >= stop):
        try:
            val = expr.subs(v, t)
            val = "undefined" if val.has(sp.zoo, sp.nan) else show(val)
        except Exception:
            val = "undefined"
        rows.append((mstr(t), val))
        t += step
    w1 = max(len(r[0]) for r in rows + [(v.name, "")])
    lines = [f"{v.name.rjust(w1)} │ y"] + [f"{r[0].rjust(w1)} │ {r[1]}" for r in rows]
    ctx.last_data = [[v.name, "y"]] + [list(r) for r in rows]
    box(f"Table: {name}", lines)
