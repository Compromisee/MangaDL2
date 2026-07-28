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
    $("modalTitle").textContent = title;
    $("modalBody").textContent = body;
    $("modalOk").textContent = okLabel;
    $("modalBackdrop").classList.remove("hidden");
  });
}
$("modalCancel").addEventListener("click", () => {
  $("modalBackdrop").classList.add("hidden");
  if (modalResolve) modalResolve(false);
});
$("modalOk").addEventListener("click", () => {
  $("modalBackdrop").classList.add("hidden");
  if (modalResolve) modalResolve(true);
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

function applyAppearance(s) {
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
  const res = await api().get_sources();
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

function getFilters() {
  return {
    source: $("fSource").value,
    genre: $("fGenre") ? $("fGenre").value : "",
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
  return f.source !== "all" || f.genre !== "" || f.sort !== "Best Match"
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
  const res = await api().get_genres($("fSource").value || "all");
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
  const current = $("fGenre").value;
  wrap.innerHTML = "";
  GENRES.slice(0, 10).forEach((g) => {
    const chip = document.createElement("button");
    chip.className = "genre-chip" + (current === g.name ? " active" : "");
    chip.textContent = g.name;
    chip.addEventListener("click", () => {
      $("fGenre").value = (current === g.name) ? "" : g.name;
      updateFilterDot();
      renderGenreChips();
      doSearch(true);
    });
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

$("fGenre").addEventListener("change", () => {
  updateFilterDot();
  renderGenreChips();
  doSearch(true);
});

$("fBrowseSort").addEventListener("change", () => doSearch(true));

$("fReset").addEventListener("click", () => {
  $("fSource").value = "all";
  $("fGenre").value = "";
  renderGenreChips();
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

    card.addEventListener("click", () => openManga(r.url, r.source));
    grid.appendChild(card);
  });
  return offset + results.length;
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
    const g = filters.genre;
    $("browseHeadText").textContent = g
      ? `Top ${g} right now`
      : `${filters.browse_sort || "Trending"} now`;
    head.classList.remove("hidden");
    renderGenreChips();
  } else {
    head.classList.add("hidden");
  }

  const seq = ++searchSeq;
  let res;
  if (browseMode) {
    res = await api().browse({
      source: filters.source,
      genre: filters.genre,
      sort: filters.browse_sort || "Trending",
      status: filters.status,
      page: browsePage,
    });
  } else {
    res = await api().search(query, { ...filters, page: browsePage });
  }
  if (seq !== searchSeq) return;   // a newer request superseded this one

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

  const res = await api().get_manga(url, sourceId || null);
  $("mangaLoading").classList.add("hidden");

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

function setBookmarkIcon(on) {
  $("bookmarkBtn").classList.toggle("on", on);
  $("bookmarkIcon").textContent = on ? "bookmark" : "bookmark_add";
}

$("bookmarkBtn").addEventListener("click", async () => {
  if (!state.manga) return;
  const res = await api().toggle_bookmark(state.manga.info);
  if (res.ok) {
    setBookmarkIcon(res.bookmarked);
    toast(res.bookmarked ? "Bookmarked" : "Bookmark removed");
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

function logLine(cls, text) {
  const log = $("dlLog");
  const t = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const line = document.createElement("div");
  line.className = "log-line " + cls;
  line.innerHTML = `<span class="t">${t}</span><span>${escapeHtml(text)}</span>`;
  log.prepend(line);
  while (log.children.length > 200) log.removeChild(log.lastChild);
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

function markChapterDownloaded(name) {
  state.downloaded.add(name);
  const item = [...document.querySelectorAll(".chapter-item")].find((el) => {
    const idx = Number(el.dataset.index);
    return state.manga && state.manga.chapters[idx] && state.manga.chapters[idx].name === name;
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
  /* Every event carries a job id so concurrent downloads never interfere.
     Aggregate counters are summed across jobs rather than overwritten. */
  const job = event.job ? (jobs.get(event.job) || registerJob(event.job, {})) : null;

  switch (event.type) {
    case "job_started":
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
      break;
    case "chapter_progress": {
      const row = ensureBar(event);
      const pct = event.total ? Math.round((event.done / event.total) * 100) : 0;
      row.querySelector(".ac-fill").style.width = pct + "%";
      row.querySelector(".ac-count").textContent = `${event.done}/${event.total}`;
      break;
    }
    case "chapter_done":
      removeBar(event);
      if (job) { job.done = event.completed; job.total = event.total || job.total; }
      state.doneChapters = totalOf("done");
      refreshOverall();
      logLine("ok", prefixed(event, `${event.chapter} — ${event.pages} pages`));
      markChapterDownloaded(event.chapter);
      break;
    case "chapter_failed":
      removeBar(event);
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
}

async function renderCart() {
  const list = $("cartList");
  if (!list) return;
  let queued = [];
  try {
    const res = await api().get_cart();
    if (res && res.ok) queued = res.queued || [];
  } catch (e) { /* bridge not ready */ }

  const rows = [];
  jobs.forEach((j) => {
    if (j.finished && j.ok) return;         // completed jobs leave the queue
    rows.push({
      title: j.title || j.url || j.id,
      status: j.finished
        ? (j.ok ? "done" : ((j.result || {}).stopped ? "stopped" : "failed"))
        : "running",
      done: j.done, total: j.total, url: j.url, cover: j.cover,
    });
  });
  queued.forEach((q) => rows.push({
    title: q.title || q.url, status: "queued", url: q.url,
    selection: q.selection, cover: q.cover,
  }));

  // The header card already describes a lone download, so the queue panel
  // only appears once there is genuinely a queue to look at.
  const worthShowing = rows.length > 1 || queued.length > 0;
  $("cartCount").textContent = rows.length;
  $("cartCard").classList.toggle("hidden", !worthShowing);
  if (!worthShowing) { list.innerHTML = ""; return; }

  list.innerHTML = rows.map((r) => {
    const badge = r.status === "running"
      ? `<span class="cart-badge run">${r.total ? `${r.done}/${r.total}` : "starting"}</span>`
      : `<span class="cart-badge ${r.status}">${r.status}</span>`;
    const remove = r.status === "queued"
      ? `<button class="icon-btn cart-x" data-url="${escapeHtml(r.url || "")}"
                 data-sel="${escapeHtml(r.selection || "all")}" title="Remove">
           <span class="material-symbols-rounded">close</span></button>`
      : "";
    return `<div class="cart-row">
      <span class="cart-title" title="${escapeHtml(r.title)}">${escapeHtml(r.title)}</span>
      ${badge}${remove}</div>`;
  }).join("");

  list.querySelectorAll(".cart-x").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api().remove_from_cart(btn.dataset.url, btn.dataset.sel);
      renderCart();
      toast("Removed from queue");
    });
  });
}

/* -------------------------------------------------------------- bookmarks */

async function loadBookmarks() {
  const res = await api().get_bookmarks();
  const grid = $("bmGrid");
  grid.innerHTML = "";
  const items = (res && res.items) || [];
  $("bmEmpty").classList.toggle("hidden", items.length > 0);
  items.forEach((b, i) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.style.setProperty("--i", i);
    card.innerHTML = `
      <img loading="lazy" src="${b.cover || ""}" alt="" onerror="this.style.visibility='hidden'">
      <div class="rc-title">${escapeHtml(b.title)}</div>
      <button class="icon-btn rc-remove" title="Remove bookmark">
        <span class="material-symbols-rounded">bookmark_remove</span>
      </button>`;
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
      ? `<img class="lib-cover" loading="lazy" src="${it.cover}" onerror="this.outerHTML='<div class=\\'lib-cover ph\\'><span class=\\'material-symbols-rounded\\'>book</span></div>'">`
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

["setDedupe", "setInterleave"].forEach((id) =>
  $(id).addEventListener("change", async () => {
    await api().set_settings({
      dedupe_results: $("setDedupe").checked,
      interleave_results: $("setInterleave").checked,
    });
  }));

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
  const [statsRes, insightRes] = await Promise.all([
    callApi("get_stats"), callApi("get_insights"),
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

  // per-source bar chart
  const entries = Object.entries(perSource)
    .sort((a, b) => (b[1].chapters || 0) - (a[1].chapters || 0));
  const max = Math.max(1, ...entries.map(([, v]) => v.chapters || 0));
  $("sourceChart").innerHTML = entries.length
    ? entries.map(([name, v]) => `
        <div class="bar-row">
          <span class="b-label">${escapeHtml(name)}</span>
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
}

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
