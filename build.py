#!/usr/bin/env python3
"""
build.py — builds lmath for whatever computer you're on.

    python build.py

On Windows it runs build.bat (portable zip + Inno Setup installer);
on Mac or Linux it runs build.sh. Finished files land in the release folder.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    os.chdir(ROOT)
    if sys.platform.startswith("win"):
        return subprocess.call(["cmd", "/c", "build.bat"])
    return subprocess.call(["bash", "build.sh"])


if __name__ == "__main__":
    sys.exit(main())
