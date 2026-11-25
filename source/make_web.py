#!/usr/bin/env python3
"""
make_web.py — prepare docs/assets for the website.

  • assets/lmath-pkg.zip   the lmath package, loaded into Pyodide by the page
  • assets/catalog.json    every command, with examples (the cheat sheet)
  • assets/grapher.js/.css the shared interactive graph

Run it before previewing locally:   python source/make_web.py && python -m http.server -d docs
The GitHub workflow runs it automatically before publishing.
"""
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def main():
    from lmath import __version__
    from lmath import webapi
    out = os.path.join(ROOT, "docs", "assets")
    os.makedirs(out, exist_ok=True)

    pkg = os.path.join(HERE, "lmath")
    zpath = os.path.join(out, "lmath-pkg.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(pkg):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(folder, name)
                z.write(full, os.path.relpath(full, HERE).replace(os.sep, "/"))
    with open(os.path.join(out, "catalog.json"), "w", encoding="utf-8") as f:
        f.write(webapi.catalog_json())
    for name in ("grapher.js", "grapher.css"):
        shutil.copy(os.path.join(pkg, "assets", name), os.path.join(out, name))
    print(f"website assets ready (lmath {__version__}, {os.path.getsize(zpath) // 1024} KB package)")


if __name__ == "__main__":
    main()
