"""Textos do Talehop em português e inglês (registo, avisos e janelas do Windows).

A língua escolhe-se na janela; sem escolha, segue TALEHOP_LANG ou a língua do Windows.
"""
import locale
import os
import sys

LANGS = ("pt", "en")

MESSAGES = {
    "no_audio": {"pt": "Não encontrei ficheiros de áudio.", "en": "No audio files found."},
    "book": {"pt": "Livro: {name}", "en": "Book: {name}"},
    "book_info": {
        "pt": "  {title} — {author}: {paras} parágrafos, {toc} entradas no índice",
        "en": "  {title} — {author}: {paras} paragraphs, {toc} table of contents entries",
    },
    "pages": {
        "pt": "  {n} páginas da edição impressa ({first}–{last})",
        "en": "  {n} print edition pages ({first}–{last})",
    },
    "no_pages": {
        "pt": "  O EPUB não indica páginas: a app mostra a percentagem.",
        "en": "  The EPUB has no page numbers: the app will show the percentage.",
    },
    "audio": {
        "pt": "Áudio: {n} ficheiro(s). A transcrever (língua: {lang})...",
        "en": "Audio: {n} file(s). Transcribing (language: {lang})...",
    },
    "lang_auto": {"pt": "a detetar no áudio", "en": "detecting it from the audio"},
    "lang_detected": {
        "pt": "  Língua detetada no áudio: {lang} ({p:.0%} de certeza)",
        "en": "  Language detected in the audio: {lang} ({p:.0%} sure)",
    },
    "lang_unknown": {
        "pt": "  O ebook indica a língua \"{lang}\", que não reconheço: vou detetá-la no áudio.",
        "en": "  The ebook says the language is \"{lang}\", which I don't know: detecting it from the audio.",
    },
    "aligning": {"pt": "A alinhar o texto com o áudio...", "en": "Aligning the text with the audio..."},
    "aligning_words": {
        "pt": "A alinhar {book} palavras do livro com {audio} palavras do áudio...",
        "en": "Aligning {book} book words with {audio} audio words...",
    },
    "no_anchors": {
        "pt": "Aviso: não encontrei correspondências — o áudio é mesmo deste livro?",
        "en": "Warning: no matches found. Is the audio really from this book?",
    },
    "sync": {
        "pt": "Sincronização: {ok}/{span} frases da parte narrada ({cov:.1f}%); {used:.1f}% das palavras do áudio usadas.",
        "en": "Sync: {ok}/{span} sentences of the narrated part ({cov:.1f}%); {used:.1f}% of the audio words used.",
    },
    "span": {"pt": "  De: {first!r}\n  Até: {last!r}", "en": "  From: {first!r}\n  To: {last!r}"},
    "created": {"pt": "Guardado: {out}", "en": "Saved: {out}"},
    "loading_model": {
        "pt": "A carregar o modelo {model} (na primeira vez é descarregado, ~1,5 GB)...",
        "en": "Loading the {model} model (downloaded the first time, ~1.5 GB)...",
    },
    "resuming": {"pt": "  {name}: a continuar aos {min:.0f} min", "en": "  {name}: resuming at {min:.0f} min"},
    "file_done": {
        "pt": "  [{i}/{n}] {name}: {audio:.1f} min de áudio em {took:.1f} min",
        "en": "  [{i}/{n}] {name}: {audio:.1f} min of audio in {took:.1f} min",
    },
    "gpu": {"pt": "A usar a placa gráfica NVIDIA.", "en": "Using the NVIDIA graphics card."},
    "gpu_no_libs": {
        "pt": "Aviso: há placa NVIDIA mas faltam bibliotecas CUDA (corre o instalar.bat). "
              "Vou usar o processador, que é mais lento.",
        "en": "Warning: there is an NVIDIA card but the CUDA libraries are missing (run instalar.bat). "
              "Using the processor instead, which is slower.",
    },
    "gpu_libs_error": {
        "pt": "O suporte da placa está descarregado mas não carregou ({error}). Vou usar o processador. "
              "Fecha outras janelas do Talehop e abre-o de novo; se continuar, envia-nos esta linha.",
        "en": "The graphics card support is downloaded but didn't load ({error}). Using the processor. "
              "Close other Talehop windows and open it again; if it keeps happening, send us this line.",
    },
    "drop_unknown": {
        "pt": "Só aceito um ebook (EPUB, MOBI ou AZW3) e ficheiros de áudio (ou uma pasta com eles).",
        "en": "I only accept an ebook (EPUB, MOBI or AZW3) and audio files (or a folder with them).",
    },
    "ebook_drm": {
        "pt": "este livro tem DRM, por isso não dá para o ler. Precisas de uma versão sem DRM.",
        "en": "this book has DRM, so it can't be read. You need a DRM-free copy.",
    },
    "gpu_ready": {
        "pt": "Suporte da placa NVIDIA instalado: a transcrição vai usar a placa.",
        "en": "NVIDIA card support installed: transcription will use the card.",
    },
    "gpu_failed": {
        "pt": "Aviso: não consegui usar a placa gráfica ({error}). Vou usar o processador.",
        "en": "Warning: couldn't use the graphics card ({error}). Using the processor.",
    },
    "cpu": {"pt": "A usar o processador.", "en": "Using the processor."},
    "filter_all": {"pt": "Todos os ficheiros", "en": "All files"},
    "filter_audio": {"pt": "Áudio", "en": "Audio"},
    "filter_tale": {"pt": "Livro sincronizado", "en": "Synced book"},
    "default_out": {"pt": "livro.tale", "en": "book.tale"},
    "still_working": {
        "pt": "Ainda está a processar. Sair mesmo assim?\nDa próxima vez continua de onde ficou.",
        "en": "Still working. Quit anyway?\nNext time it carries on from where it stopped.",
    },
}

_lang = None


def system_lang():
    """pt se o Windows (ou TALEHOP_LANG) estiver em português; senão en."""
    env = os.environ.get("TALEHOP_LANG", "").lower()[:2]
    if env in LANGS:
        return env
    name = (locale.getlocale()[0] or "").lower()
    if sys.platform == "darwin" and not name.startswith(("pt", "en")):
        # uma app aberta pelo Finder não recebe a língua no ambiente: está nas preferências do macOS
        try:
            import subprocess
            name = subprocess.run(["defaults", "read", "-g", "AppleLocale"], capture_output=True,
                                  text=True, timeout=5).stdout.strip().lower()
        except Exception:
            pass
    return "pt" if name.startswith(("pt", "portuguese")) else "en"


def lang():
    return _lang or system_lang()


def set_lang(code):
    global _lang
    _lang = code if code in LANGS else None


def t(key, **kw):
    return MESSAGES[key][lang()].format(**kw)
