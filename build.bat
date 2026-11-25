@echo off
rem ---------------------------------------------------------------------------
rem  build.bat — builds lmath for Windows (quiet). Normally run through:  python build.py
rem  Result: release\lmath-<version>-setup.exe  and  release\lmath-<version>-windows.zip
rem ---------------------------------------------------------------------------
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONWARNINGS=ignore"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

for /f "delims=" %%v in ('python -c "import sys;sys.path.insert(0,'source');from lmath import __version__ as v;print(v)"') do set "VER=%%v"
if not defined VER (echo Python was not found. Install Python 3.10 or newer from python.org and try again.& exit /b 1)
echo Building lmath %VER% for Windows ...

echo [1/5] Installing build tools
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" python -m venv .venv >nul 2>build_errors.txt
if not exist "%PY%" goto :fail
"%PY%" -m pip install -q -r requirements.txt -r requirements-build.txt >nul 2>build_errors.txt || goto :fail

echo [2/5] Drawing icons
"%PY%" source\make_icons.py >nul 2>build_errors.txt || goto :fail

echo [3/5] Packaging the program
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
"%PY%" -m PyInstaller --noconfirm --clean --log-level ERROR --distpath dist --workpath build source\lmath.spec >nul 2>build_errors.txt || goto :fail
if not exist dist\lmath\lmath.exe goto :fail

if not exist release mkdir release
echo [4/5] Making the portable zip
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\lmath' -DestinationPath 'release\lmath-%VER%-windows.zip'" >nul 2>build_errors.txt || goto :fail

echo [5/5] Making the installer
call :find_inno
if not defined ISCC (
  echo       Inno Setup not found - installing it with winget ...
  winget install -e --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
  call :find_inno
)
if defined ISCC (
  "%ISCC%" /Q /DAppVersion=%VER% source\installer.iss >nul 2>build_errors.txt || goto :fail
) else (
  echo       Could not find or install Inno Setup, so the installer was skipped.
  echo       Install it from https://jrsoftware.org/isdl.php and run build.bat again.
)

rem --- leave only the finished programs: delete every build leftover ---
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist build_errors.txt del /q build_errors.txt
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo.
echo Done. Your files are in the release folder:
dir /b release
exit /b 0

:find_inno
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0

:fail
echo.
echo The build did not finish. Details:
if exist build_errors.txt type build_errors.txt
exit /b 1
