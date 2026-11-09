"""Transcrição do audiobook com marcas de tempo por palavra (faster-whisper).

Vários ficheiros de áudio são tratados como uma única linha temporal: cada
palavra guarda o índice do ficheiro e o tempo dentro desse ficheiro.

Cada ficheiro é transcrito aos bocados (blocos de CHUNK_S segundos): o
faster-whisper analisa de uma vez todo o áudio que recebe, e um ficheiro de
15 h pediria perto de 20 GB de memória.
"""
import gc
import itertools
import json
import math
import time
from pathlib import Path

import av
import numpy as np

from . import cuda, i18n

SAMPLE_RATE = 16000
CHUNK_S = 20 * 60  # cada bloco ocupa ~1 GB durante a análise
PAD_S = 5          # áudio a mais de cada lado do bloco, para não cortar palavras nas junções


class Cancelled(Exception):
    pass


def audio_duration(path):
    with av.open(str(path)) as c:
        return c.duration / 1_000_000


def _frames(container):
    """Frames de áudio já em 16 kHz mono (16 bits), ignorando frames estragados."""
    resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    fifo = av.audio.fifo.AudioFifo()
    decoded = container.decode(audio=0)
    while True:
        try:
            frame = next(decoded)
        except StopIteration:
            break
        except av.error.InvalidDataError:
            continue
        frame.pts = None
        fifo.write(frame)
        if fifo.samples >= 500_000:
            yield from resampler.resample(fifo.read())
    if fifo.samples:
        yield from resampler.resample(fifo.read())
    yield from resampler.resample(None)
    del resampler
    gc.collect()  # o PyAV só liberta o resampler assim (faster-whisper, issue 390)


def windows(path, chunk_s=None, pad_s=PAD_S):
    """Áudio aos bocados: (início da janela, de, até, amostras float32).
    A janela tem `pad_s` a mais de cada lado; só contam as palavras que começam
    entre `de` e `até` (segundos no ficheiro), para não haver repetidas nas junções."""
    chunk_s = chunk_s or CHUNK_S
    chunk, pad = chunk_s * SAMPLE_RATE, pad_s * SAMPLE_RATE
    pieces, have, buf_start, k = [], 0, 0, 0
    with av.open(str(path), metadata_errors="ignore") as container:
        for frame in _frames(container):
            a = frame.to_ndarray().reshape(-1)
            pieces.append(a)
            have += len(a)
            while buf_start + have >= (k + 1) * chunk + pad:
                buf = np.concatenate(pieces)
                lo, hi = max(0, k * chunk - pad), (k + 1) * chunk + pad
                yield (lo / SAMPLE_RATE, k * chunk_s, (k + 1) * chunk_s,
                       buf[lo - buf_start:hi - buf_start].astype(np.float32) / 32768.0)
                k += 1
                drop = max(0, k * chunk - pad) - buf_start
                pieces, buf_start = [buf[drop:]], buf_start + drop
                have = len(pieces[0])
    if buf_start + have > k * chunk:
        buf = np.concatenate(pieces)
        lo = max(0, k * chunk - pad)
        yield lo / SAMPLE_RATE, k * chunk_s, math.inf, buf[lo - buf_start:].astype(np.float32) / 32768.0


def _detect(model, audio, log):
    """Língua do áudio, pelos primeiros 2 minutos com voz. None se não der para saber."""
    try:
        lang, prob, _ = model.detect_language(audio, vad_filter=True, language_detection_segments=4)
    except Exception:  # por exemplo, um bloco só com música ou silêncio
        return None
    log(i18n.t("lang_detected", lang=lang, p=prob))
    return lang


def transcribe(audio_files, out_path, language="pt", model_name="large-v3-turbo",
               log=print, on_progress=None, cancel=None):
    """on_progress(segundos_feitos, segundos_totais); cancel: threading.Event.
    language=None: a língua é detetada no áudio (no primeiro bloco) e usada no resto."""
    from faster_whisper.tokenizer import _LANGUAGE_CODES
    if language and language not in _LANGUAGE_CODES:
        log(i18n.t("lang_unknown", lang=language))
        language = None
    auto = language is None
    out_path = Path(out_path)
    cache = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    if auto and cache.get("auto") and cache.get("model") == model_name:
        language = cache.get("language")  # detetada numa vez anterior
    done, partial = {}, {}
    if cache.get("model") == model_name and cache.get("language") == language and language:
        for f in cache.get("files", []):
            (partial if "partial_until" in f else done)[f["name"]] = f

    durations = [audio_duration(p) for p in audio_files]
    total = sum(durations)
    finished = 0.0
    model = None

    result = {"language": language, "auto": auto, "model": model_name, "files": []}

    def save():
        out_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    for idx, (path, dur) in enumerate(zip(audio_files, durations)):
        path = Path(path)
        if path.name in done:  # retoma onde ficou, se o processo foi interrompido
            result["files"].append(done[path.name])
            finished += dur
            if on_progress:
                on_progress(finished, total)
            continue
        if model is None:
            device, compute = cuda.pick_device(log)
            log(i18n.t("loading_model", model=model_name))
            from faster_whisper import WhisperModel
            model = WhisperModel(model_name, device=device, compute_type=compute)

        t0 = time.time()
        prev = partial.get(path.name)
        resume_at = prev["partial_until"] if prev else 0.0
        entry = {"name": path.name, "duration": dur, "words": list(prev["words"]) if prev else []}
        result["files"].append(entry)
        if resume_at:
            log(i18n.t("resuming", name=path.name, min=resume_at / 60))

        for start, keep_from, keep_until, audio in windows(path):
            if keep_until <= resume_at:
                continue  # bloco já transcrito numa vez anterior
            if language is None:
                language = result["language"] = _detect(model, audio, log)
            segments, info = model.transcribe(
                audio, language=language, word_timestamps=True,
                vad_filter=True, beam_size=5, condition_on_previous_text=False,
            )
            if language is None:  # nem a deteção conseguiu: fica a que o Whisper escolheu aqui
                language = result["language"] = info.language
                log(i18n.t("lang_detected", lang=language, p=info.language_probability))
            for seg in segments:
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                for w in seg.words or []:
                    t = start + w.start
                    if keep_from <= t < keep_until:
                        entry["words"].append([w.word.strip(), round(t, 3), round(start + w.end, 3)])
                if on_progress:
                    on_progress(finished + min(start + seg.end, keep_until, dur), total)
            if keep_until < dur:  # guarda a meio do ficheiro, para poder retomar
                entry["partial_until"] = keep_until
                save()
        entry.pop("partial_until", None)
        finished += dur
        log(i18n.t("file_done", i=idx + 1, n=len(audio_files), name=path.name,
                   audio=dur / 60, took=(time.time() - t0) / 60))
        save()

    save()
    return result
