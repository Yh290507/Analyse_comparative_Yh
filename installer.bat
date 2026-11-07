@echo off
setlocal
python -m venv .venv
if errorlevel 1 (
  echo Echec de creation de l'environnement Python. Verifiez que Python 3 est installe et que la commande python fonctionne.
  exit /b 1
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo Installation terminee. Lancez lancer.bat.
