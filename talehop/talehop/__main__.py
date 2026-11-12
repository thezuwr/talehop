"""Uso:  python -m talehop livro.epub audio1.mp3 [audio2.mp3 ... | pasta]  [-o saida.tale]
Sem argumentos, abre a janela."""
import argparse
import os
import sys

from . import pipeline


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = os.environ.get("TALEHOP_GPU_CHECK")
    if check and argv == ["--gpu-check"]:  # diagnóstico da placa, escrito num ficheiro (o programa instalado não tem consola)
        import json
        from . import cuda
        with open(check, "w", encoding="utf-8") as f:
            json.dump(cuda.diagnose(), f, indent=1)
        return
    if check and argv[:1] == ["--ebook-check"]:  # ler um ebook no programa instalado, sem abrir a janela
        import json
        from . import ebook
        # o programa instalado não tem consola: um erro por apanhar abria uma janela "Unhandled exception".
        # Assim fica escrito no ficheiro e o programa sai com o código 1.
        try:
            if len(argv) != 2:
                raise ValueError("uso: --ebook-check <ebook> (com o caminho entre aspas se tiver espaços)")
            b = ebook.read(argv[1])
            result = {"title": b["title"], "paras": len(b["paras"]), "chapters": len(b["chapters"]),
                      "cover": bool(b["cover"]), "images": len(b.get("images", []))}
        except Exception as e:
            result = {"error": f"{type(e).__name__}: {e}"}
        with open(check, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        sys.exit(1 if "error" in result else 0)
    if not argv:
        try:
            from . import gui_web
        except ImportError:  # sem pywebview: a janela antiga, em Tkinter
            from . import gui
            gui.main()
        else:
            gui_web.main()
        return

    ap = argparse.ArgumentParser(prog="talehop", description="Sincroniza um audiobook com o ebook.")
    ap.add_argument("epub")
    ap.add_argument("audio", nargs="+", help="ficheiros de áudio ou uma pasta")
    ap.add_argument("-o", "--output")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--language", help="código da língua (por omissão, a do EPUB)")
    ap.add_argument("--keep-transcript", action="store_true",
                    help="guardar o .transcricao.json no fim (para voltar a alinhar sem transcrever)")
    args = ap.parse_args(argv)

    audio = pipeline.collect_audio(args.audio)
    if not audio:
        sys.exit("Não encontrei ficheiros de áudio.")
    last = [-1]

    def progress(frac, done, total):
        pct = int(frac * 100)
        if pct != last[0] and pct % 5 == 0:
            last[0] = pct
            print(f"  {pct}%", flush=True)

    pipeline.run(args.epub, audio, args.output, model=args.model, language=args.language,
                 progress=progress, keep_transcript=args.keep_transcript)


if __name__ == "__main__":
    main()
