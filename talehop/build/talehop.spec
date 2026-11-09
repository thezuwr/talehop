# -*- mode: python -*-
# Receita do PyInstaller para o Talehop.exe (uma pasta, sem consola). Corre-se pelo criar-instalador.bat.
#
# As bibliotecas da NVIDIA (pacote "nvidia", ~2 GB) ficam de fora: o programa instalado
# descarrega-as à parte quando há uma placa NVIDIA (talehop/gpu_pack.py).
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent  # a pasta talehop/ (a que tem o .venv)
PKG = ROOT / "talehop"

datas = [
    (str(PKG / "ui"), "talehop/ui"),
    (str(PKG / "talehop.ico"), "talehop"),
]
datas += collect_data_files("faster_whisper")  # o modelo de deteção de voz (VAD)
datas += collect_data_files("webview")         # o JavaScript do pywebview

a = Analysis(
    [str(ROOT / "build" / "run_talehop.py")],
    pathex=[str(ROOT)],
    binaries=collect_dynamic_libs("ctranslate2"),
    datas=datas,
    hiddenimports=["talehop.gui_web", "webview.platforms.edgechromium", "webview.platforms.winforms", "clr"],
    excludes=["nvidia", "tkinter", "talehop.gui", "matplotlib", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Talehop",
    icon=str(PKG / "talehop.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Talehop", upx=False)
