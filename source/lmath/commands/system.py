"""system.py — help, steps, history, export, and other housekeeping commands."""
import csv
import os

from .. import __version__
from ..errors import MathError, UsageError
from ..fmt import box
from ..registry import COMMANDS, catalog, command, grouped, suggest


@command("help", "Basics", "help [command]", "Show all commands, or details on one.",
         aliases=("menu", "?"), examples=("help", "help solve"))
def help_(ctx, a):
    if a:
        name = a.words[0].lower()
        c = COMMANDS.get(name)
        if not c:
            close = suggest(name)
            raise MathError(f"No command called '{name}'." + (f" Did you mean: {', '.join(close)}?" if close else ""))
        lines = [c.usage, "", c.summary]
        if c.aliases:
            lines += ["", "Also works as: " + ", ".join(c.aliases)]
        if c.examples:
            lines += ["", "Examples:"] + [f"  {ex}" for ex in c.examples]
        box(c.name, lines)
        return
    lines = []
    for group, cmds in grouped():
        lines.append(group.upper() if False else f"■ {group}")
        names = [c.name for c in cmds]
        row = "  "
        for n in names:
            if len(row) + len(n) + 2 > 66:
                lines.append(row.rstrip())
                row = "  "
            row += n + "  "
        lines.append(row.rstrip())
    lines += ["", "Just type math to calculate:  3/4 + 5/6     or an equation:  2x+3=11",
              "Save things:  r = 5     f(x) = 3x+1        More:  help <command>"]
    box(f"lmath {__version__} — commands", lines)


@command("steps", "Settings", "steps on|off", "Turn step-by-step explanations on or off.",
         examples=("steps off", "steps on"))
def steps(ctx, a):
    w = a.words[0].lower() if a else ""
    if w in ("on", "1", "true", "yes"):
        ctx.settings["steps"] = True
    elif w in ("off", "0", "false", "no"):
        ctx.settings["steps"] = False
    elif w:
        raise UsageError("Use:  steps on   or   steps off")
    else:
        ctx.settings["steps"] = not ctx.settings.get("steps", True)
    ctx.save()
    print("  Step-by-step explanations are " + ("ON" if ctx.settings["steps"] else "OFF (answers only)"))


@command("reset", "Settings", "reset", "Forget all saved variables and functions.")
def reset(ctx, a):
    ctx.reset()
    print("  Cleared your variables and functions.")


@command("version", "Settings", "version", "Show the lmath version.", aliases=("about",))
def version(ctx, a):
    print(f"  lmath {__version__}")


@command("history", "Settings", "history", "Show the last lines you typed this session.", web=False)
def history(ctx, a):
    path = os.path.join(ctx.data_dir or "", "history.txt")
    if not ctx.data_dir or not os.path.exists(path):
        print("  No history yet.")
        return
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    print("".join(lines[-30:]), end="")


@command("export", "Settings", "export <file.csv>", "Save the last table or data set to a CSV file.",
         web=False, examples=("export mytable.csv",))
def export(ctx, a):
    if not ctx.last_data:
        raise MathError("Nothing to export yet — make a table or describe some data first.")
    name = a.need("file name", "lmath.csv")
    if not name.lower().endswith(".csv"):
        name += ".csv"
    path = os.path.join(ctx.data_dir or ".", name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(ctx.last_data)
    print(f"  Saved {path}")


@command("clear", "Settings", "clear", "Clear the screen.", aliases=("cls",), web=False)
def clear(ctx, a):
    os.system("cls" if os.name == "nt" else "clear")
