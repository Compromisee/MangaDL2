"""Toonily source (toonily.com) -- Madara theme, manhwa only.

Install-specific findings, measured 2026-07:

Paths
    Series live at ``/serie/<slug>-<hash>/`` (singular "serie"), the listing
    is ``/search/`` and genres are ``/webtoon-genre/<slug>/``. ``/genre/``
    also resolves; ``/manga-genre/`` and ``/manhua-genre/`` are 404s.

Search pagination -- the trap
    ``/page/2/?s=<term>`` returns **page one**: 18 results, all 18 identical
    to page one (measured). ``&paged=2`` returns 18 results with **zero**
    overlap. The shared Madara base uses ``paged=`` for exactly this reason;
    on the other five Madara sites both forms work, here only one does.

    Browse pagination is the opposite way round: ``/search/page/2/`` works
    normally.

Page CDN needs a Referer
    ``data.tnlycdn.com`` answers **403 to any Referer that is not toonily.com**
    -- measured 403 with none, 403 with ``example.com``, 200 with
    ``https://toonily.com/`` and 200 with the chapter URL. The base class
    already forwards each chapter's ``referer`` to every image download, and
    the Madara base sets it to the series URL, so downloads work.

    Covers are different: ``static.tnlycdn.com`` serves them with **no**
    Referer (200 both ways), so ``cover_needs_referer`` stays False and the
    GUI does not need to proxy them.

Adult content
    The catalogue is largely mature manhwa and the site ships a "Mature"
    genre, but it is not an adult-only site the way Manhwa18 or nhentai are,
    so it is **not** flagged ``adult_only``. Individual titles that carry the
    Mature/Adult genre are tagged as such and Safe mode filters on the tags.
"""

from .madara import MadaraSource


class ToonilySource(MadaraSource):
    id = "toonily"
    name = "Toonily"
    base_url = "https://toonily.com"
    domains = ("toonily.com", "static.tnlycdn.com", "data.tnlycdn.com")

    default_series_type = "Manhwa"

    #: Singular "serie", and the listing is /search/, not /manga/.
    series_prefix = "/serie/"
    genre_prefix = "webtoon-genre"
    browse_path = "/search/"

    #: Fallback only -- genres() reads the live 30-slug list off the site.
    GENRES = (
        "action", "adventure", "comedy", "crime", "drama", "fantasy",
        "gossip", "historical", "horror", "isekai", "josei", "magic",
        "mature", "mystery", "psychological", "romance", "school-life",
        "scifi-webtoon", "seinen", "shoujo", "shounen", "slice-of-life",
        "sports", "supernatural", "thriller", "tragedy", "villainess",
        "wuxia", "yaoi", "yuri",
    )
