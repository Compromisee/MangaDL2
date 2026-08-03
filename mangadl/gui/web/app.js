/* MangaDL GUI logic */

"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  settings: null,
  manga: null,           // { info, chapters, downloaded, bookmarked }
  selected: new Set(),   // selected chapter indexes
  downloaded: new Set(), // downloaded chapter NAMES
  format: "cbz",
  bundleMode: "0",
  downloading: false,
  totalChapters: 0,
  doneChapters: 0,
};

/* ------------------------------------------------------------------ api */

function api() {
  return window.pywebview && window.pywebview.api;
}

/* Every new view calls the bridge through this. A missing endpoint or a
   Python-side exception returns null instead of rejecting, so one broken
   call cannot blank out a whole tab -- the same failure mode that used to
   kill the startup sequence. */
async function callApi(name, ...args) {
  const bridge = api();
  if (!bridge || typeof bridge[name] !== "function") {
    console.warn("api." + name + " is unavailable");
    return null;
  }
  try {
    return await bridge[name](...args);
  } catch (err) {
    console.warn("api." + name + " failed:", err);
    return null;
  }
}

/* Last line of defence. Without these a rejected bridge call vanished into
   the console: measured, a failing get_manga left the loading spinner up
   forever and showed the user nothing at all. These do not paper over bugs
   -- everything is still logged -- but the UI always returns to a usable
   state and says something. */
window.__mangadlErrorHandler = true;

function reportFailure(what, detail) {
  try {
    console.error(what, detail);
    // Clear any spinner that a failed step left behind.
    document.querySelectorAll(".loading:not(.hidden), #mangaLoading:not(.hidden)")
      .forEach((el) => el.classList.add("hidden"));
    if (typeof toast === "function") toast(what);
  } catch (e) { /* never throw from the error handler */ }
}

window.addEventListener("unhandledrejection", (e) => {
  e.preventDefault();
  reportFailure("Something went wrong", e.reason);
});

window.addEventListener("error", (e) => {
  // Resource errors (a cover that 404s) bubble here too and are handled
  // elsewhere; only report genuine script errors.
  if (e.target && e.target !== window) return;
  reportFailure("Something went wrong", e.error || e.message);
});

function whenReady(fn) {
  if (api()) return fn();
  window.addEventListener("pywebviewready", fn, { once: true });
}

/* ---------------------------------------------------------------- toast */

let toastTimer = null;
function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 2600);
}

/* ---------------------------------------------------------------- modal */

let modalResolve = null;
function confirmModal(title, body, okLabel = "Continue") {
  return new Promise((resolve) => {
    modalResolve = resolve;
    modalIsPrompt = false;
    $("modalInput").classList.add("hidden");
    $("modalTitle").textContent = title;
    $("modalBody").textContent = body;
    $("modalOk").textContent = okLabel;
    $("modalBackdrop").classList.remove("hidden");
  });
}
/* Same modal, with a text field. Returns the typed string, or null when
   cancelled -- so callers can tell "empty" from "dismissed". */
let modalIsPrompt = false;
function promptModal(title, placeholder, value = "") {
  return new Promise((resolve) => {
    modalResolve = resolve;
    modalIsPrompt = true;
    $("modalTitle").textContent = title;
    $("modalBody").textContent = "";
    const input = $("modalInput");
    input.classList.remove("hidden");
    input.placeholder = placeholder || "";
    input.value = value || "";
    $("modalOk").textContent = "Save";
    $("modalBackdrop").classList.remove("hidden");
    setTimeout(() => { input.focus(); input.select(); }, 40);
  });
}

function closeModal(result) {
  $("modalBackdrop").classList.add("hidden");
  $("modalInput").classList.add("hidden");
  const resolve = modalResolve;
  const wasPrompt = modalIsPrompt;
  modalResolve = null;
  modalIsPrompt = false;
  if (resolve) resolve(wasPrompt ? result : !!result);
}

$("modalCancel").addEventListener("click", () => closeModal(null));
$("modalOk").addEventListener("click", () =>
  closeModal(modalIsPrompt ? $("modalInput").value.trim() : true));
$("modalInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") closeModal($("modalInput").value.trim());
});

/* ----------------------------------------------------------- dot matrix */

const matrix = (() => {
  const canvas = $("matrix");
  const ctx = canvas.getContext("2d", { alpha: true });
  let dots = [], raf = null, enabled = true, rgb = "255,255,255";
  let lastDraw = 0;

  // Redrawing 600 dots at 60fps is ~36,000 canvas arcs per second for a
  // decorative background. It is capped to 30fps, pauses when the window is
  // hidden or the app is locked, and scales the dot count down on large
  // viewports so the cost does not grow with screen size.
  const TARGET_FPS = 30;
  const FRAME_MS = 1000 / TARGET_FPS;
  const MAX_DOTS = 420;

  function readColour() {
    rgb = getComputedStyle(document.documentElement)
      .getPropertyValue("--matrix-dot").trim() || "255,255,255";
  }

  function resize() {
    // cap the backing store on hi-dpi screens; this is a background texture
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    let gap = 46;
    const estimate = () =>
      Math.ceil(window.innerWidth / gap) * Math.ceil(window.innerHeight / gap);
    while (estimate() > MAX_DOTS) gap += 6;      // widen spacing, not density

    dots = [];
    for (let x = gap / 2; x < window.innerWidth; x += gap) {
      for (let y = gap / 2; y < window.innerHeight; y += gap) {
        dots.push({
          x, y,
          phase: Math.random() * Math.PI * 2,
          speed: 0.4 + Math.random() * 0.8,
        });
      }
    }
    readColour();
  }

  function frame(t) {
    raf = requestAnimationFrame(frame);
    if (t - lastDraw < FRAME_MS) return;         // throttle to TARGET_FPS
    lastDraw = t;

    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    // colour is read on resize/theme change, not every single frame --
    // getComputedStyle in a raf loop forces a style recalc each time
    for (let i = 0; i < dots.length; i++) {
      const d = dots[i];
      const a = 0.025 + 0.05 * (0.5 + 0.5 * Math.sin(d.phase + t * 0.0006 * d.speed));
      ctx.fillStyle = `rgba(${rgb},${a})`;
      ctx.beginPath();
      ctx.arc(d.x, d.y, 1.3, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function start() {
    if (!enabled || raf || document.hidden) return;
    resize();
    raf = requestAnimationFrame(frame);
  }
  function stop() {
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    if (!raf) return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 150);       // debounce layout thrash
  });

  // stop burning CPU while minimised or in the background
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else if (enabled) start();
  });

  return {
    set(on) { enabled = on; on ? start() : stop(); },
    refreshColour: readColour,
    pause: stop,
    resume() { if (enabled) start(); },
  };
})();

/* ----------------------------------------------------------- navigation */

function showView(name) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.querySelectorAll(".rail-btn[data-view]").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name));
  $("view-" + name).classList.add("active");
  if (name === "downloads") renderCart();
  // The Settings card lists the same shortcuts as the overlay, generated
  // from the same array, so the two cannot fall out of sync.
  if (name === "settings") renderShortcuts($("settingsShortcuts"));
  if (name === "bookmarks") loadBookmarks();
  if (name === "library") loadLibrary();
  if (name === "updates") loadUpdates();
  if (name === "insights") loadInsights();
  if (name === "tools") {
    const active = document.querySelector(".tool-tab.active");
    const tool = active ? active.dataset.tool : "disk";
    if (tool === "health") loadHealth();
    if (tool === "history") loadHistoryList();
    if (tool === "moved") loadMoved();
  }
}

document.querySelectorAll(".rail-btn[data-view]").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!btn.disabled) showView(btn.dataset.view);
  });
});

/* ------------------------------------------------------ theme & accent */

function applyColumns(n) {
  // 0 keeps the responsive auto-fill; a fixed count overrides it so users
  // who want denser or larger covers can say so.
  const count = Math.max(0, Math.min(14, parseInt(n) || 0));
  document.documentElement.style.setProperty(
    "--grid-cols", count ? `repeat(${count}, minmax(0, 1fr))` : "");
}

function applyAppearance(s) {
  applyColumns(s.columns);
  document.documentElement.setAttribute("data-theme", s.theme || "midnight");
  document.documentElement.setAttribute("data-accent", s.accent || "blue");
  document.documentElement.setAttribute("data-anim", s.animations === false ? "off" : "on");
  document.documentElement.setAttribute("data-corners", s.corners || "rounded");
  matrix.set(s.matrix !== false);
  matrix.refreshColour();   // cached per theme, not read every frame
  document.querySelectorAll(".theme-swatch").forEach((b) =>
    b.classList.toggle("active", b.dataset.theme === (s.theme || "midnight")));
  document.querySelectorAll(".accent-dot").forEach((b) =>
    b.classList.toggle("active", b.dataset.accent === (s.accent || "blue")));
}

document.querySelectorAll(".theme-swatch").forEach((btn) => {
  btn.addEventListener("click", async () => {
    state.settings.theme = btn.dataset.theme;
    applyAppearance(state.settings);
    if (api()) await api().set_settings({ theme: btn.dataset.theme });
  });
});
document.querySelectorAll(".accent-dot").forEach((btn) => {
  btn.addEventListener("click", async () => {
    state.settings.accent = btn.dataset.accent;
    applyAppearance(state.settings);
    if (api()) await api().set_settings({ accent: btn.dataset.accent });
  });
});
$("setAnimations").addEventListener("change", async (e) => {
  state.settings.animations = e.target.checked;
  applyAppearance(state.settings);
  if (api()) await api().set_settings({ animations: e.target.checked });
});
$("setMatrix").addEventListener("change", async (e) => {
  state.settings.matrix = e.target.checked;
  applyAppearance(state.settings);
  if (api()) await api().set_settings({ matrix: e.target.checked });
});

/* --------------------------------------------------------------- search */

/* Sources are discovered from the backend, so adding a source in Python
   automatically populates the picker with no JS changes. */
let SOURCES = [];
let sourceById = {};

async function loadSources() {
  if (!api() || !api().get_sources) return;
  const res = await callApi("get_sources");
  if (!res || !res.ok) return;
  SOURCES = res.sources || [];
  sourceById = {};
  SOURCES.forEach((s) => { sourceById[s.id] = s; });

  const sel = $("fSource");
  const current = sel.value || "all";
  sel.innerHTML = '<option value="all">All sources</option>';
  SOURCES.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.name;
    sel.appendChild(opt);
  });
  sel.value = sourceById[current] ? current : "all";
  syncSourceUI();
}

/* Show only the filters the selected source actually supports. */
function syncSourceUI() {
  const id = $("fSource").value;
  const src = sourceById[id];

  const langGroup = $("langGroup");
  if (langGroup) langGroup.hidden = !(src && src.supports_language);

  const sortSel = $("fSort");
  const sorts = src && src.sorts && src.sorts.length ? src.sorts : null;
  if (sorts) {
    const prev = sortSel.value;
    sortSel.innerHTML = "";
    sorts.forEach((name) => {
      const opt = document.createElement("option");
      opt.textContent = name;
      sortSel.appendChild(opt);
    });
    sortSel.value = sorts.includes(prev) ? prev : sorts[0];
    sortSel.parentElement.hidden = false;
  } else {
    sortSel.parentElement.hidden = id !== "all" ? false : true;
  }

  const browseGroup = $("browseSortGroup");
  if (browseGroup) {
    const sorts = (src && src.browse_sorts) || [];
    if (sorts.length) {
      const prev = $("fBrowseSort").value;
      $("fBrowseSort").innerHTML = "";
      sorts.forEach((name) => {
        const opt = document.createElement("option");
        opt.textContent = name;
        $("fBrowseSort").appendChild(opt);
      });
      $("fBrowseSort").value = sorts.includes(prev) ? prev : sorts[0];
    }
    browseGroup.hidden = false;
  }

  // WeebCentral-only controls
  const wcOnly = id === "weebcentral" || id === "all";
  const typeGroup = $("fType") && $("fType").parentElement;
  const offGroup = $("fOfficial") && $("fOfficial").parentElement;
  if (typeGroup) typeGroup.hidden = !wcOnly;
  if (offGroup) offGroup.hidden = !wcOnly;
}

/* Genres are multi-select: the dropdown adds to a picked list rather than
   replacing it, so "Action + Romance" is expressible. The single `genre`
   field is still sent for older call sites / one-genre searches. */
let pickedGenres = [];

function toggleGenre(name) {
  const key = (name || "").trim();
  if (!key) return;
  const at = pickedGenres.findIndex((g) => g.toLowerCase() === key.toLowerCase());
  if (at >= 0) pickedGenres.splice(at, 1);
  else pickedGenres.push(key);
  syncGenreUI();
}

function clearGenres() {
  pickedGenres = [];
  syncGenreUI();
}

function syncGenreUI() {
  const sel = $("fGenre");
  if (sel) sel.value = pickedGenres.length === 1 ? pickedGenres[0] : "";

  const group = $("genreMatchGroup");
  if (group) group.hidden = pickedGenres.length < 2;

  const wrap = $("pickedGenres");
  const list = $("pickedGenreList");
  if (wrap && list) {
    wrap.classList.toggle("hidden", pickedGenres.length === 0);
    list.innerHTML = "";
    pickedGenres.forEach((g) => {
      const chip = document.createElement("button");
      chip.className = "pg-chip";
      chip.innerHTML = `${escapeHtml(g)}<span class="material-symbols-rounded">close</span>`;
      chip.addEventListener("click", () => { toggleGenre(g); doSearch(true); });
      list.appendChild(chip);
    });
  }
  renderGenreChips();
  updateFilterDot();
}

function getFilters() {
  return {
    source: $("fSource").value,
    genres: pickedGenres.slice(),
    genre_match: $("fGenreMatch") ? $("fGenreMatch").value : "all",
    genre: pickedGenres.length ? pickedGenres[0] : "",
    browse_sort: $("fBrowseSort") ? $("fBrowseSort").value : "Trending",
    language: $("fLanguage") ? $("fLanguage").value : "en",
    sort: $("fSort").value,
    order: $("fOrder").dataset.order,
    status: $("fStatus").value,
    type: $("fType").value,
    official: $("fOfficial").value === "Only official" ? "True"
            : $("fOfficial").value === "Unofficial" ? "False"
            : $("fOfficial").value,
  };
}

function filtersActive() {
  const f = getFilters();
  return f.source !== "all" || pickedGenres.length > 0 || f.sort !== "Best Match"
      || f.order !== "Ascending" || f.status !== "Any" || f.type !== "Any"
      || f.official !== "Any";
}

/* Genres are merged across the enabled sources by the backend, so the list
   reflects whatever sites are currently switched on. */
let GENRES = [];

async function loadGenres() {
  if (!api() || !api().get_genres) return;
  const sel = $("fGenre");
  const picked = sel.value;
  const res = await callApi("get_genres", $("fSource").value || "all");
  if (!res || !res.ok) return;
  GENRES = res.genres || [];

  sel.innerHTML = '<option value="">Any genre</option>';
  GENRES.forEach((g) => {
    const opt = document.createElement("option");
    opt.value = g.name;
    opt.textContent = g.name;
    sel.appendChild(opt);
  });
  if ([...sel.options].some((o) => o.value === picked)) sel.value = picked;
  renderGenreChips();
}

/* Quick-pick chips for the most widely supported genres. */
function renderGenreChips() {
  const wrap = $("genreChips");
  if (!wrap) return;
  wrap.innerHTML = "";
  const active = new Set(pickedGenres.map((g) => g.toLowerCase()));
  GENRES.slice(0, 12).forEach((g) => {
    const chip = document.createElement("button");
    chip.className = "genre-chip" + (active.has(g.name.toLowerCase()) ? " active" : "");
    chip.textContent = g.name;
    // Chips add to the selection instead of replacing it, so several
    // genres can be combined; clicking an active chip removes it.
    chip.addEventListener("click", () => { toggleGenre(g.name); doSearch(true); });
    wrap.appendChild(chip);
  });
}

function updateFilterDot() {
  $("filterDot").classList.toggle("hidden", !filtersActive());
}

$("filterToggle").addEventListener("click", () => {
  const row = $("filtersRow");
  const open = row.classList.toggle("hidden");
  $("filterToggle").classList.toggle("on", !open);
});

$("fOrder").addEventListener("click", () => {
  const btn = $("fOrder");
  const asc = btn.dataset.order === "Ascending";
  btn.dataset.order = asc ? "Descending" : "Ascending";
  btn.classList.toggle("desc", asc);
  updateFilterDot();
  if (lastQuery) doSearch(true);
});

["fSort", "fStatus", "fType", "fOfficial", "fLanguage"].forEach((id) =>
  $(id) && $(id).addEventListener("change", () => {
    updateFilterDot();
    if (lastQuery) doSearch(true);
  }));

$("fSource").addEventListener("change", async () => {
  syncSourceUI();
  updateFilterDot();
  if (api()) await api().set_settings({ default_source: $("fSource").value });
  await loadGenres();
  doSearch(true);          // also refreshes the trending feed
});

/* The dropdown adds to the picked list rather than replacing it, so it can
   be used repeatedly to build up a multi-genre query. */
$("fGenre").addEventListener("change", () => {
  const value = $("fGenre").value;
  if (value && !pickedGenres.some((g) => g.toLowerCase() === value.toLowerCase())) {
    pickedGenres.push(value);
  } else if (!value) {
    pickedGenres = [];
  }
  syncGenreUI();
  doSearch(true);
});

$("fGenreMatch") && $("fGenreMatch").addEventListener("change", () => doSearch(true));

$("clearGenresBtn") && $("clearGenresBtn").addEventListener("click", () => {
  clearGenres();
  doSearch(true);
});

$("fBrowseSort").addEventListener("change", () => doSearch(true));

$("fReset").addEventListener("click", () => {
  $("fSource").value = "all";
  clearGenres();
  syncSourceUI();
  $("fSort").value = "Best Match";
  $("fStatus").value = "Any";
  $("fType").value = "Any";
  $("fOfficial").value = "Any";
  const btn = $("fOrder");
  btn.dataset.order = "Ascending";
  btn.classList.remove("desc");
  updateFilterDot();
  if (lastQuery) doSearch(true);
});

let lastQuery = "";
let searchSeq = 0;

let browsePage = 1;
let browseMode = false;
let lastResultCount = 0;

/* Placeholder tiles keep the grid stable while a request is in flight. */
function showSkeletons(count) {
  const grid = $("searchResults");
  grid.innerHTML = "";
  for (let i = 0; i < count; i++) {
    const sk = document.createElement("div");
    sk.className = "skeleton-card";
    sk.innerHTML = '<div class="sk-img"></div><div class="sk-line"></div>';
    grid.appendChild(sk);
  }
}

function showState(icon, title, hint, actions) {
  const buttons = (actions || [])
    .map((a, i) => `<button class="btn" data-state-act="${i}">${escapeHtml(a.label)}</button>`)
    .join("");
  $("searchResults").innerHTML = "";
  $("searchState").innerHTML = `
    <div class="state-box">
      <span class="material-symbols-rounded">${icon}</span>
      <div class="state-title">${escapeHtml(title)}</div>
      <div class="state-hint">${escapeHtml(hint || "")}</div>
      ${buttons ? `<div class="state-actions">${buttons}</div>` : ""}
    </div>`;
  (actions || []).forEach((a, i) => {
    const btn = $("searchState").querySelector(`[data-state-act="${i}"]`);
    if (btn) btn.addEventListener("click", a.onClick);
  });
}

/* Some CDNs mirror the same thumbnail across interchangeable hosts, and any
   one of them intermittently answers 404 or 429 while the others serve the
   identical file. Walk the mirror list on error rather than giving up on the
   first failure and showing an empty tile. */
function attachCover(img, card, item) {
    const candidates = [];
    if (item.cover) candidates.push(item.cover);
    (item.cover_mirrors || []).forEach((u) => {
      if (u && !candidates.includes(u)) candidates.push(u);
    });
    if (!candidates.length) {
      if (card) card.classList.add("no-cover");
      return;
    }

    /* Some CDNs (Webtoons' pstatic.net) answer 403 unless the request
       carries their own site as the Referer. This document is sent with
       "no-referrer" because MangaDex substitutes a placeholder image
       otherwise, so those covers can never load from an <img> tag. Ask
       Python to fetch them with the right header and inline the bytes. */
    const src = sourceById[item.source];
    const mustProxy = !!(src && src.cover_needs_referer);
    let proxied = false;

    const viaProxy = async (url) => {
      if (proxied || !api() || !api().proxy_cover) return false;
      proxied = true;
      try {
        const res = await api().proxy_cover(url, item.source || null);
        if (res && res.ok && res.data) { img.src = res.data; return true; }
      } catch (e) { /* fall through to the placeholder */ }
      return false;
    };

    /* Natomanga's cover hosts are shards, not mirrors: the URL in the
       markup is the only one that serves the file, and its occasional
       failure is a transient 429/503. So retry the *same* URL once after a
       short delay before giving up, rather than rewriting the host. */
    let index = 0;
    let retried = false;
    const tryNext = async () => {
      if (index >= candidates.length) {
        if (!retried && candidates.length) {
          retried = true;
          const last = candidates[candidates.length - 1];
          setTimeout(() => { img.src = last + (last.includes("?") ? "&" : "?") + "r=1"; }, 600);
          return;
        }
        // Direct loads are exhausted -- one last attempt through Python.
        if (!proxied && await viaProxy(candidates[0])) return;
        if (card) card.classList.add("no-cover");
        return;
      }
      const url = candidates[index++];
      if (mustProxy) {
        if (await viaProxy(url)) return;
        if (card) card.classList.add("no-cover");
        return;
      }
      img.src = url;
    };

    img.addEventListener("load", () => {
      img.classList.add("loaded");
      if (card) card.classList.remove("no-cover");
    });
    img.addEventListener("error", tryNext);
    tryNext();
}

