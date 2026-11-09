@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
    echo Ainda nao instalaste o Talehop. Corre primeiro o instalar.bat.
    pause
    exit /b 1
)
start "" .venv\Scripts\pythonw.exe -m talehop
