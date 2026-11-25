"""
ask.py — type a question in plain English; an AI turns it into lmath commands, and lmath does the math.

The AI never does the arithmetic and nothing it writes is executed as code: it can only
choose from lmath's own commands, which are then run exactly like commands you typed.

Setup (one time): get a free key at https://aistudio.google.com/apikey and set it as the
GEMINI_API_KEY environment variable. The key is never stored by lmath or printed.
"""
import json
import os
import urllib.error
import urllib.request

from ..errors import MathError, UsageError
from ..registry import COMMANDS, catalog, command, dispatch

_DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
_BLOCK = {"ask", "quiz", "export", "reset", "clear", "history", "exit", "quit"}


def _catalog_text():
    lines = []
    for g in catalog():
        for c in g["commands"]:
            if c["name"] in _BLOCK:
                continue
            ex = "; ".join(c["examples"][:2])
            lines.append(f"{c['usage']}  — {c['summary']}" + (f"   e.g. {ex}" if ex else ""))
    return "\n".join(lines)


def _prompt():
    return (
        "You translate math questions into commands for lmath, a command-line math tool. Reply with ONLY the commands, "
        "one per line, no explanation, no markdown, no code fences. Use only these commands:\n\n" + _catalog_text() +
        "\n\nRules: write math like x^2-5x+6 (use ^ for powers, * is optional). Never invent commands. If nothing fits, reply exactly: "
        "OUT_OF_SCOPE")


def translate(question: str):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise MathError("ask needs a Gemini API key. Get a free one at https://aistudio.google.com/apikey and set it as the "
                        "GEMINI_API_KEY environment variable (Windows: setx GEMINI_API_KEY your_key — then reopen lmath).")
    model = os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({"system_instruction": {"parts": [{"text": _prompt()}]},
                       "contents": [{"role": "user", "parts": [{"text": question}]}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        if e.code in (400, 403):
            raise MathError("Google rejected the request — check that GEMINI_API_KEY is correct.") from None
        if e.code == 404:
            raise MathError(f"Google doesn't know the model '{model}'. Set GEMINI_MODEL to a current model name "
                            "(see ai.google.dev/gemini-api/docs/models).") from None
        raise MathError(f"The AI service returned an error ({e.code}). Try again in a moment.") from None
    except (urllib.error.URLError, TimeoutError):
        raise MathError("I couldn't reach the AI service — check your internet connection.") from None
    except (KeyError, IndexError, ValueError):
        raise MathError("The AI service gave an answer I couldn't read. Try rephrasing your question.") from None
    lines = [l.strip().strip("`") for l in text.strip().splitlines()]
    return [l for l in lines if l and not l.lower().startswith(("python", "```"))]


@command("ask", "Basics", "ask <question in plain English>", "Describe a problem in words; AI picks the right lmath commands (needs a free Gemini key).",
         examples=("ask what is the area of a hexagon with side 5", "ask solve x squared minus 5x plus 6 equals zero"), web=False)
def ask(ctx, a):
    q = a.need("your question")
    lines = translate(q)
    if not lines or lines == ["OUT_OF_SCOPE"]:
        print("  That's outside what lmath can do — try rephrasing as an algebra, geometry, calculus, stats, or finance question.")
        return
    ran = 0
    for line in lines[:6]:
        word = line.split()[0].lower() if line.split() else ""
        if word in _BLOCK or word not in COMMANDS:
            continue
        print(f"  → {line}")
        dispatch(ctx, line)
        ran += 1
    if not ran:
        print("  I couldn't turn that into an lmath command. Try rephrasing, or type 'help'.")