function renderCards(results, append = false) {
  const grid = $("searchResults");
  if (!append) grid.innerHTML = "";
  const showBadge = $("fSource").value === "all";
  const offset = append ? grid.children.length : 0;

  results.forEach((r, i) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.style.setProperty("--i", Math.min(i, 17));

    const badge = (showBadge && r.source)
      ? `<span class="rc-source" data-source="${escapeHtml(r.source)}">${escapeHtml(r.source_name || r.source)}</span>`
      : "";
    const also = (r.also_on && r.also_on.length)
      ? `<span class="rc-also" title="Also on ${r.also_on.map((a) => escapeHtml(a.source_name || a.source)).join(", ")}">+${r.also_on.length}</span>`
      : "";

    const safeTitle = escapeHtml(r.title);
    card.innerHTML = `
      ${badge}${also}
      <img loading="lazy" decoding="async" alt="">
      <div class="rc-fallback">${safeTitle}</div>
      <div class="rc-title">${safeTitle}</div>`;

    // Set src in JS so load/error can be handled without inline handlers,
    // and fade in only once the bitmap is actually decoded.
    const img = card.querySelector("img");
    attachCover(img, card, r);

    card.dataset.url = r.url || "";
    card.addEventListener("click", () => openManga(r.url, r.source));
    grid.appendChild(card);
  });

  // Mark what you already have. Fire-and-forget: the cards are already on
  // screen, so a slow or failed lookup costs nothing but the badges.
  markDownloadedResults(results);
  return offset + results.length;
}

/* ------------------------------------------------- already-downloaded

   Three modes, from Settings:
     show    leave results alone
     darken  dim them; hovering fills the cover up to the percent you have
     hide    remove them from the grid entirely

   The percentage is only ever shown when the source told us how many
   chapters the series has. Plenty do not, and "12 downloaded out of
   unknown" must not be rounded up into a confident 100%. */

function downloadedMode() {
  const mode = (state.settings || {}).downloaded_results;
  return ["show", "darken", "hide"].includes(mode) ? mode : "darken";
}

async function markDownloadedResults(results) {
  const mode = downloadedMode();
  if (mode === "show") return;

  const rows = (results || [])
    .filter((r) => r && r.url)
    .map((r) => ({
      url: r.url,
      // Whatever this source happens to publish; the Python side picks
      // whichever of these it recognises.
      last_chapter: r.last_chapter,
      chapter_count: r.chapter_count,
      chapters: typeof r.chapters === "number" ? r.chapters : undefined,
      total_chapters: r.total_chapters,
    }));
  if (!rows.length) return;

  const res = await callApi("downloaded_status", rows);
  const status = (res && res.ok && res.status) || {};
  if (!Object.keys(status).length) return;

  const grid = $("searchResults");
  if (!grid) return;

  Object.entries(status).forEach(([url, info]) => {
    const card = grid.querySelector(
      `.result-card[data-url="${CSS.escape(url)}"]`);
    if (!card || card.classList.contains("dl-marked")) return;
    card.classList.add("dl-marked");

    if (mode === "hide") {
      card.classList.add("dl-hidden");
      return;
    }
    applyDownloadedOverlay(card, info);
  });

  if (mode === "hide") updateHiddenNotice();
}

function applyDownloadedOverlay(card, info) {
  card.classList.add("dl-done");
  if (info.complete) card.classList.add("dl-complete");

  const known = typeof info.percent === "number";
  // With no total to measure against, the fill has nothing honest to show,
  // so the card gets the count only.
  const pct = known ? info.percent : 0;
  const label = known
    ? `${info.percent}%`
    : `${info.chapters} ch`;
  const detail = known
    ? `${info.chapters} of ${info.total} chapters downloaded`
    : `${info.chapters} chapter${info.chapters === 1 ? "" : "s"} downloaded`
      + " — this source does not report a total";

  const wrap = document.createElement("div");
  wrap.className = "dl-overlay" + (known ? "" : " dl-unknown");
  wrap.title = detail;
  wrap.innerHTML = `
    <div class="dl-fill" style="--pct:${pct}%"></div>
    <div class="dl-badge">
      <span class="material-symbols-rounded">${info.complete ? "task_alt" : "download_done"}</span>
      <span class="dl-pct">${escapeHtml(label)}</span>
    </div>`;
  card.appendChild(wrap);
}

/* Hiding results silently would look like a broken search, so say so. */
function updateHiddenNotice() {
  const grid = $("searchResults");
  const state_ = $("searchState");
  if (!grid || !state_) return;
  const hidden = grid.querySelectorAll(".result-card.dl-hidden").length;
  if (!hidden) return;
  const note = `${hidden} already-downloaded result${hidden === 1 ? "" : "s"} hidden`;
  state_.textContent = state_.textContent
    ? `${state_.textContent} · ${note}` : note;
}

/* One entry point for both modes. An empty box means "show me something",
   which runs the trending/genre browse instead of a text search. */
async function doSearch(rerun = false, append = false) {
  const _sug = $("suggestBox");
  if (_sug) _sug.classList.add("hidden");
  const query = rerun || append ? lastQuery : $("searchInput").value.trim();

  if (!rerun && !append && /^https?:\/\//i.test(query)) {
    openManga(query);
    return;
  }
  lastQuery = query;
  const filters = getFilters();
  browseMode = !query;

  if (!append) {
    browsePage = 1;
    $("searchHero").classList.toggle("compact", true);
    $("searchState").textContent = "";
    showSkeletons(12);
    $("loadMoreBtn").classList.add("hidden");
  } else {
    $("loadMoreBtn").disabled = true;
    $("loadMoreBtn").textContent = "Loading…";
  }

  // trending / genre header
  const head = $("browseHead");
  if (browseMode) {
    const picked = filters.genres || [];
    const joiner = (filters.genre_match === "any") ? " or " : " + ";
    $("browseHeadText").textContent = picked.length
      ? `Top ${picked.join(joiner)} right now`
      : `${filters.browse_sort || "Trending"} now`;
    head.classList.remove("hidden");
    renderGenreChips();
  } else {
    head.classList.add("hidden");
  }

  const seq = ++searchSeq;
  let res;
  if (browseMode) {
    res = await callApi("browse", {
      source: filters.source,
      genre: filters.genre,
      genres: filters.genres,
      genre_match: filters.genre_match,
      sort: filters.browse_sort || "Trending",
      status: filters.status,
      page: browsePage,
    });
  } else {
    res = await callApi("search", query, { ...filters, page: browsePage });
  }
  if (seq !== searchSeq) return;   // a newer request superseded this one

  // A null here means the bridge rejected. Surface it instead of falling
  // through and throwing on res.ok, which aborted the whole handler and
  // left the spinner and the disabled Load more button behind.
  if (!res) {
    $("loadMoreBtn").disabled = false;
    $("loadMoreBtn").textContent = "Load more";
    showState("error", "Search failed",
              "The app could not reach that source. Try again.",
              [{ label: "Retry", onClick: () => doSearch(true) }]);
    return;
  }

  $("loadMoreBtn").disabled = false;
  $("loadMoreBtn").textContent = "Load more";
  $("searchState").textContent = "";

  if (!res.ok) {
    showState("cloud_off", "Could not reach the sources",
              res.error || "Request failed. Check your connection and try again.",
              [{ label: "Retry", onClick: () => doSearch(true) }]);
    return;
  }

  // the backend may resolve a pasted URL instead of returning results
  if (res.url) { openManga(res.url); return; }

  const results = res.results || [];
  if (!results.length && !append) {
    if (browseMode) {
      showState("travel_explore", "Nothing to show here",
                "Try a different genre, or enable more sources in Settings.",
                [{ label: "Clear genre", onClick: () => {
                    $("fGenre").value = ""; renderGenreChips();
                    updateFilterDot(); doSearch(true);
                  } },
                 { label: "Retry", onClick: () => doSearch(true) }]);
    } else {
      showState("search_off", `No results for "${query}"`,
                "Check the spelling, try a shorter query, or search a different source.",
                [{ label: "Show trending", onClick: () => {
                    $("searchInput").value = ""; doSearch();
                  } }]);
    }
    $("loadMoreBtn").classList.add("hidden");
    return;
  }
  if (!results.length && append) {
    $("loadMoreBtn").classList.add("hidden");
    return;
  }

  lastResultCount = renderCards(results, append);
  $("loadMoreBtn").classList.toggle("hidden", results.length === 0);
  if (res.message) $("searchState").textContent = res.message;
}

$("loadMoreBtn").addEventListener("click", () => {
  browsePage += 1;
  doSearch(true, true);
});

$("searchBtn").addEventListener("click", () => doSearch());

/* Enter must always run a search.
   The input previously carried a <datalist>. In WebView2 an open datalist
   popup consumes the Enter keypress, so keydown never reached this handler
   and the Search button was the only way to search. keyup is used as a
   belt-and-braces second path, guarded so one press cannot fire twice. */
let _lastEnter = 0;
function submitSearch(e) {
  if (e.key !== "Enter") return;
  e.preventDefault();
  const now = Date.now();
  if (now - _lastEnter < 250) return;   // ignore the paired keyup
  _lastEnter = now;
  doSearch();
}
$("searchInput").addEventListener("keydown", submitSearch);
$("searchInput").addEventListener("keyup", submitSearch);

/* Suggestions render into our own themed list rather than a native
   datalist, which cannot be styled and breaks Enter in WebView2. */
let suggestTimer = null;
$("searchInput").addEventListener("input", () => {
  clearTimeout(suggestTimer);
  suggestTimer = setTimeout(async () => {
    const box = $("suggestBox");
    if (!box) return;
    const term = $("searchInput").value.trim();
    if (!term) { box.classList.add("hidden"); return; }
    const res = await callApi("suggest_query", term);
    const items = (res && res.items) || [];
    if (!items.length) { box.classList.add("hidden"); return; }
    box.innerHTML = items.slice(0, 8)
      .map((q) => `<button type="button" class="suggest-item">${escapeHtml(q)}</button>`)
      .join("");
    box.classList.remove("hidden");
    box.querySelectorAll(".suggest-item").forEach((btn) =>
      btn.addEventListener("click", () => {
        $("searchInput").value = btn.textContent;
        box.classList.add("hidden");
        doSearch();
      }));
  }, 200);
});

document.addEventListener("click", (e) => {
  const box = $("suggestBox");
  if (!box || box.classList.contains("hidden")) return;
  if (!box.contains(e.target) && e.target !== $("searchInput")) {
    box.classList.add("hidden");
  }
});

