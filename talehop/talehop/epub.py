"""Extração do texto de um EPUB: parágrafos e frases, pela ordem de leitura."""
import bisect
import itertools
import posixpath
import re
import warnings
import zipfile
from urllib.parse import unquote

from bs4 import (BeautifulSoup, Comment, Declaration, Doctype, NavigableString, ProcessingInstruction, Tag,
                 XMLParsedAsHTMLWarning)

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_NOT_TEXT = (Comment, Declaration, Doctype, ProcessingInstruction)

BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre",
          "dt", "dd", "figcaption", "td", "th"}
SKIP = {"script", "style", "head", "nav", "svg", "math", "rt", "rp"}

# Fim de frase: pontuação final, eventualmente seguida de aspas/parênteses,
# e depois espaço. Não parte em abreviaturas comuns.
_SENT_END = re.compile(r"[.!?…]+[»\"”’')\]]*\s+")
_ABBREV = re.compile(r"(?:\b(?:Sr|Sra|Srs|Dr|Dra|D|Exmo|Exma|V|S|Mr|Mrs|St|Prof|"
                     r"pag|pág|cap|n|nº|etc|Ex|vol|fl)\.|\b[A-Z]\.)\s*$")


def split_sentences(text):
    out, start = [], 0
    for m in _SENT_END.finditer(text):
        piece = text[start:m.end()]
        if _ABBREV.search(text[start:m.end()].rstrip()):
            continue
        out.append(piece)
        start = m.end()
    if start < len(text):
        out.append(text[start:])
    return [s for s in out if s.strip()]


def _read(z, name):
    return z.read(name)


def _opf_path(z):
    soup = BeautifulSoup(_read(z, "META-INF/container.xml"), "xml")
    return soup.find("rootfile")["full-path"]


# Marca de início de página dentro do texto de um bloco (retirada antes de dividir em frases).
_MARK = re.compile("([^]*)")


def _block_text(el, page_label=None):
    """Texto de um bloco, sem incluir blocos filhos (esses são tratados à parte).
    As marcas de página ficam no texto como \\ue000rótulo\\ue001."""
    parts = []
    for node in el.children:
        if isinstance(node, _NOT_TEXT):
            continue  # p.ex. <!--<a href="...">-->, que não se lê
        if isinstance(node, NavigableString):
            parts.append(str(node))
        elif isinstance(node, Tag):
            if node.name in SKIP or node.name in BLOCKS:
                continue
            label = page_label(node) if page_label else None
            if label is not None:
                parts.append(f"{label}")
            elif _is_noteref(node):
                continue
            elif node.name == "br":
                parts.append(" ")
            else:
                parts.append(_block_text(node, page_label))
    return "".join(parts)


def _take_marks(raw):
    """Texto limpo (sem marcas, espaços normalizados) e a posição de cada marca nesse texto."""
    def clean(s):
        return re.sub(r"\s+", " ", _MARK.sub("", s)).lstrip()
    marks = [(len(clean(raw[:m.start()])), m.group(1)) for m in _MARK.finditer(raw)]
    return clean(raw).rstrip(), marks


# Chamada de nota: "57", "[3]", "a", "*"... (o narrador não as lê)
_NOTE_MARK = re.compile(r"[\[(]?(?:\d{1,4}|[a-z]|[*†‡§¶]+)[\])]?")


def _is_noteref(tag):
    """Número de nota de rodapé no meio do texto (p.ex. <a href="notas.html#n57"><sup>57</sup></a>)."""
    if "noteref" in (tag.get("epub:type") or "").split() or tag.get("role") == "doc-noteref":
        return True
    if not _NOTE_MARK.fullmatch(tag.get_text().strip()):
        return False
    if tag.name == "a":
        return bool(tag.get("href"))
    return tag.name == "sup" and (tag.find("a", href=True) is not None or tag.find_parent("a", href=True) is not None)


# Marca de página sem lista de páginas nem epub:type (comum em EPUBs passados pelo Calibre): <a id="page_57"></a>
_PAGE_ID = re.compile(r"page[_-]?(\d+|[ivxlcdm]+)", re.I)


