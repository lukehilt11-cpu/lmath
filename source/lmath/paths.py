"""paths.py — where lmath keeps its data (history, saved functions, graphs)."""
import os
import sys


def app_dir() -> str:
    """Folder that holds the program: the .exe folder when frozen, else the repo root."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    here = os.path.dirname(os.path.abspath(__file__))            # source/lmath
    return os.path.dirname(os.path.dirname(here))                # repo root


def _writable(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def data_dir() -> str:
    """The data folder next to the program (or $LMATH_DATA), falling back to ~/.lmath if read-only."""
    override = os.environ.get("LMATH_DATA")
    primary = override if override else os.path.join(app_dir(), "data")
    if _writable(primary):
        return primary
    fallback = os.path.join(os.path.expanduser("~"), ".lmath", "data")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def asset_path(name: str) -> str:
    """Path to a file in lmath/assets (works from source and from a PyInstaller build)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "lmath", "assets", name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)