$("searchInput").addEventListener("input", () => {
  // restore the centered hero when the box is cleared
  if (!$("searchInput").value.trim() && !$("searchResults").children.length) {
    $("searchHero").classList.remove("compact");
    $("browseHead").classList.add("hidden");
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------------------------------------------------------- manga */

async function openManga(url, sourceId) {
  $("railManga").disabled = false;
  showView("manga");
  $("mangaLoading").classList.remove("hidden");
  $("mangaLayout").classList.add("hidden");

  const res = await callApi("get_manga", url, sourceId || null);
  $("mangaLoading").classList.add("hidden");

  // callApi returns null when the bridge is missing or the call rejected.
  if (!res) {
    toast("Could not load that manga");
    showView("search");
    return;
  }
  if (!res.ok) {
    toast("Failed to load manga: " + res.error);
    showView("search");
    return;
  }

  state.manga = res;
  state.source = res.source || sourceId || null;
  state.downloaded = new Set(res.downloaded || []);
  // preselect only chapters that are NOT downloaded yet; if all downloaded, select all
  const fresh = res.chapters
    .map((c, i) => (state.downloaded.has(c.name) ? -1 : i))
    .filter((i) => i >= 0);
  state.selected = new Set(fresh.length ? fresh : res.chapters.map((_, i) => i));

  $("mangaTitle").textContent = res.info.title;

  // provider note, directly beneath the title
  const srcId = res.source || res.info.source || "";
  const srcName = res.source_name || res.info.source_name || srcId;
  const note = $("mangaSourceNote");
  if (srcName) {
    $("mangaSourceName").textContent = srcName;
    $("mangaSourceDot").dataset.source = srcId;
    const link = $("mangaSourceLink");
    link.href = res.info.url || "#";
    link.onclick = (e) => {
      e.preventDefault();
      if (api().open_url) api().open_url(res.info.url);
    };
    note.style.display = "";
  } else {
    note.style.display = "none";
  }
  const cover = $("mangaCover");
  cover.style.display = "";
  cover.className = "";
  // replace the node so previous listeners do not stack across opens
  const freshCover = cover.cloneNode(false);
  cover.parentNode.replaceChild(freshCover, cover);
  freshCover.addEventListener("error", () => { freshCover.style.display = "none"; });
  attachCover(freshCover, null, res.info);
  if (!res.info.cover) freshCover.style.display = "none";
  $("mangaDesc").textContent = res.info.description || "";
  $("mangaAuthors").textContent = (res.info.authors || []).join(", ");
  renderAdvancedInfo(res.info);
  setBookmarkIcon(!!res.bookmarked);
  setWatchIcon(!!res.watched);

  const chips = $("mangaTags");
  chips.innerHTML = "";
  if (res.source_name || res.source) {
    const src = document.createElement("span");
    src.className = "chip source";
    src.dataset.source = res.source || "";
    src.textContent = res.source_name || res.source;
    chips.appendChild(src);
  }
  if (res.info.status) {
    const s = document.createElement("span");
    s.className = "chip status";
    s.textContent = res.info.status;
    chips.appendChild(s);
  }
  (res.info.tags || []).forEach((t) => {
    const c = document.createElement("span");
    c.className = "chip";
    c.textContent = t;
    chips.appendChild(c);
  });

  renderChapterList();
  updateDownloadButton();
  $("mangaLayout").classList.remove("hidden");
}

/* Extra metadata, shown only when Advanced info is enabled in Settings.
   Every field is optional: sources report wildly different amounts, so a
   row is omitted rather than printed empty. */
function renderAdvancedInfo(info) {
  const box = $("mangaAdvanced");
  if (!box) return;
  if (!state.settings || !state.settings.advanced_info) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  const started = info.year || info.start_date || info.started;
  const ended = info.end_date || info.ended ||
    (String(info.status || "").toLowerCase() === "completed" ? info.last_year : null);

  const rows = [
    ["Status", info.status],
    ["Type", info.series_type || info.type],
    ["First released", started],
    ["Ended", ended],
    ["Original language", info.original_language],
    ["Demographic", info.demographic],
    ["Last chapter", info.last_chapter],
    ["Volumes", info.last_volume],
    ["Authors", (info.authors || []).join(", ")],
    ["Artists", (info.artists || []).join(", ")],
    ["Rating", info.content_rating],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");

  if (!rows.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = rows.map(([label, value]) => `
    <div class="adv-row">
      <span class="adv-key">${escapeHtml(label)}</span>
      <span class="adv-val">${escapeHtml(String(value))}</span>
    </div>`).join("");
}

function setBookmarkIcon(on) {
  $("bookmarkBtn").classList.toggle("on", on);
  $("bookmarkIcon").textContent = on ? "bookmark" : "bookmark_add";
}

$("bookmarkBtn").addEventListener("click", async () => {
  if (!state.manga) return;

  // Removing never asks anything. Adding offers a folder, but only when
  // folders exist -- otherwise the prompt is pure friction.
  const already = $("bookmarkBtn").classList.contains("on");
  if (already) {
    const res = await callApi("toggle_bookmark", state.manga.info);
    if (res.ok) { setBookmarkIcon(res.bookmarked); toast("Bookmark removed"); }
    return;
  }

  const listing = await callApi("get_bookmark_folders");
  const hasFolders = listing && (listing.folders || []).length > 0;

  let folderId = "";
  if (hasFolders) {
    folderId = await pickFolder("Save bookmark to");
    if (folderId === null) return;          // dismissed, do nothing
  }

  const res = await callApi("bookmark_into", state.manga.info, folderId);
  if (res && res.ok) {
    setBookmarkIcon(res.bookmarked);
    toast(folderId ? "Bookmarked to folder" : "Bookmarked");
  }
});

function setWatchIcon(on) {
  $("watchBtn").classList.toggle("on", on);
  $("watchIcon").textContent = on ? "notifications_active" : "notifications_none";
  $("watchBtn").title = on ? "Stop watching" : "Watch for new chapters";
}

$("watchBtn").addEventListener("click", async () => {
  if (!state.manga) return;
  const info = state.manga.info;
  const watching = $("watchBtn").classList.contains("on");
  if (watching) {
    await callApi("unwatch", info.url);
    setWatchIcon(false);
    toast("Stopped watching");
  } else {
    await callApi("watch", info.url, info.title,
                  (state.manga.chapters || []).length,
                  state.source || info.source, info.cover);
    setWatchIcon(true);
    toast("Watching for new chapters");
  }
  loadUpdates();
});

/* Read the min/max, name filter and sort controls. Filtering only changes
   what is *shown*: selections are keyed by the chapter's real index, so
   hiding a row never silently drops it from an existing selection. */
function chapterFilters() {
  const num = (id) => {
    const raw = ($(id) && $(id).value || "").trim();
    if (!raw) return null;
    const v = parseFloat(raw);
    return Number.isFinite(v) ? v : null;
  };
  return {
    min: num("chMin"),
    max: num("chMax"),
    text: (($("chSearch") && $("chSearch").value) || "").trim().toLowerCase(),
    sort: ($("chSort") && $("chSort").value) || "desc",
    hideDl: !!($("chHideDl") && $("chHideDl").checked),
  };
}

function chapterMatches(chapter, index, f) {
  const n = chapterNumber(chapter.name);
  if (f.min !== null && n < f.min) return false;
  if (f.max !== null && n > f.max) return false;
  if (f.text && !chapter.name.toLowerCase().includes(f.text)) return false;
  if (f.hideDl && state.downloaded.has(chapter.name)) return false;
  return true;
}

/* Indices of the chapters currently visible, in display order. */
function visibleChapterIndices() {
  const chapters = (state.manga && state.manga.chapters) || [];
  const f = chapterFilters();
  const idx = [];
  for (let i = 0; i < chapters.length; i++) {
    if (chapterMatches(chapters[i], i, f)) idx.push(i);
  }
  // chapters arrive oldest-first
  if (f.sort === "desc") idx.reverse();
  return idx;
}

function renderChapterList() {
  const list = $("chapterList");
  list.innerHTML = "";
  const chapters = state.manga.chapters;
  const shown = visibleChapterIndices();

  shown.forEach((i) => {
    const name = chapters[i].name;
    const isDl = state.downloaded.has(name);
    const item = document.createElement("div");
    item.className = "chapter-item"
      + (state.selected.has(i) ? " selected" : "")
      + (isDl ? " downloaded" : "");
    item.dataset.index = i;
    item.innerHTML = `
      <span class="cbx"></span><span>${escapeHtml(name)}</span>
      <span class="dl-mark"><span class="material-symbols-rounded">check_circle</span>downloaded</span>`;
    item.addEventListener("click", () => {
      if (state.selected.has(i)) state.selected.delete(i);
      else state.selected.add(i);
      item.classList.toggle("selected");
      updateDownloadButton();
    });
    list.appendChild(item);
  });

  const hidden = chapters.length - shown.length;
  if (hidden > 0) {
    const note = document.createElement("div");
    note.className = "chapter-hidden-note";
    note.textContent = `${hidden} chapter${hidden === 1 ? "" : "s"} hidden by filters`;
    list.appendChild(note);
  }

  $("chapterCount").textContent = shown.length === chapters.length
    ? chapters.length
    : `${shown.length} / ${chapters.length}`;

  const dlPill = $("downloadedCount");
  if (state.downloaded.size) {
    dlPill.textContent = `${state.downloaded.size} downloaded`;
    dlPill.classList.remove("hidden");
  } else {
    dlPill.classList.add("hidden");
  }
}

/* Re-render as the filters change. */
["chMin", "chMax", "chSearch", "chSort", "chHideDl"].forEach((id) => {
  const el = $(id);
  if (!el) return;
  const evt = el.tagName === "SELECT" || el.type === "checkbox" ? "change" : "input";
  el.addEventListener(evt, () => { if (state.manga) renderChapterList(); });
});

$("chFilterReset") && $("chFilterReset").addEventListener("click", () => {
  ["chMin", "chMax", "chSearch"].forEach((id) => { if ($(id)) $(id).value = ""; });
  if ($("chHideDl")) $("chHideDl").checked = false;
  if ($("chSort")) $("chSort").value = "desc";
  if (state.manga) renderChapterList();
});


function refreshChapterSelection() {
  document.querySelectorAll(".chapter-item").forEach((item) => {
    item.classList.toggle("selected", state.selected.has(Number(item.dataset.index)));
  });
  updateDownloadButton();
}

function updateDownloadButton() {
  const n = state.selected.size;
  const total = state.manga ? state.manga.chapters.length : 0;
  const label = $("downloadBtnLabel");
  if (n === 0) label.textContent = "Select chapters to download";
  else if (n === total) label.textContent = `Download all ${total} chapters`;
  else label.textContent = `Download ${n} chapter${n > 1 ? "s" : ""}`;
  // Downloading no longer disables the button: several manga can run at
  // once, and anything over the concurrency limit is queued rather than
  // rejected. Only an empty selection blocks it.
  $("downloadBtn").disabled = n === 0;
  const cart = $("addCartBtn");
  if (cart) cart.disabled = n === 0;
}

/* The bulk buttons act on what is *visible*. Selecting chapters you have
   filtered out would be a nasty surprise -- you would download rows you
   cannot see. With no filters active this is every chapter, unchanged. */
$("selectAllBtn").addEventListener("click", () => {
  const shown = visibleChapterIndices();
  state.selected = new Set(shown);
  refreshChapterSelection();
  const total = state.manga.chapters.length;
  if (shown.length !== total) {
    toast(`Selected ${shown.length} visible of ${total}`);
  }
});
$("selectNoneBtn").addEventListener("click", () => {
  state.selected = new Set();
  refreshChapterSelection();
});
$("selectNewBtn").addEventListener("click", () => {
  const chapters = state.manga.chapters;
  state.selected = new Set(
    visibleChapterIndices().filter((i) => !state.downloaded.has(chapters[i].name)));
  refreshChapterSelection();
  toast(`Selected ${state.selected.size} new chapter${state.selected.size !== 1 ? "s" : ""}`);
});
$("selectLatestBtn").addEventListener("click", () => {
  // highest-numbered visible chapter, not simply the last array entry
  const chapters = state.manga.chapters;
  const shown = visibleChapterIndices();
  if (!shown.length) return;
  const latest = shown.reduce((best, i) =>
    chapterNumber(chapters[i].name) > chapterNumber(chapters[best].name) ? i : best,
    shown[0]);
  state.selected = new Set([latest]);
  refreshChapterSelection();
});

function chapterNumber(name) {
  const m = /(\d+(?:\.\d+)?)/.exec(name);
  return m ? parseFloat(m[1]) : 0;
}

$("rangeApplyBtn").addEventListener("click", applyRange);
$("rangeInput").addEventListener("keydown", (e) => { if (e.key === "Enter") applyRange(); });

function applyRange() {
  const spec = $("rangeInput").value.trim();
  if (!spec) return;
  const chapters = state.manga.chapters;
  const selected = new Set();
  try {
    for (let part of spec.split(",")) {
      part = part.trim();
      if (!part) continue;
      if (part.includes("-")) {
        const [l, r] = part.split("-");
        const lo = l.trim() === "" ? -Infinity : parseFloat(l);
        const hi = r.trim() === "" ? Infinity : parseFloat(r);
        if (isNaN(lo) && isNaN(hi)) throw new Error(part);
        chapters.forEach((c, i) => {
          const n = chapterNumber(c.name);
          if (n >= Math.min(lo, hi) && n <= Math.max(lo, hi)) selected.add(i);
        });
      } else {
        const target = parseFloat(part);
        if (isNaN(target)) throw new Error(part);
        chapters.forEach((c, i) => { if (chapterNumber(c.name) === target) selected.add(i); });
      }
    }
  } catch (e) {
    toast("Invalid selection: " + e.message);
    return;
  }
  if (!selected.size) { toast("No chapters matched"); return; }
  state.selected = selected;
  refreshChapterSelection();
  toast(`Selected ${selected.size} chapter${selected.size > 1 ? "s" : ""}`);
}

/* ----------------------------------------------------- format / bundling */

function bindSegmented(id, onChange) {
  const seg = $(id);
  seg.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      seg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      onChange(btn.dataset.value);
    });
  });
}

function setSegmented(id, value) {
  $(id).querySelectorAll("button").forEach((b) =>
    b.classList.toggle("active", b.dataset.value === value));
}

bindSegmented("fmtSeg", (v) => {
  state.format = v;
  $("bundleGroup").style.display = v === "images" ? "none" : "";
});
bindSegmented("bundleSeg", (v) => {
  state.bundleMode = v;
  $("bundleNWrap").classList.toggle("hidden", v !== "n");
});

$("browseBtn").addEventListener("click", async () => {
  const folder = await api().choose_folder();
  if (!folder) return;
  $("outputDir").value = folder;
  if ($("setOutputDir")) $("setOutputDir").value = folder;
  // persist it, otherwise the choice is lost on restart
  await saveOutputDir(folder);
});

/* Write the download location straight to settings.json so it survives a
   restart. Previously picking a folder only filled the field in. */
async function saveOutputDir(folder) {
  folder = (folder || "").trim();
  if (!folder) return;
  const res = await callApi("set_settings", { output_dir: folder });
  if (res) {
    state.settings = res;
    toast("Download folder saved");
  }
}

$("outputDir") && $("outputDir").addEventListener("change", (e) =>
  saveOutputDir(e.target.value));

/* -------------------------------------------------------------- download */

function buildDownloadOptions() {
  const s = state.settings;
  const chapters = state.manga.chapters;
  const nums = [...state.selected]
    .map((i) => chapterNumber(chapters[i].name)).sort((a, b) => a - b);
  const selection = state.selected.size === chapters.length ? "all" : nums.join(",");

  let bundle = 0;
  if (state.bundleMode === "1") bundle = 1;
  else if (state.bundleMode === "n") bundle = Math.max(2, parseInt($("bundleN").value) || 10);

  return {
    url: state.manga.info.url,
    title: state.manga.info.title,
    cover: state.manga.info.cover || "",
    source: state.source || "",
    language: $("fLanguage") ? $("fLanguage").value : "en",
    selection,
    output_dir: $("outputDir").value.trim() || s.output_dir,
    format: state.format,
    bundle,
    chapter_workers: s.chapter_workers,
    image_workers: s.image_workers,
    delay: s.delay,
    retries: s.retries || 5,
    keep_images: s.keep_images || state.format === "images",
    name_single: s.name_single,
    name_chapter: s.name_chapter,
    name_range: s.name_range,
  };
}

/* Queue this manga and stay where you are -- the point of the cart is to
   line several up without waiting for each to finish. */
$("addCartBtn").addEventListener("click", async () => {
  if (!state.manga || state.selected.size === 0) return;
  const res = await api().add_to_cart(buildDownloadOptions());
  if (!res || !res.ok) { toast((res && res.error) || "Could not queue"); return; }
  state.downloading = true;
  $("railDot").classList.add("on");
  $("dlEmpty").classList.add("hidden");
  $("dlActive").classList.remove("hidden");
  $("stopBtn").classList.remove("hidden");
  toast(`Queued ${state.manga.info.title}`);
  renderCart();
});

$("downloadBtn").addEventListener("click", async () => {
  if (!state.manga || state.selected.size === 0) return;

  const s = state.settings;
  if (s.confirm_large !== false && state.selected.size >= (s.large_threshold || 100)) {
    const ok = await confirmModal(
      "Large download",
      `You are about to download ${state.selected.size} chapters. This may take a while and use significant bandwidth. Continue?`,
      "Download");
    if (!ok) return;
  }

  const res = await api().start_download(buildDownloadOptions());
  if (!res.ok) { toast(res.error); return; }

  if (res.queued) {
    toast(`Queued — ${res.position} waiting for a free slot`);
  }
  beginDownloadUI(state.manga.info.title, state.selected.size);
});

function beginDownloadUI(title, total) {
  const fresh = ![...jobs.values()].some((j) => !j.finished);
  state.downloading = true;
  $("railDot").classList.add("on");
  $("dlEmpty").classList.add("hidden");
  $("dlActive").classList.remove("hidden");
  $("dlTitle").textContent = title;
  $("dlStatus").textContent = "Starting…";
  // Only reset the aggregate counters when nothing else is running, so
  // starting a second manga does not wipe the first one's progress.
  if (fresh) {
    jobs.clear();
    state.totalChapters = total;
    state.doneChapters = 0;
    $("overallFill").style.width = "0%";
    $("overallText").textContent = total ? `0 / ${total}` : "…";
    $("dlLog").innerHTML = "";
    $("activeChapters").innerHTML = '<div class="none">Waiting…</div>';
  }
  $("stopBtn").classList.remove("hidden");
  $("openFolderBtn").classList.add("hidden");
  updateDownloadButton();
  renderCart();
  showView("downloads");
}

$("cartClearBtn") && $("cartClearBtn").addEventListener("click", async () => {
  const res = await api().clear_cart();
  renderCart();
  toast(res && res.removed ? `Removed ${res.removed} queued` : "Queue empty");
});

$("stopBtn").addEventListener("click", async () => {
  await api().stop_download();
  $("dlStatus").textContent = "Stopping…";
});

let lastOutputDir = null;
$("openFolderBtn").addEventListener("click", () => {
  if (lastOutputDir) api().open_folder(lastOutputDir);
});

/* ------------------------------------------------------- engine events */

const activeBars = new Map();
/* job id -> {title, total, done, status} for concurrent downloads */
const jobs = new Map();

/* Advanced logging.

   The queue log is a milestone log by default -- a chapter finished, a file
   was written, something failed. Advanced mode also records the per-page
   chatter (every chapter_progress tick, every retry), which is what you
   want when diagnosing a stall and noise the rest of the time.

   The cap scales with the mode: 200 lines is plenty of milestones, but at
   one line per page it is about four chapters of history, so verbose mode
   keeps more. */
const LOG_CAP = 200;
const LOG_CAP_ADVANCED = 2000;

function logAdvanced() {
  const box = $("logAdvanced");
  if (box) return box.checked;
  return !!(state.settings && state.settings.queue_log_advanced);
}

function logLine(cls, text, verbose) {
  // Verbose lines exist only in advanced mode.
  if (verbose && !logAdvanced()) return;
  const log = $("dlLog");
  if (!log) return;
  const t = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const line = document.createElement("div");
  line.className = "log-line " + cls + (verbose ? " verbose" : "");
  line.innerHTML = `<span class="t">${t}</span><span>${escapeHtml(text)}</span>`;
  log.prepend(line);
  const cap = logAdvanced() ? LOG_CAP_ADVANCED : LOG_CAP;
  while (log.children.length > cap) log.removeChild(log.lastChild);
}

/* Progress rows are keyed on job + chapter, never on the chapter name
   alone. Chapter names are not unique across manga: two series downloading
   at once both reporting "Chapter 01" shared a single row, so one series'
   progress visibly overwrote the other's. */
function barKey(event) {
  return `${event.job || "job"}\u0000${event.chapter}`;
}

function jobLabel(jobId) {
  const job = jobs.get(jobId);
  return job && job.title ? job.title : "";
}

function ensureBar(event) {
  const key = barKey(event);
  if (activeBars.has(key)) return activeBars.get(key);
  const wrap = $("activeChapters");
  const none = wrap.querySelector(".none");
  if (none) none.remove();
  const row = document.createElement("div");
  row.className = "ac-row";
  const owner = jobLabel(event.job) || event.job_title || "";
  // Only show the owning manga when more than one is running, so the
  // single-download case looks exactly as it always has.
  const tag = (owner && jobs.size > 1)
    ? `<span class="ac-job" title="${escapeHtml(owner)}">${escapeHtml(owner)}</span>`
    : "";
  row.innerHTML = `
    ${tag}
    <span class="ac-name" title="${escapeHtml(event.chapter)}">${escapeHtml(event.chapter)}</span>
    <div class="ac-bar"><div class="ac-fill"></div></div>
    <span class="ac-count">–</span>`;
  wrap.appendChild(row);
  activeBars.set(key, row);
  return row;
}

function removeBar(event) {
  const key = barKey(event);
  const row = activeBars.get(key);
  if (row) { row.remove(); activeBars.delete(key); }
  if (!activeBars.size) {
    $("activeChapters").innerHTML = state.downloading
      ? '<div class="none">Waiting…</div>'
      : '<div class="none">Idle</div>';
  }
}

/* Remove every row belonging to one job (used when it finishes). */
function removeJobBars(jobId) {
  const prefix = `${jobId}\u0000`;
  [...activeBars.keys()].forEach((key) => {
    if (key.startsWith(prefix)) {
      const row = activeBars.get(key);
      if (row) row.remove();
      activeBars.delete(key);
    }
  });
  if (!activeBars.size) {
    $("activeChapters").innerHTML = state.downloading
      ? '<div class="none">Waiting…</div>'
      : '<div class="none">Idle</div>';
  }
}

function trackChapter(job, name, done, total) {
  /* Which chapters of this job are in flight right now. Kept on the job so
     the queue tile can list them without inventing its own bookkeeping. */
  if (!job || !name) return;
  if (!job.chapters) job.chapters = [];
  const existing = job.chapters.find((c) => c.name === name);
  if (existing) {
    existing.done = done;
    existing.total = total || existing.total;
  } else {
    job.chapters.push({ name, done: done || 0, total: total || 0 });
  }
}

function untrackChapter(job, name) {
  if (!job || !job.chapters) return;
  job.chapters = job.chapters.filter((c) => c.name !== name);
}

function sameManga(a, b) {
  /* Compare by URL, ignoring a trailing slash and case. Titles are not
     unique enough -- two sources spell the same series differently. */
  const norm = (u) => String(u || "").trim().toLowerCase().replace(/\/+$/, "");
  return !!norm(a) && norm(a) === norm(b);
}

function markChapterDownloaded(name, jobUrl) {
  /* Only touch the page when the finished chapter belongs to the manga the
     user is actually looking at.

     Without this check, browsing to any book while a download ran made its
     "N downloaded" pill climb 1, 2, 3... in step with the *other* book's
     progress, and could highlight rows that were never downloaded. The event
     carries no manga of its own, so the job's URL is the only correct
     source of truth. */
  if (!state.manga) return;
  if (jobUrl !== undefined && !sameManga(jobUrl, state.manga.url)) return;

  state.downloaded.add(name);
  const item = [...document.querySelectorAll(".chapter-item")].find((el) => {
    const idx = Number(el.dataset.index);
    return state.manga.chapters[idx] && state.manga.chapters[idx].name === name;
  });
  if (item) item.classList.add("downloaded");
  const dlPill = $("downloadedCount");
  dlPill.textContent = `${state.downloaded.size} downloaded`;
  dlPill.classList.remove("hidden");
}

/* The Python side batches high-frequency progress events and delivers them
   through onEngineEvents(). DOM writes are deferred to one animation frame so
   a burst of updates repaints once instead of once per event. */
window.onEngineEvents = function (events) {
  if (!Array.isArray(events)) { events = [events]; }
  events.forEach((e) => { try { window.onEngineEvent(e); } catch (err) {} });
};

window.onEngineEvent = function (event) {
  /* Smart-cover events belong to the Tools tab, not to a download job, so
     they are handled before the job lookup below (which would register a
     phantom job for them). */
  if (typeof handleSmartEvent === "function" && handleSmartEvent(event)) {
    return;
  }

  /* Every event carries a job id so concurrent downloads never interfere.
     Aggregate counters are summed across jobs rather than overwritten. */
  const job = event.job ? (jobs.get(event.job) || registerJob(event.job, {})) : null;

  switch (event.type) {
    case "job_started":
      startCartPolling();
      registerJob(event.job, {
        title: event.title, url: event.url,
        cover: event.cover, source: event.source,
      });
      renderCart();
      break;
    case "status":
      if (job) job.status = event.message;
      $("dlStatus").textContent = summaryText();
      break;
    case "plan":
      if (job) {
        job.title = event.title || job.title;
        job.total = event.total;
        job.done = 0;
        job.directory = event.directory;
      }
      state.totalChapters = totalOf("total");
      lastOutputDir = event.directory;
      logLine("info", `${event.title || ""} → ${event.directory}`);
      refreshOverall();
      renderCart();
      break;
    case "chapter_start":
      ensureBar(event);
      trackChapter(job, event.chapter, 0, event.total || 0);
      logLine("info", prefixed(event, `Start ${event.chapter}`
        + (event.total ? ` (${event.total} pages)` : "")), true);
      break;
    case "chapter_progress": {
      const row = ensureBar(event);
      const pct = event.total ? Math.round((event.done / event.total) * 100) : 0;
      row.querySelector(".ac-fill").style.width = pct + "%";
      row.querySelector(".ac-count").textContent = `${event.done}/${event.total}`;
      trackChapter(job, event.chapter, event.done, event.total);
      logLine("info", prefixed(event,
        `${event.chapter} page ${event.done}/${event.total}`), true);
      break;
    }
    case "chapter_done":
      removeBar(event);
      if (job) { job.done = event.completed; job.total = event.total || job.total; }
      state.doneChapters = totalOf("done");
      refreshOverall();
      logLine("ok", prefixed(event, `${event.chapter} — ${event.pages} pages`));
      markChapterDownloaded(event.chapter, job ? job.url : undefined);
      untrackChapter(job, event.chapter);
      renderCart();
      break;
    case "chapter_failed":
      removeBar(event);
      untrackChapter(job, event.chapter);
      logLine("err", prefixed(event, `Failed: ${event.chapter}`));
      break;
    case "packaging":
      logLine("info", prefixed(event, `Packing ${event.file}`));
      break;
    case "packaged":
      logLine("ok", prefixed(event, `Created ${event.file.split(/[\\/]/).pop()}`));
      break;
    case "error":
      logLine("err", prefixed(event, event.message));
      toast(event.message);
      break;
    case "stopped":
      logLine("info", prefixed(event, "Stopped by user"));
      break;
    case "finished": {
      const r = event.result || {};
      if (job) {
        job.finished = true;
        job.ok = !!r.ok;
        job.result = r;
        if (r.title) job.title = r.title;
      }
      if (event.job) removeJobBars(event.job);

      if (r.ok) {
        lastOutputDir = r.directory || lastOutputDir;
        $("openFolderBtn").classList.remove("hidden");
        logLine("ok", prefixed(event, `Complete — ${r.downloaded} chapters`));
      } else if (r.stopped) {
        logLine("info", prefixed(event, "Stopped"));
      } else {
        logLine("err", prefixed(event, "Failed" + (r.error ? `: ${r.error}` : "")));
      }

      // The whole panel only goes idle once every job has finished.
      const running = [...jobs.values()].filter((j) => !j.finished);
      if (!running.length) {
        state.downloading = false;
        $("railDot").classList.remove("on");
        $("stopBtn").classList.add("hidden");
        activeBars.forEach((row) => row.remove());
        activeBars.clear();
        $("activeChapters").innerHTML = '<div class="none">Idle</div>';
        const okCount = [...jobs.values()].filter((j) => j.ok).length;
        $("dlStatus").textContent = okCount
          ? `Complete — ${okCount} manga downloaded`
          : "Finished";
        if (okCount) {
          toast("Download complete");
          if (state.settings.open_folder_when_done && lastOutputDir) {
            api().open_folder(lastOutputDir);
          }
        }
      } else {
        $("dlStatus").textContent = summaryText();
      }
      refreshOverall();
      renderCart();
      updateDownloadButton();
      break;
    }
  }
};

/* ------------------------------------------------------------------ cart */

function registerJob(id, info) {
  let job = jobs.get(id);
  if (!job) {
    job = { id, title: "", total: 0, done: 0, finished: false, ok: false };
    jobs.set(id, job);
  }
  Object.assign(job, info || {});
  return job;
}

function totalOf(field) {
  let sum = 0;
  jobs.forEach((j) => { sum += Number(j[field] || 0); });
  return sum;
}

function prefixed(event, text) {
  // Name the manga in the log only when more than one is running.
  const owner = jobLabel(event.job) || event.job_title || "";
  return (owner && jobs.size > 1) ? `[${owner}] ${text}` : text;
}

function summaryText() {
  const running = [...jobs.values()].filter((j) => !j.finished);
  if (!running.length) return "Finished";
  if (running.length === 1) {
    const j = running[0];
    return j.total ? `Downloading ${j.total} chapters` : "Preparing…";
  }
  return `Downloading ${running.length} manga`;
}

function refreshOverall() {
  const total = totalOf("total");
  const done = totalOf("done");
  const pct = total ? Math.round((done / total) * 100) : 0;
  $("overallFill").style.width = pct + "%";
  $("overallText").textContent = `${done} / ${total}`;
  const running = [...jobs.values()].filter((j) => !j.finished);
  $("dlTitle").textContent = running.length > 1
    ? `${running.length} downloads`
    : (running[0] || [...jobs.values()].pop() || {}).title || "–";
  refreshOverallRate();
}

/* Combined throughput and ETA across every running job, shown in the
   queue card header so the headline figure is next to the headline bar
   instead of only inside the tiles. */
function refreshOverallRate() {
  const el = $("dlRate");
  if (!el) return;
  let rate = 0, eta = null;
  Object.values(cartProgress || {}).forEach((p) => {
    rate += Number(p.bytes_per_second || 0);
    if (p.eta_seconds != null) {
      eta = Math.max(eta == null ? 0 : eta, Number(p.eta_seconds));
    }
  });
  const parts = [];
  if (rate > 0) parts.push(formatRate(rate));
  if (eta != null) parts.push(`ETA ${formatEta(eta)}`);
  el.textContent = parts.join("  ·  ");
}

/* --------------------------------------------------------------- queue

   Grouped by manga, one collapsible tile each. Collapsed by default: a long
   queue should read as a list of books, not a wall of chapters.

   Collapsed shows a rate sparkline and a chapter fraction pill; expanded adds
   the cover, source, ETA, totals and the chapters currently downloading. */

const cartOpen = new Set();      // series keys the user has expanded
let cartProgress = {};           // job id -> live progress snapshot

function mangaKey(row) {
  const url = String(row.url || "").trim().toLowerCase().replace(/\/+$/, "");
  return url || `title:${String(row.title || "").trim().toLowerCase()}`;
}

/* An inline SVG sparkline of the recent transfer rate. Drawn as a path so it
   scales with the tile and costs no images. */
function sparkline(history, width, height) {
  const values = (history || []).slice(-40);
  if (values.length < 2) {
    return `<svg class="q-sparkline" viewBox="0 0 ${width} ${height}"
                 preserveAspectRatio="none" aria-hidden="true"></svg>`;
  }
  const peak = Math.max(...values, 1);
  const step = width / (values.length - 1);
  const points = values.map((v, i) => {
    const x = (i * step).toFixed(1);
    const y = (height - (v / peak) * (height - 2) - 1).toFixed(1);
    return `${x},${y}`;
  });
  const line = `M${points.join(" L")}`;
  const area = `${line} L${width},${height} L0,${height} Z`;
  return `<svg class="q-sparkline" viewBox="0 0 ${width} ${height}"
               preserveAspectRatio="none" aria-hidden="true">
      <path class="spark-area" d="${area}"></path>
      <path class="spark-line" d="${line}"></path>
    </svg>`;
}

function cartRowsFromState(queued) {
  const rows = [];
  jobs.forEach((j) => {
    if (j.finished && j.ok) return;        // completed jobs leave the queue
    rows.push({
      id: j.id,
      title: j.title || j.url || j.id,
      status: j.finished
        ? (j.ok ? "done" : ((j.result || {}).stopped ? "stopped" : "failed"))
        : "running",
      done: j.done, total: j.total, url: j.url, cover: j.cover,
      source: j.source, chapters: j.chapters ? [...j.chapters] : [],
    });
  });
  (queued || []).forEach((q) => rows.push({
    title: q.title || q.url, status: "queued", url: q.url,
    selection: q.selection, cover: q.cover, source: q.source, chapters: [],
  }));
  return rows;
}

function groupCartRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = mangaKey(row);
    let group = groups.get(key);
    if (!group) {
      group = { key, title: row.title, cover: row.cover, url: row.url,
                source: row.source, items: [], done: 0, total: 0,
                running: false, statuses: new Set() };
      groups.set(key, group);
    }
    group.items.push(row);
    group.statuses.add(row.status);
    group.done += Number(row.done || 0);
    group.total += Number(row.total || 0);
    if (row.status === "running") group.running = true;
    if (!group.cover && row.cover) group.cover = row.cover;
    if (!group.source && row.source) group.source = row.source;
  });
  return [...groups.values()];
}

