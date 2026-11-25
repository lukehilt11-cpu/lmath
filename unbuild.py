#!/usr/bin/env python3
"""
unbuild.py — undoes a build, or removes the whole project from this computer.

    python unbuild.py            delete build leftovers (build/, dist/, release/, .venv/, caches)
    python unbuild.py --all      ALSO delete this whole project folder — but only after
                                 checking that everything is committed and pushed to GitHub

--all refuses to run if there is any unsaved or un-pushed work, so nothing is lost.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LEFTOVERS = ["build", "dist", "release", "build_errors.txt", ".pytest_cache", ".venv"]


def clean_build():
    for name in LEFTOVERS:
        path = os.path.join(ROOT, name)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)
    for folder, dirs, _ in os.walk(ROOT):
        if ".git" in folder.split(os.sep):
            continue
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(folder, d), ignore_errors=True)
                dirs.remove(d)
    print("Removed build leftovers.")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def pushed_check() -> str:
    """Return '' if everything is safely on GitHub, otherwise a reason it isn't."""
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        return "this folder isn't a Git repository, so I can't confirm anything is backed up."
    if git("status", "--porcelain").stdout.strip():
        return "there are uncommitted changes (run: git status)."
    if git("remote").stdout.strip() == "":
        return "no GitHub remote is set up."
    up = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if up.returncode != 0:
        return "this branch has never been pushed."
    ahead = git("rev-list", "--count", "@{u}..HEAD").stdout.strip()
    if ahead not in ("", "0"):
        return f"{ahead} commit(s) have not been pushed yet (run: git push)."
    git("fetch", "--quiet")
    if git("rev-list", "--count", "HEAD..@{u}").stdout.strip() not in ("", "0"):
        return "GitHub has newer commits than this folder (run: git pull) — nothing of yours is lost, but check first."
    return ""


def delete_project():
    reason = pushed_check()
    if reason:
        print(f"Not deleting the project: {reason}")
        return 1
    name = os.path.basename(ROOT)
    print(f"Everything is committed and pushed. This will DELETE the folder:\n  {ROOT}")
    if input(f"Type the folder name ({name}) to confirm: ").strip() != name:
        print("Cancelled — nothing was deleted.")
        return 1
    clean_build()
    parent = os.path.dirname(ROOT)
    if sys.platform.startswith("win"):                      # Windows can't delete a folder it is running from
        subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{ROOT}"', shell=True, cwd=parent,
                         creationflags=0x00000008)
        print("The project folder will be removed in a moment.")
    else:
        os.chdir(parent)
        shutil.rmtree(ROOT, ignore_errors=True)
        print("Project folder deleted.")
    return 0


def main() -> int:
    if "--all" in sys.argv[1:]:
        return delete_project()
    clean_build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
