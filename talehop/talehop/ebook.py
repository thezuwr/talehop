"""Abre um ebook em qualquer formato aceite. Só o EPUB é lido diretamente: MOBI e AZW3 (sem DRM)
são desfeitos pela biblioteca mobi, que deixa os mesmos pedaços de um EPUB (ou o próprio EPUB)."""
import os
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

from . import epub
from .i18n import t

KINDLE_EXT = {".mobi", ".azw3", ".azw", ".prc"}
EXTENSIONS = {".epub"} | KINDLE_EXT

_CONTAINER = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""


def has_drm(path):
    """O campo de encriptação do cabeçalho MOBI (no início do primeiro registo do ficheiro)."""
    with open(path, "rb") as f:
        f.seek(78)
        first = struct.unpack(">I", f.read(4))[0]
        f.seek(first + 12)
        return struct.unpack(">H", f.read(2))[0] != 0


def _as_epub(folder, dest):
    """O MOBI antigo sai como pasta com book.html, content.opf e toc.ncx: só falta o invólucro de um EPUB."""
    with zipfile.ZipFile(dest, "w") as z:
        z.writestr("META-INF/container.xml", _CONTAINER)
        for f in folder.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(folder).as_posix())
    return dest


def read(path):
    """Devolve o mesmo que epub.read_epub, para qualquer formato aceite."""
    path = Path(path)
    if path.suffix.lower() not in KINDLE_EXT:
        return epub.read_epub(path)
    if has_drm(path):
        raise ValueError(t("ebook_drm"))
    # o programa instalado não tem consola, e a biblioteca escreve nela (e usa-a logo ao ser importada)
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    import mobi
    tmp, out = mobi.extract(str(path))
    try:
        out = Path(out)
        if out.suffix.lower() == ".epub":
            book = epub.read_epub(out)
        else:
            with tempfile.TemporaryDirectory() as d:
                book = epub.read_epub(_as_epub(out.parent, Path(d) / "livro.epub"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not book["chapters"]:  # sem índice (muitos MOBI convertidos): os títulos do próprio livro
        book["chapters"] = [{"title": " ".join("".join(p["sentences"]).split())[:80], "para": i}
                            for i, p in enumerate(book["paras"]) if p["kind"] == "h"]
    return book
