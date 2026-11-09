@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Cria dist\TalehopSetup-<versão>.exe: o PyInstaller faz o programa (dist\Talehop),
rem o Inno Setup junta-o num instalador. A versão está em talehop\__init__.py.

if not exist .venv\Scripts\python.exe (
    echo Corre primeiro o instalar.bat.
    goto erro
)
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Falta o Inno Setup 6: winget install JRSoftware.InnoSetup --scope user
    goto erro
)
for /f %%v in ('.venv\Scripts\python.exe -c "import talehop; print(talehop.__version__)"') do set "VERSION=%%v"

echo A criar o programa (Talehop %VERSION%)...
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist --workpath build\tmp build\talehop.spec
if errorlevel 1 goto erro

echo A criar o instalador...
"%ISCC%" /Qp /DAppVersion=%VERSION% build\installer.iss
if errorlevel 1 goto erro

echo.
echo Pronto: dist\TalehopSetup-%VERSION%.exe
exit /b 0

:erro
echo.
echo Algo correu mal. As mensagens acima dizem onde.
exit /b 1
