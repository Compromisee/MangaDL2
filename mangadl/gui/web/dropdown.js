/* Custom dropdowns.
 *
 * Native <select> popups are drawn by the OS and cannot be styled, so on a
 * dark theme they appear as bright system menus that ignore the accent colour
 * and border radius. This replaces them with themed listboxes.
 *
 * Design: progressive enhancement, not replacement.
 * ------------------------------------------------
 * The real <select> stays in the DOM and remains the source of truth. It is
 * visually hidden, and a button + panel is rendered next to it. That matters
 * because the rest of the app already drives these elements directly:
 *
 *     sel.innerHTML = "...";  sel.appendChild(opt);  sel.value = "all";
 *     [...sel.options].some(...)                     $("fSort").value
 *
 * All of that keeps working untouched. A MutationObserver picks up option
 * changes, and the `value` property is wrapped so programmatic assignment
 * repaints the custom UI. Selecting an item writes to the native element and
 * dispatches a real `change` event, so existing listeners fire as before.
 *
 * Extras the native control cannot offer:
 *   - type-to-filter box once a list gets long (the genre list has ~99 items)
 *   - full keyboard support: arrows, Home/End, Enter, Escape, typeahead
 *   - panel portalled to <body> so it is never clipped by a scroll container
 *   - flips above the trigger when there is no room below
 *   - ARIA combobox/listbox roles and active-descendant tracking
 */

