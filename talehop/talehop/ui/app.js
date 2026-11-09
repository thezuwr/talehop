"use strict";
// A janela do Talehop. Fala com o Python por window.pywebview.api (gui_web.Api)
// e recebe o andamento do trabalho por app.on(tipo, dados). Textos: i18n.js (tr).

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const STEPS = [
  ["ebook", "step_ebook"],
  ["transcrever", "step_transcribe"],
  ["alinhar", "step_align"],
  ["criar", "step_create"],
];
const STAGE_LABEL = { ebook: "s_ebook", transcrever: "s_transcribe", alinhar: "s_align", criar: "s_create" };
const SHORT_LOG = 6;

const state = {
  theme: "dark", epub: null, audio: null, quality: "rapida",
  phase: "idle", // idle | run | done | error | cancelled
  stage: null, speed: null, log: [], logOpen: false, device: null, stats: null,
};

// --- formatos ------------------------------------------------------------------

function fmtDuration(sec) {
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min` : `${m} min`;
}
function fmtShortDuration(sec) {
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}` : `${m} min`;
}
function fmtSize(bytes) {
  const gb = (bytes / 1e9).toFixed(1);
  return bytes >= 1e9 ? `${uiLang === "pt" ? gb.replace(".", ",") : gb} GB` : `${Math.round(bytes / 1e6)} MB`;
}
function fmtEta(sec) {
  sec = Math.round(sec);
  if (sec >= 3600) return `${Math.floor(sec / 3600)} h ${String(Math.floor((sec % 3600) / 60)).padStart(2, "0")} min`;
  if (sec >= 60) return `${Math.round(sec / 60)} min`;
  return tr("under_min");
}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

// --- tema e língua --------------------------------------------------------------

function setTheme(t) {
  state.theme = t;
  document.documentElement.dataset.theme = t;
  $("theme").setAttribute("aria-label", tr(t === "dark" ? "theme_to_light" : "theme_to_dark"));
}

function setLang(l) {
  uiLang = l === "en" ? "en" : "pt";
  for (const b of $("ui-lang").children) b.classList.toggle("on", b.dataset.l === uiLang);
  applyStatic();
  setTheme(state.theme);
  renderAll();
}

function saveSettings() {
  api().save_settings({ theme: state.theme, lang: uiLang });
}

// --- desenho -------------------------------------------------------------------

function renderAll() {
  renderEpub();
  renderAudio();
  renderDevice();
  renderPhase();
  renderLog();
  if (state.stats) renderDone(state.stats);
  if (state.stage) $("ring-label").textContent = tr(STAGE_LABEL[state.stage]);
}

function renderEpub() {
  const b = state.epub;
  $("cover").classList.toggle("hidden", !(b && b.cover));
  $("cover-empty").classList.toggle("hidden", !!(b && b.cover));
  $("n1").classList.toggle("done", !!b);
  $("pick-epub").textContent = tr(b ? "change" : "choose");
  const langs = STR[uiLang].langs;
  const first = $("language").options[0];
  first.textContent = b && langs[b.language] ? tr("from_ebook_lang", { lang: langs[b.language] }) : tr("from_ebook");
  if (!b) {
    $("book-title").textContent = tr("no_ebook");
    $("book-author").textContent = tr("pick_epub_hint");
    return;
  }
  if (b.cover) $("cover").src = b.cover;
  $("book-title").textContent = b.title;
  $("book-author").textContent = b.author || "";
  const chips = $("book-chips");
  chips.replaceChildren(
    el("span", "chip", langs[b.language] ? `${b.format} · ${langs[b.language]}` : b.format),
    b.pages ? el("span", "chip on", tr("print_pages", { n: b.pages })) : el("span", "chip", tr("no_pages_chip")),
    el("span", "chip", tr("chapters_chip", { n: b.chapters })),
  );
  chips.classList.remove("hidden");
}

