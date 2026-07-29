"""Manhua Plus source (manhuaplus.com) -- Madara theme.

See :mod:`mangadl.sources.madara` for the shared scraping. Install-specific
findings, measured 2026-07:

Paths
    Series ``/manga/<slug>/``, genres ``/manga-genre/<slug>/``, listing
    ``/manga/?m_orderby=<key>``. All three verified; ``/manhua-genre/`` 404s.

Covers
    Cards ship the theme's ``dflazy`` placeholder in ``src`` and the real
    cover in ``data-src``, so reading ``src`` first would give every card the
    same grey rectangle. The shared parser prefers ``data-src`` for exactly
    this reason. Covers are WordPress thumbnails (``-193x278``) served from
    the site itself and hotlink fine.

Chapters
    The AJAX route returns the full list in one request (27 chapters on the
    series measured) -- there is no "load more".

Images
    ``cdn.manhuaplus.com``, hotlinks fine (200 image/jpeg, no Referer).
"""

from .madara import MadaraSource


class ManhuaPlusSource(MadaraSource):
    id = "manhuaplus"
    name = "Manhua Plus"
    base_url = "https://manhuaplus.com"
    domains = ("manhuaplus.com", "cdn.manhuaplus.com")

    default_series_type = "Manhua"

    series_prefix = "/manga/"
    genre_prefix = "manga-genre"
    browse_path = "/manga/"

    #: Fallback only -- genres() reads the live 46-slug list off the site.
    GENRES = (
        "action", "adult", "adventure", "comedy", "cooking", "doujinshi",
        "drama", "ecchi", "fantasy", "gender-bender", "harem", "historical",
        "horror", "josei", "manhua", "manhwa", "martial-arts", "mature",
        "mecha", "mystery", "one-shot", "psychological", "romance",
        "school-life", "sci-fi", "seinen", "shoujo", "shounen",
        "slice-of-life", "smut", "sports", "supernatural", "tragedy",
        "webtoon", "yaoi", "yuri",
    )