(function () {
  "use strict";

  var FILTER_THRESHOLD = 8;   // show the filter box past this many options
  var registry = [];          // every enhanced select, for outside-click close
  var openOne = null;         // at most one panel open at a time
  var uid = 0;

  function h(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }

  /* The native `value` setter lives on the prototype. Shadow it per element so
     `sel.value = x` from existing code also repaints our button. */
  function wrapValue(select, onSet) {
    var proto = Object.getPrototypeOf(select);
    var desc = Object.getOwnPropertyDescriptor(proto, "value")
            || Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
    if (!desc || !desc.set) return;
    Object.defineProperty(select, "value", {
      configurable: true,
      enumerable: true,
      get: function () { return desc.get.call(this); },
      set: function (v) { desc.set.call(this, v); onSet(); },
    });
  }

  function Dropdown(select) {
    var self = this;
    this.select = select;
    this.id = "dd" + (++uid);
    this.open = false;
    this.activeIndex = -1;
    this.items = [];

    select.classList.add("dd-native");
    select.setAttribute("tabindex", "-1");
    select.setAttribute("aria-hidden", "true");

    // wrapper keeps the trigger where the select used to sit
    this.root = h("div", "dd");
    select.parentNode.insertBefore(this.root, select);
    this.root.appendChild(select);

    this.button = h("button", "dd-btn");
    this.button.type = "button";
    this.button.id = this.id + "-btn";
    this.button.setAttribute("aria-haspopup", "listbox");
    this.button.setAttribute("aria-expanded", "false");

    this.label = h("span", "dd-label");
    this.caret = h("span", "dd-caret material-symbols-rounded", "expand_more");
    this.button.appendChild(this.label);
    this.button.appendChild(this.caret);
    this.root.appendChild(this.button);

    // panel is portalled to body so overflow/transform ancestors cannot clip it
    this.panel = h("div", "dd-panel");
    this.panel.id = this.id + "-panel";
    this.panel.setAttribute("role", "listbox");
    this.panel.tabIndex = -1;          // required for programmatic .focus()
    this.panel.hidden = true;

    this.filterWrap = h("div", "dd-filter");
    this.filterIcon = h("span", "material-symbols-rounded", "search");
    this.filter = h("input", "dd-filter-input");
    this.filter.type = "text";
    this.filter.placeholder = "Filter…";
    this.filter.setAttribute("aria-label", "Filter options");
    this.filterWrap.appendChild(this.filterIcon);
    this.filterWrap.appendChild(this.filter);
    this.panel.appendChild(this.filterWrap);

    this.list = h("div", "dd-list");
    this.panel.appendChild(this.list);

    this.empty = h("div", "dd-empty", "No matches");
    this.empty.hidden = true;
    this.panel.appendChild(this.empty);

    document.body.appendChild(this.panel);

    this.button.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      self.toggle();
    });
    this.button.addEventListener("keydown", function (e) { self.onButtonKey(e); });
    this.filter.addEventListener("input", function () { self.renderList(); });
    this.filter.addEventListener("keydown", function (e) { self.onPanelKey(e); });
    this.panel.addEventListener("keydown", function (e) { self.onPanelKey(e); });
    this.panel.addEventListener("mousedown", function (e) { e.stopPropagation(); });

    // repaint when the app rewrites options or flips disabled state
    this.observer = new MutationObserver(function () { self.sync(); });
    this.observer.observe(select, {
      childList: true, subtree: true, attributes: true,
      attributeFilter: ["disabled", "value"],
    });
    select.addEventListener("change", function () { self.sync(); });

    wrapValue(select, function () { self.sync(); });

    this.sync();
    registry.push(this);
  }

  Dropdown.prototype.options = function () {
    return Array.prototype.slice.call(this.select.options);
  };

  /* Mirror the native element's current state onto the trigger. */
  Dropdown.prototype.sync = function () {
    var chosen = this.select.selectedOptions && this.select.selectedOptions[0];
    var text = chosen ? chosen.textContent.trim() : "";
    this.label.textContent = text || this.select.getAttribute("data-placeholder") || "—";
    this.label.classList.toggle("dd-placeholder", !text);
    this.button.disabled = this.select.disabled;
    this.root.classList.toggle("dd-disabled", this.select.disabled);
    if (this.open) this.renderList();
  };

  Dropdown.prototype.toggle = function () {
    if (this.open) this.close(); else this.openPanel();
  };

  Dropdown.prototype.openPanel = function () {
    if (this.select.disabled) return;
    if (openOne && openOne !== this) openOne.close();
    openOne = this;
    this.open = true;

    var many = this.options().length > FILTER_THRESHOLD;
    this.filterWrap.hidden = !many;
    this.filter.value = "";

    this.panel.hidden = false;
    this.panel.classList.add("dd-open");
    this.button.setAttribute("aria-expanded", "true");
    this.button.setAttribute("aria-controls", this.panel.id);

    this.renderList();
    this.position();

    // start on the current selection so arrows move from there
    this.activeIndex = this.items.findIndex(function (it) { return it.selected; });
    if (this.activeIndex < 0 && this.items.length) this.activeIndex = 0;
    this.paintActive(true);

    if (many) this.filter.focus();
    else this.panel.focus({ preventScroll: true });
  };

  Dropdown.prototype.close = function (refocus) {
    if (!this.open) return;
    this.open = false;
    this.panel.hidden = true;
    this.panel.classList.remove("dd-open", "dd-up");
    this.button.setAttribute("aria-expanded", "false");
    this.button.removeAttribute("aria-activedescendant");
    if (openOne === this) openOne = null;
    if (refocus) this.button.focus();
  };

  /* Fixed positioning against the trigger, flipping up when short of room. */
  Dropdown.prototype.position = function () {
    var r = this.button.getBoundingClientRect();
    var margin = 8;
    var panel = this.panel;

    panel.style.minWidth = r.width + "px";
    panel.style.left = "0px";
    panel.style.top = "0px";
    panel.style.maxHeight = "";

    var ph = panel.offsetHeight;
    var below = window.innerHeight - r.bottom - margin;
    var above = r.top - margin;
    var up = ph > below && above > below;

    var maxH = Math.max(140, Math.min(320, up ? above : below));
    panel.style.maxHeight = maxH + "px";
    ph = Math.min(panel.offsetHeight, maxH);

    var left = Math.min(r.left, window.innerWidth - panel.offsetWidth - margin);
    panel.style.left = Math.max(margin, left) + "px";
    panel.style.top = (up ? r.top - ph - 6 : r.bottom + 6) + "px";
    panel.classList.toggle("dd-up", up);
  };

  Dropdown.prototype.renderList = function () {
    var self = this;
    var needle = (this.filter.value || "").trim().toLowerCase();
    this.list.innerHTML = "";
    this.items = [];

    this.options().forEach(function (opt, index) {
      var text = opt.textContent.trim();
      if (needle && text.toLowerCase().indexOf(needle) === -1) return;

      var row = h("div", "dd-item");
      row.id = self.id + "-opt" + index;
      row.setAttribute("role", "option");
      row.dataset.value = opt.value;

      var selected = opt.selected;
      row.setAttribute("aria-selected", selected ? "true" : "false");
      if (selected) row.classList.add("dd-selected");
      if (opt.disabled) row.classList.add("dd-item-disabled");

      var tick = h("span", "dd-tick material-symbols-rounded", "check");
      row.appendChild(tick);
      row.appendChild(h("span", "dd-text", text));

      row.addEventListener("click", function () {
        if (opt.disabled) return;
        self.choose(opt);
      });
      row.addEventListener("mousemove", function () {
        var i = self.items.indexOf(row);
        if (i !== self.activeIndex) { self.activeIndex = i; self.paintActive(); }
      });

      self.list.appendChild(row);
      row.selected = selected;
      self.items.push(row);
    });

    this.empty.hidden = this.items.length > 0;
    if (this.activeIndex >= this.items.length) this.activeIndex = this.items.length - 1;
    this.paintActive();
  };

  Dropdown.prototype.paintActive = function (scroll) {
    var self = this;
    this.items.forEach(function (row, i) {
      var on = i === self.activeIndex;
      row.classList.toggle("dd-active", on);
      if (on) {
        self.button.setAttribute("aria-activedescendant", row.id);
        if (scroll !== false) {
          row.scrollIntoView({ block: "nearest" });
        }
      }
    });
  };

  Dropdown.prototype.move = function (delta) {
    if (!this.items.length) return;
    var next = this.activeIndex + delta;
    if (next < 0) next = this.items.length - 1;
    if (next >= this.items.length) next = 0;
    this.activeIndex = next;
    this.paintActive();
  };

  /* Write through to the native element so existing listeners still fire. */
  Dropdown.prototype.choose = function (opt) {
    var changed = this.select.value !== opt.value;
    this.select.value = opt.value;      // wrapped setter repaints the trigger
    this.close(true);
    if (changed) {
      this.select.dispatchEvent(new Event("input", { bubbles: true }));
      this.select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  Dropdown.prototype.commitActive = function () {
    var row = this.items[this.activeIndex];
    if (!row) return;
    var match = this.options().filter(function (o) { return o.value === row.dataset.value; })[0];
    if (match && !match.disabled) this.choose(match);
  };

  /* Opening keys on the trigger, plus typeahead when closed so the control
     behaves like a real <select> (pressing "r" jumps to Romance). */
  Dropdown.prototype.onButtonKey = function (e) {
    // Short lists have no filter box, so focus stays on the trigger while the
    // panel is open. Forward navigation keys instead of reopening.
    if (this.open) {
      this.onPanelKey(e);
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp"
        || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      this.openPanel();
      if (e.key === "ArrowUp") {
        this.activeIndex = this.items.length - 1;
        this.paintActive();
      }
      return;
    }
    if (e.key === "Escape") { this.close(); return; }
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      this.typeahead(e.key);
    }
  };

  /* Jump to the next option starting with the typed run of characters. */
  Dropdown.prototype.typeahead = function (ch) {
    var self = this;
    clearTimeout(this._typeTimer);
    this._typed = (this._typed || "") + ch.toLowerCase();
    this._typeTimer = setTimeout(function () { self._typed = ""; }, 700);

    var opts = this.options();
    var match = opts.filter(function (o) {
      return !o.disabled
        && o.textContent.trim().toLowerCase().indexOf(self._typed) === 0;
    })[0];
    if (match) this.choose(match);
  };

  Dropdown.prototype.onPanelKey = function (e) {
    switch (e.key) {
      case "ArrowDown": e.preventDefault(); this.move(1); break;
      case "ArrowUp":   e.preventDefault(); this.move(-1); break;
      case "Home":      e.preventDefault(); this.activeIndex = 0; this.paintActive(); break;
      case "End":       e.preventDefault(); this.activeIndex = this.items.length - 1; this.paintActive(); break;
      case "Enter":     e.preventDefault(); this.commitActive(); break;
      case "Tab":       this.close(); break;
      case "Escape":    e.preventDefault(); this.close(true); break;
      default: break;
    }
  };

  /* ------------------------------------------------------------- global */

  document.addEventListener("mousedown", function (e) {
    if (!openOne) return;
    if (openOne.root.contains(e.target) || openOne.panel.contains(e.target)) return;
    openOne.close();
  });

  window.addEventListener("resize", function () { if (openOne) openOne.position(); });
  window.addEventListener("scroll", function () { if (openOne) openOne.position(); }, true);

  function enhance(root) {
    var scope = root || document;
    var found = scope.querySelectorAll("select:not(.dd-native)");
    Array.prototype.forEach.call(found, function (sel) {
      if (sel.multiple || sel.dataset.noCustom === "true") return;
      try {
        new Dropdown(sel);
      } catch (err) {
        // never let a styling failure break the page
        if (window.console) console.warn("dropdown enhance failed", err);
      }
    });
  }

  window.MangaDropdown = {
    enhance: enhance,
    refresh: function () { registry.forEach(function (d) { d.sync(); }); },
    closeAll: function () { if (openOne) openOne.close(); },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { enhance(); });
  } else {
    enhance();
  }
})();