function renderAudio() {
  const a = state.audio;
  const list = $("files");
  list.replaceChildren();
  $("n2").classList.toggle("done", !!(a && a.files.length));
  if (!a) {
    $("audio-note").textContent = tr("audio_hint");
    return;
  }
  if (!a.files.length) {
    $("audio-note").textContent = tr("audio_none");
    return;
  }
  for (const f of a.files) {
    const row = el("div", "file");
    const ico = el("span", "ico");
    ico.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="14" width="4.5" height="6.5" rx="1.6"/><rect x="16.5" y="14" width="4.5" height="6.5" rx="1.6"/></svg>';
    row.append(ico, el("span", "name ellipsis", f.name), el("span", "small muted", fmtDuration(f.duration)));
    list.append(row);
  }
  const n = a.files.length;
  $("audio-note").textContent = `${n > 1 ? tr("file_many", { n }) : tr("file_one")} · ${fmtDuration(a.duration)} · ${fmtSize(a.size)}` +
    (n > 1 ? tr("order_note") : "");
}

function renderDevice() {
  const d = state.device;
  if (!d) return;
  $("device-dot").classList.remove("hidden");
  $("device").classList.toggle("slow", !d.gpu && !d.mac);
  const pack = $("gpu-pack");
  pack.classList.toggle("hidden", !d.needs_pack);
  if (d.needs_pack && !pack.disabled) {
    pack.textContent = d.pack_size ? tr("gpu_get", { size: fmtSize(d.pack_size) }) : tr("gpu_get_nosize");
  }
  if (d.gpu) {
    $("device-name").textContent = d.name ? tr("gpu_name", { name: d.name }) : tr("gpu_generic");
    $("device-speed").textContent = tr("gpu_fast");
    $("device-speed").className = "ok";
  } else if (d.needs_pack) {
    $("device-name").textContent = d.name ? tr("gpu_name", { name: d.name }) : tr("gpu_generic");
    $("device-speed").textContent = tr("gpu_needs_pack");
    $("device-speed").className = "slow";
  } else if (d.mac) {
    // no Mac não há placa NVIDIA: o processador faz o trabalho, com um modelo mais leve na qualidade rápida
    $("device-name").textContent = tr("mac_cpu");
    $("device-speed").textContent = tr("mac_speed");
    $("device-speed").className = "ok";
  } else {
    $("device-name").textContent = tr("no_gpu");
    $("device-speed").textContent = tr("gpu_slow");
    $("device-speed").className = "slow";
  }
}

function renderSteps(box, current, finished) {
  const idx = STEPS.findIndex(([k]) => k === current);
  box.replaceChildren(...STEPS.map(([, label], i) => {
    const s = el("div", "step");
    const ok = finished || (idx >= 0 && i < idx);
    const now = !finished && i === idx;
    if (ok) s.classList.add("ok");
    if (now) s.classList.add("now");
    const dot = el("i");
    if (ok) dot.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
    else dot.textContent = i + 1;
    s.append(dot, el("span", null, tr(label)));
    return s;
  }));
}

function renderPhase() {
  const p = state.phase;
  $("st-idle").classList.toggle("hidden", !(p === "idle" || p === "cancelled"));
  $("st-run").classList.toggle("hidden", p !== "run");
  $("st-done").classList.toggle("hidden", p !== "done");
  $("st-error").classList.toggle("hidden", p !== "error");
  $("hint").classList.toggle("hidden", p !== "done");

  const running = p === "run";
  for (const id of ["pick-epub", "pick-files", "pick-dir", "pick-out", "language", "out"]) $(id).disabled = running;
  for (const b of $("quality").children) b.disabled = running;
  const go = $("go");
  go.classList.toggle("hidden", running);
  go.classList.toggle("again", p === "done");
  go.textContent = tr(p === "done" ? "again" : p === "error" || p === "cancelled" ? "continue" : "create");
  go.disabled = !(state.epub && state.audio && state.audio.files.length);
  if (!$("cancel").disabled) $("cancel").textContent = tr("cancel");

  if (p === "idle" || p === "cancelled") {
    $("idle-title").textContent = tr(p === "cancelled" ? "cancelled" : "ready");
    $("idle-sub").textContent = p === "cancelled" ? tr("cancelled_sub") : tr(go.disabled ? "ready_pick" : "ready_go");
    renderSteps($("idle-steps"), p === "cancelled" ? state.stage : null, false);
  }
  if (p === "run") renderSteps($("run-steps"), state.stage, false);
}

