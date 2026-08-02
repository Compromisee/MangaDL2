#!/usr/bin/env python3
"""MangaDL as a LAN server — use the desktop UI from your phone.

    python server.py                      # http://<this-pc>:8577
    python server.py --port 9000
    python server.py --host 127.0.0.1     # this machine only
    python server.py --no-auth            # skip the access token

Everything happens on the host computer
---------------------------------------
The phone is a **remote control, nothing more**. It sends
``POST /api/<method>`` to this machine; the request is executed here, by the
same ``mangadl.gui.Api`` object the desktop app uses. So:

* the phone never talks to a manga site — every scrape leaves the host's IP;
* files are written to the host's disk, in the host's output folder;
* the library, settings, history and job journals stay in the host's
  ``~/.mangadl/``;
* closing the browser on the phone does not interrupt a download.

That is the point of routing through the host rather than peer-to-peer: your
phone's connection is not used for the actual downloading, and a phone that
walks out of Wi-Fi range does not abort a 300-chapter job.

Why the whole desktop UI, not a separate mobile one
---------------------------------------------------
``mangadl/gui/web`` is already a plain HTML/JS app that talks to Python over
one narrow bridge — ``window.pywebview.api.<method>(...)`` returning a
promise. ``static/bridge.js`` reimplements exactly that shape over ``fetch``,
so the same UI runs unmodified in a phone browser. One UI to maintain, and
no risk of the two drifting apart.

Two things genuinely cannot work remotely, and are handled honestly rather
than silently failing:

``choose_folder`` / ``choose_file``
    A native file dialog would open on the *host's* screen, where nobody is
    looking. They return an error telling you to type the path instead.
``open_folder`` / ``open_in_reader``
    These would open a window on the host. Allowed, because "start it
    downloading and open the folder on the PC" is a real thing to want, but
    they say plainly that they acted on the host.

Security
--------
This binds to your LAN. An access token is generated at startup, printed to
the console and embedded in the QR/URL you open on the phone; every API call
must carry it. It is a shared secret over plain HTTP, not real
authentication — do not port-forward this to the internet.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, Response, abort, jsonify, request, send_from_directory
except ImportError:                                        # pragma: no cover
    print("Flask is not installed. Run:\n\n    pip install flask\n"
          "\nor install the server extra:\n\n    pip install -e \".[server]\"\n",
          file=sys.stderr)
    raise SystemExit(1)

from mangadl import logs as wclogs
from mangadl.gui import Api

logger = logging.getLogger("mangadl.server")

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "mangadl", "gui", "web")

DEFAULT_PORT = 8577

#: Methods that would act on the host's screen and cannot work from a phone.
BLOCKED = {
    "choose_folder": ("Pick a folder on the phone? There is no folder picker "
                      "here — type the path as it looks on the host PC, "
                      "e.g. D:/Manga"),
    "choose_file": ("No file picker over the network — type the full path as "
                    "it looks on the host PC."),
}

#: Methods that are host-side actions, allowed but worth being clear about.
HOST_SIDE = {"open_folder", "open_in_reader", "open_url"}

#: Never reachable over HTTP: it would tear down the process serving you.
FORBIDDEN = {"shutdown"}


class EventBuffer:
    """Collects engine events for polling clients.

    The desktop app pushes events into the page with
    ``window.evaluate_js``. There is no such channel to a browser on another
    device, so events are buffered here and the page drains them with
    ``GET /api/_events?since=N``.

    Long-polling rather than a WebSocket or SSE: it needs no extra
    dependency, survives a phone sleeping and reconnecting, and the payload
    is already batched by the Api's own coalescing.
    """

    #: Ring size. A long download emits a lot of chapter_progress; a client
    #: that has been away simply resumes from the oldest event still held.
    LIMIT = 2000

    def __init__(self):
        self._events = []
        self._seq = 0
        self._lock = threading.Condition()

    def push(self, event):
        with self._lock:
            self._seq += 1
            self._events.append((self._seq, event))
            if len(self._events) > self.LIMIT:
                del self._events[:len(self._events) - self.LIMIT]
            self._lock.notify_all()

    def since(self, cursor, timeout=25.0):
        """Events newer than ``cursor``, waiting up to ``timeout`` for one.

        Returning promptly when idle would mean a request per second per
        phone; waiting means a quiet app costs one open connection.
        """
        deadline = time.monotonic() + timeout
        with self._lock:
            while True:
                fresh = [e for seq, e in self._events if seq > cursor]
                if fresh or time.monotonic() >= deadline:
                    return self._seq, fresh
                self._lock.wait(min(1.0, deadline - time.monotonic()))

    def cursor(self):
        with self._lock:
            return self._seq


class ServerApi(Api):
    """The desktop Api, with its event channel pointed at a buffer.

    Subclassing rather than copying: every endpoint the desktop app gains
    works here on the next release with no extra wiring.
    """

    def __init__(self, buffer):
        super().__init__()
        self._buffer = buffer
        # Api._push() returns early when self.window is None, which is how
        # it avoids talking to a window that does not exist. Give it a
        # truthy stand-in so the events reach _flush() instead.
        self.window = _NullWindow()

    def _flush(self):
        """Send everything queued into the buffer instead of a webview."""
        with self._push_lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None
            batch = self._pending_events
            batch += list(self._pending_progress.values())
            self._pending_events = []
            self._pending_progress = {}
        for event in batch:
            self._buffer.push(event)


class _NullWindow:
    """Stands in for the pywebview window. Only truthiness is required."""

    def evaluate_js(self, *_args, **_kwargs):
        return None


def local_ip():
    """The address a phone on the same Wi-Fi should use.

    Connecting a UDP socket to an off-net address asks the OS which
    interface it would route through, without sending anything. Reading
    ``gethostbyname(gethostname())`` instead returns 127.0.1.1 on most Linux
    boxes, which is useless to a phone.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def create_app(token=None, api=None, buffer=None):
    """Build the Flask app. Exposed separately so tests can drive it."""
    buffer = buffer if buffer is not None else EventBuffer()
    api = api if api is not None else ServerApi(buffer)

    app = Flask(__name__, static_folder=None)
    app.config["MANGADL_TOKEN"] = token
    app.config["MANGADL_API"] = api
    app.config["MANGADL_BUFFER"] = buffer

    # ----------------------------------------------------------- auth

    def authorised():
        if not token:
            return True
        supplied = (request.headers.get("X-MangaDL-Token")
                    or request.args.get("token")
                    or (request.get_json(silent=True) or {}).get("_token"))
        # Constant-time: this is a shared secret in a query string, so the
        # comparison is the one part that costs nothing to get right.
        return bool(supplied) and secrets.compare_digest(str(supplied), token)

    # -------------------------------------------------------- the page

    @app.get("/")
    def index():
        if token and not authorised():
            return Response(_TOKEN_PAGE, mimetype="text/html", status=401)
        return Response(_page_html(), mimetype="text/html")

    @app.get("/<path:filename>")
    def asset(filename):
        """Serve the desktop UI's own assets untouched."""
        # Defence in depth. Werkzeug already normalises the URL before
        # routing, so "../../etc/passwd" never reaches here as a traversal
        # -- verified by removing this check and re-running the attacks,
        # which still 404'd. It stays because a future change to how this
        # route is mounted should not silently make the app serve the disk.
        full = os.path.normpath(os.path.join(WEB_DIR, filename))
        if not full.startswith(os.path.realpath(WEB_DIR) + os.sep) and \
           not full.startswith(WEB_DIR + os.sep):
            abort(404)
        if not os.path.isfile(full):
            abort(404)
        return send_from_directory(WEB_DIR, filename)

    @app.get("/bridge.js")
    def bridge():
        """The shim that makes fetch() look like window.pywebview.api."""
        return Response(_BRIDGE_JS.replace("__TOKEN__", token or ""),
                        mimetype="application/javascript")

    # ------------------------------------------------------------ api

    @app.post("/api/<method>")
    def call(method):
        if not authorised():
            return jsonify({"ok": False, "error": "Bad or missing token"}), 401

        if method in FORBIDDEN:
            return jsonify({"ok": False,
                            "error": "Not available over the network"}), 403
        if method in BLOCKED:
            return jsonify({"ok": False, "error": BLOCKED[method]})

        if method.startswith("_"):
            return jsonify({"ok": False, "error": "Unknown method"}), 404
        fn = getattr(api, method, None)
        if fn is None or not callable(fn):
            return jsonify({"ok": False,
                            "error": f"Unknown method '{method}'"}), 404

        payload = request.get_json(silent=True) or {}
        args = payload.get("args", [])
        if not isinstance(args, list):
            args = [args]

        try:
            result = fn(*args)
        except TypeError as exc:
            # A wrong-arity call is a client bug, not a server fault; say so
            # rather than returning a 500 the UI cannot interpret.
            logger.warning("bad call to %s: %s", method, exc)
            return jsonify({"ok": False, "error": f"{method}: {exc}"}), 400
        except Exception as exc:
            logger.exception("api.%s failed", method)
            return jsonify({"ok": False, "error": str(exc)}), 500

        if method in HOST_SIDE and isinstance(result, dict) and result.get("ok"):
            result = dict(result, host_side=True)
        return jsonify({"result": _safe(result)})

    @app.get("/api/_events")
    def events():
        if not authorised():
            return jsonify({"ok": False, "error": "Bad or missing token"}), 401
        try:
            cursor = int(request.args.get("since", 0))
        except (TypeError, ValueError):
            cursor = 0
        # A client that reconnects with a cursor from a previous run of the
        # server would otherwise wait forever for events numbered above it.
        if cursor > buffer.cursor():
            cursor = 0
        seq, fresh = buffer.since(cursor)
        return jsonify({"ok": True, "cursor": seq, "events": fresh})

    @app.get("/api/_ping")
    def ping():
        return jsonify({"ok": True, "app": "mangadl",
                        "auth": bool(token),
                        "authorised": authorised()})

    return app


