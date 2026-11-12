"""Pacote .tale (antes .sincro, que a app continua a abrir): um zip com livro.json, a capa e os
ficheiros de áudio.

livro.json:
{
  "format": 1, "title", "author", "language",
  "cover": "capa.jpg" | null,
  "audio": [{"file": "audio/001.mp3", "duration": segundos}],
  "chapters": [{"title", "para": índice, "audio": [ficheiro, segundos] | null}],
  "paras": [{"k": "h"|"p", "s": [[texto, ficheiro, início, fim] | [texto], ...]}],
  "pages": [[rótulo, parágrafo, frase], ...]
}
Uma frase sem tempo ([texto]) aparece no texto mas não está no áudio.
"pages" (opcional): onde começa cada página da edição impressa, quando o EPUB as indica
(os números de página que o Kindle mostra). Por ordem no texto.

Ilustrações (opcional), fora do livro.json, como a app as guarda:
  ilustracoes/001.jpg, ...
  ilustracoes.json: [{"f": "ilustracoes/001.jpg", "p": parágrafo, "alt": texto, "w": largura, "h": altura}]
A imagem aparece antes do parágrafo p. Os títulos desenhados ("Chapter One") e as vinhetas ficam de fora,
com as mesmas regras do Illustrations.kt da app.
"""
import json
import re
import struct
import unicodedata
import zipfile
from pathlib import Path

_MIN_SIDE = 160
_MIN_BYTES = 6000
_TITLE_WORDS = re.compile(
    r"^(chapter|capitulo|part|parte|book|livro|prologue|prologo|epilogue|epilogo|interlude|interludio|"
    r"acknowledg\w*|agradecimentos|postscript|posfacio|preface|prefacio|introduction|introducao|contents|indice)\b")


def _normalize(s):
    """Como o normalizeForSearch da app: minúsculas, sem acentos, só letras e números separados por espaços."""
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[\W_]+", " ", s)


def is_title_image(alt, chapter_titles):
    a = _normalize(alt).strip()
    if not a:
        return False
    return a in chapter_titles or (len(a) <= 40 and bool(_TITLE_WORDS.search(a)))


def image_size(data):
    """Largura e altura de um PNG, JPEG, GIF ou WebP, lidas do cabeçalho; (0, 0) se não souber."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", data[6:10])
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            kind = data[12:16]
            if kind == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if kind == b"VP8L":
                b = data[21:25]
                return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            if kind == b"VP8X":
                return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if data[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                length = struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + length
    except (struct.error, IndexError):
        pass
    return 0, 0


def illustrations(book):
    """As ilustrações a guardar: [(nome no pacote, bytes, entrada do ilustracoes.json)]."""
    titles = {_normalize(c["title"]).strip() for c in book["chapters"]}
    out = []
    for img in book.get("images", []):
        data = img.get("data")
        if not data or len(data) < _MIN_BYTES or is_title_image(img["alt"], titles):
            continue
        w, h = image_size(data)
        if w < _MIN_SIDE or h < _MIN_SIDE:
            continue
        ext = (Path(img["path"]).suffix.lower().lstrip(".") or "jpg")[:4]
        name = f"ilustracoes/{len(out) + 1:03d}.{ext}"
        out.append((name, data, {"f": name, "p": img["para"], "alt": img["alt"], "w": w, "h": h}))
    return out


def build(book, audio_files, durations, timings, out_path):
    paras = []
    for p, times in zip(book["paras"], timings):
        s = []
        for text, t in zip(p["sentences"], times):
            s.append([text] + t if t else [text])
        paras.append({"k": p["kind"], "s": s})

    def first_time(start, end):
        """Início do capítulo no áudio: a primeira frase com tempo dentro dele, se o capítulo
        tiver texto corrido narrado. Um capítulo que não é narrado (agradecimentos, ilustrações)
        ou só com títulos (que se confundem com os créditos do audiobook) fica sem tempo."""
        part = paras[start:end]
        if not any(p["k"] == "p" and len(s) > 1 for p in part for s in p["s"]):
            return None
        return next([s[1], s[2]] for p in part for s in p["s"] if len(s) > 1)

    starts = [c["para"] for c in book["chapters"]] + [len(paras)]
    chapters = [{"title": c["title"], "para": c["para"], "audio": first_time(c["para"], starts[i + 1])}
                for i, c in enumerate(book["chapters"])]

    audio = []
    names = []
    for i, (f, d) in enumerate(zip(audio_files, durations)):
        name = f"audio/{i + 1:03d}{Path(f).suffix.lower()}"
        names.append(name)
        audio.append({"file": name, "duration": round(d, 2)})

    cover = f"capa{book['cover_ext'] or '.jpg'}" if book["cover"] else None
    data = {"format": 1, "title": book["title"], "author": book["author"],
            "language": book["language"], "cover": cover, "audio": audio,
            "chapters": chapters, "paras": paras,
            "pages": [[p["label"], p["para"], p["sent"]] for p in book.get("pages", [])]}

    out_path = Path(out_path)
    tmp = out_path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w") as z:
        z.writestr("livro.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   compress_type=zipfile.ZIP_DEFLATED)
        if cover:
            z.writestr(cover, book["cover"])
        pictures = illustrations(book)
        if pictures:
            z.writestr("ilustracoes.json", json.dumps([e for _, _, e in pictures], ensure_ascii=False),
                       compress_type=zipfile.ZIP_DEFLATED)
            for name, data, _ in pictures:
                z.writestr(name, data)  # imagens já vêm comprimidas
        for f, name in zip(audio_files, names):
            z.write(f, name, compress_type=zipfile.ZIP_STORED)  # áudio já vem comprimido
    tmp.replace(out_path)
    return out_path
