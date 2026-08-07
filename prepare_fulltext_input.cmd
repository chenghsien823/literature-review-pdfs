@echo off
setlocal
set "SKILL_DIR=%~dp0"
set "PYTHONUTF8=1"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%SKILL_DIR%scripts\prepare_fulltext_input.py" %*
  exit /b %errorlevel%
)
where python >nul 2>nul
if not errorlevel 1 (
  python "%SKILL_DIR%scripts\prepare_fulltext_input.py" %*
  exit /b %errorlevel%
)
echo Python 3.10 or later was not found. Install Python, then run: python -m pip install -r requirements.txt
exit /b 1
