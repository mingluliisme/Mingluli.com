@echo off
chcp 65001 >nul
cd /d "%~dp0"
python build.py
if errorlevel 1 (
  echo.
  echo Build failed.
) else (
  echo.
  echo Done. Open index.html to check.
)
pause
