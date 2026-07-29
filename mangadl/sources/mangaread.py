"""MangaRead source (mangaread.org) -- Madara theme.

Install-specific findings, measured 2026-07:

Host
    The canonical host is ``www.mangaread.org``; the bare domain redirects
    there. The ``www.`` form is used directly so every request saves a hop.

Genres
    ``/genres/<slug>/`` -- plural, and *not* the theme default.
    ``/manga-genre/<slug>/`` is a hard 404 here, which is the wrong guess for
    a Madara site and would have silently produced an empty genre picker.

Catalogue
    Mixed: manga, manhwa and manhua, with the type carried as a genre tag
    ("Manhwa", "Manhua", "Manga"), so ``classify_type`` resolves it per title
    and no ``default_series_type`` is set -- claiming one would mislabel two
    thirds of the catalogue.

Images
    Served from the site's own ``/wp-content/uploads/WP-manga/data/`` and
    hotlink fine (200 image/jpeg with no Referer).
"""

from .madara import MadaraSource


class MangaReadSource(MadaraSource):
    id = "mangaread"
    name = "MangaRead"
    base_url = "https://www.mangaread.org"
    domains = ("mangaread.org",)

    #: Genuinely mixed catalogue -- let each title's own tags decide.
    default_series_type = None

    series_prefix = "/manga/"
    #: /manga-genre/ is a 404 here; the archive is /genres/.
    genre_prefix = "genres"
    browse_path = "/manga/"

    #: Fallback only -- genres() reads the live 48-slug list off the site.
    GENRES = (
        "action", "adventure", "comedy", "cooking", "doujinshi", "drama",
        "ecchi", "fantasy", "gender-bender", "harem", "historical", "horror",
        "isekai", "josei", "magic", "manga", "manhua", "manhwa",
        "martial-arts", "mature", "mecha", "military", "mystery", "one-shot",
        "psychological", "reincarnation", "romance", "school-life", "sci-fi",
        "seinen", "shoujo", "shoujo-ai", "shounen", "shounen-ai",
        "slice-of-life", "smut", "sports", "super-power", "supernatural",
        "thriller", "tragedy", "webtoon",
    )
