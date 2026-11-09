"use strict";
// Textos da janela em português e inglês. Nos elementos fixos do HTML:
// data-i18n (texto), data-i18n-html (texto com <b>), data-i18n-aria e data-i18n-ph (placeholder).

const STR = {
  pt: {
    tag: "Junta o audiobook e o ebook num só livro",
    mac_cpu: "Mac", mac_speed: "usa o processador",
    checking_gpu: "A verificar a placa gráfica…",
    gpu_name: "Placa {name}", gpu_generic: "Placa NVIDIA", gpu_fast: "rápido",
    no_gpu: "Sem placa NVIDIA", gpu_slow: "vai usar o processador (lento)",
    gpu_needs_pack: "falta o suporte", gpu_get: "Ativar a placa · {size}", gpu_get_nosize: "Ativar a placa",
    gpu_getting: "A descarregar… {pct}%", gpu_pack_failed: "Não consegui descarregar o suporte da placa: {error}",
    theme_to_light: "Mudar para tema claro", theme_to_dark: "Mudar para tema escuro", ui_lang: "Língua da janela",
    ebook: "Ebook", choose: "Escolher…", change: "Trocar", reading: "A ler…",
    no_ebook: "Nenhum ebook escolhido", pick_epub_hint: "Escolhe o ficheiro do livro (EPUB, MOBI ou AZW3) ou arrasta-o para aqui.",
    read_failed: "Não consegui ler o ebook: {error}",
    epub_lang: "EPUB · {lang}", print_pages: "{n} páginas impressas", no_pages_chip: "Sem páginas: usa a %",
    chapters_chip: "{n} capítulos",
    audiobook: "Audiobook", files_btn: "Ficheiros…", folder_btn: "Pasta…",
    audio_hint: "Escolhe um ficheiro (por exemplo .m4b) ou a pasta com os MP3, ou arrasta-os para aqui. Com vários ficheiros, a ordem segue o número no nome (2 antes de 10).",
    audio_none: "Não encontrei ficheiros de áudio aí.",
    file_one: "1 ficheiro", file_many: "{n} ficheiros",
    order_note: " · por esta ordem (o número no nome manda: 2 antes de 10)",
    options: "Opções", quality: "Qualidade", fast: "Rápida", best: "Máxima",
    book_lang: "Língua do livro", from_ebook: "Automática", from_audio: "Automática (pelo áudio)", from_ebook_lang: "Automática ({lang}, do ebook)",
    save_to: "Guardar em", out_placeholder: "Escolhe primeiro o ebook", pick_out: "Escolher onde guardar",
    create: "Sincronizar", again: "Sincronizar outra vez", continue: "Continuar",
    step_ebook: "Ler o ebook", step_transcribe: "Transcrever o áudio",
    step_align: "Sincronizar o texto com o áudio", step_create: "Guardar o ficheiro .tale",
    ready: "Pronto para começar", ready_pick: "Escolhe o ebook e o audiobook à esquerda.",
    ready_go: "Carrega em Sincronizar.",
    cancelled: "Cancelado", cancelled_sub: "Da próxima vez continua de onde ficou.",
    starting: "a começar", s_ebook: "a ler o ebook", s_transcribe: "a transcrever", s_align: "a sincronizar",
    s_create: "a guardar o ficheiro",
    preparing: "A preparar…", cancel: "Cancelar", cancelling: "A cancelar…",
    run_note: "Podes cancelar ou fechar: da próxima vez continua de onde ficou, sem repetir o que já foi transcrito.",
    almost: "Quase pronto", almost_sub: "A sincronizar o texto com o áudio. Demora poucos minutos.",
    transcribed: "{done} de {total} de áudio transcritos", eta: "Faltam cerca de {time}",
    measuring: "A medir a velocidade…", under_min: "menos de 1 min",
    done: "Sincronização concluída", synced: "das frases sincronizadas",
    low_warn: "Poucas frases ficaram sincronizadas. O audiobook e o ebook podem ser de edições ou traduções diferentes, ou a língua pode não ser a certa.",
    pages: "páginas", no_pages_stat: "sem páginas no ebook", chapters: "capítulos", of_audio: "de áudio",
    open_folder: "Abrir pasta",
    error: "Ocorreu um erro", error_note: "Os detalhes estão no registo, em baixo. O que já foi transcrito fica guardado.",
    hint: "Copia o ficheiro <b>.tale</b> para o telemóvel e, na app, carrega em <b>Importar</b>.",
    log: "Registo", show_all: "Mostrar tudo", show_less: "Mostrar menos",
    legal: "O Talehop é software livre (GPL-3.0), sem garantia · <a href=\"https://github.com/thezuwr/talehop\" target=\"_blank\">Código</a>",
    langs: { pt: "português", en: "inglês", es: "espanhol", fr: "francês", it: "italiano", de: "alemão" },
    lang_options: { pt: "Português", en: "Inglês", es: "Espanhol", fr: "Francês", it: "Italiano", de: "Alemão" },
  },
  en: {
    tag: "Joins the audiobook and the ebook into one book",
    mac_cpu: "Mac", mac_speed: "uses the processor",
    checking_gpu: "Checking the graphics card…",
    gpu_name: "{name}", gpu_generic: "NVIDIA card", gpu_fast: "fast",
    no_gpu: "No NVIDIA card", gpu_slow: "will use the processor (slow)",
    gpu_needs_pack: "support missing", gpu_get: "Enable the card · {size}", gpu_get_nosize: "Enable the card",
    gpu_getting: "Downloading… {pct}%", gpu_pack_failed: "Couldn't download the card support: {error}",
    theme_to_light: "Switch to light theme", theme_to_dark: "Switch to dark theme", ui_lang: "Window language",
    ebook: "Ebook", choose: "Choose…", change: "Change", reading: "Reading…",
    no_ebook: "No ebook chosen", pick_epub_hint: "Choose the book's file (EPUB, MOBI or AZW3) or drag it here.",
    read_failed: "Couldn't read the ebook: {error}",
    epub_lang: "EPUB · {lang}", print_pages: "{n} print pages", no_pages_chip: "No pages: uses %",
    chapters_chip: "{n} chapters",
    audiobook: "Audiobook", files_btn: "Files…", folder_btn: "Folder…",
    audio_hint: "Choose a file (for example .m4b) or the folder with the MP3s, or drag them here. With several files, the order follows the number in the name (2 before 10).",
    audio_none: "No audio files found there.",
    file_one: "1 file", file_many: "{n} files",
    order_note: " · in this order (the number in the name decides: 2 before 10)",
    options: "Options", quality: "Quality", fast: "Fast", best: "Best",
    book_lang: "Book language", from_ebook: "Automatic", from_audio: "Automatic (from the audio)", from_ebook_lang: "Automatic ({lang}, from the ebook)",
    save_to: "Save to", out_placeholder: "Choose the ebook first", pick_out: "Choose where to save",
    create: "Sync", again: "Sync again", continue: "Continue",
    step_ebook: "Read the ebook", step_transcribe: "Transcribe the audio",
    step_align: "Sync the text with the audio", step_create: "Save the .tale file",
    ready: "Ready to start", ready_pick: "Choose the ebook and the audiobook on the left.",
    ready_go: "Click Sync.",
    cancelled: "Cancelled", cancelled_sub: "Next time it carries on from where it stopped.",
    starting: "starting", s_ebook: "reading the ebook", s_transcribe: "transcribing", s_align: "syncing",
    s_create: "saving the file",
    preparing: "Preparing…", cancel: "Cancel", cancelling: "Cancelling…",
    run_note: "You can cancel or close: next time it carries on from where it stopped, without redoing what's already transcribed.",
    almost: "Almost done", almost_sub: "Syncing the text with the audio. Takes a few minutes.",
    transcribed: "{done} of {total} of audio transcribed", eta: "About {time} left",
    measuring: "Measuring the speed…", under_min: "under 1 min",
    done: "Sync complete", synced: "of sentences synced",
    low_warn: "Few sentences were synced. The audiobook and the ebook may be different editions or translations, or the language may be wrong.",
    pages: "pages", no_pages_stat: "no pages in the ebook", chapters: "chapters", of_audio: "of audio",
    open_folder: "Open folder",
    error: "Something went wrong", error_note: "The details are in the log below. What was already transcribed is kept.",
    hint: "Copy the <b>.tale</b> file to your phone and tap <b>Import</b> in the app.",
    log: "Log", show_all: "Show all", show_less: "Show less",
    legal: "Talehop is free software (GPL-3.0), with no warranty · <a href=\"https://github.com/thezuwr/talehop\" target=\"_blank\">Source code</a>",
    langs: { pt: "Portuguese", en: "English", es: "Spanish", fr: "French", it: "Italian", de: "German" },
    lang_options: { pt: "Portuguese", en: "English", es: "Spanish", fr: "French", it: "Italian", de: "German" },
  },
};

let uiLang = "pt";

/** Texto na língua da janela, com {nome} trocado por vars.nome. */
function tr(key, vars) {
  const s = STR[uiLang][key] ?? STR.pt[key] ?? key;
  return vars ? s.replace(/\{(\w+)\}/g, (_, k) => vars[k]) : s;
}

/** Aplica a língua aos elementos fixos do HTML. */
function applyStatic() {
  document.documentElement.lang = uiLang;
  for (const e of document.querySelectorAll("[data-i18n]")) e.textContent = tr(e.dataset.i18n);
  for (const e of document.querySelectorAll("[data-i18n-html]")) e.innerHTML = tr(e.dataset.i18nHtml);
  for (const e of document.querySelectorAll("[data-i18n-aria]")) e.setAttribute("aria-label", tr(e.dataset.i18nAria));
  for (const e of document.querySelectorAll("[data-i18n-ph]")) e.placeholder = tr(e.dataset.i18nPh);
  for (const o of document.querySelectorAll("#language option")) {
    if (o.value) o.textContent = STR[uiLang].lang_options[o.value];
  }
}