function groupProgress(group) {
  /* Sum the live metrics of every job in this group. */
  let rate = 0, eta = null, bytes = 0, history = [];
  group.items.forEach((item) => {
    const p = cartProgress[item.id];
    if (!p) return;
    rate += Number(p.bytes_per_second || 0);
    bytes += Number(p.bytes || 0);
    if (p.eta_seconds != null) eta = Math.max(eta == null ? 0 : eta, p.eta_seconds);
    if ((p.history || []).length > history.length) history = p.history;
  });
  return { rate, eta, bytes, history };
}

function formatRate(bytesPerSecond) {
  const v = Number(bytesPerSecond || 0);
  if (v <= 0) return "0 KB/s";
  if (v < 1024) return `${v.toFixed(0)} B/s`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(0)} KB/s`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB/s`;
}

function formatEta(seconds) {
  if (seconds == null) return "--";
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total}s`;
  if (total < 3600) return `${Math.floor(total / 60)}m ${String(total % 60).padStart(2, "0")}s`;
  return `${Math.floor(total / 3600)}h ${String(Math.floor((total % 3600) / 60)).padStart(2, "0")}m`;
}

function formatBytes(value) {
  const v = Number(value || 0);
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(0)} KB`;
  if (v < 1024 * 1024 * 1024) return `${(v / (1024 * 1024)).toFixed(1)} MB`;
  return `${(v / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function groupStatus(group) {
  if (group.running) return "running";
  if (group.statuses.has("failed")) return "failed";
  if (group.statuses.has("stopped")) return "stopped";
  if (group.statuses.has("queued")) return "queued";
  return "done";
}

function groupFraction(group, status) {
  if (group.total) return `${group.done}/${group.total}`;
  return status === "queued" ? "queued" : "starting";
}

function cartTileHtml(group) {
  const open = cartOpen.has(group.key);
  const live = groupProgress(group);
  const status = groupStatus(group);
  const fraction = groupFraction(group, status);
  const percent = group.total
    ? Math.min(100, Math.round((group.done / group.total) * 100)) : 0;
  const starting = status === "running" && !group.total;

  const chapters = group.items.flatMap((i) => i.chapters || []);
  const cover = (cls, iconSize) => group.cover
    ? `<img class="${cls}" src="${escapeHtml(group.cover)}" alt="" loading="lazy">`
    : `<div class="${cls} ${cls}-blank"><span class="material-symbols-rounded">book</span></div>`;

  /* The collapsed row carries a small cover too. A queue of six books that
     differ only by a line of text is much harder to scan than one with
     artwork, and the thumbnail costs nothing -- it is the same image the
     expanded tile shows, at 30px. */
  const subParts = [];
  if (group.source) subParts.push(group.source);
  if (status === "running" && live.eta != null) subParts.push(`ETA ${formatEta(live.eta)}`);
  else if (status !== "running") subParts.push(status);

  return `
  <div class="q-tile ${open ? "open" : ""} ${status} ${starting ? "starting" : ""}"
       data-key="${escapeHtml(group.key)}">
    <button class="q-head" data-toggle="${escapeHtml(group.key)}"
            aria-expanded="${open}">
      <span class="material-symbols-rounded q-chev">chevron_right</span>
      ${cover("q-thumb")}
      <span class="q-headings">
        <span class="q-name" title="${escapeHtml(group.title)}">${escapeHtml(group.title)}</span>
        <span class="q-sub">${escapeHtml(subParts.join(" · "))}</span>
      </span>
      ${group.running ? `<span class="q-spark">${sparkline(live.history, 84, 24)}</span>
        <span class="q-rate">${escapeHtml(formatRate(live.rate))}</span>` : ""}
      <span class="q-pill ${status}">${escapeHtml(fraction)}</span>
    </button>
    <div class="q-body">
      <div class="q-body-inner">
        ${cover("q-cover")}
        <div class="q-detail">
          <div class="q-meta">
            ${group.source ? `<span class="q-chip src">${escapeHtml(group.source)}</span>` : ""}
            <span class="q-chip">${escapeHtml(status)}</span>
            ${group.total ? `<span class="q-chip">${percent}%</span>` : ""}
            ${group.items.length > 1
              ? `<span class="q-chip">${group.items.length} jobs</span>` : ""}
          </div>
          <div class="q-stats">
            <div><span class="q-k">Speed</span><span class="q-v">${escapeHtml(formatRate(live.rate))}</span></div>
            <div><span class="q-k">ETA</span><span class="q-v">${escapeHtml(formatEta(live.eta))}</span></div>
            <div><span class="q-k">Downloaded</span><span class="q-v">${escapeHtml(formatBytes(live.bytes))}</span></div>
            <div><span class="q-k">Chapters</span><span class="q-v">${escapeHtml(fraction)}</span></div>
          </div>
          ${group.total ? `<div class="q-bar"><i style="width:${percent}%"></i></div>` : ""}
          ${chapters.length
            ? `<div class="q-now"><span class="q-k">Downloading now</span>
                 <div class="q-now-list">${chapters.map(chapterRowHtml).join("")}</div>
               </div>`
            : ""}
          ${group.url && status === "queued"
            ? `<div class="q-actions">
                 <button class="btn btn-tonal btn-sm cart-x" data-url="${escapeHtml(group.url)}"
                         data-sel="${escapeHtml((group.items[0] || {}).selection || "all")}">
                   <span class="material-symbols-rounded">close</span> Remove</button>
               </div>`
            : ""}
        </div>
      </div>
    </div>
  </div>`;
}

/* One in-flight chapter. Rendered here rather than in a separate panel:
   the old "Active chapters" card under the queue listed exactly the same
   rows, so every downloading chapter appeared twice on the same screen. */
function chapterRowHtml(chapter) {
  const pct = chapter.total
    ? Math.min(100, Math.round((chapter.done / chapter.total) * 100)) : 0;
  const count = chapter.total ? `${chapter.done}/${chapter.total}` : "–";
  return `<div class="q-chapter" data-chapter="${escapeHtml(chapter.name)}">
      <i style="width:${pct}%"></i>
      <span class="q-ch-name">${escapeHtml(chapter.name)}</span>
      <span class="q-ch-count">${escapeHtml(count)}</span>
    </div>`;
}

async function renderCart() {
  const list = $("cartList");
  if (!list) return;
  let queued = [];
  try {
    const res = await api().get_cart();
    if (res && res.ok) queued = res.queued || [];
  } catch (e) { /* bridge not ready */ }

  const rows = cartRowsFromState(queued);
  const groups = groupCartRows(rows);

  /* The card is shown whenever there is ANY row. It used to require two
     rows or a queued item, so a single download -- the common case --
     rendered no tile at all and the tab showed only the floating summary
     card, which is half of why the queue looked disconnected. */
  const worthShowing = rows.length > 0;
  $("cartCount").textContent = groups.length;
  $("cartCard").classList.toggle("hidden", !worthShowing);
  $("dlEmpty").classList.toggle("hidden", worthShowing || state.downloading);
  if (!worthShowing) { list.innerHTML = ""; return; }

  list.innerHTML = groups.map(cartTileHtml).join("");
  list.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.toggle;
      if (cartOpen.has(key)) cartOpen.delete(key); else cartOpen.add(key);
      const tile = btn.closest(".q-tile");
      tile.classList.toggle("open");
      btn.setAttribute("aria-expanded", cartOpen.has(key));
    });
  });
  list.querySelectorAll(".cart-x").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.stopPropagation();
      await api().remove_from_cart(btn.dataset.url, btn.dataset.sel);
      renderCart();
      toast("Removed from queue");
    });
  });
}

/* Poll live throughput while anything is running. 1s is frequent enough for
   a readable sparkline and cheap enough not to matter: the Python side just
   reads counters. The timer stops itself when nothing is downloading. */
let cartPollTimer = null;

function startCartPolling() {
  if (cartPollTimer) return;
  cartPollTimer = setInterval(async () => {
    const res = await callApi("get_progress");
    if (!res || !res.ok) return;
    cartProgress = {};
    (res.jobs || []).forEach((j) => { cartProgress[j.job_id] = j; });
    refreshCartLive();
    refreshOverallRate();
    if (!res.active) stopCartPolling();
  }, 1000);
}

function stopCartPolling() {
  if (!cartPollTimer) return;
  clearInterval(cartPollTimer);
  cartPollTimer = null;
  cartProgress = {};
  refreshCartLive();
  refreshOverallRate();
}

/* Repaint only what changes while downloading, so an open tile is not
   rebuilt from scratch (which would collapse it mid-interaction). */
function refreshCartLive() {
  const list = $("cartList");
  if (!list || !list.children.length) return;
  const groups = groupCartRows(cartRowsFromState([]));
  groups.forEach((group) => {
    const tile = list.querySelector(`.q-tile[data-key="${CSS.escape(group.key)}"]`);
    if (!tile) return;
    const live = groupProgress(group);
    const status = groupStatus(group);
    const fraction = groupFraction(group, status);

    const pill = tile.querySelector(".q-pill");
    if (pill && pill.textContent !== fraction) {
      pill.textContent = fraction;
      pill.classList.remove("bump");
      void pill.offsetWidth;               // restart the animation
      pill.classList.add("bump");
    }
    const rate = tile.querySelector(".q-rate");
    if (rate) rate.textContent = formatRate(live.rate);
    const spark = tile.querySelector(".q-spark");
    if (spark) spark.innerHTML = sparkline(live.history, 84, 24);
    tile.classList.toggle("starting", status === "running" && !group.total);

    // The collapsed subtitle carries the live ETA, so a closed tile still
    // answers "how much longer" without being expanded.
    const sub = tile.querySelector(".q-sub");
    if (sub) {
      const parts = [];
      if (group.source) parts.push(group.source);
      if (status === "running" && live.eta != null) parts.push(`ETA ${formatEta(live.eta)}`);
      else if (status !== "running") parts.push(status);
      const text = parts.join(" \u00b7 ");
      if (sub.textContent !== text) sub.textContent = text;
    }

    if (tile.classList.contains("open")) {
      const values = tile.querySelectorAll(".q-stats .q-v");
      if (values.length >= 4) {
        values[0].textContent = formatRate(live.rate);
        values[1].textContent = formatEta(live.eta);
        values[2].textContent = formatBytes(live.bytes);
        values[3].textContent = fraction;
      }
      const bar = tile.querySelector(".q-bar i");
      if (bar && group.total) {
        bar.style.width = `${Math.min(100, Math.round((group.done / group.total) * 100))}%`;
      }
      refreshChapterRows(tile, group);
    }
  });
}

/* Update the in-flight chapter rows of one open tile in place.

   Rebuilding this list from innerHTML on every 1s poll restarted each row's
   entry animation and made the whole block flicker. Rows are matched by
   chapter name: existing ones are updated, new ones appended, finished ones
   removed. */
function refreshChapterRows(tile, group) {
  const holder = tile.querySelector(".q-now-list");
  const chapters = group.items.flatMap((i) => i.chapters || []);
  if (!holder) {
    // The tile had no chapters when it was drawn; a full repaint adds the
    // section. Cheap, and only happens on the first chapter of a job.
    if (chapters.length) renderCart();
    return;
  }
  const seen = new Set();
  chapters.forEach((chapter) => {
    seen.add(chapter.name);
    let row = holder.querySelector(
      `.q-chapter[data-chapter="${CSS.escape(chapter.name)}"]`);
    if (!row) {
      holder.insertAdjacentHTML("beforeend", chapterRowHtml(chapter));
      return;
    }
    const pct = chapter.total
      ? Math.min(100, Math.round((chapter.done / chapter.total) * 100)) : 0;
    const fill = row.querySelector("i");
    if (fill) fill.style.width = `${pct}%`;
    const count = row.querySelector(".q-ch-count");
    const text = chapter.total ? `${chapter.done}/${chapter.total}` : "\u2013";
    if (count && count.textContent !== text) count.textContent = text;
  });
  holder.querySelectorAll(".q-chapter").forEach((row) => {
    if (!seen.has(row.dataset.chapter)) row.remove();
  });
}

/* -------------------------------------------------------------- bookmarks */

/* ------------------------------------------------------ bookmark folders */

let folderState = { folders: [], unfiled: [], open: null, unlocked: new Set() };

async function loadBookmarks() {
  const res = await callApi("get_bookmark_folders");
  folderState.folders = (res && res.folders) || [];
  folderState.unfiled = (res && res.unfiled) || [];

  const total = folderState.unfiled.length +
    folderState.folders.reduce((n, f) => n + f.count, 0);
  $("bmEmpty").classList.toggle("hidden", total > 0);

  if (folderState.open) {
    const still = folderState.folders.find((f) => f.id === folderState.open);
    if (still) return renderFolderContents(still);
    folderState.open = null;      // it was deleted while open
  }

  $("folderOpen").classList.add("hidden");
  $("bmGrid").classList.remove("hidden");
  $("folderGrid").classList.remove("hidden");
  renderFolderGrid();
  renderBookmarkCards($("bmGrid"), folderState.unfiled);
}

/* One card per bookmark. Cards are draggable so they can be dropped onto a
   folder tile, which is the quickest way to file something. */
function renderBookmarkCards(grid, items) {
  grid.innerHTML = "";
  items.forEach((b, i) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.style.setProperty("--i", Math.min(i, 17));
    card.draggable = true;
    card.dataset.url = b.url || "";
    card.innerHTML = `
      <img loading="lazy" decoding="async" alt="">
      <div class="rc-fallback">${escapeHtml(b.title)}</div>
      <div class="rc-title">${escapeHtml(b.title)}</div>
      <button class="icon-btn rc-remove" title="Remove bookmark">
        <span class="material-symbols-rounded">bookmark_remove</span>
      </button>`;
    // attachCover, not a raw src: proxied and sharded covers need it.
    const coverImg = card.querySelector("img");
    // An <img> is natively draggable, so starting the gesture on the cover
    // dragged the *picture* (text/uri-list + Files) instead of the card.
    coverImg.draggable = false;
    attachCover(coverImg, card, b);

    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", b.url || "");
      e.dataTransfer.effectAllowed = "move";
      card.classList.add("dragging");
      // Reveals the drop zones, which are otherwise invisible or absent.
      document.body.classList.add("dragging-bookmark");
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      document.body.classList.remove("dragging-bookmark");
    });

    card.addEventListener("click", () => openManga(b.url));
    card.querySelector(".rc-remove").addEventListener("click", async (e) => {
      e.stopPropagation();
      await api().toggle_bookmark(b);
      loadBookmarks();
      toast("Bookmark removed");
    });
    grid.appendChild(card);
  });
}

/* Attach drop behaviour to any tile.
   dragleave fires when the pointer crosses onto a *child*, so a naive
   handler flickers the highlight off mid-drag. Counting enter/leave pairs
   keeps it stable. */
function makeDropTarget(el, onDrop) {
  let depth = 0;
  el.addEventListener("dragenter", (e) => {
    e.preventDefault();
    depth += 1;
    el.classList.add("drop-target");
  });
  el.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  });
  el.addEventListener("dragleave", () => {
    depth = Math.max(0, depth - 1);
    if (!depth) el.classList.remove("drop-target");
  });
  el.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    depth = 0;
    el.classList.remove("drop-target");
    document.body.classList.remove("dragging-bookmark");
    const url = e.dataTransfer.getData("text/plain");
    if (!url) return;
    await onDrop(url);
  });
}

/* Without this the browser treats a missed drop as "open this link", which
   navigates the whole app away. */
["dragover", "drop"].forEach((type) =>
  document.addEventListener(type, (e) => {
    if (document.body.classList.contains("dragging-bookmark")) e.preventDefault();
  }));

function renderFolderGrid() {
  const grid = $("folderGrid");
  grid.innerHTML = "";
  grid.classList.toggle("hidden", folderState.folders.length === 0);

  folderState.folders.forEach((f) => {
    const tile = document.createElement("div");
    const hidden = f.blurred && !folderState.unlocked.has(f.id);
    tile.className = "folder-tile" + (hidden ? " blurred" : "");
    tile.dataset.folder = f.id;
    tile.innerHTML = `
      <div class="ft-cover">
        ${f.cover ? '<img loading="lazy" decoding="async" alt="">'
                  : '<span class="material-symbols-rounded ft-ph">folder</span>'}
        ${f.locked ? '<span class="material-symbols-rounded ft-lock">lock</span>' : ""}
      </div>
      <div class="ft-name">${escapeHtml(f.name)}</div>
      <div class="ft-count">${f.count} item${f.count === 1 ? "" : "s"}</div>`;

    // The folder's cover is simply the first bookmark added to it.
    const img = tile.querySelector("img");
    if (img) attachCover(img, null, { cover: f.cover, cover_mirrors: f.cover_mirrors,
                                      source: f.cover_source });

    makeDropTarget(tile, async (url) => {
      await callApi("move_bookmark", url, f.id);
      toast(`Moved to ${f.name}`);
      loadBookmarks();
    });

    tile.addEventListener("click", () => openFolder(f));
    grid.appendChild(tile);
  });

  // A bookmark filed into a folder had nowhere to go back to, and with no
  // folders yet there was no drop target on screen at all -- so dragging
  // simply did nothing. Both cases now have a real zone.
  const root = $("rootDropZone");
  if (root && !root.dataset.wired) {
    root.dataset.wired = "1";
    makeDropTarget(root, async (url) => {
      await callApi("move_bookmark", url, "");
      toast("Moved to All bookmarks");
      loadBookmarks();
    });
  }
  const maker = $("newFolderDropZone");
  if (maker && !maker.dataset.wired) {
    maker.dataset.wired = "1";
    makeDropTarget(maker, async (url) => {
      const name = await promptModal("New folder", "Folder name");
      if (!name) return;
      const res = await callApi("create_bookmark_folder", name, {});
      if (!res || !res.ok) { toast((res && res.error) || "Could not create"); return; }
      await callApi("move_bookmark", url, res.folder.id);
      toast(`Moved to ${name}`);
      loadBookmarks();
    });
  }
}

async function openFolder(folder) {
  // A locked folder asks for the app passcode before revealing anything.
  if (folder.locked && !folderState.unlocked.has(folder.id)) {
    const ok = await confirmModal(
      "Locked folder",
      `"${folder.name}" is locked. Unlock it for this session?`, "Unlock");
    if (!ok) return;
    folderState.unlocked.add(folder.id);
  }
  folderState.open = folder.id;
  renderFolderContents(folder);
}

function renderFolderContents(folder) {
  folderState.open = folder.id;
  $("folderGrid").classList.add("hidden");
  $("bmGrid").classList.add("hidden");
  $("folderOpen").classList.remove("hidden");
  $("folderOpenName").textContent = folder.name;
  $("folderOpenCount").textContent =
    `${folder.count} item${folder.count === 1 ? "" : "s"}`;
  $("folderLockBtn").querySelector("span").textContent =
    folder.locked ? "lock" : "lock_open";
  $("folderItems").classList.toggle(
    "blur-covers", !!folder.blurred && !folderState.unlocked.has(folder.id));
  renderBookmarkCards($("folderItems"), folder.items || []);
}

$("folderBackBtn") && $("folderBackBtn").addEventListener("click", () => {
  folderState.open = null;
  loadBookmarks();
});

$("newFolderBtn") && $("newFolderBtn").addEventListener("click", async () => {
  const name = await promptModal("New folder", "Folder name");
  if (!name) return;
  const res = await callApi("create_bookmark_folder", name, {});
  if (res && res.ok) { toast(`Created ${name}`); loadBookmarks(); }
  else toast((res && res.error) || "Could not create folder");
});

function currentFolder() {
  return folderState.folders.find((f) => f.id === folderState.open);
}

$("folderRenameBtn") && $("folderRenameBtn").addEventListener("click", async () => {
  const f = currentFolder();
  if (!f) return;
  const name = await promptModal("Rename folder", "Folder name", f.name);
  if (!name) return;
  await callApi("update_bookmark_folder", f.id, { name });
  loadBookmarks();
});

$("folderLockBtn") && $("folderLockBtn").addEventListener("click", async () => {
  const f = currentFolder();
  if (!f) return;
  await callApi("update_bookmark_folder", f.id, { locked: !f.locked });
  toast(f.locked ? "Folder unlocked" : "Folder locked");
  loadBookmarks();
});

$("folderBlurBtn") && $("folderBlurBtn").addEventListener("click", async () => {
  const f = currentFolder();
  if (!f) return;
  await callApi("update_bookmark_folder", f.id, { blurred: !f.blurred });
  loadBookmarks();
});

$("folderDeleteBtn") && $("folderDeleteBtn").addEventListener("click", async () => {
  const f = currentFolder();
  if (!f) return;
  const ok = await confirmModal(
    "Delete folder",
    `Delete "${f.name}"? Its ${f.count} bookmark(s) move back to All bookmarks.`,
    "Delete");
  if (!ok) return;
  await callApi("delete_bookmark_folder", f.id, false);
  folderState.open = null;
  loadBookmarks();
  toast("Folder deleted");
});

/* --------------------------------------------------------- folder picker */

let folderPickResolve = null;

function pickFolder(title) {
  return new Promise(async (resolve) => {
    folderPickResolve = resolve;
    const res = await callApi("get_bookmark_folders");
    const folders = (res && res.folders) || [];
    $("fpTitle").textContent = title || "Save bookmark to";
    const list = $("fpList");
    list.innerHTML = folders.length
      ? folders.map((f) => `
          <button class="fp-item" data-id="${escapeHtml(f.id)}">
            <span class="material-symbols-rounded">${f.locked ? "lock" : "folder"}</span>
            <span class="fp-name">${escapeHtml(f.name)}</span>
            <span class="fp-count">${f.count}</span>
          </button>`).join("")
      : '<p class="hint fp-empty">No folders yet — create one below.</p>';
    list.querySelectorAll(".fp-item").forEach((btn) =>
      btn.addEventListener("click", () => closeFolderPicker(btn.dataset.id)));
    $("folderPicker").classList.remove("hidden");
  });
}

function closeFolderPicker(value) {
  $("folderPicker").classList.add("hidden");
  if (folderPickResolve) { folderPickResolve(value); folderPickResolve = null; }
}

$("fpCancel") && $("fpCancel").addEventListener("click", () => closeFolderPicker(null));
$("fpRoot") && $("fpRoot").addEventListener("click", () => closeFolderPicker(""));
$("fpCreate") && $("fpCreate").addEventListener("click", async () => {
  const name = $("fpNewName").value.trim();
  if (!name) return;
  const res = await callApi("create_bookmark_folder", name, {});
  if (res && res.ok) { $("fpNewName").value = ""; closeFolderPicker(res.folder.id); }
  else toast((res && res.error) || "Could not create folder");
});
$("folderPicker") && $("folderPicker").addEventListener("click", (e) => {
  if (e.target.id === "folderPicker") closeFolderPicker(null);
});

/* ---------------------------------------------------------------- library */

async function loadLibrary() {
  const res = await api().get_library();
  const list = $("libList");
  list.innerHTML = "";
  const items = (res && res.items) || [];
  $("libPath").textContent = res.path || "";
  $("libEmpty").classList.toggle("hidden", items.length > 0);

  items.forEach((it, i) => {
    const item = document.createElement("div");
    item.className = "lib-item";
    item.style.animationDelay = `${i * 40}ms`;
    const coverHtml = it.cover
      ? `<img class="lib-cover" loading="lazy" decoding="async" alt="">`
      : `<div class="lib-cover ph"><span class="material-symbols-rounded">book</span></div>`;

    const parts = it.parts || [];
    const nParts = parts.length;
    item.innerHTML = `
      <div class="lib-row">
        ${coverHtml}
        <div class="lib-info">
          <div class="lib-title">${escapeHtml(it.title)}</div>
          <div class="lib-sub">
            <span><span class="material-symbols-rounded">library_books</span> ${it.chapter_count} chapters</span>
            <span><span class="material-symbols-rounded">image</span> ${it.pages} pages</span>
            ${it.last_download ? `<span><span class="material-symbols-rounded">schedule</span> ${escapeHtml(it.last_download)}</span>` : ""}
          </div>
        </div>
        <span class="lib-badge">${nParts ? nParts + " part" + (nParts > 1 ? "s" : "") : "images"}</span>
        <div class="lib-actions">
          ${nParts === 1 ? `<button class="icon-btn lib-read accent" title="Open in reader"><span class="material-symbols-rounded">auto_stories</span></button>` : ""}
          ${nParts > 1 ? `<button class="icon-btn lib-expand" title="Show parts"><span class="material-symbols-rounded">expand_more</span></button>` : ""}
          <button class="icon-btn lib-open" title="Open manga page"><span class="material-symbols-rounded">menu_book</span></button>
          <button class="icon-btn lib-folder" title="Open folder"><span class="material-symbols-rounded">folder_open</span></button>
          <button class="icon-btn lib-del" title="Remove from library"><span class="material-symbols-rounded">delete</span></button>
        </div>
      </div>
      ${nParts ? `<div class="lib-parts hidden">
        ${parts.map((p, pi) => `
          <div class="lib-part ${p.exists ? "" : "missing"}" data-pi="${pi}">
            <span class="material-symbols-rounded part-icon">${p.exists ? "book_2" : "error"}</span>
            <span class="part-name" title="${escapeHtml(p.path)}">${escapeHtml(p.name)}</span>
            <span class="part-size">${p.exists ? formatSize(p.size) : "missing"}</span>
            ${p.exists ? `<button class="btn btn-tonal btn-mini part-read"><span class="material-symbols-rounded">auto_stories</span> Read</button>` : ""}
          </div>`).join("")}
      </div>` : ""}`;

    const readBtn = item.querySelector(".lib-read");
    if (readBtn) readBtn.addEventListener("click", () => openInReader(parts[0].path));

    const expandBtn = item.querySelector(".lib-expand");
    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        const box = item.querySelector(".lib-parts");
        const open = !box.classList.contains("hidden");
        box.classList.toggle("hidden", open);
        expandBtn.querySelector(".material-symbols-rounded").textContent =
          open ? "expand_more" : "expand_less";
      });
    }
    item.querySelectorAll(".part-read").forEach((btn) => {
      const pi = Number(btn.closest(".lib-part").dataset.pi);
      btn.addEventListener("click", () => openInReader(parts[pi].path));
    });

    item.querySelector(".lib-open").addEventListener("click", () => openManga(it.url));
    item.querySelector(".lib-folder").addEventListener("click", async () => {
      const ok = await api().open_folder(it.directory);
      if (!ok) toast("Folder not found");
    });
    item.querySelector(".lib-del").addEventListener("click", async () => {
      const ok = await confirmModal("Remove entry",
        `Remove "${it.title}" from the library? Downloaded files are NOT deleted.`, "Remove");
      if (ok) {
        await api().remove_library_entry(it.url);
        loadLibrary();
        toast("Removed from library");
      }
    });
    // Same reason as bookmarks: a bare src cannot load a proxied or sharded
    // cover, so library rows were blank for those sources.
    const libImg = item.querySelector("img.lib-cover");
    if (libImg) attachCover(libImg, null, it);
    list.appendChild(item);
  });
}

function formatSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
  return bytes.toFixed(bytes >= 100 || i === 0 ? 0 : 1) + " " + units[i];
}

async function openInReader(path) {
  const res = await api().open_in_reader(path);
  if (!res.ok) toast(res.error || "Could not open reader");
}

/* -------------------------------------------------------------- settings */

function fillSettings(s) {
  $("setOutputDir").value = s.output_dir;
  $("outputDir").value = s.output_dir;
  setSegmented("setFmtSeg", s.format);
  setSegmented("fmtSeg", s.format);
  state.format = s.format;
  $("bundleGroup").style.display = s.format === "images" ? "none" : "";
  $("setKeepImages").checked = !!s.keep_images;
  $("setOpenWhenDone").checked = !!s.open_folder_when_done;
  $("setConfirmLarge").checked = s.confirm_large !== false;
  $("setLargeThreshold").value = s.large_threshold || 100;
  $("setMaxJobs").value = s.max_concurrent_jobs || 2;
  if ($("setColumns")) $("setColumns").value = s.columns || 0;
  if ($("setAdvanced")) $("setAdvanced").checked = !!s.advanced_info;
  $("setChapterWorkers").value = s.chapter_workers;
  $("setImageWorkers").value = s.image_workers;
  $("setDelay").value = s.delay;
  $("setRetries").value = s.retries || 5;
  $("setReaderPath").value = s.reader_path || "";
  $("setNameSingle").value = s.name_single || "{title} - Chapters {chapters}";
  $("setNameChapter").value = s.name_chapter || "{title} - Chapter {chapter}";
  $("setNameRange").value = s.name_range || "{title} - Chapters {chapters}";
  $("setAnimations").checked = s.animations !== false;
  $("setMatrix").checked = s.matrix !== false;
  if ($("setCorners")) $("setCorners").checked = (s.corners || "rounded") === "square";
  updateNamingPreview();
  applyAppearance(s);
}

function renderName(template, fallback, vars) {
  try {
    let out = template;
    for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(v);
    if (/\{\w+\}/.test(out) || !out.trim()) throw new Error("unresolved");
    return out;
  } catch {
    let out = fallback;
    for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(v);
    return out;
  }
}

function updateNamingPreview() {
  const vars = { title: "One Piece", chapter: "023.5", start: "001", end: "010" };
  const single = renderName($("setNameSingle").value, "{title}", vars);
  const per = renderName($("setNameChapter").value, "{title} - Chapter {chapter}", vars);
  const range = renderName($("setNameRange").value, "{title} - Chapters {start}-{end}", vars);
  $("namingPreview").textContent = `${single}.cbz · ${per}.cbz · ${range}.cbz`;
}
["setNameSingle", "setNameChapter", "setNameRange"].forEach((id) =>
  $(id).addEventListener("input", updateNamingPreview));

bindSegmented("setFmtSeg", () => {});

document.querySelectorAll(".stepper").forEach((stepper) => {
  const input = $(stepper.dataset.target);
  const step = parseFloat(stepper.dataset.step || input.step || 1);
  const clamp = (v) => Math.min(parseFloat(input.max), Math.max(parseFloat(input.min), v));
  stepper.querySelector(".step-down").addEventListener("click", () => {
    input.value = clamp((parseFloat(input.value) || 0) - step);
  });
  stepper.querySelector(".step-up").addEventListener("click", () => {
    input.value = clamp((parseFloat(input.value) || 0) + step);
  });
});

$("setBrowseBtn").addEventListener("click", async () => {
  const folder = await api().choose_folder();
  if (folder) $("setOutputDir").value = folder;
});

$("setReaderBrowseBtn").addEventListener("click", async () => {
  const file = await api().choose_file();
  if (file) $("setReaderPath").value = file;
});

$("saveSettingsBtn").addEventListener("click", async () => {
  const fmt = document.querySelector("#setFmtSeg button.active");
  const updated = {
    output_dir: $("setOutputDir").value.trim(),
    format: fmt ? fmt.dataset.value : "cbz",
    keep_images: $("setKeepImages").checked,
    open_folder_when_done: $("setOpenWhenDone").checked,
    confirm_large: $("setConfirmLarge").checked,
    large_threshold: parseInt($("setLargeThreshold").value) || 100,
    max_concurrent_jobs: Math.max(1, Math.min(5,
      parseInt($("setMaxJobs").value) || 2)),
    columns: Math.max(0, Math.min(14, parseInt($("setColumns").value) || 0)),
    advanced_info: $("setAdvanced").checked,
    chapter_workers: parseInt($("setChapterWorkers").value) || 3,
    image_workers: parseInt($("setImageWorkers").value) || 6,
    delay: parseFloat($("setDelay").value) || 0.5,
    retries: parseInt($("setRetries").value) || 5,
    reader_path: $("setReaderPath").value.trim(),
    name_single: $("setNameSingle").value.trim() || "{title} - Chapters {chapters}",
    name_chapter: $("setNameChapter").value.trim() || "{title} - Chapter {chapter}",
    name_range: $("setNameRange").value.trim() || "{title} - Chapters {chapters}",
  };
  state.settings = await api().set_settings(updated);
  fillSettings(state.settings);
  const flash = $("savedFlash");
  flash.classList.remove("hidden");
  setTimeout(() => flash.classList.add("hidden"), 1800);
});

$("clearLibBtn").addEventListener("click", async () => {
  const ok = await confirmModal("Clear library",
    "Remove ALL entries from the library? Downloaded files are NOT deleted.", "Clear");
  if (ok) { await api().clear_library(); toast("Library cleared"); }
});
$("clearBmBtn").addEventListener("click", async () => {
  const ok = await confirmModal("Clear bookmarks", "Remove all bookmarks?", "Clear");
  if (ok) { await api().clear_bookmarks(); toast("Bookmarks cleared"); }
});

/* ------------------------------------------------------------------ logs */

async function refreshLogInfo() {
  const info = await api().get_log_info();
  if (info && info.ok) {
    $("logInfo").textContent = `${info.path}${info.exists ? " · " + formatSize(info.size) : " · empty"}`;
  }
}

$("exportLogBtn").addEventListener("click", async () => {
  const res = await api().export_log();
  if (res.ok) toast("Log exported to " + res.path);
  else if (!res.cancelled) toast(res.error || "Export failed");
});

$("clearLogBtn").addEventListener("click", async () => {
  const ok = await confirmModal("Clear log", "Delete the log file contents?", "Clear");
  if (ok) {
    const res = await api().clear_log();
    toast(res.ok ? "Log cleared" : res.error || "Failed");
    refreshLogInfo();
  }
});

/* --------------------------------------------------------- crash resume */

async function refreshTrayState() {
  const hint = $("trayHint");
  const box = $("setTray");
  if (!hint || !box || !api().get_tray_state) return;
  const res = await api().get_tray_state();
  if (!res || !res.ok) return;
  if (!res.available) {
    // Be explicit rather than letting the toggle silently do nothing:
    // pystray is optional and cannot start without a desktop tray.
    box.disabled = true;
    hint.textContent =
      "No system tray was detected here. Install the tray extra " +
      "(pip install mangadl[tray]) and run on a desktop session.";
  } else if (!res.running && res.enabled) {
    hint.textContent =
      "Enabled - restart MangaDL to start the tray icon.";
  }
}

async function checkPendingJob() {
  const res = await api().get_pending_job();
  if (!res || !res.ok || !res.pending) return;
  const p = res.pending;
  $("resumeInfo").textContent =
    `${p.title}${p.started ? " · started " + p.started : ""} — completed chapters will be skipped`;
  $("resumeBanner").classList.remove("hidden");
}

$("resumeYesBtn").addEventListener("click", async () => {
  $("resumeBanner").classList.add("hidden");
  const res = await api().resume_pending_job();
  if (!res.ok) { toast(res.error || "Could not resume"); return; }
  const pend = await api().get_pending_job();
  beginDownloadUI((pend && pend.pending && pend.pending.title) || "Resuming download", 0);
  toast("Resuming where you left off");
});

$("resumeNoBtn").addEventListener("click", async () => {
  $("resumeBanner").classList.add("hidden");
  await api().discard_pending_job();
});

/* ------------------------------------------------------------------ init */

/* Boot steps are isolated. Previously every step was an unguarded `await`,
   so a single failing bridge call (a Python exception on one endpoint) threw
   out of the whole handler and everything after it silently never ran --
   including the initial trending load, which is why search appeared dead. */
async function bootStep(label, fn) {
  try {
    return await fn();
  } catch (err) {
    console.warn("startup step failed:", label, err);
    bootFailures.push(label);
    return null;
  }
}

let bootFailures = [];

whenReady(async () => {
  // The passcode has to gate the app before anything else happens.
  // Previously the lock check ran seven steps into boot, so the library,
  // stats and trending feed were already fetched and painted underneath
  // the overlay before it appeared.
  await bootStep("lock", checkLock);
  if (document.body.classList.contains("locked")) {
    await waitForUnlock();
  }

  state.settings = (await bootStep("settings", () => api().get_settings())) || {};
  bootStep("fillSettings", () => fillSettings(state.settings));
  await bootStep("sources", loadSources);

  if (state.settings.default_source && $("fSource")) {
    const want = state.settings.default_source;
    if ([...$("fSource").options].some((o) => o.value === want)) {
      $("fSource").value = want;
      syncSourceUI();
      updateFilterDot();
    }
  }
  applyRailState(state.settings.rail_expanded === true);
  $("setDedupe").checked = state.settings.dedupe_results !== false;
  if ($("setTray")) $("setTray").checked = !!state.settings.minimize_to_tray;
  if ($("setTrayNotify")) $("setTrayNotify").checked = state.settings.tray_notifications !== false;
  if ($("setLogAdvanced")) $("setLogAdvanced").checked = !!state.settings.queue_log_advanced;
  if ($("logAdvanced")) $("logAdvanced").checked = !!state.settings.queue_log_advanced;
  if ($("setDownloadedResults")) {
    $("setDownloadedResults").value =
      state.settings.downloaded_results || "darken";
  }
  bootStep("trayState", refreshTrayState);
  bootStep("serverConfig", loadServerConfig);
  $("setInterleave").checked = !!state.settings.interleave_results;

  await bootStep("sourceConfig", loadSourceConfig);
  await bootStep("genres", loadGenres);
  await bootStep("security", loadSecurity);
  await bootStep("filters", loadFilters);
  await bootStep("stats", loadStats);
  resetIdleTimer();

  const lib = await bootStep("library", () => api().get_library());
  if (lib && lib.path) $("dataLibPath").textContent = lib.path;
  bootStep("logInfo", refreshLogInfo);
  bootStep("pendingJob", checkPendingJob);

  if (!document.body.classList.contains("locked")) $("searchInput").focus();

  if (bootFailures.length) {
    console.warn("startup completed with failures:", bootFailures);
  }
  // greet with a trending feed rather than a blank page
  doSearch(true);
});

/* ================================================================= lock */

let lockIdleTimer = null;

/* Resolves once the lock screen is dismissed, so boot can await it. */
let _unlockResolvers = [];
function waitForUnlock() {
  if (!document.body.classList.contains("locked")) return Promise.resolve();
  return new Promise((resolve) => _unlockResolvers.push(resolve));
}

function showLock(show) {
  $("lockOverlay").classList.toggle("hidden", !show);
  document.body.classList.toggle("locked", !!show);
  if (!show && _unlockResolvers.length) {
    const waiting = _unlockResolvers;
    _unlockResolvers = [];
    waiting.forEach((resolve) => resolve());
  }
  // nothing is visible behind the lock screen, so stop animating
  if (show) matrix.pause(); else matrix.resume();
  if (show) {
    $("lockError").textContent = "";
    $("lockInput").value = "";
    $("lockRecovery").classList.add("hidden");
    setTimeout(() => {
      const input = $("lockInput");
      if (input && !input.disabled) input.focus();
    }, 60);
  }
}

/* Remember whether a passcode was set, so the very first frame can decide
   whether to paint the overlay at all. Without this the app either flashes
   its contents before locking, or (if the bridge never answers) stays
   covered forever. */
const LOCK_HINT_KEY = "mangadl-lock-enabled";

function clearLockPending() {
  const overlay = $("lockOverlay");
  if (!overlay) return;
  overlay.classList.remove("lock-pending");
  // .lock-overlay is display:flex by default, so removing the pending class
  // is not enough -- it must be explicitly hidden unless we are locked.
  if (!document.body.classList.contains("locked")) {
    overlay.classList.add("hidden");
  }
}

(function primeLockOverlay() {
  // No passcode last time -> do not cover the UI while the bridge answers.
  try {
    if (localStorage.getItem(LOCK_HINT_KEY) !== "1") clearLockPending();
  } catch (e) {
    clearLockPending();
  }
  // Fail-safe: whatever happens -- no bridge, a crashed handler, a hung
  // call -- the app must never stay permanently covered.
  setTimeout(clearLockPending, 4000);
})();

async function checkLock() {
  const overlay = $("lockOverlay");
  // The overlay is painted on the very first frame via .lock-pending, so a
  // passcode-protected app is never briefly readable while the bridge
  // answers. Clearing that class is what reveals the UI underneath.
  const settle = (locked) => {
    overlay.classList.remove("lock-pending");
    showLock(locked);
  };

  if (!api() || !api().lock_status) { settle(false); return; }
  const st = await callApi("lock_status");
  try {
    localStorage.setItem(LOCK_HINT_KEY, st && st.enabled ? "1" : "0");
  } catch (e) { /* private mode: the timeout fail-safe still applies */ }
  if (!st || !st.enabled) { settle(false); return; }

  state.lock = st;
  $("lockSub").textContent = st.hint
    ? `Hint: ${st.hint}`
    : "Enter your passcode to continue";
  if (st.cooldown) {
    $("lockError").textContent = `Too many attempts - wait ${st.cooldown}s`;
  }
  settle(true);
}

let _cooldownTimer = null;

function lockCooldown(seconds) {
  clearInterval(_cooldownTimer);
  const btn = $("lockUnlockBtn");
  const label = $("lockBtnText");
  const input = $("lockInput");
  let left = Math.max(0, parseInt(seconds) || 0);
  if (!left) return;

  const tick = () => {
    if (left <= 0) {
      clearInterval(_cooldownTimer);
      btn.disabled = false;
      input.disabled = false;
      label.textContent = "Unlock";
      $("lockError").textContent = "";
      input.focus();
      return;
    }
    btn.disabled = true;
    input.disabled = true;
    label.textContent = `Locked out (${left}s)`;
    left -= 1;
  };
  tick();
  _cooldownTimer = setInterval(tick, 1000);
}

function showAttempts(left) {
  const el = $("lockAttempts");
  if (left == null) { el.classList.add("hidden"); return; }
  el.textContent = `${left} attempt${left === 1 ? "" : "s"} remaining`;
  el.classList.remove("hidden");
  el.classList.toggle("danger", left <= 1);
  el.classList.toggle("warn", left === 2);
}

async function attemptUnlock() {
  const input = $("lockInput");
  const code = input.value;
  if (!code || input.disabled) return;

  const btn = $("lockUnlockBtn");
  btn.disabled = true;
  $("lockBtnText").textContent = "Checking…";

  const res = await callApi("lock_verify", code);

  btn.disabled = false;
  $("lockBtnText").textContent = "Unlock";

  if (res && res.ok) {
    showAttempts(null);
    $("lockError").textContent = "";
    showLock(false);
    resetIdleTimer();
    toast("Unlocked");
    return;
  }

  // wrong: shake the panel so the failure is unmistakable
  const box = document.querySelector(".lock-box");
  box.classList.remove("shake");
  void box.offsetWidth;                 // restart the animation
  box.classList.add("shake");

  if (res && res.cooldown) {
    $("lockError").textContent = "Too many attempts";
    showAttempts(null);
    lockCooldown(res.cooldown);
  } else {
    $("lockError").textContent = (res && res.error) || "Incorrect passcode";
    if (res && res.attempts_left != null) showAttempts(res.attempts_left);
  }
  input.value = "";
  input.focus();
}

/* show/hide the passcode */
$("lockEyeBtn") && $("lockEyeBtn").addEventListener("click", () => {
  const input = $("lockInput");
  const showing = input.type === "text";
  input.type = showing ? "password" : "text";
  $("lockEyeIcon").textContent = showing ? "visibility" : "visibility_off";
  $("lockEyeBtn").title = showing ? "Show passcode" : "Hide passcode";
  input.focus();
});

$("lockUnlockBtn").addEventListener("click", attemptUnlock);
$("lockInput").addEventListener("keydown", (e) => { if (e.key === "Enter") attemptUnlock(); });

$("lockForgotBtn").addEventListener("click", () => {
  $("lockRecovery").classList.toggle("hidden");
});
$("recoverCancelBtn").addEventListener("click", () => {
  $("lockRecovery").classList.add("hidden");
});
$("recoverBtn").addEventListener("click", async () => {
  const res = await api().lock_recover($("recoveryKeyInput").value,
                                       $("recoveryNewInput").value);
  if (res.ok) { toast("Passcode reset"); showLock(false); resetIdleTimer(); }
  else $("lockError").textContent = res.error;
});

/* auto-lock on idle */
function resetIdleTimer() {
  clearTimeout(lockIdleTimer);
  const minutes = (state.lock && state.lock.auto_lock_minutes) || 0;
  if (!minutes) return;
  lockIdleTimer = setTimeout(() => checkLock(), minutes * 60 * 1000);
}
["mousemove", "keydown", "click", "wheel"].forEach((evt) =>
  window.addEventListener(evt, () => {
    if (!document.body.classList.contains("locked")) resetIdleTimer();
  }, { passive: true }));

/* ============================================== source ranking (drag) */

let rankOrder = [];

function renderSourceRanks(rows) {
  const list = $("sourceRankList");
  list.innerHTML = "";
  rankOrder = rows.map((r) => r.id);

  rows.forEach((row, index) => {
    const li = document.createElement("li");
    li.draggable = true;
    li.dataset.id = row.id;
    li.classList.toggle("disabled", !row.enabled);

    const caps = [];
    if (row.supports_language) caps.push("languages");
    if (row.supports_scanlator) caps.push("scanlators");
    if (row.needs_flaresolverr) caps.push("cloudflare");
    const adultCap = row.adult_only
      ? '<span class="cap adult">18+</span>' : "";

    li.innerHTML = `
      <span class="drag-handle material-symbols-rounded">drag_indicator</span>
      <span class="rank-num">${index + 1}</span>
      <span class="src-name">${escapeHtml(row.name)}
        <span class="src-host">${escapeHtml((row.base_url || "").replace(/^https?:\/\//, ""))}</span>
      </span>
      <span class="src-caps">${adultCap}${caps.map((c) => `<span class="cap">${c}</span>`).join("")}</span>
      <span class="move-btns">
        <button data-move="-1" title="Move up"><span class="material-symbols-rounded">expand_less</span></button>
        <button data-move="1" title="Move down"><span class="material-symbols-rounded">expand_more</span></button>
      </span>
      <label class="switch" title="Include this source">
        <input type="checkbox" ${row.enabled ? "checked" : ""}><span></span>
      </label>`;

    li.querySelector("input[type=checkbox]").addEventListener("change", async (e) => {
      const res = await api().toggle_source(row.id, e.target.checked);
      renderSourceRanks(res.sources);
      await loadSources();
      toast(`${row.name} ${e.target.checked ? "enabled" : "excluded"}`);
    });

    li.querySelectorAll("[data-move]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        const res = await api().move_source(row.id, parseInt(btn.dataset.move));
        renderSourceRanks(res.sources);
      }));

    li.addEventListener("dragstart", () => {
      li.classList.add("dragging");
      list.dataset.dragging = row.id;
    });
    li.addEventListener("dragend", async () => {
      li.classList.remove("dragging");
      [...list.children].forEach((c) => c.classList.remove("drag-over"));
      const order = [...list.children].map((c) => c.dataset.id);
      const res = await api().reorder_sources(order);
      renderSourceRanks(res.sources);
    });
    li.addEventListener("dragover", (e) => {
      e.preventDefault();
      const dragging = list.querySelector(".dragging");
      if (!dragging || dragging === li) return;
      li.classList.add("drag-over");
      const rect = li.getBoundingClientRect();
      const after = e.clientY > rect.top + rect.height / 2;
      list.insertBefore(dragging, after ? li.nextSibling : li);
    });
    li.addEventListener("dragleave", () => li.classList.remove("drag-over"));

    list.appendChild(li);
  });
}

async function loadSourceConfig() {
  if (!api() || !api().get_source_config) return;
  const res = await api().get_source_config();
  if (res.ok) renderSourceRanks(res.sources);
}

$("resetSourcesBtn").addEventListener("click", async () => {
  const res = await api().reset_source_config();
  renderSourceRanks(res.sources);
  await loadSources();
  toast("Source ranking reset");
});

/* ==================================================== settings wiring */

async function loadSecurity() {
  const st = await api().lock_status();
  state.lock = st;
  $("setLockEnabled").checked = st.enabled;
  $("lockStateHint").textContent = st.enabled
    ? `On${st.auto_lock_minutes ? ` · auto-locks after ${st.auto_lock_minutes} min` : ""}`
    : "Off";
  $("lockConfigRows").classList.toggle("hidden", !st.enabled);
  $("setAutoLock").value = st.auto_lock_minutes || 0;
  $("setLockOnStart").checked = st.lock_on_start;
  $("setBlurCovers").checked = st.blur_covers;
  $("setLockHint").value = st.hint || "";
}

$("setLockEnabled").addEventListener("change", async (e) => {
  if (e.target.checked) {
    const code = prompt("Choose a passcode (at least 4 characters):");
    if (!code) { e.target.checked = false; return; }
    const res = await api().lock_set(code, "", 0, true, true);
    if (!res.ok) { toast(res.error); e.target.checked = false; return; }
    alert("Save this recovery key somewhere safe.\n\nIt is shown only once and " +
          "is the only way back in if you forget your passcode:\n\n" + res.recovery_key);
  } else {
    const code = prompt("Enter your current passcode to turn the lock off:");
    if (!code) { e.target.checked = true; return; }
    const res = await api().lock_disable(code);
    if (!res.ok) { toast(res.error); e.target.checked = true; return; }
  }
  await loadSecurity();
});

$("changePassBtn").addEventListener("click", async () => {
  const current = prompt("Current passcode:");
  if (!current) return;
  const next = prompt("New passcode:");
  if (!next) return;
  const res = await api().lock_change(current, next);
  toast(res.ok ? "Passcode changed" : res.error);
});

["setAutoLock", "setLockOnStart", "setBlurCovers", "setLockHint"].forEach((id) =>
  $(id).addEventListener("change", async () => {
    await api().lock_options({
      auto_lock_minutes: parseInt($("setAutoLock").value) || 0,
      lock_on_start: $("setLockOnStart").checked,
      blur_covers: $("setBlurCovers").checked,
      hint: $("setLockHint").value,
    });
    await loadSecurity();
    resetIdleTimer();
  }));

async function loadFilters() {
  const res = await api().get_filters();
  const f = res.filters || {};
  $("setSafeMode").checked = !!f.safe_mode;
  $("setHideNoCover").checked = !!f.hide_no_cover;
  if ($("setMinChapters")) $("setMinChapters").value = f.min_chapters || "";
  if ($("setMaxChapters")) $("setMaxChapters").value = f.max_chapters || "";
  if ($("setStrictRange")) $("setStrictRange").checked = !!f.strict_chapter_range;
  $("setBlockedTags").value = (f.blocked_tags || []).join(", ");
  $("setBlockedTitles").value = (f.blocked_titles || []).join(", ");
}

function splitList(value) {
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

["setSafeMode", "setHideNoCover", "setBlockedTags", "setBlockedTitles",
 "setMinChapters", "setMaxChapters"].forEach((id) =>
  $(id) && $(id).addEventListener("change", async () => {
    await callApi("set_filters", {
      safe_mode: $("setSafeMode").checked,
      hide_no_cover: $("setHideNoCover").checked,
      blocked_tags: splitList($("setBlockedTags").value),
      blocked_titles: splitList($("setBlockedTitles").value),
      strict_chapter_range: $("setStrictRange") ? $("setStrictRange").checked : false,
      min_chapters: parseInt($("setMinChapters").value) || 0,
      max_chapters: parseInt($("setMaxChapters").value) || 0,
    });
    toast("Filters updated");
  }));

$("setCorners") && $("setCorners").addEventListener("change", async (e) => {
  const value = e.target.checked ? "square" : "rounded";
  document.documentElement.setAttribute("data-corners", value);
  state.settings.corners = value;
  await callApi("set_settings", { corners: value });
});

/* The tray switches were listed inside this handler's payload but were
   never in the ids it binds, so flipping "Minimise to system tray" saved
   nothing unless the user happened to also toggle dedupe or interleave.
   They are bound now. */
["setDedupe", "setInterleave", "setTray", "setTrayNotify", "setLogAdvanced"]
  .forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("change", async () => {
      const changes = {
        dedupe_results: $("setDedupe").checked,
        minimize_to_tray: $("setTray") ? $("setTray").checked : false,
        tray_notifications: $("setTrayNotify") ? $("setTrayNotify").checked : true,
        interleave_results: $("setInterleave").checked,
        queue_log_advanced: $("setLogAdvanced") ? $("setLogAdvanced").checked : false,
      };
      state.settings = Object.assign(state.settings || {}, changes);
      // Keep the in-panel checkbox on the Queue tab in step with Settings.
      if ($("logAdvanced")) $("logAdvanced").checked = changes.queue_log_advanced;
      await api().set_settings(changes);
      if (id === "setTray") {
        toast(changes.minimize_to_tray
          ? "Closing the window will keep downloads running"
          : "Closing the window will quit MangaDL");
        refreshTrayState();
      }
    });
  });

/* Changing how already-downloaded results are treated re-runs the current
   search, so the choice is visible immediately rather than at the next
   query. */
$("setDownloadedResults") &&
  $("setDownloadedResults").addEventListener("change", async (e) => {
    const mode = e.target.value;
    state.settings = Object.assign(state.settings || {},
                                   { downloaded_results: mode });
    await callApi("set_settings", { downloaded_results: mode });
    toast(mode === "hide" ? "Hiding results you already have"
        : mode === "show" ? "Showing all results"
        : "Dimming results you already have");
    doSearch(true);
  });

/* ------------------------------------------------- phone server settings

   The token is validated by the Python side (mangadl/servercfg.py), which
   is the same code the server itself and its control window use -- three
   copies of a length check is how one of them ends up accepting four
   characters. */

let serverCfg = null;

async function loadServerConfig() {
  const res = await callApi("get_server_config");
  if (!res || !res.ok) return;
  serverCfg = res;
  if ($("setServerToken") && document.activeElement !== $("setServerToken")) {
    $("setServerToken").value = res.token || "";
  }
  if ($("setServerPort") && document.activeElement !== $("setServerPort")) {
    $("setServerPort").value = res.port || 8577;
  }
  if ($("setServerVerbose")) $("setServerVerbose").checked = !!res.verbose;
  if ($("serverUrlHint")) $("serverUrlHint").textContent = res.url || "";
}

function serverHint(text, bad) {
  const hint = $("serverTokenHint");
  if (!hint) return;
  hint.textContent = text;
  hint.style.color = bad ? "var(--danger)" : "";
}

$("setServerToken") && $("setServerToken").addEventListener("input", (e) => {
  const n = e.target.value.trim().length;
  const min = (serverCfg && serverCfg.min_length) || 16;
  if (n && n < min) serverHint(`${n} of ${min} characters minimum.`, true);
  else serverHint("At least 16 characters. The phone needs this to connect.");
});

$("setServerToken") && $("setServerToken").addEventListener("change", async (e) => {
  const res = await callApi("set_server_config", e.target.value.trim());
  if (!res) return;
  serverHint(res.message || "", !res.ok);
  if (res.ok) { await loadServerConfig(); toast("Server token saved"); }
});

$("genServerToken") && $("genServerToken").addEventListener("click", async () => {
  const res = await callApi("generate_server_token");
  if (res && res.ok) {
    await loadServerConfig();
    serverHint("Generated and saved.");
    toast("New server token generated");
  }
});

$("setServerPort") && $("setServerPort").addEventListener("change", async (e) => {
  const res = await callApi("set_server_config", null, e.target.value);
  if (!res) return;
  serverHint(res.message || "", !res.ok);
  if (res.ok) { await loadServerConfig(); toast("Server port saved"); }
});

$("setServerVerbose") && $("setServerVerbose").addEventListener("change", async (e) => {
  await callApi("set_server_config", null, null, e.target.checked);
  toast(e.target.checked ? "Verbose server log on" : "Verbose server log off");
});

$("copyServerLink") && $("copyServerLink").addEventListener("click", async () => {
  await loadServerConfig();
  const url = (serverCfg && serverCfg.url) || "";
  if (!url) { toast("Could not work out the address"); return; }
  try {
    await navigator.clipboard.writeText(url);
    toast("Link copied");
  } catch (e) {
    // The packaged app is not a secure context, so the clipboard API can
    // refuse. Showing the link is better than failing silently.
    if ($("serverUrlHint")) $("serverUrlHint").textContent = url;
    toast("Copy failed - the link is shown above");
  }
});

/* The Queue tab's own Advanced checkbox is the same setting, mirrored so it
   can be flipped while watching a download without leaving the tab. */
$("logAdvanced") && $("logAdvanced").addEventListener("change", async (e) => {
  const on = e.target.checked;
  state.settings = Object.assign(state.settings || {}, { queue_log_advanced: on });
  if ($("setLogAdvanced")) $("setLogAdvanced").checked = on;
  await callApi("set_settings", { queue_log_advanced: on });
});

async function loadStats() {
  const [statsRes, insightRes] = await Promise.all([
    api().get_stats(), api().get_insights(),
  ]);
  const t = (statsRes.stats && statsRes.stats.totals) || {};
  const d = (statsRes.stats && statsRes.stats.derived) || {};
  const i = insightRes.insights || {};
  const tiles = [
    ["Series", i.series || 0],
    ["Chapters", t.chapters || 0],
    ["Pages", t.pages || 0],
    ["Downloaded", d.human_bytes || "0 B"],
    ["Time spent", d.human_time || "0s"],
    ["Top source", d.top_source || "-"],
  ];
  $("statGrid").innerHTML = tiles.map(
    ([k, v]) => `<div class="stat-tile"><div class="v">${escapeHtml(String(v))}</div><div class="k">${k}</div></div>`
  ).join("");
}

document.querySelectorAll("[data-export]").forEach((btn) =>
  btn.addEventListener("click", async () => {
    const res = await api().export_library(btn.dataset.export);
    if (res.ok) toast("Exported to " + res.path);
    else if (!res.cancelled) toast(res.error || "Export failed");
  }));

$("importLibBtn").addEventListener("click", async () => {
  const res = await api().import_library();
  if (res.ok) toast(`Imported ${res.imported} entries (${res.added} new)`);
  else if (!res.cancelled) toast(res.error || "Import failed");
});

$("resetStatsBtn").addEventListener("click", async () => {
  await api().reset_stats();
  await loadStats();
  toast("Statistics reset");
});

/* ======================================================= updates view */

function coverTag(url, cls) {
  return url
    ? `<img class="${cls}" loading="lazy" decoding="async" src="${url}" alt=""
         onerror="this.style.visibility='hidden'">`
    : `<div class="${cls}"></div>`;
}

async function loadUpdates() {
  const res = await callApi("get_watchlist");
  const items = (res && res.items) || [];
  const list = $("watchList");

  if (!items.length) {
    list.innerHTML = `
      <div class="state-box">
        <span class="material-symbols-rounded">notifications_off</span>
        <div class="state-title">Nothing on the watchlist</div>
        <div class="state-hint">Open a series and press Watch to be told when
          it gains new chapters.</div>
      </div>`;
    $("railUpdates").classList.add("hidden");
    return;
  }

  let pending = 0;
  list.innerHTML = "";
  items.forEach((w) => {
    const n = w.new_chapters || 0;
    if (n) pending += 1;
    const row = document.createElement("div");
    row.className = "update-row";
    row.innerHTML = `
      ${coverTag(w.cover, "u-cover")}
      <div class="u-main">
        <div class="u-title">${escapeHtml(w.title || "Unknown")}</div>
        <div class="u-meta">${escapeHtml(w.source || "")} ·
          ${w.known_chapters || 0} chapters · checked ${escapeHtml(w.checked || "never")}</div>
      </div>
      ${n ? `<span class="pill-new">+${n}</span>` : ""}
      <button class="icon-btn" title="Stop watching">
        <span class="material-symbols-rounded">notifications_off</span>
      </button>`;
    row.querySelector(".u-main").addEventListener("click", () => openManga(w.url, w.source));
    row.querySelector("button").addEventListener("click", async (e) => {
      e.stopPropagation();
      await callApi("unwatch", w.url);
      loadUpdates();
    });
    list.appendChild(row);
  });

  const badge = $("railUpdates");
  badge.textContent = pending;
  badge.classList.toggle("hidden", pending === 0);
}

$("checkUpdatesBtn").addEventListener("click", async () => {
  const btn = $("checkUpdatesBtn");
  btn.disabled = true;
  $("updatesState").innerHTML = '<div class="spinner" style="margin:16px auto"></div>';
  const res = await callApi("check_updates");
  btn.disabled = false;
  $("updatesState").textContent = "";

  const updates = (res && res.updates) || [];
  const box = $("updatesList");
  if (!updates.length) {
    box.innerHTML = `
      <div class="state-box">
        <span class="material-symbols-rounded">check_circle</span>
        <div class="state-title">Everything is up to date</div>
      </div>`;
  } else {
    box.innerHTML = "";
    updates.forEach((u) => {
      const row = document.createElement("div");
      row.className = "update-row";
      row.innerHTML = `
        ${coverTag(u.cover, "u-cover")}
        <div class="u-main">
          <div class="u-title">${escapeHtml(u.title)}</div>
          <div class="u-meta">now ${u.total} chapters</div>
        </div>
        <span class="pill-new">+${u.new}</span>`;
      row.addEventListener("click", () => openManga(u.url, u.source));
      box.appendChild(row);
    });
    toast(`${updates.length} series updated`);
  }
  loadUpdates();
});

/* ====================================================== insights view */

async function loadInsights() {
  const [statsRes, insightRes, calRes] = await Promise.all([
    callApi("get_stats"), callApi("get_insights"), callApi("get_calendar"),
  ]);
  const totals = (statsRes && statsRes.stats && statsRes.stats.totals) || {};
  const derived = (statsRes && statsRes.stats && statsRes.stats.derived) || {};
  const perSource = (statsRes && statsRes.stats && statsRes.stats.sources) || {};
  const days = (statsRes && statsRes.stats && statsRes.stats.days) || {};
  const ins = (insightRes && insightRes.insights) || {};

  const tiles = [
    ["Series", ins.series || 0, "collections_bookmark"],
    ["Chapters", totals.chapters || 0, "menu_book"],
    ["Pages", totals.pages || 0, "image"],
    ["On disk", ins.human_bytes || "0 B", "hard_drive"],
    ["Time spent", derived.human_time || "0s", "schedule"],
    ["Avg speed", `${derived.avg_pages_per_second || 0}/s`, "speed"],
  ];
  $("insightTiles").innerHTML = tiles.map(([k, v, icon]) => `
    <div class="stat-tile">
      <div class="v">${escapeHtml(String(v))}</div>
      <div class="k">${escapeHtml(k)}</div>
    </div>`).join("");

  // per-source bar chart. Labelled with display names, not raw ids: the
  // chart used to read "flamecomics" and "madara.toonily".
  const calNames = (calRes && calRes.ok && calRes.calendar
                    && calRes.calendar.names) || {};
  const entries = Object.entries(perSource)
    .sort((a, b) => (b[1].chapters || 0) - (a[1].chapters || 0));
  const max = Math.max(1, ...entries.map(([, v]) => v.chapters || 0));
  $("sourceChart").innerHTML = entries.length
    ? entries.map(([name, v]) => `
        <div class="bar-row">
          <span class="b-label" title="${escapeHtml(name)}">${escapeHtml(calNames[name] || name)}</span>
          <span class="b-track"><span class="b-fill" style="width:${((v.chapters || 0) / max) * 100}%"></span></span>
          <span class="b-value">${v.chapters || 0}</span>
        </div>`).join("")
    : '<div class="tool-note">No downloads recorded yet.</div>';

  // last 14 days of activity
  const dayKeys = Object.keys(days).sort().slice(-14);
  const dayMax = Math.max(1, ...dayKeys.map((d) => days[d].chapters || 0));
  $("activityChart").innerHTML = dayKeys.length
    ? dayKeys.map((d) => {
        const v = days[d].chapters || 0;
        return `<div class="sp-bar" style="height:${Math.max(3, (v / dayMax) * 100)}%"
                 title="${escapeHtml(d)}: ${v} chapters"></div>`;
      }).join("")
    : '<div class="tool-note">No activity yet.</div>';

  const rankRows = (rows, valueKey, labelKey) => rows.length
    ? rows.map((r) => `
        <div class="rank-row">
          <div class="r-main">
            <div class="r-title">${escapeHtml(r[labelKey] || "Unknown")}</div>
          </div>
          <span class="r-value">${escapeHtml(String(r[valueKey] ?? ""))}</span>
        </div>`).join("")
    : '<div class="tool-note">Nothing yet.</div>';

  $("largestList").innerHTML = rankRows(ins.largest || [], "chapters", "title");
  $("recentList").innerHTML = rankRows(ins.recent || [], "date", "title");

  // The contribution calendar and the source carousel share one payload.
  const cal = calRes && calRes.ok ? calRes.calendar : null;
  if (cal) {
    renderCalendar(cal);
    renderSourceCarousel(cal, perSource);
  }
}

/* ============================== contribution calendar + source carousel

   Every source gets a stable colour, derived from its id rather than an
   assignment table, so adding a site never renumbers everyone else's
   colour and the same source is the same hue on every machine. */

const CAL_STATE = { calendar: null, colors: {}, filter: null };

/* Golden-angle hue rotation over a hash of the id: deterministic, evenly
   spread, and no two of the 19 sources land close enough to confuse. */
function sourceColor(sourceId) {
  if (CAL_STATE.colors[sourceId]) return CAL_STATE.colors[sourceId];
  const id = String(sourceId || "?");
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  const hue = (hash * 137.508) % 360;         // golden angle
  const sat = 62 + (hash % 3) * 9;            // 62/71/80%
  const light = 52 + ((hash >> 3) % 3) * 6;   // 52/58/64%
  const color = `hsl(${hue.toFixed(1)} ${sat}% ${light}%)`;
  CAL_STATE.colors[sourceId] = color;
  return color;
}

/* Mix a day's source colours in proportion to how many chapters each one
   contributed, then scale the result's opacity by the day's intensity.

   Mixing happens in RGB after converting each HSL colour, because
   color-mix() cannot take a weighted list of N colours in CSS. */
function hslToRgb(hsl) {
  const m = /hsl\(([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\)/.exec(hsl);
  if (!m) return [128, 128, 128];
  const h = parseFloat(m[1]) / 360, s = parseFloat(m[2]) / 100, l = parseFloat(m[3]) / 100;
  if (s === 0) { const v = Math.round(l * 255); return [v, v, v]; }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const conv = (t) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  return [conv(h + 1 / 3), conv(h), conv(h - 1 / 3)].map((v) => Math.round(v * 255));
}

function mixDayColor(sources, level) {
  const entries = Object.entries(sources || {}).filter(([, n]) => n > 0);
  if (!entries.length || level <= 0) return null;
  const total = entries.reduce((n, [, v]) => n + v, 0) || 1;
  let r = 0, g = 0, b = 0;
  entries.forEach(([id, count]) => {
    const [cr, cg, cb] = hslToRgb(sourceColor(id));
    const w = count / total;
    r += cr * w; g += cg * w; b += cb * w;
  });
  // Level drives alpha: a busy day is a solid colour, a quiet one a wash.
  const alpha = [0, 0.32, 0.55, 0.78, 1][Math.max(0, Math.min(4, level))];
  return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${alpha})`;
}

function fmtDay(iso) {
  const d = new Date(iso + "T00:00:00");
  return isNaN(d) ? iso : d.toLocaleDateString(undefined,
    { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function renderCalendar(cal) {
  const grid = $("calGrid");
  if (!grid || !cal) return;
  CAL_STATE.calendar = cal;
  const days = cal.days || [];

  grid.innerHTML = days.map((day, i) => {
    const color = mixDayColor(day.sources, day.level);
    const style = color ? `--cal-color:${color};` : "";
    // Stagger the entry animation across the grid, capped so the far end
    // does not wait a second and a half to appear.
    const delay = Math.min(0.6, (i / Math.max(1, days.length)) * 0.6);
    return `<span class="cal-day lvl-${day.level}"
                  style="${style}--cal-delay:${delay.toFixed(2)}s"
                  data-date="${escapeHtml(day.date)}"></span>`;
  }).join("");

  // Month labels above the columns, one per week-column where the month
  // changes -- the same convention GitHub uses.
  const months = $("calMonths");
  if (months) {
    const cells = [];
    let last = -1;
    for (let week = 0; week * 7 < days.length; week++) {
      const day = days[week * 7];
      if (!day) break;
      const m = new Date(day.date + "T00:00:00").getMonth();
      const label = (m !== last && !isNaN(m)) ? MONTHS[m] : "";
      if (label) last = m;
      cells.push(`<span class="cal-month">${label}</span>`);
    }
    months.innerHTML = cells.join("");
  }

  const summary = $("calSummary");
  if (summary) {
    summary.textContent = `${cal.total || 0} chapters in the last ${cal.weeks || 53} weeks`;
  }
  const range = $("calRange");
  if (range && days.length) {
    range.textContent = `${fmtDay(days[0].date)} – ${fmtDay(days[days.length - 1].date)}`;
  }

  attachCalendarTooltips(grid, cal);
}

/* Tooltips are one shared, position:fixed node rather than a title
   attribute: native tooltips cannot show the per-source breakdown, and 371
   permanent DOM nodes for something only ever seen one at a time is waste. */
let calTip = null;

function ensureTip() {
  if (calTip && document.body.contains(calTip)) return calTip;
  calTip = document.createElement("div");
  calTip.className = "cal-tip";
  document.body.appendChild(calTip);
  return calTip;
}

function showTip(html, x, y) {
  const tip = ensureTip();
  tip.innerHTML = html;
  tip.classList.add("show");
  // Keep it on screen near the right/bottom edges.
  const r = tip.getBoundingClientRect();
  const left = Math.min(Math.max(8, x - r.width / 2), window.innerWidth - r.width - 8);
  const top = y - r.height - 10 < 8 ? y + 18 : y - r.height - 10;
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

function hideTip() {
  if (calTip) calTip.classList.remove("show");
}

function attachCalendarTooltips(grid, cal) {
  const names = (cal && cal.names) || {};
  const byDate = {};
  (cal.days || []).forEach((d) => { byDate[d.date] = d; });

  grid.querySelectorAll(".cal-day").forEach((cell) => {
    cell.addEventListener("mouseenter", () => {
      const day = byDate[cell.dataset.date];
      if (!day) return;
      const r = cell.getBoundingClientRect();
      showTip(dayTipHtml(day, names), r.left + r.width / 2, r.top);
    });
    cell.addEventListener("mouseleave", hideTip);
  });
  grid.addEventListener("mouseleave", hideTip);
}

/* The plain calendar tooltip: how many books/chapters that day, then the
   per-source split as a fraction of that day's total. */
function dayTipHtml(day, names) {
  const head = `<div><b>${escapeHtml(fmtDay(day.date))}</b></div>`;
  if (!day.chapters) {
    return head + '<div class="tip-muted">No downloads</div>';
  }
  const total = day.chapters;
  const rows = Object.entries(day.sources || {})
    .sort((a, b) => b[1] - a[1])
    .map(([id, n]) => `
      <div class="tip-row">
        <span class="tip-dot" style="--tip-color:${sourceColor(id)}"></span>
        <span>${escapeHtml(names[id] || id)}</span>
        <span class="tip-muted">${n}/${total}</span>
      </div>`).join("");
  const noSources = !rows
    ? '<div class="tip-muted">Source not recorded</div>' : "";
  return `${head}
    <div>${total} chapter${total === 1 ? "" : "s"} downloaded</div>
    ${rows}${noSources}`;
}

/* ---------------------------------------------------- source carousel */

function renderSourceCarousel(cal, perSource) {
  const track = $("srcTrack");
  if (!track) return;
  const names = (cal && cal.names) || {};
  const days = (cal && cal.days) || [];

  const totals = {};
  Object.entries(perSource || {}).forEach(([id, v]) => {
    totals[id] = Number((v && v.chapters) || 0);
  });
  // Days data can name a source the totals do not (older stats files).
  days.forEach((d) => Object.entries(d.sources || {}).forEach(([id, n]) => {
    if (!(id in totals)) totals[id] = 0;
    totals[id] = Math.max(totals[id], 0);
    void n;
  }));

  const entries = Object.entries(totals)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]);

  const grand = entries.reduce((n, [, v]) => n + v, 0);
  const summary = $("srcSummary");
  if (summary) {
    summary.textContent = entries.length
      ? `${entries.length} source${entries.length === 1 ? "" : "s"} · ${grand} chapters`
      : "";
  }

  if (!entries.length) {
    track.innerHTML = '<div class="tool-note">No downloads recorded yet.</div>';
    updateCarouselNav();
    return;
  }

  const peak = entries[0][1] || 1;
  track.innerHTML = entries.map(([id, count], i) => {
    const share = grand ? Math.round((count / grand) * 100) : 0;
    // A miniature 7-row contribution strip for this source alone.
    const mini = days.slice(-98).map((d) => {
      const n = (d.sources || {})[id] || 0;
      const alpha = n <= 0 ? 0.07 : Math.min(1, 0.3 + (n / Math.max(1, peak)) * 3);
      return `<i style="opacity:${alpha.toFixed(2)}"></i>`;
    }).join("");
    return `
      <div class="src-card" style="--src-color:${sourceColor(id)};
                                   animation-delay:${(i * 0.04).toFixed(2)}s"
           data-source="${escapeHtml(id)}">
        <div class="src-card-head">
          <span class="src-swatch"></span>
          <span class="src-card-name" title="${escapeHtml(names[id] || id)}">${escapeHtml(names[id] || id)}</span>
        </div>
        <div class="src-card-value">${count}</div>
        <div class="src-card-sub">${share}% of all chapters</div>
        <div class="src-card-bar"><i style="width:${Math.round((count / peak) * 100)}%"></i></div>
        <div class="src-mini">${mini}</div>
      </div>`;
  }).join("");

  // Hovering a card explains that source's share of the whole library.
  track.querySelectorAll(".src-card").forEach((card) => {
    card.addEventListener("mouseenter", () => {
      const id = card.dataset.source;
      const count = totals[id] || 0;
      const r = card.getBoundingClientRect();
      const activeDays = days.filter((d) => (d.sources || {})[id] > 0).length;
      showTip(`
        <div class="tip-row">
          <span class="tip-dot" style="--tip-color:${sourceColor(id)}"></span>
          <b>${escapeHtml(names[id] || id)}</b>
        </div>
        <div>${count}/${grand} chapters downloaded</div>
        <div class="tip-muted">Active on ${activeDays} day${activeDays === 1 ? "" : "s"}</div>`,
        r.left + r.width / 2, r.top);
    });
    card.addEventListener("mouseleave", hideTip);
  });

  updateCarouselNav();
}

function updateCarouselNav() {
  const track = $("srcTrack");
  const prev = $("srcPrev"), next = $("srcNext");
  if (!track || !prev || !next) return;
  const max = track.scrollWidth - track.clientWidth;
  prev.disabled = track.scrollLeft <= 2;
  next.disabled = track.scrollLeft >= max - 2;
}

(function wireCarousel() {
  const track = $("srcTrack");
  if (!track) return;
  const step = () => Math.max(200, track.clientWidth * 0.8);
  $("srcPrev") && $("srcPrev").addEventListener("click",
    () => track.scrollBy({ left: -step(), behavior: "smooth" }));
  $("srcNext") && $("srcNext").addEventListener("click",
    () => track.scrollBy({ left: step(), behavior: "smooth" }));
  track.addEventListener("scroll", updateCarouselNav, { passive: true });
  window.addEventListener("resize", updateCarouselNav);
})();

/* ========================================================= tools view */

document.querySelectorAll(".tool-tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tool-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tool-panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    const panel = $("tool-" + tab.dataset.tool);
    if (panel) panel.classList.add("active");
    if (tab.dataset.tool === "health") loadHealth();
    if (tab.dataset.tool === "history") loadHistoryList();
    if (tab.dataset.tool === "moved") loadMoved();
  }));

$("scanDiskBtn").addEventListener("click", async () => {
  $("diskNote").textContent = "Scanning…";
  const res = await callApi("disk_usage");
  const rows = (res && res.rows) || [];
  $("diskNote").textContent = rows.length
    ? `${rows.length} series in ${res.root || "downloads"}`
    : "Nothing found.";
  $("diskList").innerHTML = rows.slice(0, 40).map((r) => `
    <div class="rank-row">
      <div class="r-main">
        <div class="r-title">${escapeHtml(r.name)}</div>
        <div class="r-meta">${r.files} files</div>
      </div>
      <span class="r-value">${escapeHtml(humanSize(r.bytes))}</span>
    </div>`).join("");
});

$("scanDupesBtn").addEventListener("click", async () => {
  $("dupeNote").textContent = "Scanning (this hashes every file)…";
  const res = await callApi("scan_duplicates");
  const groups = (res && res.groups) || [];
  $("dupeNote").textContent = groups.length
    ? `${groups.length} duplicate groups · ${humanSize(res.wasted || 0)} wasted`
    : "No duplicates found.";
  $("dupeList").innerHTML = groups.slice(0, 30).map((g) => `
    <div class="dupe-group">
      <div class="dg-head">
        <span class="material-symbols-rounded">content_copy</span>
        ${g.files.length} copies · ${escapeHtml(humanSize(g.size))} each
      </div>
      ${g.files.map((f) => `
        <div class="dg-file"><span class="material-symbols-rounded">description</span>
          ${escapeHtml(f)}</div>`).join("")}
    </div>`).join("");
});

$("scanOrphansBtn").addEventListener("click", async () => {
  $("orphanNote").textContent = "Checking…";
  const res = await callApi("find_orphans");
  const rows = (res && res.orphans) || [];
  $("orphanNote").textContent = rows.length
    ? `${rows.length} entries point at missing files`
    : "No orphaned entries.";
  $("orphanList").innerHTML = rows.map((o) => `
    <div class="rank-row">
      <div class="r-main">
        <div class="r-title">${escapeHtml(o.title || "Unknown")}</div>
        <div class="r-meta">${o.directory_gone ? "folder missing" : ""}
          ${o.missing && o.missing.length ? `${o.missing.length} missing file(s)` : ""}</div>
      </div>
    </div>`).join("");
});

/* ------------------------------------------------- rebuild CBZ covers */

let coverGroups = [];
let coverRoot = null;          // null = use the configured downloads folder

$("smartCoversBtn").addEventListener("click", async () => {
  $("smartLog").innerHTML = "";
  $("smartNote").textContent = "Starting\u2026";
  const res = await callApi("smart_covers", coverRoot,
                            $("coverOverwrite").checked, true);
  if (!res || !res.ok) {
    $("smartNote").textContent = (res && res.error) || "Could not start";
    return;
  }
  $("smartCoversBtn").disabled = true;
  $("stopSmartBtn").style.display = "";
});

$("stopSmartBtn").addEventListener("click", async () => {
  $("smartNote").textContent = "Stopping after this series\u2026";
  await callApi("stop_smart_covers");
});

function smartLogRow(html) {
  const box = $("smartLog");
  box.insertAdjacentHTML("beforeend", html);
  box.scrollTop = box.scrollHeight;
}

function handleSmartEvent(ev) {
  if (ev.type === "smart_start") {
    $("smartNote").textContent = `Scanning ${ev.total} series\u2026`;
    return true;
  }
  if (ev.type === "smart_progress") {
    $("smartNote").textContent =
      `${ev.done}/${ev.total} \u00b7 ${ev.title}`;
    return true;
  }
  if (ev.type === "smart_item") {
    smartLogRow(`
      <div class="rank-row">
        <div class="r-main">
          <div class="r-title">${escapeHtml(ev.title || "")}</div>
          <div class="r-meta">${ev.ok
            ? `chose ${escapeHtml(ev.source || "")} \u00b7 ${ev.width || "?"}\u00d7${ev.height || "?"}`
            : escapeHtml(ev.error || "no cover found")}</div>
        </div>
        <span class="cap">${ev.ok ? "saved" : "skipped"}</span>
      </div>`);
    return true;
  }
  if (ev.type === "smart_done") {
    $("smartCoversBtn").disabled = false;
    $("stopSmartBtn").style.display = "none";
    $("smartNote").textContent =
      `${ev.done} cover(s) saved` +
      (ev.moved ? `, ${ev.moved} archive(s) sorted` : "") +
      (ev.failed ? `, ${ev.failed} skipped` : "") +
      (ev.stopped ? " (stopped)" : "");
    toast(`Smart search finished: ${ev.done} cover(s)`);
    return true;
  }
  return false;
}

$("pickCoverFolderBtn").addEventListener("click", async () => {
  const folder = await callApi("choose_folder");
  if (!folder) return;         // cancelled
  coverRoot = folder;
  $("coverRoot").textContent = folder;
  $("coverNote").textContent = "Folder chosen - scan when ready.";
});

$("resetCoverFolderBtn").addEventListener("click", () => {
  coverRoot = null;
  $("coverRoot").textContent = "your downloads folder";
  $("coverNote").textContent = "";
});

$("organiseCoversBtn").addEventListener("click", async () => {
  const loose = coverGroups.filter((g) => g.needs_move);
  if (!loose.length) return;
  $("coverNote").textContent = "Sorting into folders\u2026";
  const res = await callApi("organise_covers", coverRoot);
  if (!res || !res.ok) {
    $("coverNote").textContent = (res && res.error) || "Could not sort";
    return;
  }
  toast(`${res.moved} archive(s) sorted into ${res.folders} folder(s)`);
  $("scanCoversBtn").click();     // re-scan so the list reflects disk
});

$("scanCoversBtn").addEventListener("click", async () => {
  $("coverNote").textContent = "Scanning\u2026";
  $("coverList").innerHTML = "";
  $("coverBulkBar").style.display = "none";
  const res = await callApi("scan_covers", coverRoot,
                            $("coverOverwrite").checked);
  if (!res || !res.ok) {
    $("coverNote").textContent = (res && res.error) || "Scan failed";
    return;
  }
  coverGroups = res.groups || [];
  if (res.root) $("coverRoot").textContent = res.root;
  const loose = coverGroups.filter((g) => g.needs_move).length;
  $("coverNote").textContent = coverGroups.length
    ? `${coverGroups.length} series need a cover`
      + (loose ? ` \u00b7 ${loose} still loose in a shared folder` : "")
    : "Every archive already has a cover.";
  // Offer the bulk tidy only when there is something loose to tidy.
  $("coverBulkBar").style.display = loose ? "" : "none";
  renderCoverGroups();
});

function renderCoverGroups() {
  $("coverList").innerHTML = coverGroups.map((g, i) => `
    <div class="rank-row" id="coverRow${i}">
      <div class="r-main">
        <div class="r-title">${escapeHtml(g.title)}</div>
        <div class="r-meta">
          ${g.count} archive${g.count === 1 ? "" : "s"}
          &middot; ${escapeHtml(g.directory)}
          ${g.needs_move
            ? ` &middot; <span class="cap">will move into ${escapeHtml(g.title)}/</span>`
            : ""}
          ${g.has_cover ? ' &middot; <span class="cap">has a cover</span>' : ""}
        </div>
        <div class="cover-picks" id="coverPicks${i}"></div>
      </div>
      <button class="btn" data-cover-find="${i}">Find covers</button>
    </div>`).join("");
}

$("coverList").addEventListener("click", async (event) => {
  const findBtn = event.target.closest("[data-cover-find]");
  if (findBtn) {
    const index = Number(findBtn.dataset.coverFind);
    const group = coverGroups[index];
    const box = $(`coverPicks${index}`);
    box.innerHTML = '<span class="tool-note">Searching every source\u2026</span>';
    const res = await callApi("cover_candidates", group.title);
    const picks = (res && res.candidates) || [];
    if (!picks.length) {
      box.innerHTML = '<span class="tool-note">No cover found for this title.</span>';
      return;
    }
    // The user ranks and chooses; nothing is applied automatically.
    box.innerHTML = picks.map((c, j) => `
      <button class="cover-pick" data-cover-pick="${index}:${j}"
              title="${escapeHtml(c.title || "")} — ${escapeHtml(c.source_name || "")}">
        <img src="${escapeHtml(c.preview || c.cover)}" alt="" loading="lazy">
        <span>${escapeHtml(c.source_name || c.source || "")}</span>
      </button>`).join("");
    group._picks = picks;
    return;
  }

  const pick = event.target.closest("[data-cover-pick]");
  if (!pick) return;
  const [gi, ci] = pick.dataset.coverPick.split(":").map(Number);
  const group = coverGroups[gi];
  const candidate = (group._picks || [])[ci];
  if (!candidate) return;

  pick.disabled = true;
  const box = $(`coverPicks${gi}`);
  box.innerHTML = '<span class="tool-note">Saving\u2026</span>';
  const res = await callApi("apply_cover", group, candidate);
  if (res && res.ok) {
    box.innerHTML = `<span class="tool-note">Saved to ${escapeHtml(res.directory)}/cover.jpg` +
      (res.moved ? " (archives moved into their own folder)" : "") + "</span>";
    toast(`Cover saved for ${group.title}`);
  } else {
    box.innerHTML = `<span class="tool-note">${escapeHtml((res && res.error) || "Failed")}</span>`;
  }
});

async function loadHealth() {
  const res = await callApi("get_health");
  const breakers = (res && res.report && res.report.breakers) || {};
  const names = Object.keys(breakers);
  $("healthList").innerHTML = names.length
    ? names.sort().map((n) => {
        const b = breakers[n];
        return `<div class="rank-row">
          <span class="health-dot ${escapeHtml(b.state)}"></span>
          <div class="r-main">
            <div class="r-title">${escapeHtml(n)}</div>
            <div class="r-meta">${escapeHtml(b.state)}${b.failures ? ` · ${b.failures} recent failures` : ""}${b.last_error ? ` · ${escapeHtml(b.last_error)}` : ""}</div>
          </div>
          ${b.retry_after ? `<span class="r-value">${b.retry_after}s</span>` : ""}
        </div>`;
      }).join("")
    : '<div class="tool-note">No source calls recorded yet this session.</div>';
}

async function loadHistoryList() {
  const res = await callApi("get_history", 40);
  const items = (res && res.items) || [];
  $("historyList").innerHTML = items.length
    ? items.map((h) => `
        <div class="rank-row" data-q="${escapeHtml(h.query)}">
          <div class="r-main">
            <div class="r-title">${escapeHtml(h.query)}</div>
            <div class="r-meta">${escapeHtml(h.source || "all")} · ${h.results || 0} results · ${escapeHtml(h.date || "")}</div>
          </div>
          <span class="material-symbols-rounded" style="opacity:.5">north_east</span>
        </div>`).join("")
    : '<div class="tool-note">No searches yet.</div>';
  $("historyList").querySelectorAll("[data-q]").forEach((row) =>
    row.addEventListener("click", () => {
      showView("search");
      $("searchInput").value = row.dataset.q;
      doSearch();
    }));
}

$("clearHistoryBtn").addEventListener("click", async () => {
  await callApi("clear_history");
  loadHistoryList();
  toast("History cleared");
});

function humanSize(n) {
  n = Number(n) || 0;
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return (i === 0 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i];
}

/* ================================================= moved / relocated files */

function relocRow(item, actions) {
  const row = document.createElement("div");
  row.className = "rank-row";
  row.innerHTML = `
    <div class="r-main">
      <div class="r-title">${escapeHtml(item.title || "Unknown")}</div>
      <div class="r-meta">${escapeHtml(item.old || item.directory || "")}${
        item.new ? ` &rarr; ${escapeHtml(item.new)}` : ""}</div>
    </div>`;
  (actions || []).forEach((a) => {
    const btn = document.createElement("button");
    btn.className = "btn" + (a.primary ? " btn-filled" : "");
    btn.textContent = a.label;
    btn.addEventListener("click", a.onClick);
    row.appendChild(btn);
  });
  return row;
}

async function loadMoved() {
  const res = await callApi("verify_library");
  const missing = (res && res.missing) || [];
  const present = (res && res.present) || [];
  const list = $("movedList");
  list.innerHTML = "";

  if (!missing.length) {
    list.innerHTML = `
      <div class="state-box">
        <span class="material-symbols-rounded">check_circle</span>
        <div class="state-title">Every library entry resolves</div>
        <div class="state-hint">${present.length} series verified on disk.</div>
      </div>`;
    return;
  }

  const head = document.createElement("div");
  head.className = "tool-note";
  head.style.marginBottom = "8px";
  head.textContent = `${missing.length} entr${missing.length === 1 ? "y" : "ies"} `
    + `point at files that are no longer there.`;
  list.appendChild(head);

  missing.forEach((item) => {
    list.appendChild(relocRow(item, [{
      label: "Locate…",
      primary: true,
      onClick: async () => {
        const res = await callApi("relocate_entry", item.url, null);
        if (res && res.ok) { toast(`Re-linked ${res.title || "entry"}`); loadMoved(); }
        else if (res && !res.cancelled) toast(res.error || "Could not relocate");
      },
    }]));
  });
}

$("verifyLibBtn") && $("verifyLibBtn").addEventListener("click", loadMoved);

$("findMovedBtn") && $("findMovedBtn").addEventListener("click", async () => {
  const res = await callApi("find_moved_entries");
  const proposals = (res && res.proposals) || [];
  const list = $("movedList");
  if (!proposals.length) {
    toast("No moved folders found");
    loadMoved();
    return;
  }
  list.innerHTML = "";
  const head = document.createElement("div");
  head.className = "tool-note";
  head.style.marginBottom = "8px";
  head.textContent = `Found ${proposals.length} likely match${
    proposals.length === 1 ? "" : "es"}. Review, then apply.`;
  list.appendChild(head);

  proposals.forEach((p) => list.appendChild(relocRow(p, [{
    label: "Re-link",
    primary: true,
    onClick: async () => {
      const r = await callApi("relocate_entry", p.url, p.new);
      if (r && r.ok) { toast(`Re-linked ${r.title || "entry"}`); loadMoved(); }
    },
  }])));

  const applyAll = document.createElement("button");
  applyAll.className = "btn btn-filled";
  applyAll.style.marginTop = "10px";
  applyAll.textContent = `Apply all ${proposals.length}`;
  applyAll.addEventListener("click", async () => {
    const r = await callApi("apply_relocations", proposals);
    toast(`Re-linked ${(r && r.applied) || 0} entries`);
    loadMoved();
  });
  list.appendChild(applyAll);
});

$("rescanRootBtn") && $("rescanRootBtn").addEventListener("click", async () => {
  const res = await callApi("rescan_output_dir", null);
  if (!res || !res.ok) {
    if (res && !res.cancelled) toast(res.error || "Could not rescan");
    return;
  }
  toast(`Downloads folder set. Re-linked ${res.relocated} entr`
        + `${res.relocated === 1 ? "y" : "ies"}.`);
  if ($("outputDir")) $("outputDir").value = res.output_dir;
  if ($("setOutputDir")) $("setOutputDir").value = res.output_dir;
  loadMoved();
});


/* ============================================== expandable side rail */

function applyRailState(open) {
  document.body.classList.toggle("rail-open", !!open);
  const rail = $("rail");
  if (rail) rail.classList.toggle("is-open", !!open);
  const btn = $("railToggle");
  if (btn) {
    btn.title = open ? "Collapse sidebar" : "Expand sidebar";
    btn.setAttribute("aria-label", btn.title);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }
}

$("railToggle") && $("railToggle").addEventListener("click", async () => {
  const open = !document.body.classList.contains("rail-open");
  applyRailState(open);
  const res = await callApi("set_settings", { rail_expanded: open });
  if (res) state.settings = res;
});

/* ------------------------------------------------------------ QOL bits */

/* Invert acts on the visible rows only, matching the other bulk buttons:
   selecting chapters hidden by a filter would download rows you cannot see. */
$("selectInvertBtn") && $("selectInvertBtn").addEventListener("click", () => {
  const shown = visibleChapterIndices();
  const next = new Set(state.selected);
  shown.forEach((i) => (next.has(i) ? next.delete(i) : next.add(i)));
  state.selected = next;
  renderChapterList();
  updateDownloadButton();
});

/* Copy the current manga's title + link, handy for sharing or pasting back
   into the search box. Uses the async clipboard API with a legacy fallback,
   because WebView2 does not always grant clipboard-write. */
async function copyText(text, okMessage) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      toast(okMessage || "Copied");
      return true;
    }
  } catch (e) { /* fall through */ }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    toast(ok ? (okMessage || "Copied") : "Could not copy");
    return ok;
  } catch (e) {
    toast("Could not copy");
    return false;
  }
}

