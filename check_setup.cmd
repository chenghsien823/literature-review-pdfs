@echo off
setlocal
set "ROOT=%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%ROOT%scripts\check_setup.py" %*
  exit /b %errorlevel%
)
where python >nul 2>nul
if not errorlevel 1 (
  python "%ROOT%scripts\check_setup.py" %*
  exit /b %errorlevel%
)
echo [X ] Python 3.10 or later was not found. Install Python, enable Add Python to PATH, then try again.
exit /b 1
