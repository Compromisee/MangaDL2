/* WeebCentral Downloader GUI logic */

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
  const ctx = canvas.getContext("2d");
  let dots = [], raf = null, enabled = true;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const gap = 46;
    dots = [];
    for (let x = gap / 2; x < canvas.width; x += gap) {
      for (let y = gap / 2; y < canvas.height; y += gap) {
        dots.push({ x, y, phase: Math.random() * Math.PI * 2, speed: 0.4 + Math.random() * 0.8 });
      }
    }
  }

  function frame(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const rgb = getComputedStyle(document.documentElement)
      .getPropertyValue("--matrix-dot").trim() || "255,255,255";
    for (const d of dots) {
      const a = 0.025 + 0.05 * (0.5 + 0.5 * Math.sin(d.phase + t * 0.0006 * d.speed));
      ctx.fillStyle = `rgba(${rgb},${a})`;
      ctx.beginPath();
      ctx.arc(d.x, d.y, 1.3, 0, Math.PI * 2);
      ctx.fill();
    }
    raf = requestAnimationFrame(frame);
  }

  function start() {
    if (!enabled || raf) return;
    resize();
    raf = requestAnimationFrame(frame);
  }
  function stop() {
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  window.addEventListener("resize", () => { if (raf) resize(); });

  return {
    set(on) { enabled = on; on ? start() : stop(); },
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
  matrix.set(s.matrix !== false);
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

function getFilters() {
  return {
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
  return f.sort !== "Best Match" || f.order !== "Ascending"
      || f.status !== "Any" || f.type !== "Any" || f.official !== "Any";
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

["fSort", "fStatus", "fType", "fOfficial"].forEach((id) =>
  $(id).addEventListener("change", () => {
    updateFilterDot();
    if (lastQuery) doSearch(true);
  }));

$("fReset").addEventListener("click", () => {
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

async function doSearch(rerun = false) {
  const query = rerun ? lastQuery : $("searchInput").value.trim();
  if (!query) return;

  if (!rerun && query.includes("weebcentral.com/")) {
    openManga(query);
    return;
  }
  lastQuery = query;

  $("searchHero").classList.add("compact");
  $("searchState").innerHTML = '<div class="spinner" style="margin:20px auto"></div>';
  $("searchResults").innerHTML = "";

  const seq = ++searchSeq;
  const res = await api().search(query, getFilters());
  if (seq !== searchSeq) return;   // a newer search superseded this one
  $("searchState").textContent = "";

  if (!res.ok) { $("searchState").textContent = "Search failed: " + res.error; return; }
  if (!res.results.length) { $("searchState").textContent = "No results found."; return; }

  const grid = $("searchResults");
  res.results.forEach((r, i) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.style.setProperty("--i", Math.min(i, 17));
    card.innerHTML = `
      <img loading="lazy" src="${r.cover || ""}" alt="" onerror="this.style.visibility='hidden'">
      <div class="rc-title">${escapeHtml(r.title)}</div>`;
    card.addEventListener("click", () => openManga(r.url));
    grid.appendChild(card);
  });
}

$("searchBtn").addEventListener("click", () => doSearch());
$("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
$("searchInput").addEventListener("input", () => {
  // restore the centered hero when the box is cleared
  if (!$("searchInput").value.trim() && !$("searchResults").children.length) {
    $("searchHero").classList.remove("compact");
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------------------------------------------------------- manga */

async function openManga(url) {
  $("railManga").disabled = false;
  showView("manga");
  $("mangaLoading").classList.remove("hidden");
  $("mangaLayout").classList.add("hidden");

  const res = await api().get_manga(url);
  $("mangaLoading").classList.add("hidden");

  if (!res.ok) {
    toast("Failed to load manga: " + res.error);
    showView("search");
    return;
  }

  state.manga = res;
  state.downloaded = new Set(res.downloaded || []);
  // preselect only chapters that are NOT downloaded yet; if all downloaded, select all
  const fresh = res.chapters
    .map((c, i) => (state.downloaded.has(c.name) ? -1 : i))
    .filter((i) => i >= 0);
  state.selected = new Set(fresh.length ? fresh : res.chapters.map((_, i) => i));

  $("mangaTitle").textContent = res.info.title;
  const cover = $("mangaCover");
  cover.style.display = "";
  cover.onerror = () => { cover.style.display = "none"; };
  cover.src = res.info.cover || "";
  if (!res.info.cover) cover.style.display = "none";
  $("mangaDesc").textContent = res.info.description || "";
  $("mangaAuthors").textContent = (res.info.authors || []).join(", ");
  setBookmarkIcon(!!res.bookmarked);

  const chips = $("mangaTags");
  chips.innerHTML = "";
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

function renderChapterList() {
  const list = $("chapterList");
  list.innerHTML = "";
  const chapters = state.manga.chapters;
  for (let i = chapters.length - 1; i >= 0; i--) {
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
  }
  $("chapterCount").textContent = chapters.length;
  const dlPill = $("downloadedCount");
  if (state.downloaded.size) {
    dlPill.textContent = `${state.downloaded.size} downloaded`;
    dlPill.classList.remove("hidden");
  } else {
    dlPill.classList.add("hidden");
  }
}

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
  $("downloadBtn").disabled = n === 0 || state.downloading;
}

$("selectAllBtn").addEventListener("click", () => {
  state.selected = new Set(state.manga.chapters.map((_, i) => i));
  refreshChapterSelection();
});
$("selectNoneBtn").addEventListener("click", () => {
  state.selected = new Set();
  refreshChapterSelection();
});
$("selectNewBtn").addEventListener("click", () => {
  state.selected = new Set(
    state.manga.chapters
      .map((c, i) => (state.downloaded.has(c.name) ? -1 : i))
      .filter((i) => i >= 0));
  refreshChapterSelection();
  toast(`Selected ${state.selected.size} new chapter${state.selected.size !== 1 ? "s" : ""}`);
});
$("selectLatestBtn").addEventListener("click", () => {
  state.selected = new Set([state.manga.chapters.length - 1]);
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
  if (folder) $("outputDir").value = folder;
});

/* -------------------------------------------------------------- download */

$("downloadBtn").addEventListener("click", async () => {
  if (!state.manga || state.selected.size === 0) return;
  if (state.downloading) { toast("A download is already running"); return; }

  const s = state.settings;
  if (s.confirm_large !== false && state.selected.size >= (s.large_threshold || 100)) {
    const ok = await confirmModal(
      "Large download",
      `You are about to download ${state.selected.size} chapters. This may take a while and use significant bandwidth. Continue?`,
      "Download");
    if (!ok) return;
  }

  const chapters = state.manga.chapters;
  const nums = [...state.selected].map((i) => chapterNumber(chapters[i].name)).sort((a, b) => a - b);
  const selection = state.selected.size === chapters.length ? "all" : nums.join(",");

  let bundle = 0;
  if (state.bundleMode === "1") bundle = 1;
  else if (state.bundleMode === "n") bundle = Math.max(2, parseInt($("bundleN").value) || 10);

  const options = {
    url: state.manga.info.url,
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

  const res = await api().start_download(options);
  if (!res.ok) { toast(res.error); return; }

  beginDownloadUI(state.manga.info.title, state.selected.size);
});

function beginDownloadUI(title, total) {
  state.downloading = true;
  state.totalChapters = total;
  state.doneChapters = 0;
  $("railDot").classList.add("on");
  $("dlEmpty").classList.add("hidden");
  $("dlActive").classList.remove("hidden");
  $("dlTitle").textContent = title;
  $("dlStatus").textContent = "Starting…";
  $("overallFill").style.width = "0%";
  $("overallText").textContent = total ? `0 / ${total}` : "…";
  $("activeChapters").innerHTML = '<div class="none">Waiting…</div>';
  $("dlLog").innerHTML = "";
  $("stopBtn").classList.remove("hidden");
  $("openFolderBtn").classList.add("hidden");
  updateDownloadButton();
  showView("downloads");
}

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

function logLine(cls, text) {
  const log = $("dlLog");
  const t = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const line = document.createElement("div");
  line.className = "log-line " + cls;
  line.innerHTML = `<span class="t">${t}</span><span>${escapeHtml(text)}</span>`;
  log.prepend(line);
  while (log.children.length > 200) log.removeChild(log.lastChild);
}

function ensureBar(chapter) {
  if (activeBars.has(chapter)) return activeBars.get(chapter);
  const wrap = $("activeChapters");
  const none = wrap.querySelector(".none");
  if (none) none.remove();
  const row = document.createElement("div");
  row.className = "ac-row";
  row.innerHTML = `
    <span class="ac-name" title="${escapeHtml(chapter)}">${escapeHtml(chapter)}</span>
    <div class="ac-bar"><div class="ac-fill"></div></div>
    <span class="ac-count">–</span>`;
  wrap.appendChild(row);
  activeBars.set(chapter, row);
  return row;
}

function removeBar(chapter) {
  const row = activeBars.get(chapter);
  if (row) { row.remove(); activeBars.delete(chapter); }
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

window.onEngineEvent = function (event) {
  switch (event.type) {
    case "status":
      $("dlStatus").textContent = event.message;
      break;
    case "plan":
      state.totalChapters = event.total;
      lastOutputDir = event.directory;
      $("dlStatus").textContent = `Downloading ${event.total} chapters`;
      $("overallText").textContent = `0 / ${event.total}`;
      logLine("info", `Saving to ${event.directory}`);
      break;
    case "chapter_start":
      ensureBar(event.chapter);
      break;
    case "chapter_progress": {
      const row = ensureBar(event.chapter);
      const pct = event.total ? Math.round((event.done / event.total) * 100) : 0;
      row.querySelector(".ac-fill").style.width = pct + "%";
      row.querySelector(".ac-count").textContent = `${event.done}/${event.total}`;
      break;
    }
    case "chapter_done":
      removeBar(event.chapter);
      state.doneChapters = event.completed;
      $("overallFill").style.width = Math.round((event.completed / event.total) * 100) + "%";
      $("overallText").textContent = `${event.completed} / ${event.total}`;
      logLine("ok", `${event.chapter} — ${event.pages} pages`);
      markChapterDownloaded(event.chapter);
      break;
    case "chapter_failed":
      removeBar(event.chapter);
      logLine("err", `Failed: ${event.chapter}`);
      break;
    case "packaging":
      $("dlStatus").textContent = `Packaging ${event.file}`;
      logLine("info", `Packing ${event.file}`);
      break;
    case "packaged":
      logLine("ok", `Created ${event.file.split(/[\\/]/).pop()}`);
      break;
    case "error":
      logLine("err", event.message);
      toast(event.message);
      break;
    case "stopped":
      logLine("info", "Stopped by user");
      break;
    case "finished": {
      state.downloading = false;
      $("railDot").classList.remove("on");
      $("stopBtn").classList.add("hidden");
      activeBars.forEach((row) => row.remove());
      activeBars.clear();
      $("activeChapters").innerHTML = '<div class="none">Idle</div>';
      const r = event.result || {};
      if (r.ok) {
        $("dlStatus").textContent = `Complete — ${r.downloaded} chapters downloaded`;
        $("overallFill").style.width = "100%";
        lastOutputDir = r.directory || lastOutputDir;
        $("openFolderBtn").classList.remove("hidden");
        toast("Download complete");
        if (state.settings.open_folder_when_done && lastOutputDir) {
          api().open_folder(lastOutputDir);
        }
      } else if (r.stopped) {
        $("dlStatus").textContent = "Stopped";
      } else {
        $("dlStatus").textContent = "Failed" + (r.error ? `: ${r.error}` : "");
      }
      updateDownloadButton();
      break;
    }
  }
};

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
  $("setChapterWorkers").value = s.chapter_workers;
  $("setImageWorkers").value = s.image_workers;
  $("setDelay").value = s.delay;
  $("setRetries").value = s.retries || 5;
  $("setReaderPath").value = s.reader_path || "";
  $("setNameSingle").value = s.name_single || "{title}";
  $("setNameChapter").value = s.name_chapter || "{title} - Chapter {chapter}";
  $("setNameRange").value = s.name_range || "{title} - Chapters {start}-{end}";
  $("setAnimations").checked = s.animations !== false;
  $("setMatrix").checked = s.matrix !== false;
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
    chapter_workers: parseInt($("setChapterWorkers").value) || 3,
    image_workers: parseInt($("setImageWorkers").value) || 6,
    delay: parseFloat($("setDelay").value) || 0.5,
    retries: parseInt($("setRetries").value) || 5,
    reader_path: $("setReaderPath").value.trim(),
    name_single: $("setNameSingle").value.trim() || "{title}",
    name_chapter: $("setNameChapter").value.trim() || "{title} - Chapter {chapter}",
    name_range: $("setNameRange").value.trim() || "{title} - Chapters {start}-{end}",
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

whenReady(async () => {
  state.settings = await api().get_settings();
  fillSettings(state.settings);
  const lib = await api().get_library();
  if (lib && lib.path) $("dataLibPath").textContent = lib.path;
  refreshLogInfo();
  checkPendingJob();
  $("searchInput").focus();
});
