# lmath

**Math that shows its work.** Type a problem the way you'd write it; lmath answers in exact fractions and radicals, explains every step, and draws the graph.

```text
lmath> 2x^2+3x-1=0
┌───────────────────────────────────────────────────────┐
│ Solve: 2x² + 3x - 1 = 0                               │
├───────────────────────────────────────────────────────┤
│ Step 1: Write in standard form  ax² + bx + c = 0      │
│         2x² + 3x - 1 = 0                              │
│ Step 2: Identify the coefficients                     │
│         a = 2,  b = 3,  c = -1                        │
│ Step 3: Find the discriminant  D = b² − 4ac           │
│         D = (3)² − 4(2)(-1) = 17                      │
│   ↳ D > 0: two real solutions                         │
│ Step 4: Use the quadratic formula  x = (−b ± √D) / 2a │
│         x = (-3 ± √17) / 4                            │
│                                                       │
│ ✓ x = (-3 ± √17)/4                                    │
│   x ≈ 0.280776   or   x ≈ -1.78078                    │
└───────────────────────────────────────────────────────┘
lmath> plot x^2-4x+3        (opens an interactive graph; intercepts and vertex are labelled)
```

Covers Algebra 1 & 2, Geometry, conic sections, trig, Pre-Calc, Calculus, linear algebra, statistics, number theory, physics/chemistry helpers, finance, unit conversion, and practice worksheets.

**Try it without installing:** the project website runs the real engine in your browser (Pyodide).

## Install

Download from the **Releases** page:

| | |
|---|---|
| Windows | `lmath-<version>-setup.exe` (installer) or `…-windows.zip` (portable) |
| Mac (Apple Silicon) | `…-macos.zip` → unzip → double-click **Open lmath.command** |
| From source | `pip install -r requirements.txt` then `python source/engine.py` |

## Using it

Just type. Anything that isn't a command is treated as math:

| You type | lmath does |
|---|---|
| `3/4 + 5/6` | exact arithmetic → `19/12` |
| `2x+3=11` | solves it, with steps |
| `r = 5` then `circle r` | variables (`25π`, never `78.5398`) |
| `f(x) = 3x+1` then `f(2)`, `plot f` | your own functions (saved between sessions) |
| `help` / `help solve` | every command, generated from the code |

Everyday notation works: `2x`, `(x+1)(x-1)`, `x^2`, `0.25`, `35%`, `√12`, `π`, `|2x-1|`, `sin(30°)`, `3+2i`. `log` is base 10, `ln` is natural.
`steps off` turns the explanations off. `worksheet quad 8` makes a printable problem list with an answer key. `ask …` (optional) turns plain English into lmath commands — set a free `GEMINI_API_KEY` first; the AI only chooses commands, it never does the arithmetic and nothing it writes is run as code.

## Repository layout

```text
source/
  engine.py            the prompt (start here)
  lmath/               the math package
    parse.py           ONE reader for everything typed (SymPy, implicit ×, exact decimals)
    fmt.py             exact-first printing (√, π, x², fractions)
    session.py         variables, functions, settings, saving
    registry.py        @command table → help, typo suggestions, website cheat sheet
    commands/          algebra, algebra2, geometry, conics, trig, calculus, linalg, stats, …
    assets/            grapher.js/.css — the interactive graph (shared by app and website)
    webapi.py          what the website calls
  make_icons.py        draws the icon (.ico/.icns/.png + website logo)
  make_web.py          builds docs/assets (package zip, command list)
  lmath.spec           PyInstaller recipe        installer.iss   Inno Setup installer
data/                  saved functions, history, last graph (created at run time; git-ignored)
tests/                 python -m unittest discover -s tests   (+ node tests for the graph and site)
docs/                  the website (GitHub Pages)
build.py  build.bat  build.sh  unbuild.py  .github/workflows/build.yml
```

## Develop

```bash
pip install -r requirements.txt
python source/engine.py                       # run
python -m unittest discover -s tests          # the Python tests
npm install --no-save jsdom && node tests/grapher.test.js && node tests/grapher.dom.test.js
python source/make_web.py && python -m http.server -d docs     # preview the website at localhost:8000
```

Adding a command is one function:

```python
@command("area", "Geometry", "area <w> <h>", "Area of a rectangle.", examples=("area 3 4",))
def area(ctx, a):
    w, h = (ctx.number(t) for t in a.words[:2])
    box("Area", [mstr(w * h)])
```

It then appears in `help`, in typo suggestions, and on the website's cheat sheet — and the test suite runs its example automatically.

### Build

```bash
python build.py        # Windows → release/…-setup.exe + …-windows.zip   Mac/Linux → release/…-macos.zip
python unbuild.py      # delete build leftovers (build/, dist/, release/, .venv)
python unbuild.py --all  # …and delete this whole folder, but only if everything is committed AND pushed
```

`build.bat` installs Inno Setup with `winget` if it's missing, and leaves only the finished files in `release/`.

### Release & website (GitHub)

1. Repository → **Settings → Pages → Source: GitHub Actions** (one time).
2. Change `__version__` in `source/lmath/__init__.py`, commit, push.
3. To publish downloads: `git tag v4.0.1 && git push --tags`. The workflow tests, builds Windows and Mac, and creates the release with auto-generated notes.

Every push to `main` re-publishes the website.

## Data folder

`data/state.json` (variables, functions, settings), `data/history.txt`, `data/graph.html`. Set `LMATH_DATA` to use another folder. If the program folder is read-only, lmath uses `~/.lmath/data`.

## Coming from v3

All v3 command names still work. What changed: input is read by one SymPy-based parser (so `2(x+1)`, `x(x+1)`, spaces, decimals just work); results are exact by default; `plot` opens an interactive browser graph (with `plot ascii …` for the terminal); steps are on by default; matrices and statistics are exact; `ask` returns commands instead of Python; `g` is 9.8 m/s² unless you pass `g=`.