function renderLog() {
  const lines = state.logOpen ? state.log : state.log.slice(-SHORT_LOG);
  const box = $("log");
  box.textContent = lines.join("\n");
  box.scrollTop = box.scrollHeight;
  $("log-toggle").textContent = tr(state.logOpen ? "show_less" : "show_all");
  $("log-toggle").classList.toggle("hidden", state.log.length <= SHORT_LOG);
}

function renderDone(stats) {
  const cov = Math.round((stats.coverage || 0) * 100);
  $("done-file").textContent = `${stats.file} · ${fmtSize(stats.size)}`;
  $("done-pct").textContent = `${cov}%`;
  $("done-bar").style.width = `${cov}%`;
  $("done-warn").classList.toggle("hidden", cov >= 80);
  $("done-pages").textContent = stats.pages || "%";
  $("done-pages-l").textContent = tr(stats.pages ? "pages" : "no_pages_stat");
  $("done-chapters").textContent = stats.chapters;
  $("done-duration").textContent = fmtShortDuration(stats.duration);
}

// --- acontecimentos vindos do Python --------------------------------------------

const handlers = {
  log(msg) {
    state.log.push(...String(msg).replace(/\s+$/, "").split("\n"));
    renderLog();
  },
  stage(s) {
    state.stage = s;
    $("ring-label").textContent = tr(STAGE_LABEL[s]);
    if (s === "alinhar" || s === "criar") {
      $("eta").textContent = tr("almost");
      $("eta-sub").textContent = tr("almost_sub");
    }
    renderPhase();
  },
  progress([frac, done, total]) {
    const pct = Math.min(100, Math.round(frac * 100));
    $("ring").style.setProperty("--p", pct);
    $("ring-pct").textContent = `${pct}%`;
    if (!total) return;
    const now = Date.now() / 1000;
    if (!state.speed) state.speed = { t0: now, d0: done }; // mede a partir daqui (o que veio da cache não conta)
    const { t0, d0 } = state.speed;
    $("eta-sub").textContent = tr("transcribed", { done: fmtDuration(done), total: fmtDuration(total) });
    $("eta").textContent = done > d0 && now - t0 > 15
      ? tr("eta", { time: fmtEta((total - done) * (now - t0) / (done - d0)) })
      : tr("measuring");
  },
  done(stats) {
    state.phase = "done";
    state.stats = stats;
    renderDone(stats);
    renderPhase();
  },
  async pack(p) {
    const b = $("gpu-pack");
    if (p.total) {
      b.textContent = tr("gpu_getting", { pct: Math.floor((p.done / p.total) * 100) });
    } else if (p.ok) {
      b.disabled = false;
      state.device = await api().device();
      renderDevice();
    } else if (p.error) {
      b.disabled = false;
      handlers.log(tr("gpu_pack_failed", { error: p.error }));
      renderDevice();
    }
  },
  // ficheiros arrastados para a janela
  reading_epub() {
    $("pick-epub").disabled = true;
    $("pick-epub").textContent = tr("reading");
  },
  epub(b) { setEpub(b); },
  epub_failed(error) {
    handlers.log(tr("read_failed", { error }));
    renderEpub();
    renderPhase();
  },
  audio(a) { setAudio(a); },
  cancelled() { state.phase = "cancelled"; renderPhase(); },
  error(msg) { state.phase = "error"; $("error-msg").textContent = msg; renderPhase(); },
};
window.app = { on: (kind, data) => handlers[kind] && handlers[kind](data) };

// --- botões ------------------------------------------------------------------------

