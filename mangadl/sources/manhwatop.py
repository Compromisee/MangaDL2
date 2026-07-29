"""Manhwa Top source (manhwatop.com) -- Madara theme.

Install-specific findings, measured 2026-07:

Genre slugs are SEO-mangled
    This is the reason genre slugs are read off the live form rather than
    guessed anywhere in the Madara base. The site does not use ``action`` and
    ``romance``; it ships ``genre-action-new-genre``,
    ``adventure-genre-hot``, ``fantasy-new-genres``, ``josei-new-genre``,
    ``romance-genre-hot`` and 56 more in that shape. No amount of guessing
    produces those, and each wrong guess is a 404.

    ``MadaraSource._genre_label`` strips the ``new``/``hot``/``genre(s)``
    noise so the picker reads "Action", "Adventure", "Romance" while the
    request still uses the real slug.

Paths
    Series ``/manga/<slug>/``, genres ``/manga-genre/<slug>/`` (the theme
    default is correct here), listing ``/manga/?m_orderby=<key>``.

Images
    ``c3.manhwatop.com``, hotlinks fine (200 image/webp with no Referer).
"""

from .madara import MadaraSource


class ManhwaTopSource(MadaraSource):
    id = "manhwatop"
    name = "Manhwa Top"
    base_url = "https://manhwatop.com"
    domains = ("manhwatop.com", "c3.manhwatop.com")

    default_series_type = "Manhwa"

    series_prefix = "/manga/"
    genre_prefix = "manga-genre"
    browse_path = "/manga/"

    #: Fallback only, and note the shapes: these are the site's real slugs,
    #: not tidied ones. genres() prefers the live list.
    GENRES = (
        "genre-action-new-genre", "adventure-genre-hot", "genre-comedy",
        "genre-drama", "ecchi-genre-hot", "fantasy-genre-hot",
        "gender-bender-genre-hot", "harem-new", "historical-new-genre",
        "horror-genres-new", "isekai-new-genres", "josei-new-genre",
        "manhwa-hot", "martial-arts-genre-hot", "mature", "murim",
        "mystery-new-genres", "psychological-genre-hot", "romance-genre-hot",
        "school-life-genres", "sci-fi-genre-hot", "seinen-genre-hot",
        "shoujo-genres", "shounen-genres", "slice-of-life-genres",
        "smut-genre-hot", "supernatural-genres", "tragedy-genre-hot",
        "webtoons", "yaoi", "yuri",
    )
