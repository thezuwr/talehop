"""Janela do Talehop: a interface é HTML (pasta ui/) mostrado pelo WebView2 do Windows ou pelo
WebKit do Mac (pywebview).

A página chama os métodos de Api (escolher ficheiros, começar, cancelar...) e recebe os
acontecimentos do trabalho em segundo plano por app.on(tipo, dados).
"""
import base64
import json
import os
import subprocess
import threading
import traceback
from pathlib import Path

import webview
from webview.dom import DOMEventHandler

from . import cuda, ebook, gpu_pack, i18n, pipeline, transcribe
from .i18n import t
from .paths import IS_MAC, settings_dir

UI = Path(__file__).with_name("ui")
ICON = Path(__file__).with_name("talehop.ico")
SETTINGS = settings_dir() / "settings.json"
OLD_SETTINGS_DIR = SETTINGS.parent.with_name("Sincro")  # nome antigo da app
# O Mac transcreve com o processador (não há placa NVIDIA): a qualidade rápida usa o modelo small,
# que no teste com o Leonardo sincronizou tanto como o turbo (95,5% das frases) e é várias vezes mais leve.
QUALITY = ({"rapida": "small", "maxima": "large-v3-turbo"} if IS_MAC
           else {"rapida": "large-v3-turbo", "maxima": "large-v3"})
MAC_BUNDLE_ID = "app.talehop.Talehop"  # o mesmo que build/talehop-mac.spec
EBOOK_PATTERNS = ";".join(f"*{e}" for e in sorted(ebook.EXTENSIONS))
AUDIO_PATTERNS = ";".join(f"*{e}" for e in sorted(pipeline.AUDIO_EXT))
DIALOG = getattr(webview, "FileDialog", None)


def _all_files():
    return f"{t('filter_all')} (*.*)"


def _dialog(kind):
    """Tipos de janela de ficheiros, nas versões novas e antigas do pywebview."""
    if DIALOG is not None:
        return getattr(DIALOG, kind)
    return {"OPEN": webview.OPEN_DIALOG, "FOLDER": webview.FOLDER_DIALOG, "SAVE": webview.SAVE_DIALOG}[kind]


def _paths(result):
    if not result:
        return []
    return [result] if isinstance(result, str) else list(result)