/* ================================================ keyboard shortcuts */

/* A single global handler. Every entry is data so the help overlay is
   generated from the same source of truth the handler uses -- the list can
   never drift out of sync with what actually works. */
const SHORTCUTS = [
  { keys: ["/"], label: "Focus search", group: "General",
    run: () => { showView("search"); const i = $("searchInput"); i.focus(); i.select(); } },
  { keys: ["?"], label: "Show this help", group: "General",
    run: () => toggleShortcuts() },
  { keys: ["Escape"], label: "Close overlay / clear search", group: "General",
    run: () => {
      if (!$("shortcutsOverlay").classList.contains("hidden")) return toggleShortcuts(false);
      const input = $("searchInput");
      if (document.activeElement === input && input.value) { input.value = ""; return; }
      if (document.activeElement) document.activeElement.blur();
    } },
  { keys: ["g", "s"], label: "Go to Search", group: "Navigation",
    run: () => showView("search") },
  { keys: ["g", "d"], label: "Go to Downloads", group: "Navigation",
    run: () => showView("downloads") },
  { keys: ["g", "b"], label: "Go to Bookmarks", group: "Navigation",
    run: () => showView("bookmarks") },
  { keys: ["g", "l"], label: "Go to Library", group: "Navigation",
    run: () => showView("library") },
  { keys: ["g", "u"], label: "Go to Updates", group: "Navigation",
    run: () => showView("updates") },
  { keys: ["g", ","], label: "Go to Settings", group: "Navigation",
    run: () => showView("settings") },
  { keys: ["a"], label: "Select all chapters", group: "Manga",
    when: () => state.manga, run: () => $("selectAllBtn").click() },
  { keys: ["n"], label: "Select undownloaded only", group: "Manga",
    when: () => state.manga && $("selectNewBtn"),
    run: () => $("selectNewBtn").click() },
  { keys: ["c"], label: "Clear chapter selection", group: "Manga",
    when: () => state.manga, run: () => $("selectNoneBtn").click() },
  { keys: ["d"], label: "Download selection", group: "Manga",
    when: () => state.manga && !$("downloadBtn").disabled,
    run: () => $("downloadBtn").click() },
  { keys: ["q"], label: "Add selection to queue", group: "Manga",
    when: () => state.manga && $("addCartBtn") && !$("addCartBtn").disabled,
    run: () => $("addCartBtn").click() },
  { keys: ["b"], label: "Bookmark this manga", group: "Manga",
    when: () => state.manga, run: () => $("bookmarkBtn").click() },
  { keys: ["r"], label: "Refresh current view", group: "General",
    run: () => refreshCurrentView() },
  { keys: ["i"], label: "Invert chapter selection", group: "Manga",
    when: () => state.manga && $("selectInvertBtn"),
    run: () => $("selectInvertBtn").click() },
  { keys: ["y"], label: "Copy title and link", group: "Manga",
    when: () => state.manga,
    run: () => copyText(`${state.manga.info.title} — ${state.manga.info.url}`,
                        "Title and link copied") },
];