def _page_anchor(tag):
    m = _PAGE_ID.fullmatch(tag.get("id") or "")
    if m and not tag.get_text(strip=True):
        return m.group(1)
    return None


def _is_pagebreak(tag):
    return "pagebreak" in (tag.get("epub:type") or "").split() or tag.get("role") == "doc-pagebreak"


def _walk(el, emit, saw):
    for node in el.children:
        if not isinstance(node, Tag) or node.name in SKIP:
            continue
        saw(node)
        if node.name in BLOCKS:
            emit(node)
        # parágrafos e títulos não contêm outros blocos; o resto pode conter
        if node.name not in {"p", "h1", "h2", "h3", "h4", "h5", "h6"}:
            _walk(node, emit, saw)


def read_epub(path):
    z = zipfile.ZipFile(path)
    opf_name = _opf_path(z)
    base = posixpath.dirname(opf_name)
    opf = BeautifulSoup(_read(z, opf_name), "xml")

    def full(href):
        return posixpath.normpath(posixpath.join(base, unquote(href.split("#")[0])))

    manifest = {i["id"]: i for i in opf.find_all("item")}
    meta = opf.find("metadata")
    title = meta.find("title").get_text(strip=True) if meta.find("title") else ""
    author = meta.find("creator").get_text(strip=True) if meta.find("creator") else ""
    language = meta.find("language").get_text(strip=True) if meta.find("language") else ""

    cover = None
    for i in manifest.values():
        if "cover-image" in (i.get("properties") or ""):
            cover = full(i["href"])
    if cover is None:
        m = meta.find("meta", attrs={"name": "cover"})
        if m and m.get("content") in manifest:
            cover = full(manifest[m["content"]]["href"])

    paras = []        # {"kind": "h"|"p", "sentences": [texto, ...]}
    anchors = {}      # "ficheiro#id" -> índice do parágrafo
    page_map = _page_list(z, opf, manifest, full)
    pages = []        # (rótulo, parágrafo, frase): onde começa cada página da edição impressa
    pending_pages = []  # páginas que começam no próximo parágrafo com texto (pode ser no ficheiro seguinte)
    spine = [manifest[r["idref"]] for r in opf.find("spine").find_all("itemref")
             if r["idref"] in manifest]
    for item in spine:
        if "html" not in item.get("media-type", ""):
            continue
        fname = full(item["href"])
        soup = BeautifulSoup(_read(z, fname), "lxml")
        body = soup.body or soup
        anchors.setdefault(fname, len(paras))
        pending_ids = []

        def page_label(node):
            """Rótulo da página que começa neste elemento, ou None."""
            if page_map:
                return page_map.get(f"{fname}#{node['id']}") if node.get("id") else None
            if _is_pagebreak(node):
                return node.get("title") or node.get("aria-label") or node.get_text(strip=True) or None
            return _page_anchor(node)

        def saw(node):
            if node.get("id"):
                pending_ids.append(node["id"])
            label = page_label(node)
            if label is not None:
                pending_pages.append(label)

        def emit(node):
            pending_ids.extend(t["id"] for t in node.find_all(id=True))
            text, marks = _take_marks(_block_text(node, page_label))
            if not text:
                pending_pages.extend(label for _, label in marks)
                return
            for i in pending_ids:
                anchors.setdefault(f"{fname}#{i}", len(paras))
            pending_ids.clear()
            kind = "h" if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"} else "p"
            sentences = split_sentences(text + " ")
            pi = len(paras)
            pages.extend((label, pi, 0) for label in pending_pages)
            pending_pages.clear()
            # as frases são troços seguidos do texto: a marca fica na frase onde calha
            ends = list(itertools.accumulate(len(s) for s in sentences))
            for pos, label in marks:
                si = bisect.bisect_right(ends, pos)
                if si < len(sentences):
                    pages.append((label, pi, si))
                else:
                    pending_pages.append(label)
            paras.append({"kind": kind, "sentences": sentences})

        _walk(body, emit, saw)

    chapters = _toc(z, opf, manifest, full, anchors, paras)
    cover_bytes = z.read(cover) if cover and cover in z.namelist() else None
    return {"title": title, "author": author, "language": language,
            "paras": paras, "chapters": chapters, "pages": _dedupe_pages(pages),
            "cover": cover_bytes, "cover_ext": posixpath.splitext(cover or "")[1]}


