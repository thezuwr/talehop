"""Janela do Talehop: escolher o ebook e o áudio, criar o .tale."""
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from . import pipeline

QUALITY = {
    "Rápida (recomendado)": "large-v3-turbo",
    "Máxima (mais lenta)": "large-v3",
}
LANGUAGES = {
    "A do ebook": None, "Português": "pt", "Inglês": "en", "Espanhol": "es",
    "Francês": "fr", "Italiano": "it", "Alemão": "de",
}
AUDIO_TYPES = [("Áudio", " ".join(f"*{e}" for e in sorted(pipeline.AUDIO_EXT))), ("Todos", "*.*")]


def fmt_eta(seconds):
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600} h {seconds % 3600 // 60:02d} min"
    if seconds >= 60:
        return f"{seconds // 60} min"
    return f"{seconds} s"


class App:
    def __init__(self, root):
        self.root = root
        self.audio = []
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.result = None
        self.t_start = None

        root.title("Talehop — criar livro sincronizado")
        root.minsize(640, 520)
        frm = ttk.Frame(root, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # ebook
        ttk.Label(frm, text="Ebook (EPUB)").grid(row=0, column=0, sticky="w", pady=4)
        self.epub = tk.StringVar()
        ttk.Entry(frm, textvariable=self.epub).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(frm, text="Escolher…", command=self.pick_epub).grid(row=0, column=2, sticky="ew")

        # áudio
        ttk.Label(frm, text="Audiobook").grid(row=1, column=0, sticky="nw", pady=4)
        box = ttk.Frame(frm)
        box.grid(row=1, column=1, sticky="nsew", padx=8)
        box.columnconfigure(0, weight=1)
        self.audio_list = tk.Listbox(box, height=6, activestyle="none")
        self.audio_list.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.audio_list.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.audio_list.configure(yscrollcommand=sb.set)
        self.audio_info = ttk.Label(box, text="Escolhe um ficheiro (ex.: .m4b) ou uma pasta com os MP3.")
        self.audio_info.grid(row=1, column=0, sticky="w", pady=(4, 0))
        btns = ttk.Frame(frm)
        btns.grid(row=1, column=2, sticky="new")
        ttk.Button(btns, text="Ficheiros…", command=self.pick_audio_files).pack(fill="x")
        ttk.Button(btns, text="Pasta…", command=self.pick_audio_dir).pack(fill="x", pady=4)

        # destino
        ttk.Label(frm, text="Guardar em").grid(row=2, column=0, sticky="w", pady=4)
        self.out = tk.StringVar()
        ttk.Entry(frm, textvariable=self.out).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(frm, text="Escolher…", command=self.pick_out).grid(row=2, column=2, sticky="ew")

        # opções
        opts = ttk.Frame(frm)
        opts.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 4))
        ttk.Label(opts, text="Qualidade").pack(side="left")
        self.quality = ttk.Combobox(opts, values=list(QUALITY), state="readonly", width=20)
        self.quality.current(0)
        self.quality.pack(side="left", padx=(6, 18))
        ttk.Label(opts, text="Língua").pack(side="left")
        self.language = ttk.Combobox(opts, values=list(LANGUAGES), state="readonly", width=12)
        self.language.current(0)
        self.language.pack(side="left", padx=6)

        self.device = ttk.Label(frm, text="A verificar a placa gráfica…", foreground="#666")
        self.device.grid(row=4, column=0, columnspan=3, sticky="w")

        # ação e progresso
        act = ttk.Frame(frm)
        act.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(12, 4))
        act.columnconfigure(1, weight=1)
        self.go = ttk.Button(act, text="Criar livro sincronizado", command=self.start)
        self.go.grid(row=0, column=0)
        self.bar = ttk.Progressbar(act, maximum=1000)
        self.bar.grid(row=0, column=1, sticky="ew", padx=12)
        self.open_btn = ttk.Button(act, text="Abrir pasta", command=self.open_folder, state="disabled")
        self.open_btn.grid(row=0, column=2)
        self.status = ttk.Label(frm, text="")
        self.status.grid(row=6, column=0, columnspan=3, sticky="w")

        self.log = ScrolledText(frm, height=10, state="disabled", wrap="word", font=("Consolas", 9))
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        frm.rowconfigure(7, weight=1)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.poll)
        threading.Thread(target=self.check_device, daemon=True).start()

    # --- escolha de ficheiros ------------------------------------------------

    def pick_epub(self):
        f = filedialog.askopenfilename(title="Ebook", filetypes=[("EPUB", "*.epub"), ("Todos", "*.*")])
        if f:
            self.epub.set(f)
            if not self.out.get():
                self.out.set(str(Path(f).with_suffix(".tale")))

    def pick_audio_files(self):
        files = filedialog.askopenfilenames(title="Ficheiros do audiobook", filetypes=AUDIO_TYPES)
        if files:
            self.set_audio(pipeline.collect_audio(files))

    def pick_audio_dir(self):
        d = filedialog.askdirectory(title="Pasta do audiobook")
        if d:
            self.set_audio(pipeline.collect_audio([d]))

    def set_audio(self, files):
        self.audio = files
        self.audio_list.delete(0, "end")
        for f in files:
            self.audio_list.insert("end", f.name)
        if files:
            self.audio_info.configure(text=f"{len(files)} ficheiro(s), por esta ordem.")
        else:
            self.audio_info.configure(text="Não encontrei ficheiros de áudio aí.")

    def pick_out(self):
        initial = Path(self.out.get() or self.epub.get() or "livro.tale")
        f = filedialog.asksaveasfilename(
            title="Guardar como", defaultextension=".tale", filetypes=[("Talehop", "*.tale")],
            initialdir=str(initial.parent), initialfile=initial.with_suffix(".tale").name,
        )
        if f:
            self.out.set(f)

    # --- trabalho em segundo plano ---------------------------------------------

    def check_device(self):
        try:
            from . import cuda
            text = cuda.describe()
        except Exception as e:
            text = f"Não consegui verificar a placa gráfica: {e}"
        self.events.put(("device", text))

    def start(self):
        if self.worker:  # o botão serve para cancelar
            self.cancel.set()
            self.go.configure(state="disabled", text="A cancelar…")
            return
        epub = self.epub.get().strip()
        if not epub or not Path(epub).is_file():
            messagebox.showwarning("Talehop","Escolhe primeiro o ebook (EPUB).")
            return
        if not self.audio:
            messagebox.showwarning("Talehop","Escolhe os ficheiros do audiobook.")
            return
        out = self.out.get().strip() or str(Path(epub).with_suffix(".tale"))
        self.out.set(out)

        self.cancel.clear()
        self.result = None
        self.t_start = None
        self.bar["value"] = 0
        self.open_btn.configure(state="disabled")
        self.go.configure(text="Cancelar")
        self.write_log("", clear=True)
        args = (epub, list(self.audio), out, QUALITY[self.quality.get()], LANGUAGES[self.language.get()])
        self.worker = threading.Thread(target=self.work, args=args, daemon=True)
        self.worker.start()

    def work(self, epub, audio, out, model, language):
        try:
            path, stats = pipeline.run(
                epub, audio, out, model=model, language=language,
                log=lambda m: self.events.put(("log", m)),
                progress=lambda f, d, t: self.events.put(("progress", (f, d, t))),
                cancel=self.cancel,
            )
            self.events.put(("done", (path, stats)))
        except pipeline.Cancelled:
            self.events.put(("cancelled", None))
        except Exception as e:
            self.events.put(("error", (e, traceback.format_exc())))

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                getattr(self, "on_" + kind)(data)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def on_device(self, text):
        self.device.configure(text=text)

    def on_log(self, msg):
        self.write_log(msg)

    def on_progress(self, data):
        frac, done, total = data
        self.bar["value"] = frac * 1000
        if total:
            now = time.time()
            if self.t_start is None:
                self.t_start = (now, done)  # a partir daqui mede a velocidade (ignora o que veio da cache)
            t0, d0 = self.t_start
            text = f"A transcrever: {frac / 0.97 * 100:.0f}%"
            if done > d0 and now - t0 > 15:
                eta = (total - done) * (now - t0) / (done - d0)
                text += f" · faltam cerca de {fmt_eta(eta)}"
            self.status.configure(text=text)
        else:
            self.status.configure(text="A alinhar e a criar o ficheiro…")

    def on_done(self, data):
        path, stats = data
        self.finish()
        self.result = Path(path)
        self.bar["value"] = 1000
        self.open_btn.configure(state="normal")
        cov = stats.get("coverage", 0) * 100
        self.status.configure(text=f"Pronto: {self.result.name} · {cov:.0f}% das frases sincronizadas")
        if cov < 80:
            messagebox.showwarning(
                "Talehop",
                f"Só {cov:.0f}% das frases ficaram sincronizadas. O áudio e o ebook podem ser "
                "de edições diferentes, ou a língua escolhida pode não ser a certa.",
            )

    def on_cancelled(self, _):
        self.finish()
        self.status.configure(text="Cancelado. Da próxima vez continua de onde ficou.")

    def on_error(self, data):
        e, tb = data
        self.finish()
        self.write_log(tb)
        self.status.configure(text="Ocorreu um erro.")
        messagebox.showerror("Talehop",f"Ocorreu um erro:\n\n{e}")

    def finish(self):
        self.worker = None
        self.go.configure(state="normal", text="Criar livro sincronizado")

    def write_log(self, msg, clear=False):
        self.log.configure(state="normal")
        if clear:
            self.log.delete("1.0", "end")
        if msg:
            self.log.insert("end", msg + "\n")
            self.log.see("end")
        self.log.configure(state="disabled")

    def open_folder(self):
        if not self.result:
            return
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", str(self.result)])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(self.result)])
        else:
            subprocess.run(["xdg-open", str(self.result.parent)])

    def on_close(self):
        if self.worker and not messagebox.askyesno(
            "Talehop","Ainda está a processar. Sair mesmo assim? (Da próxima vez continua de onde ficou.)"
        ):
            return
        self.root.destroy()


def main():
    if sys.platform == "win32":
        try:  # texto nítido em ecrãs com escala
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    try:
        root.iconbitmap(default=str(Path(__file__).with_name("talehop.ico")))
    except tk.TclError:
        pass
    try:
        ttk.Style(root).theme_use("vista" if sys.platform == "win32" else "clam")
    except tk.TclError:
        pass
    App(root)
    if os.environ.get("TALEHOP_SMOKE_TEST"):  # teste automático: abre e fecha
        root.after(1500, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
