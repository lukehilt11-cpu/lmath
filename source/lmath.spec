# PyInstaller spec for lmath. Don't run this directly — use  python build.py
# (it runs build.bat on Windows or build.sh on Mac/Linux, then tidies up).
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SRC = os.path.abspath(SPECPATH)                       # .../source
ROOT = os.path.dirname(SRC)

datas = [(os.path.join(SRC, "lmath", "assets"), os.path.join("lmath", "assets"))]
datas += collect_data_files("sympy") + collect_data_files("mpmath")
hidden = collect_submodules("sympy.parsing") + collect_submodules("sympy.printing") + ["mpmath"]

# Not needed by lmath — leaving them out keeps the download small.
excludes = ["tkinter", "matplotlib", "numpy", "scipy", "PIL", "pytest", "IPython", "pandas", "setuptools", "pip"]

icon = None
for name in ("lmath.ico" if os.name == "nt" else "lmath.icns",):
    path = os.path.join(ROOT, "icons", name)
    if os.path.exists(path):
        icon = path

a = Analysis([os.path.join(SRC, "engine.py")], pathex=[SRC], datas=datas, hiddenimports=hidden,
             excludes=excludes, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="lmath", console=True, icon=icon, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="lmath", upx=False)
