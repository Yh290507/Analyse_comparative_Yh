@echo off
if not exist .venv\Scripts\python.exe (
  echo Lancez d'abord installer.bat.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m src.main
pause
