"""Alinhamento entre o texto do livro e a transcrição do áudio.

1. Âncoras: n-gramas de palavras que só aparecem uma vez no livro e uma vez na
   transcrição; fica a maior cadeia que respeita a ordem nos dois lados.
2. Entre âncoras, repete-se com n-gramas mais curtos e, quando o troço já é
   pequeno, faz-se um alinhamento palavra a palavra (programação dinâmica)
   que tolera erros de transcrição e diferenças de ortografia.
3. Cada frase do livro fica com o tempo da primeira e da última palavra
   correspondida; frases sem correspondência são interpoladas pelos vizinhos.
"""
import bisect
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache

from . import i18n

_WORD = re.compile(r"\w+", re.UNICODE)
_ORTHO = [("ph", "f"), ("th", "t"), ("y", "i"), ("z", "s"), ("ae", "ai"), ("ao", "au")]


@lru_cache(maxsize=200_000)
def key(word):
    """Forma normalizada para comparar: sem acentos, ortografia antiga ≈ moderna."""
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    for a, b in _ORTHO:
        w = w.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", w)  # annos -> anos, elle -> ele


@lru_cache(maxsize=500_000)
def similarity(a, b):
    if a == b:
        return 1.0
    if min(len(a), len(b)) <= 2:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def words_of(text):
    return _WORD.findall(text)


# ---------------------------------------------------------------------------

def _lis(pairs):
    """Maior subsequência crescente em t (pairs já ordenados por b)."""
    tails, tails_idx, prev = [], [], [-1] * len(pairs)
    for i, (_, t) in enumerate(pairs):
        j = bisect.bisect_left(tails, t)
        if j == len(tails):
            tails.append(t)
            tails_idx.append(i)
        else:
            tails[j] = t
            tails_idx[j] = i
        prev[i] = tails_idx[j - 1] if j else -1
    out, i = [], tails_idx[-1] if tails_idx else -1
    while i >= 0:
        out.append(pairs[i])
        i = prev[i]
    return out[::-1]


def _anchors(B, T, b0, b1, t0, t1, n):
    def grams(seq, lo, hi):
        return [tuple(seq[i:i + n]) for i in range(lo, hi - n + 1)]

    gb, gt = grams(B, b0, b1), grams(T, t0, t1)
    cb, ct = Counter(gb), Counter(gt)
    tpos = {g: t0 + i for i, g in enumerate(gt) if ct[g] == 1}
    pairs = [(b0 + i, tpos[g]) for i, g in enumerate(gb)
             if cb[g] == 1 and g in tpos]
    chain = _lis(pairs)
    # anchors sobrepostos: fica só um a cada n palavras
    out, last_b, last_t = [], -1, -1
    for b, t in chain:
        if b >= last_b + n and t >= last_t + n:
            out.append((b, t))
            last_b, last_t = b, t
    return out


MATCH_MIN = 0.72
DP_MAX_CELLS = 400_000


def _dp(B, T, b0, b1, t0, t1, match):
    """Alinhamento global palavra a palavra num troço pequeno."""
    nb, nt = b1 - b0, t1 - t0
    if nb == 0 or nt == 0:
        return
    if nb * nt > DP_MAX_CELLS:
        return  # troço demasiado grande e sem âncoras: fica por alinhar
    GAP = -0.4
    prev_row = [GAP * j for j in range(nt + 1)]
    back = []
    for i in range(1, nb + 1):
        bi = B[b0 + i - 1]
        row = [GAP * i] + [0.0] * nt
        brow = [1] + [0] * nt
        for j in range(1, nt + 1):
            s = similarity(bi, T[t0 + j - 1])
            diag = prev_row[j - 1] + (2 * s if s >= MATCH_MIN else -0.6)
            up = prev_row[j] + GAP
            left = row[j - 1] + GAP
            if diag >= up and diag >= left:
                row[j], brow[j] = diag, 0
            elif up >= left:
                row[j], brow[j] = up, 1
            else:
                row[j], brow[j] = left, 2
        back.append(brow)
        prev_row = row
    i, j = nb, nt
    while i > 0 and j > 0:
        d = back[i - 1][j]
        if d == 0:
            if similarity(B[b0 + i - 1], T[t0 + j - 1]) >= MATCH_MIN:
                match[b0 + i - 1] = t0 + j - 1
            i, j = i - 1, j - 1
        elif d == 1:
            i -= 1
        else:
            j -= 1


def _align_range(B, T, b0, b1, t0, t1, match, n=5, edge=None):
    """edge="lead": troço antes da 1ª âncora (o que interessa está no fim do troço);
    edge="trail": depois da última âncora (o que interessa está no início)."""
    if b1 <= b0 or t1 <= t0:
        return
    # nos extremos, um lado pode ser enorme (ex.: o resto do livro ainda por narrar);
    # procura-se só numa janela junto à âncora
    nb, nt = b1 - b0, t1 - t0
    if edge:
        if nb > 3 * nt + 100:
            w = 3 * nt + 100
            b0, b1 = (b1 - w, b1) if edge == "lead" else (b0, b0 + w)
        elif nt > 3 * nb + 100:
            w = 3 * nb + 100
            t0, t1 = (t1 - w, t1) if edge == "lead" else (t0, t0 + w)
        nb, nt = b1 - b0, t1 - t0
    if nb * nt <= 4000:
        _dp(B, T, b0, b1, t0, t1, match)
        return
    # âncoras curtas só quando os dois lados têm tamanhos parecidos (senão coincidem por acaso)
    if n <= 3 and max(nb, nt) > 4 * min(nb, nt) + 40:
        _dp(B, T, b0, b1, t0, t1, match)
        return
    anchors = _anchors(B, T, b0, b1, t0, t1, n)
    if not anchors:
        if n > 2:
            _align_range(B, T, b0, b1, t0, t1, match, n - 1, edge)
        else:
            _dp(B, T, b0, b1, t0, t1, match)
        return
    sub = max(2, n - 1)
    pb, pt = b0, t0
    for k, (b, t) in enumerate(anchors):
        _align_range(B, T, pb, b, pt, t, match, sub, edge if k == 0 and edge == "lead" else None)
        for i in range(n):
            match[b + i] = t + i
        pb, pt = b + n, t + n
    _align_range(B, T, pb, b1, pt, t1, match, sub, "trail" if edge == "trail" else None)


