"""EPUB + áudio → .tale, com progresso e possibilidade de cancelar."""
import re
from pathlib import Path

from . import align, ebook, package, transcribe
from .i18n import t

AUDIO_EXT = {".mp3", ".m4a", ".m4b", ".aac", ".ogg", ".opus", ".flac", ".wav", ".wma"}
Cancelled = transcribe.Cancelled


def natural(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", Path(p).name)]


def collect_audio(paths):
    """Ficheiros e/ou pastas → lista de ficheiros de áudio, por ordem natural (2 antes de 10)."""
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted((f for f in p.iterdir() if f.suffix.lower() in AUDIO_EXT), key=natural)
        elif p.suffix.lower() in AUDIO_EXT:
            files.append(p)
    return files


def run(epub_path, audio_files, out_path=None, model="large-v3-turbo", language=None,
        log=print, progress=None, cancel=None, stage=None, keep_transcript=False):
    """progress(fração 0–1, segundos de áudio feitos, segundos totais);
    stage("ebook" | "transcrever" | "alinhar" | "criar") no início de cada passo.
    A transcrição (.transcricao.json) só serve para retomar: apaga-se quando o .tale fica pronto,
    a não ser com keep_transcript (para voltar a alinhar sem transcrever outra vez).
    Devolve (caminho do .tale, estatísticas)."""
    epub_path = Path(epub_path)
    audio_files = [Path(f) for f in audio_files]
    if not audio_files:
        raise ValueError(t("no_audio"))
    out = Path(out_path) if out_path else epub_path.with_suffix(".tale")
    work = out.with_suffix(".transcricao.json")  # cache: permite retomar
    report = progress or (lambda *a: None)
    step = stage or (lambda s: None)

    step("ebook")
    log(t("book", name=epub_path.name))
    book = ebook.read(epub_path)
    log(t("book_info", title=book["title"], author=book["author"], paras=len(book["paras"]), toc=len(book["chapters"])))
    if book["pages"]:
        log(t("pages", n=len(book["pages"]), first=book["pages"][0]["label"], last=book["pages"][-1]["label"]))
    else:
        log(t("no_pages"))
    lang = (language or book["language"] or "pt").split("-")[0].lower()

    step("transcrever")
    log(t("audio", n=len(audio_files), lang=lang))
    tr = transcribe.transcribe(
        audio_files, work, language=lang, model_name=model, log=log, cancel=cancel,
        on_progress=lambda done, total: report(0.97 * done / max(total, 1), done, total),
    )

    step("alinhar")
    log(t("aligning"))
    timings, stats = align.align(book["paras"], tr, progress=log)
    span = stats.get("sentences_in_span", 0)
    ok = stats.get("sentences_timed", 0)
    stats["coverage"] = ok / max(1, span)
    log(t("sync", ok=ok, span=span, cov=stats["coverage"] * 100, used=stats["audio_words_used"] * 100))
    if span:
        log(t("span", first=stats["first_sentence"], last=stats["last_sentence"]))
    report(0.99, 0, 0)

    step("criar")
    durations = [f["duration"] for f in tr["files"]]
    stats.update(pages=len(book["pages"]), chapters=len(book["chapters"]), duration=sum(durations))
    package.build(book, audio_files, durations, timings, out)
    if not keep_transcript:
        work.unlink(missing_ok=True)
    report(1.0, 0, 0)
    log(t("created", out=out))
    return out, stats