/* Typing must never trigger a shortcut. */
function isTypingTarget(el) {
  if (!el) return false;
  if (el.isContentEditable) return true;
  const tag = (el.tagName || "").toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select";
}

let chordPrefix = "";
let chordTimer = null;

function clearChord() {
  chordPrefix = "";
  if (chordTimer) { clearTimeout(chordTimer); chordTimer = null; }
}

function matchShortcut(key, shift) {
  const combo = chordPrefix ? [chordPrefix, key] : [key];
  return SHORTCUTS.find((sc) => {
    if (sc.keys.length !== combo.length) return false;
    if (!sc.keys.every((k, i) => k.toLowerCase() === combo[i].toLowerCase())) return false;
    // Shift+/ is how "?" is typed on most layouts, and Chromium reports it
    // as key "/" with shiftKey set -- which used to match "focus search"
    // before the help overlay ever got a chance. Only accept an unshifted
    // key unless the shortcut itself is a shifted character.
    const needsShift = sc.keys.some((k) => k.length === 1 && k !== k.toLowerCase()) ||
                       sc.keys.includes("?");
    if (shift && !needsShift) return false;
    return true;
  });
}

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  // The lock screen owns the keyboard while it is up.
  const lock = $("lockOverlay");
  if (lock && !lock.classList.contains("hidden")) return;
  if (isTypingTarget(document.activeElement) && e.key !== "Escape") return;

  const hit = matchShortcut(e.key, e.shiftKey);
  if (hit) {
    if (hit.when && !hit.when()) { clearChord(); return; }
    e.preventDefault();
    clearChord();
    try { hit.run(); } catch (err) { /* never break typing */ }
    return;
  }

  // Start (or restart) a two-key chord such as "g s".
  const startsChord = !chordPrefix &&
    SHORTCUTS.some((sc) => sc.keys.length === 2 &&
                   sc.keys[0].toLowerCase() === e.key.toLowerCase());
  if (startsChord) {
    e.preventDefault();
    chordPrefix = e.key;
    chordTimer = setTimeout(clearChord, 1200);
    return;
  }
  clearChord();
});

