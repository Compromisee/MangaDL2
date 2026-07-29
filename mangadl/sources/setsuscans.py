"""Setsu Scans source (setsuscans.com) -- Madara theme, Cloudflare-gated.

**Read this before reporting it broken.** As of 2026-07 the site answers
**HTTP 403 to every request** from a plain HTTP client, with
``cf-mitigated: challenge``, ``server: cloudflare`` and a
``<title>Just a moment...</title>`` interstitial. That is true for ``/``,
``/manga/`` and ``www.``, with a full set of browser headers
(``Sec-Fetch-*``, ``Upgrade-Insecure-Requests``, real UA, Accept-Language).
It is a JavaScript challenge, not a block on this client -- there is nothing
a header can do about it.

So this source is registered with ``needs_flaresolverr = True``. The base
class already routes challenged responses through FlareSolverr when one is
reachable; without it, every call here will fail with a clear Cloudflare
error rather than silently returning nothing. Weeb Central is in the same
position and has been since v1.0.

What the scraping is based on
-----------------------------
Because the live site cannot be read, the layout was taken from the Internet
Archive snapshot of 2025-07-09 (``web.archive.org/web/20250709010555/``),
which confirms:

* ``<meta generator>``: "Powered by Madara", ``themes/madara-child-mk``
* series live at ``/manga/<slug>/`` (86 such links in the snapshot)
* the listing offers ``?m_orderby=latest|alphabet|rating|trending|views``

Everything else is the stock Madara behaviour implemented in
:mod:`mangadl.sources.madara`. The genre prefix is the theme default,
``/manga-genre/``; the snapshot carries no genre archive links, so unlike the
other five sites added in this release **that one path is unverified**. If a
FlareSolverr instance is available and genres 404, that is the line to look
at.
"""

from .madara import MadaraSource


class SetsuScansSource(MadaraSource):
    id = "setsuscans"
    name = "Setsu Scans"
    base_url = "https://setsuscans.com"
    domains = ("setsuscans.com",)

    #: Mixed manga/manhwa catalogue; no reliable per-card type, so no default.
    default_series_type = None

    #: Every request answers 403 + cf-mitigated: challenge without a solver.
    needs_flaresolverr = True

    series_prefix = "/manga/"
    genre_prefix = "manga-genre"
    browse_path = "/manga/"

    #: Stock Madara genre set. genres() prefers the live form when the site
    #: is reachable; this is what is offered when it is not.
    GENRES = (
        "action", "adventure", "comedy", "drama", "ecchi", "fantasy",
        "gender-bender", "harem", "historical", "horror", "isekai", "josei",
        "manga", "manhua", "manhwa", "martial-arts", "mature", "mecha",
        "mystery", "one-shot", "psychological", "romance", "school-life",
        "sci-fi", "seinen", "shoujo", "shounen", "slice-of-life", "smut",
        "sports", "supernatural", "tragedy", "webtoon", "yaoi", "yuri",
    )
