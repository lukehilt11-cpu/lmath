#!/usr/bin/env bash
# build.sh — builds lmath for macOS or Linux (quiet). Normally run through:  python3 build.py
# Result: release/lmath-<version>-macos.zip  (or -linux.tar.gz)
set -u
cd "$(dirname "$0")"
export PYTHONWARNINGS=ignore PIP_DISABLE_PIP_VERSION_CHECK=1
PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
ERR="$(mktemp)"
fail() { echo; echo "The build did not finish. Details:"; cat "$ERR"; rm -f "$ERR"; exit 1; }

VER="$($PY -c "import sys;sys.path.insert(0,'source');from lmath import __version__ as v;print(v)" 2>/dev/null)" \
  || { echo "Python 3 was not found. Install it from python.org and try again."; exit 1; }
OS="$(uname -s)"
echo "Building lmath $VER for $OS ..."

echo "[1/4] Installing build tools"
[ -x .venv/bin/python ] || $PY -m venv .venv >/dev/null 2>"$ERR" || fail
VPY=.venv/bin/python
$VPY -m pip install -q -r requirements.txt -r requirements-build.txt >/dev/null 2>"$ERR" || fail

echo "[2/4] Drawing icons"
$VPY source/make_icons.py >/dev/null 2>"$ERR" || fail

echo "[3/4] Packaging the program"
rm -rf build dist
$VPY -m PyInstaller --noconfirm --clean --log-level ERROR --distpath dist --workpath build source/lmath.spec >/dev/null 2>"$ERR" || fail
[ -x dist/lmath/lmath ] || fail

echo "[4/4] Making the download"
mkdir -p release
if [ "$OS" = "Darwin" ]; then
  cat > dist/Open\ lmath.command <<'LAUNCH'
#!/bin/bash
# Double-click this file to start lmath in Terminal.
cd "$(dirname "$0")"
xattr -dr com.apple.quarantine . 2>/dev/null
./lmath/lmath
LAUNCH
  chmod +x "dist/Open lmath.command"
  (cd dist && zip -qry "../release/lmath-$VER-macos.zip" lmath "Open lmath.command") 2>"$ERR" || fail
else
  (cd dist && tar -czf "../release/lmath-$VER-linux.tar.gz" lmath) 2>"$ERR" || fail
fi

rm -rf build dist "$ERR"
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
echo
echo "Done. Your files are in the release folder:"
ls release