function keyCap(key) {
  const pretty = { Escape: "Esc", " ": "Space" }[key] || key;
  return `<kbd>${escapeHtml(pretty)}</kbd>`;
}

function renderShortcuts(target) {
  const body = target || $("shortcutsBody");
  if (!body) return;
  const groups = {};
  SHORTCUTS.forEach((sc) => (groups[sc.group] = groups[sc.group] || []).push(sc));
  body.innerHTML = Object.entries(groups).map(([name, list]) => `
    <div class="sc-group">
      <h3>${escapeHtml(name)}</h3>
      ${list.map((sc) => `
        <div class="sc-row">
          <span class="sc-keys">${sc.keys.map(keyCap).join(" ")}</span>
          <span class="sc-label">${escapeHtml(sc.label)}</span>
        </div>`).join("")}
    </div>`).join("");
}

function toggleShortcuts(force) {
  const el = $("shortcutsOverlay");
  if (!el) return;
  const show = force === undefined ? el.classList.contains("hidden") : force;
  if (show) renderShortcuts();
  el.classList.toggle("hidden", !show);
}

$("shortcutsClose") && $("shortcutsClose").addEventListener("click",
  () => toggleShortcuts(false));
$("shortcutsOverlay") && $("shortcutsOverlay").addEventListener("click", (e) => {
  if (e.target.id === "shortcutsOverlay") toggleShortcuts(false);
});

/* Re-run whatever the active view shows, so "r" always does something sane. */
function refreshCurrentView() {
  const active = document.querySelector(".view.active");
  const id = active ? active.id.replace("view-", "") : "search";
  if (id === "search") doSearch(true);
  else if (id === "bookmarks") loadBookmarks();
  else if (id === "library") loadLibrary();
  else if (id === "updates") loadUpdates();
  else if (id === "insights") loadInsights();
  else if (id === "manga" && state.manga) openManga(state.manga.info.url);
  toast("Refreshed");
}
