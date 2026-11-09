# -*- mode: python -*-
# Receita do PyInstaller para o Talehop.app (Mac). Corre-se no GitHub, num Mac
# (.github/workflows/mac.yml): o PyInstaller não faz apps de Mac a partir do Windows.
#
# No Mac não há placa NVIDIA: a transcrição usa o processador (talehop/gui_web.py escolhe
# um modelo mais leve para a qualidade rápida).
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent  # a pasta talehop/
PKG = ROOT / "talehop"
VERSION = (PKG / "__init__.py").read_text(encoding="utf-8").split('__version__ = "')[1].split('"')[0]

datas = [(str(PKG / "ui"), "talehop/ui")]
datas += collect_data_files("faster_whisper")  # o modelo de deteção de voz (VAD)
datas += collect_data_files("webview")         # o JavaScript do pywebview

a = Analysis(
    [str(ROOT / "build" / "run_talehop.py")],
    pathex=[str(ROOT)],
    binaries=collect_dynamic_libs("ctranslate2"),
    datas=datas,
    hiddenimports=["talehop.gui_web", "webview.platforms.cocoa"],
    excludes=["nvidia", "tkinter", "talehop.gui", "matplotlib", "IPython", "pytest", "clr", "pythonnet"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Talehop",
    console=False,
    argv_emulation=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Talehop", upx=False)
app = BUNDLE(
    coll,
    name="Talehop.app",
    icon=str(ROOT / "build" / "talehop.icns"),  # feito no GitHub a partir do talehop.ico
    bundle_identifier="app.talehop.Talehop",    # o mesmo que MAC_BUNDLE_ID em gui_web.py
    version=VERSION,
    info_plist={
        "CFBundleName": "Talehop",
        "CFBundleDisplayName": "Talehop",
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "NSRequiresAquaSystemAppearance": False,  # segue o modo escuro do Mac
    },
)
