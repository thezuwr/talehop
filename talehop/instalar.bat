@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Talehop - instalacao (so e preciso uma vez)
echo ============================================
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo A instalar o uv ^(gestor de Python^)...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 goto erro

echo.
echo A preparar o Python e as bibliotecas ^(pode demorar alguns minutos, ~3 GB^)...
uv venv -p 3.11 --allow-existing .venv
if errorlevel 1 goto erro
uv pip install -p .venv\Scripts\python.exe -r requirements-windows.txt
if errorlevel 1 goto erro

echo.
echo A criar o atalho no Ambiente de Trabalho...
powershell -NoProfile -ExecutionPolicy ByPass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Talehop.lnk'); $s.TargetPath='%~dp0Talehop.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0talehop\talehop.ico'; $s.WindowStyle=7; $s.Save()"

echo.
echo Pronto! Abre o Talehop pelo atalho no Ambiente de Trabalho ^(ou pelo Talehop.bat^).
echo Na primeira vez que sincronizares um livro, o modelo de voz e descarregado ^(~1,5 GB^).
pause
exit /b 0

:erro
echo.
echo Algo correu mal. Copia as mensagens acima e envia-mas.
pause
exit /b 1
