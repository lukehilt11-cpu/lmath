#!/usr/bin/env python3
"""
engine.py — lmath's interactive prompt.

    python engine.py                    start the prompt
    python engine.py -c "solve x^2=4"   run one command and exit
    python engine.py --version
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _setup_streams():
    """Make sure special characters (√ π ≤ │) print on any console or when piped."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _banner(ctx, version):
    print(f"\n  lmath {version} — exact answers, step by step")
    print("  Type math to calculate (3/4 + 5/6), an equation to solve (2x+3=11), or  help")
    n = len(ctx.fn_src) + len(ctx.vars)
    if n:
        print(f"  (loaded {len(ctx.fn_src)} saved function(s) and {len(ctx.vars)} variable(s) — type  reset  to clear them)")
    print()


def _history_file(data_dir):
    path = os.path.join(data_dir, "history.txt")
    try:                                                      # keep it from growing forever
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 1500:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[-500:])
    except OSError:
        pass
    return path


def repl(ctx, version):
    from lmath.registry import dispatch
    try:
        import readline  # noqa: F401  (arrow-key history where the OS provides it)
    except ImportError:
        pass
    hist = _history_file(ctx.data_dir) if ctx.data_dir else None
    _banner(ctx, version)
    while True:
        try:
            line = input("lmath> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("   (Ctrl-C — type exit to leave)")
            continue
        word = line.strip().lower()
        if word in ("exit", "quit", "q", "bye"):
            break
        if not word:
            continue
        if hist:
            try:
                with open(hist, "a", encoding="utf-8") as f:
                    f.write(line.strip() + "\n")
            except OSError:
                pass
        try:
            dispatch(ctx, line)
        except KeyboardInterrupt:
            print("\n  (stopped)")
        print()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    _setup_streams()
    from lmath import __version__
    import lmath.commands  # noqa: F401  (registers every command)
    from lmath.commands.graph import desktop_sink
    from lmath.paths import data_dir
    from lmath.registry import dispatch
    from lmath.session import Context

    if argv and argv[0] in ("--version", "-V"):
        print(f"lmath {__version__}")
        return 0
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    folder = data_dir()
    interactive = sys.stdin.isatty()
    ctx = Context(data_dir=folder, interactive=interactive)
    ctx.graph_sink = desktop_sink(folder)
    if argv and argv[0] == "-c":
        ctx.interactive = False
        for cmd in argv[1:]:
            dispatch(ctx, cmd)
        return 0
    if argv and not argv[0].startswith("-") and os.path.exists(argv[0]):      # run a script file
        ctx.interactive = False
        with open(argv[0], encoding="utf-8") as f:
            for line in f:
                print(f"lmath> {line.rstrip()}")
                dispatch(ctx, line)
        return 0
    if not interactive:                                                      # piped input
        for line in sys.stdin:
            if line.strip():
                print(f"lmath> {line.rstrip()}")
                dispatch(ctx, line)
        return 0
    repl(ctx, __version__)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # never close a student's window silently
        import traceback
        traceback.print_exc()
        print("\nSomething unexpected went wrong — please tell your teacher what you typed.")
        if getattr(sys, "frozen", False):
            try:
                input("Press Enter to close...")
            except EOFError:
                pass
        sys.exit(1)