# ---------------------------------------------------------------------------

def align(paras, transcript, progress=print):
    """Devolve, para cada parágrafo, a lista de tempos das frases:
    [file_idx, início, fim] ou None quando a frase não foi encontrada no áudio."""
    # tokens do livro
    B, b_sent = [], []
    sentences = []  # (para_idx, sent_idx, texto)
    for pi, p in enumerate(paras):
        for si, s in enumerate(p["sentences"]):
            for w in words_of(s):
                B.append(key(w))
                b_sent.append(len(sentences))
            sentences.append((pi, si, s))

    # tokens da transcrição (uma palavra do Whisper pode ter várias partes: "vendendo-se")
    T, t_time = [], []
    for fi, f in enumerate(transcript["files"]):
        for text, start, end in f["words"]:
            parts = words_of(text)
            total = sum(len(p) for p in parts) or 1
            pos = start
            for p in parts:
                d = (end - start) * len(p) / total
                T.append(key(p))
                t_time.append((fi, pos, pos + d))
                pos += d

    progress(i18n.t("aligning_words", book=len(B), audio=len(T)))
    match = [None] * len(B)
    anchors = _anchors(B, T, 0, len(B), 0, len(T), 5)
    if not anchors:
        progress(i18n.t("no_anchors"))
    pb, pt = 0, 0
    for k, (b, t) in enumerate(anchors):
        _align_range(B, T, pb, b, pt, t, match, 4, "lead" if k == 0 else None)
        for i in range(5):
            match[b + i] = t + i
        pb, pt = b + 5, t + 5
    if anchors:
        _align_range(B, T, pb, len(B), pt, len(T), match, 4, "trail")
    matched = sum(m is not None for m in match)

    # tempos por frase
    times = [None] * len(sentences)
    counts = [0] * len(sentences)
    words_per = Counter(b_sent)
    for bi, ti in enumerate(match):
        if ti is None:
            continue
        si = b_sent[bi]
        fi, st, en = t_time[ti]
        cur = times[si]
        if cur is None:
            times[si] = [fi, st, en]
        elif cur[0] == fi:
            cur[1], cur[2] = min(cur[1], st), max(cur[2], en)
        counts[si] += 1
    # frases com poucas palavras correspondidas são pouco fiáveis
    for si, c in enumerate(counts):
        if times[si] is not None and words_per[si] >= 6 and c / words_per[si] < 0.25:
            times[si] = None
    _monotonic(times)
    _interpolate(times, sentences)

    out = [[None] * len(p["sentences"]) for p in paras]
    for (pi, si, _), t in zip(sentences, times):
        out[pi][si] = [t[0], round(t[1], 2), round(t[2], 2)] if t else None

    timed = [i for i, t in enumerate(times) if t]
    stats = {"book_words": len(B), "audio_words": len(T), "matched_words": matched}
    if timed:
        span = range(timed[0], timed[-1] + 1)
        stats["sentences_in_span"] = len(span)
        stats["sentences_timed"] = sum(1 for i in span if times[i])
        stats["first_sentence"] = sentences[timed[0]][2][:80]
        stats["last_sentence"] = sentences[timed[-1]][2][:80]
    stats["audio_words_used"] = len(set(m for m in match if m is not None)) / max(1, len(T))
    return out, stats


def _monotonic(times):
    """Remove frases cujo tempo recua em relação às vizinhas (erros de alinhamento)."""
    def pos(t):
        return (t[0], t[1])
    idx = [i for i, t in enumerate(times) if t]
    keep = set(b for b, _ in _lis([(i, pos(times[i])) for i in idx]))
    for i in idx:
        if i not in keep:
            times[i] = None


def _interpolate(times, sentences):
    """Frases sem tempo entre duas frases do mesmo ficheiro: distribui pelo nº de letras."""
    n = len(times)
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        if i > 0 and j < n and times[i - 1][0] == times[j][0]:
            fi, a, b = times[i - 1][0], times[i - 1][2], times[j][1]
            lens = [len(sentences[k][2]) for k in range(i, j)]
            total = sum(lens) or 1
            # só se o ritmo for plausível: nem texto saltado pelo narrador (demasiado
            # depressa, ~15 letras/s é o normal) nem uma pausa enorme
            if b > a and total / (b - a) <= 25 and b - a < 20 * (j - i) + 10:
                pos = a
                for k, L in zip(range(i, j), lens):
                    d = (b - a) * L / total
                    times[k] = [fi, pos, pos + d]
                    pos += d
        i = j
