"""Onde o Talehop guarda as suas coisas, em cada sistema.

Windows: definições em %APPDATA%\\Talehop, dados grandes (suporte da placa) em %LOCALAPPDATA%\\Talehop.
Mac: tudo em ~/Library/Application Support/Talehop.
"""
import os
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"


def settings_dir():
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / "Talehop"
    return Path(os.environ.get("APPDATA") or Path.home()) / "Talehop"


def data_dir():
    if IS_MAC:
        return settings_dir()
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Talehop"