def _page_html():
    """The desktop page with the remote bridge injected.

    The file on disk is left exactly as the desktop app needs it: no
    ``if remote`` branches in the UI, and no second copy of index.html to
    keep in sync. The bridge tag goes in immediately before dropdown.js so
    ``window.pywebview`` exists by the time app.js runs.
    """
    with open(os.path.join(WEB_DIR, "index.html"), encoding="utf-8") as fh:
        html = fh.read()

    anchor = '<script src="dropdown.js"></script>'
    tag = ('<script src="/bridge.js"></script>\n'
           '<meta name="viewport" content="width=device-width,'
           'initial-scale=1,viewport-fit=cover">\n')
    if anchor in html:
        html = html.replace(anchor, tag + anchor, 1)
    else:                                   # markup moved; still work
        html = html.replace("</body>", tag + "</body>", 1)
    return html


def _safe(value):
    """Make sure whatever the Api returned survives JSON encoding."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


_TOKEN_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MangaDL</title><style>
body{background:#0b0a12;color:#f2f0ff;font:16px/1.6 system-ui,sans-serif;
     display:grid;place-items:center;height:100vh;margin:0;text-align:center}
div{max-width:34ch;padding:24px}code{background:#1c1b28;padding:2px 6px;
     border-radius:6px;font-size:14px}
</style></head><body><div>
<h2>Access token required</h2>
<p>Open the link printed in the terminal on the host PC — it already
carries the token.</p>
<p><code>http://HOST:PORT/?token=…</code></p>
</div></body></html>"""