class Api:
    def __init__(self):
        self._window = None
        self._cancel = threading.Event()
        self._worker = None
        self._result = None

    # --- página → Python ------------------------------------------------------

    def settings(self):
        """Tema e língua guardados; sem língua guardada, a do Windows."""
        try:
            values = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            values = {}
        values.setdefault("theme", "dark")
        values.setdefault("lang", i18n.system_lang())
        i18n.set_lang(values["lang"])
        return values

    def save_settings(self, values):
        i18n.set_lang(values.get("lang"))
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps(values), encoding="utf-8")

    def device(self):
        info = cuda.summary()
        # diagnóstico da placa, sempre: um ficheiro pequeno ao lado das definições, para perceber um problema
        log = os.environ.get("TALEHOP_GPU_CHECK") or str(SETTINGS.with_name("diagnostico-placa.json"))
        try:
            with open(log, "w", encoding="utf-8") as f:
                json.dump({"summary": info, "error": cuda.last_error, **cuda.diagnose()}, f, indent=1)
        except Exception:
            pass
        if info.get("libs_error"):
            self._emit("log", t("gpu_libs_error", error=info["libs_error"]))
        if info["needs_pack"]:
            try:
                info["pack_size"] = gpu_pack.size()
            except Exception:
                info["pack_size"] = None  # sem internet: o botão aparece sem o tamanho
        return info

    def download_gpu_pack(self):
        """Descarrega o suporte da placa NVIDIA em segundo plano (acontecimentos "pack")."""
        def work():
            try:
                gpu_pack.download(progress=lambda d, total: self._emit("pack", {"done": d, "total": total}))
                self._emit("log", t("gpu_ready"))
                self._emit("pack", {"ok": True})
            except Exception as e:
                self._emit("log", traceback.format_exc())
                self._emit("pack", {"error": str(e)})
        threading.Thread(target=work, daemon=True).start()

    def pick_epub(self):
        found = _paths(self._window.create_file_dialog(
            _dialog("OPEN"), file_types=(f"Ebook ({EBOOK_PATTERNS})", _all_files())))
        if not found:
            return None
        return self._epub_info(Path(found[0]))

    def _epub_info(self, path):
        book = ebook.read(path)
        cover = None
        if book["cover"]:
            mime = "image/png" if book["cover_ext"].lower() == ".png" else "image/jpeg"
            cover = f"data:{mime};base64," + base64.b64encode(book["cover"]).decode()
        return {
            "path": str(path), "title": book["title"] or path.stem, "author": book["author"],
            "language": (book["language"] or "").split("-")[0].lower(),
            "pages": len(book["pages"]), "chapters": len(book["chapters"]),
            "cover": cover, "out": str(path.with_suffix(".tale")), "format": path.suffix[1:].upper(),
        }

    def pick_audio_files(self):
        found = _paths(self._window.create_file_dialog(
            _dialog("OPEN"), allow_multiple=True,
            file_types=(f"{t('filter_audio')} ({AUDIO_PATTERNS})", _all_files())))
        return self._audio_info(pipeline.collect_audio(found)) if found else None

    def pick_audio_dir(self):
        found = _paths(self._window.create_file_dialog(_dialog("FOLDER")))
        return self._audio_info(pipeline.collect_audio(found)) if found else None

    def enable_drop(self):
        """Passa a aceitar ficheiros arrastados para a janela (a página chama-o quando está pronta)."""
        self._window.dom.document.events.drop += DOMEventHandler(self._on_drop, True, True)

    def _on_drop(self, event):
        if self._worker:  # a sincronizar: os campos estão bloqueados
            return
        files = event.get("dataTransfer", {}).get("files", [])
        self._accept_dropped([f["pywebviewFullPath"] for f in files if f.get("pywebviewFullPath")])

    def _accept_dropped(self, paths):
        """O tipo de ficheiro decide o campo, seja qual for o sítio onde foi largado."""
        epubs = [p for p in paths if Path(p).suffix.lower() in ebook.EXTENSIONS]
        audio = pipeline.collect_audio([p for p in paths if p not in epubs])
        if epubs:
            self._emit("reading_epub")
            try:
                self._emit("epub", self._epub_info(Path(epubs[0])))
            except Exception as e:
                self._emit("epub_failed", str(e))
        if audio:
            self._emit("audio", self._audio_info(audio))
        if not epubs and not audio:
            self._emit("log", t("drop_unknown"))

    def pick_out(self, current):
        current = Path(current) if current else Path.home() / t("default_out")
        found = _paths(self._window.create_file_dialog(
            _dialog("SAVE"), directory=str(current.parent), save_filename=current.name,
            file_types=(f"{t('filter_tale')} (*.tale)",)))
        if not found:
            return None
        return str(Path(found[0]).with_suffix(".tale"))

    def start(self, opts):
        if self._worker:
            return False
        self._cancel.clear()
        self._result = None
        self._worker = threading.Thread(target=self._work, args=(opts,), daemon=True)
        self._worker.start()
        return True

    def cancel(self):
        self._cancel.set()

    def open_folder(self):
        if self._result:
            if IS_MAC:
                subprocess.run(["open", "-R", str(self._result)])  # mostra o ficheiro no Finder
            else:
                subprocess.run(["explorer", "/select,", str(self._result)])

    # --- trabalho em segundo plano ---------------------------------------------

    def _emit(self, kind, data=None):
        if self._window:
            self._window.evaluate_js(f"app.on({json.dumps(kind)}, {json.dumps(data, ensure_ascii=False)})")

    def _work(self, o):
        try:
            path, stats = pipeline.run(
                o["epub"], o["audio"], o["out"], model=QUALITY.get(o.get("quality"), QUALITY["rapida"]),
                language=o.get("language") or None,
                log=lambda m: self._emit("log", m),
                progress=lambda f, d, t: self._emit("progress", [f, d, t]),
                stage=lambda s: self._emit("stage", s),
                cancel=self._cancel,
            )
            self._result = Path(path)
            stats.update(file=self._result.name, size=self._result.stat().st_size)
            self._emit("done", stats)
        except pipeline.Cancelled:
            self._emit("cancelled")
        except Exception as e:
            self._emit("log", traceback.format_exc())
            self._emit("error", str(e))
        finally:
            self._worker = None

    @staticmethod
    def _audio_info(files):
        if not files:
            return {"files": [], "duration": 0, "size": 0}
        out = []
        for f in files:
            try:
                dur = transcribe.audio_duration(f)
            except Exception:
                dur = 0
            out.append({"path": str(f), "name": f.name, "duration": dur, "size": f.stat().st_size})
        return {"files": out, "duration": sum(f["duration"] for f in out), "size": sum(f["size"] for f in out)}


def _clear_ui_cache():
    """Numa versão nova, apaga a cache do WebView2: sem isto, a janela continuava a mostrar o
    app.js e o i18n.js da versão anterior (os textos antigos). As definições ficam."""
    import shutil
    from . import __version__
    store = SETTINGS.parent / "webview"
    marker = store / "versao.txt"
    try:
        if marker.read_text(encoding="utf-8") == __version__:
            return
    except OSError:
        pass
    for profile in store.glob("**/EBWebView/*"):
        for name in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
            shutil.rmtree(profile / name, ignore_errors=True)
    if IS_MAC:  # o WebKit guarda a cache por app, pelo identificador da app
        lib = Path.home() / "Library"
        for d in (lib / "Caches" / MAC_BUNDLE_ID, lib / "WebKit" / MAC_BUNDLE_ID):
            shutil.rmtree(d, ignore_errors=True)
    store.mkdir(parents=True, exist_ok=True)
    marker.write_text(__version__, encoding="utf-8")


def main():
    if not SETTINGS.parent.exists() and OLD_SETTINGS_DIR.exists():
        try:
            OLD_SETTINGS_DIR.rename(SETTINGS.parent)
        except OSError:
            pass
    try:  # a barra de tarefas agrupa a janela como Talehop (com o seu ícone), não como Python
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Talehop.Talehop")
    except Exception:
        pass
    _clear_ui_cache()
    api = Api()
    window = webview.create_window(
        "Talehop", url=str(UI / "index.html"), js_api=api,
        width=1220, height=860, min_size=(980, 680), background_color="#121316",
    )
    api._window = window

    def closing():
        if api._worker and not window.create_confirmation_dialog("Talehop", t("still_working")):
            return False
        return True

    window.events.closing += closing
    webview.start(private_mode=False, storage_path=str(SETTINGS.parent / "webview"),
                  icon=str(ICON), debug=bool(os.environ.get("TALEHOP_DEBUG")))


if __name__ == "__main__":
    main()