async function busy(button, key, work) {
  button.disabled = true;
  button.textContent = tr(key);
  try { return await work(); } finally { button.disabled = false; renderEpub(); }
}

function setEpub(b) {
  state.epub = b;
  $("out").value = b.out;
  renderEpub();
  renderPhase();
}

function setAudio(a) {
  state.audio = a;
  renderAudio();
  renderPhase();
}

/** Ao arrastar ficheiros sobre a janela, os dois campos ficam realçados (o Python recebe o que for largado). */
function bindDrag() {
  const mark = (on) => {
    for (const c of document.querySelectorAll(".drop-zone")) c.classList.toggle("drag-over", on);
  };
  window.addEventListener("dragover", (e) => {
    e.preventDefault(); // sem isto, o browser abria o ficheiro em vez de o entregar
    const running = state.phase === "run";
    e.dataTransfer.dropEffect = running ? "none" : "copy";
    mark(!running);
  });
  window.addEventListener("dragleave", (e) => { if (!e.relatedTarget) mark(false); });
  window.addEventListener("drop", (e) => { e.preventDefault(); mark(false); }, true);
}

function bind() {
  bindDrag();
  $("theme").onclick = () => {
    setTheme(state.theme === "dark" ? "light" : "dark");
    saveSettings();
  };
  for (const b of $("ui-lang").children) {
    b.onclick = () => { setLang(b.dataset.l); saveSettings(); };
  }
  $("pick-epub").onclick = async () => {
    try {
      const b = await busy($("pick-epub"), "reading", () => api().pick_epub());
      if (b) setEpub(b);
    } catch (e) { handlers.log(tr("read_failed", { error: e.message || e })); }
  };
  const pickAudio = (id, fn) => async () => {
    const old = $(id).textContent;
    $(id).disabled = true;
    $(id).textContent = tr("reading");
    try {
      const a = await fn();
      if (a) setAudio(a);
    } finally {
      $(id).disabled = false;
      $(id).textContent = old;
    }
  };
  $("pick-files").onclick = pickAudio("pick-files", () => api().pick_audio_files());
  $("pick-dir").onclick = pickAudio("pick-dir", () => api().pick_audio_dir());
  $("pick-out").onclick = async () => {
    const out = await api().pick_out($("out").value);
    if (out) $("out").value = out;
  };
  for (const b of $("quality").children) {
    b.onclick = () => {
      state.quality = b.dataset.q;
      for (const o of $("quality").children) o.classList.toggle("on", o === b);
    };
  }
  $("go").onclick = async () => {
    if (!state.epub || !state.audio) return;
    state.phase = "run";
    state.stage = "ebook";
    state.speed = null;
    state.stats = null;
    state.log = [];
    renderLog();
    $("ring").style.setProperty("--p", 0);
    $("ring-pct").textContent = "0%";
    $("ring-label").textContent = tr("starting");
    $("eta").textContent = tr("preparing");
    $("eta-sub").textContent = "";
    $("cancel").disabled = false;
    renderPhase();
    await api().start({
      epub: state.epub.path, audio: state.audio.files.map((f) => f.path),
      out: $("out").value.trim() || state.epub.out, quality: state.quality, language: $("language").value,
    });
  };
  $("cancel").onclick = () => {
    $("cancel").disabled = true;
    $("cancel").textContent = tr("cancelling");
    api().cancel();
  };
  $("open-folder").onclick = () => api().open_folder();
  $("gpu-pack").onclick = () => {
    $("gpu-pack").disabled = true;
    $("gpu-pack").textContent = tr("gpu_getting", { pct: 0 });
    api().download_gpu_pack();
  };
  $("log-toggle").onclick = () => { state.logOpen = !state.logOpen; renderLog(); };
}

async function init() {
  const s = await api().settings();
  state.theme = s.theme === "light" ? "light" : "dark";
  bind();
  setLang(s.lang);
  api().enable_drop();
  state.device = await api().device();
  renderDevice();
}

window.addEventListener("pywebviewready", init);
