"""Suporte para a placa NVIDIA (cuBLAS e cuDNN), descarregado à parte no programa instalado.

São ~1,8 GB, por isso o instalador não os traz: quando há uma placa NVIDIA e faltam as
bibliotecas, a janela oferece-se para as descarregar. Vêm dos pacotes oficiais da NVIDIA no
PyPI (as mesmas versões que o instalar.bat usa), com a soma SHA-256 verificada, e ficam em
%LOCALAPPDATA%\\Talehop\\gpu\\<pacote>\\bin.
"""
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .paths import data_dir

PACK_DIR = data_dir() / "gpu"
PACKAGES = [("nvidia-cublas-cu12", "12.9.2.10"), ("nvidia-cudnn-cu12", "9.27.0.42")]
MARKER = PACK_DIR / "instalado.json"


class Cancelled(Exception):
    pass


def installed():
    return MARKER.exists()


def dll_dirs():
    """Pastas com as DLLs descarregadas (vazio se ainda não houver)."""
    return [str(d) for d in PACK_DIR.glob("*/bin") if d.is_dir()]


def _wheel(name, version):
    """URL, tamanho e SHA-256 da wheel para Windows de 64 bits, segundo o PyPI."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30) as r:
        info = json.load(r)
    for f in info["urls"]:
        if f["filename"].endswith("win_amd64.whl"):
            return f["url"], f["size"], f["digests"]["sha256"]
    raise RuntimeError(f"{name} {version}: sem versão para Windows")


def size():
    """Total a descarregar, em bytes."""
    return sum(_wheel(n, v)[1] for n, v in PACKAGES)


def download(progress=None, cancel=None):
    """progress(bytes feitos, bytes totais). Descarrega, verifica e extrai só as DLLs."""
    wheels = [_wheel(n, v) for n, v in PACKAGES]
    total = sum(w[1] for w in wheels)
    done = 0
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PACK_DIR.parent) as tmp:
        for url, length, sha in wheels:
            path = Path(tmp) / url.rsplit("/", 1)[1]
            digest = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as out:
                while chunk := r.read(1 << 20):
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
            if digest.hexdigest() != sha:
                raise RuntimeError(f"{path.name}: a verificação SHA-256 falhou")
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    parts = info.filename.split("/")
                    # nvidia/<pacote>/bin/<nome>.dll
                    if len(parts) == 4 and parts[0] == "nvidia" and parts[2] == "bin" and parts[3].lower().endswith(".dll"):
                        _extract(z, info, PACK_DIR / parts[1] / "bin" / parts[3])
            path.unlink()
    MARKER.write_text(json.dumps(dict(PACKAGES)), encoding="utf-8")


def _extract(z, info, dest):
    """Escreve uma DLL com outro nome e só depois a põe no lugar. Uma que já lá está, completa,
    fica como está: pode estar a ser usada (por esta ou outra janela do Talehop) e o Windows não
    deixa reescrevê-la."""
    if dest.exists() and dest.stat().st_size == info.file_size:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    with z.open(info) as src, open(tmp, "wb") as out:
        shutil.copyfileobj(src, out)
    try:
        os.replace(tmp, dest)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise
