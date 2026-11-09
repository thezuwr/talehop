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
"""
import json
import zipfile
from pathlib import Path


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
        for f, name in zip(audio_files, names):
            z.write(f, name, compress_type=zipfile.ZIP_STORED)  # áudio já vem comprimido
    tmp.replace(out_path)
    return out_path
