"""Manhua Top source (manhuatop.org) -- Madara theme.

See :mod:`mangadl.sources.madara` for how the theme is scraped. Only what is
specific to this install is recorded here, measured 2026-07:

Rate limiting
    The site answers **HTTP 503** to the first request from a cold client and
    200 to retries a few seconds later (measured: 503, then 200/200/200). The
    base class already retries with backoff, so this is handled -- but it is
    why the source can look dead on the very first search of a session.

Series prefix
    ``/manhua/<slug>/`` -- there is no ``/manga/<slug>/``.

Genres
    ``/manhua-genre/<slug>/``. ``/manga-genre/``, ``/webtoon-genre/`` and
    ``/genre/`` all 404 here.

Browse path
    ``/manga/`` is the listing, even though series live under ``/manhua/``.
    ``/manhua/?m_orderby=views`` returns **zero** cards -- consistently, over
    four attempts spaced three seconds apart -- so using the obvious path
    would have produced a source that silently never browses.

Cards
    This child theme drops ``.post-title`` entirely: the title link is only
    ``h3 a`` (measured 0 vs 12 matches per page), which the shared base
    already falls back to. Headings are prefixed with "HOT"/"NEW" badges,
    stripped by the base parser.

Images
    ``s3.manhuatop.org``, hotlinks fine (200 image/jpeg with no Referer).
"""

from .madara import MadaraSource


class ManhuaTopSource(MadaraSource):
    id = "manhuatop"
    name = "Manhua Top"
    base_url = "https://manhuatop.org"
    domains = ("manhuatop.org", "s3.manhuatop.org")

    default_series_type = "Manhua"

    series_prefix = "/manhua/"
    genre_prefix = "manhua-genre"
    #: /manhua/ returns an empty grid; /manga/ is the real listing.
    browse_path = "/manga/"

    #: Fallback only -- genres() reads the live list off the site's own form,
    #: which currently exposes 114 slugs including install-specific ones.
    GENRES = (
        "action", "adventure", "comedy", "cultivation", "drama", "dungeons",
        "fantasy", "game", "harem", "historical", "horror", "isekai",
        "magic", "manhua", "manhwa", "martial-arts", "mature", "murim",
        "mystery", "reincarnation", "romance", "school-life", "sci-fi",
        "seinen", "shounen", "slice-of-life", "supernatural", "system",
        "time-travel", "tragedy", "transmigration", "villainess", "wuxia",
    )