#: Reimplements window.pywebview.api over fetch, so the desktop UI runs
#: unmodified. Loaded before app.js by the injected tag in index.html.
_BRIDGE_JS = r"""
/* MangaDL remote bridge -- makes a browser look like pywebview to app.js. */
(function () {
  "use strict";
  var TOKEN = "__TOKEN__";

  function call(method, args) {
    return fetch("/api/" + method, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-MangaDL-Token": TOKEN,
      },
      body: JSON.stringify({args: args, _token: TOKEN}),
    }).then(function (response) {
      return response.json().catch(function () { return {}; });
    }).then(function (payload) {
      if (payload && "result" in payload) return payload.result;
      // Mirror the desktop shape: the UI expects {ok:false,error:...}
      // rather than a rejected promise, and handles it gracefully.
      return payload || {ok: false, error: "No response"};
    }).catch(function (err) {
      return {ok: false, error: String(err)};
    });
  }

  /* Every method resolves lazily, so the shim never needs a list of the
     113 endpoints -- and never goes stale when one is added. */
  var api = new Proxy({}, {
    get: function (_target, name) {
      if (typeof name !== "string") return undefined;
      return function () {
        return call(name, Array.prototype.slice.call(arguments));
      };
    },
    has: function () { return true; },
  });

  window.pywebview = {api: api};

  /* Engine events. The desktop app has them pushed in with evaluate_js;
     here the page pulls them. Long-poll, so an idle app is one open
     connection rather than a request every second. */
  var cursor = 0;
  var stopped = false;

  function poll() {
    if (stopped) return;
    fetch("/api/_events?since=" + cursor + "&token=" + encodeURIComponent(TOKEN))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.ok) {
          cursor = data.cursor;
          if (data.events && data.events.length &&
              typeof window.onEngineEvents === "function") {
            window.onEngineEvents(data.events);
          }
        }
        setTimeout(poll, 50);
      })
      .catch(function () {
        // Phone slept, Wi-Fi dropped, host restarted: back off and retry
        // rather than giving up on the session.
        setTimeout(poll, 2000);
      });
  }

  /* pywebviewready is what app.js waits for before booting. */
  function ready() {
    poll();
    window.dispatchEvent(new Event("pywebviewready"));
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ready);
  } else {
    ready();
  }

  window.addEventListener("beforeunload", function () { stopped = true; });
})();
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="server.py",
        description="Run MangaDL as a LAN server you can drive from a phone. "
                    "All downloading happens on this computer.")
    parser.add_argument("--host", default="0.0.0.0",
                        help="interface to bind (default: every interface, "
                             "so other devices can reach it)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"port (default: {DEFAULT_PORT})")
    parser.add_argument("--no-auth", action="store_true",
                        help="do not require an access token (trusted "
                             "networks only)")
    parser.add_argument("--token", default=None,
                        help="use a fixed token instead of a random one")
    parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    wclogs.setup_logging()

    token = None if args.no_auth else (args.token or secrets.token_urlsafe(12))
    app = create_app(token=token)

    address = local_ip() if args.host == "0.0.0.0" else args.host
    suffix = f"/?token={token}" if token else "/"
    url = f"http://{address}:{args.port}{suffix}"

    line = "─" * 62
    print(f"\n{line}")
    print("  MangaDL server")
    print(f"{line}")
    print(f"  On this PC     http://localhost:{args.port}{suffix}")
    print(f"  On your phone  {url}")
    if token:
        print(f"\n  Access token   {token}")
    else:
        print("\n  Access token   DISABLED (--no-auth)")
    print("\n  Downloads run on this computer and are saved here.")
    print("  Leave this window open; closing the phone's browser is fine.")
    print(f"{line}\n")

    try:
        app.run(host=args.host, port=args.port, debug=args.debug,
                threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            app.config["MANGADL_API"].shutdown()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