def _dedupe_pages(pages):
    """Por ordem no texto; se uma página aparecer duas vezes, fica a primeira."""
    seen, out = set(), []
    for label, pi, si in sorted(pages, key=lambda p: (p[1], p[2])):
        if label not in seen:
            seen.add(label)
            out.append({"label": label, "para": pi, "sent": si})
    return out


def _nav(manifest):
    return next((i for i in manifest.values() if "nav" in (i.get("properties") or "").split()), None)


def _page_list(z, opf, manifest, full):
    """Páginas da edição impressa (page-list do EPUB 3, ou pageList do toc.ncx): "ficheiro#id" -> rótulo."""
    pages = {}
    nav = _nav(manifest)
    if nav:
        nav_file = full(nav["href"])
        soup = BeautifulSoup(z.read(nav_file), "lxml")
        pl = soup.find("nav", attrs={"epub:type": "page-list"})
        for a in pl.find_all("a", href=True) if pl else []:
            href = posixpath.normpath(posixpath.join(posixpath.dirname(nav_file), unquote(a["href"])))
            pages.setdefault(href, a.get_text(" ", strip=True))
    if not pages:
        ncx = opf.find("spine").get("toc")
        if ncx in manifest:
            ncx_file = full(manifest[ncx]["href"])
            soup = BeautifulSoup(z.read(ncx_file), "xml")
            for pt in soup.find_all("pageTarget"):
                href = posixpath.normpath(posixpath.join(posixpath.dirname(ncx_file),
                                                         unquote(pt.find("content")["src"])))
                pages.setdefault(href, pt.find("text").get_text(" ", strip=True))
    return {h: label for h, label in pages.items() if label}


def _title(el):
    """Texto de um título, como o navegador o mostra: sem espaços a mais nem a menos."""
    return " ".join(el.get_text().split())


def _toc(z, opf, manifest, full, anchors, paras):
    """Capítulos a partir do índice do EPUB (nav do EPUB 3, ou toc.ncx do EPUB 2)."""
    entries = []
    nav = _nav(manifest)
    if nav:
        nav_file = full(nav["href"])
        soup = BeautifulSoup(z.read(nav_file), "lxml")
        toc = soup.find("nav", attrs={"epub:type": "toc"}) or soup.find("nav")
        if toc:
            for a in toc.find_all("a", href=True):
                href = posixpath.normpath(posixpath.join(posixpath.dirname(nav_file), unquote(a["href"])))
                entries.append((_title(a), href))
    if not entries:
        ncx = opf.find("spine").get("toc")
        if ncx in manifest:
            ncx_file = full(manifest[ncx]["href"])
            soup = BeautifulSoup(z.read(ncx_file), "xml")
            for np_ in soup.find_all("navPoint"):
                href = posixpath.normpath(posixpath.join(posixpath.dirname(ncx_file),
                                                         unquote(np_.find("content")["src"])))
                entries.append((_title(np_.find("text")), href))

    chapters = []
    for title, href in entries:
        idx = anchors.get(href, anchors.get(href.split("#")[0]))
        if idx is not None and title:
            chapters.append({"title": re.sub(r"\s+", " ", title), "para": idx})
    chapters.sort(key=lambda c: c["para"])
    # o capítulo começa nos títulos imediatamente anteriores (ex.: "II" antes de "Do livro.")
    starts = {c["para"] for c in chapters}
    for c in chapters:
        while c["para"] > 0 and paras[c["para"] - 1]["kind"] == "h" and c["para"] - 1 not in starts:
            c["para"] -= 1
    # remove duplicados no mesmo parágrafo (fica o primeiro)
    seen, out = set(), []
    for c in chapters:
        if c["para"] not in seen:
            seen.add(c["para"])
            out.append(c)
    return out
