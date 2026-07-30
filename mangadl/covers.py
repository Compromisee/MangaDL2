"""Cover rebuilder: give every CBZ folder a ``cover.jpg``.

What it does
------------
Walk a folder tree, find every ``.cbz``, work out the series each one belongs
to, search the enabled sources for a cover, and write ``cover.jpg`` **next to
the CBZ** -- not in the parent.

Two rules make that harder than it sounds, and both come straight from how
real libraries look:

**1. One series per folder.** If several different series sit loose in the
same directory, writing one ``cover.jpg`` there would be wrong for all but
one of them. So those archives are first moved into a subfolder each, named
after the series, and the cover goes in with its archive. Archives that are
already alone with their own series are left exactly where they are -- this
never reorganises a library that is already tidy.

**2. Titles have to be recovered from filenames.** A CBZ is named for what is
inside it, not for the series alone::

    Afterlife Diner - Chapters 001.cbz
    Afterlife Diner - Chapters 001-050.cbz
    Afterlife Diner - Chapters 001-003, 007-008, 020.cbz
    Afterlife Diner - Chapter 005.cbz

...and third-party libraries add their own noise: ``[Group]`` prefixes,
``(2024)`` years, ``v03``, ``c045``, scanlator suffixes, resolution tags.
:func:`clean_title` strips all of it so the search actually matches.

Nothing is destructive
----------------------
* Planning and applying are separate: :func:`plan` only reads.
* An existing ``cover.jpg`` is skipped unless ``overwrite`` is set.
* Moving a file never overwrites another; a clashing name gets a suffix.
* Every failure is collected and reported rather than aborting the run.
"""

import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)

#: Archive types worth covering.
ARCHIVE_EXTENSIONS = (".cbz", ".cbr", ".cb7", ".zip")

#: Cover filenames already understood by comic readers, in preference order.
COVER_NAMES = ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp",
               "folder.jpg", "poster.jpg")

# --------------------------------------------------------------- cleaning
#
# Each pattern removes one naming convention. Order matters: bracketed groups
# go first so their contents cannot be mistaken for chapter markers.

#: "[Group]", "(2024)", "{v2}" -- anywhere in the name.
_BRACKETED = re.compile(r"[\[\(\{][^\]\)\}]*[\]\)\}]")

#: MangaDL's own suffixes, and the usual third-party equivalents.
#: Handles "Chapter 5", "Chapters 001-050", "Ch. 3-9", "c045", "#12".
_CHAPTER_TAIL = re.compile(
    r"""[\s._-]*                       # separator before the marker
        (?:-\s*)?                      # MangaDL writes " - Chapters ..."
        (?:chapters?|chaps?|ch|c|episodes?|eps?|e|\#)
        [\s._]*                        # "Chapter 5", "Ch.5", "c045"
        \d+(?:\.\d+)?                  # the number
        (?:\s*[-–—]\s*\d+(?:\.\d+)?)?  # an inclusive range: 001-050
        (?:\s*,\s*\d+(?:\.\d+)?        # further comma-separated runs
           (?:\s*[-–—]\s*\d+(?:\.\d+)?)?)*
        .*$                            # and anything after it
    """, re.I | re.X)

#: Volume markers: "Vol 3", "v03", "Volume 12".
_VOLUME_TAIL = re.compile(
    r"[\s._-]*(?:-\s*)?(?:vol(?:ume)?|v)[\s._]*\d+(?:\.\d+)?.*$", re.I)

#: A trailing bare number that is clearly an index, e.g. "Series - 005".
#: Requires a dash separator OR zero-padding: plain "Series 2" is a title
#: ("Kingdom 2", "Overlord 3"), whereas "Series - 005" and "Series 005" are
#: indexes. Getting this wrong truncates real titles.
_TRAILING_INDEX = re.compile(
    r"(?:[\s._]*-[\s._]*\d{1,4}(?:\.\d+)?"      # " - 5", " - 005"
    r"|[\s._]+0\d{1,3}(?:\.\d+)?)$")            # " 005" (zero padded)

#: Quality/format noise some releases carry.
_QUALITY = re.compile(
    r"\b(?:\d{3,4}p|hd|fhd|uhd|4k|web[\s-]?rip|digital|scan(?:s|ned)?|"
    r"colou?red|official|raw|complete[d]?|repack|fixed|v\d)\b", re.I)

#: Separators that stand in for spaces in filenames.
_SEPARATORS = re.compile(r"[._]+")


def clean_title(name):
    """Recover a searchable series title from a file or folder name.

    ``"[Group] Afterlife Diner - Chapters 001-050 (2024) [1080p].cbz"``
    becomes ``"Afterlife Diner"``.

    Never returns an empty string when the input had any word characters:
    if stripping removes everything, the least-stripped form is kept. A
    title reduced to "" would search for nothing and match everything.
    """
    text = str(name or "")
    text = os.path.splitext(text)[0]

    stages = [text]
    text = _BRACKETED.sub(" ", text)
    stages.append(text)
    text = _SEPARATORS.sub(" ", text)
    stages.append(text)
    text = _QUALITY.sub(" ", text)
    stages.append(text)
    text = _CHAPTER_TAIL.sub("", text)
    stages.append(text)
    text = _VOLUME_TAIL.sub("", text)
    stages.append(text)
    text = _TRAILING_INDEX.sub("", text)
    stages.append(text)

    # Walk back to the last stage that still held something.
    for candidate in reversed(stages):
        cleaned = re.sub(r"\s+", " ", candidate).strip(" -–—_,.")
        if cleaned:
            return cleaned
    return ""


def series_key(name):
    """Case/punctuation-insensitive identity for grouping archives."""
    return re.sub(r"[^a-z0-9]+", " ", clean_title(name).lower()).strip()


# ---------------------------------------------------------------- scanning


def _archives_in(directory):
    try:
        entries = os.listdir(directory)
    except OSError:
        return []
    return sorted(
        name for name in entries
        if name.lower().endswith(ARCHIVE_EXTENSIONS)
        and os.path.isfile(os.path.join(directory, name))
    )


def existing_cover(directory):
    """Path of a cover already in this folder, or ``None``."""
    for name in COVER_NAMES:
        path = os.path.join(directory, name)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return path
    return None


def scan(root, overwrite=False):
    """Plan the work for one tree, without changing anything.

    Returns a list of *groups*, each describing one series found in one
    directory::

        {"title", "key", "directory", "archives", "needs_move",
         "target_dir", "has_cover"}

    ``needs_move`` is True when the directory holds more than one distinct
    series, so this group's archives must be given a folder of their own.
    """
    root = os.path.abspath(os.path.expanduser(root or ""))
    groups = []
    if not os.path.isdir(root):
        return groups

    for directory, subdirs, _files in os.walk(root):
        # Skip the raw page folders the downloader leaves behind.
        subdirs[:] = [d for d in subdirs if d not in ("raw", ".raw")]

        archives = _archives_in(directory)
        if not archives:
            continue

        by_series = {}
        for archive in archives:
            key = series_key(archive) or "unknown"
            by_series.setdefault(key, []).append(archive)

        # Several series loose in one folder: each needs its own home, or a
        # single cover.jpg here would be wrong for all but one of them.
        mixed = len(by_series) > 1

        for key, names in sorted(by_series.items()):
            title = clean_title(names[0])
            target = os.path.join(directory, title) if mixed else directory
            groups.append({
                "title": title,
                "key": key,
                "directory": directory,
                "archives": names,
                "needs_move": mixed,
                "target_dir": target,
                "has_cover": existing_cover(target) is not None,
            })

    return groups


def plan(root, overwrite=False):
    """Groups that still need a cover (or all of them when overwriting)."""
    return [g for g in scan(root) if overwrite or not g["has_cover"]]


# ----------------------------------------------------------------- moving


def _unique_path(path):
    """A path that does not exist yet, by adding ' (2)', ' (3)', ..."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    index = 2
    while os.path.exists(f"{stem} ({index}){ext}"):
        index += 1
    return f"{stem} ({index}){ext}"


def isolate(group, dry_run=False):
    """Move a group's archives into their own folder when they share one.

    Returns the directory the cover belongs in. Existing files are never
    overwritten -- a clash is renamed.
    """
    if not group.get("needs_move"):
        return group["directory"]

    target = group["target_dir"]
    if dry_run:
        return target

    os.makedirs(target, exist_ok=True)
    for name in list(group["archives"]):
        source = os.path.join(group["directory"], name)
        if not os.path.isfile(source):
            continue
        destination = _unique_path(os.path.join(target, name))
        try:
            shutil.move(source, destination)
        except OSError as e:
            logger.warning("could not move %s: %s", source, e)
            raise
    return target


# ---------------------------------------------------------------- covers


def candidates(title, sources=None, limit=6, timeout=None):
    """Cover candidates for a title, from every enabled source.

    Returns ``[{"title", "cover", "source", "source_name", "url", "score"}]``
    ranked best-first. Scoring favours an exact title match, because a fuzzy
    hit on a long catalogue is usually a different series entirely.
    """
    from .features import _normalise_title
    from .sources import search_all

    title = (title or "").strip()
    if not title:
        return []

    try:
        results = search_all(title, source_ids=sources, limit=limit,
                             use_config=sources is None)
    except Exception as e:
        logger.warning("cover search failed for %r: %s", title, e)
        return []

    wanted = _normalise_title(title)
    ranked = []
    for row in results:
        cover = (row.get("cover") or "").strip()
        if not cover:
            continue
        found = _normalise_title(row.get("title"))
        if found == wanted:
            score = 100
        elif wanted and (wanted in found or found in wanted):
            score = 70
        else:
            # Weak match: keep it, but rank it below anything better. The
            # user picks, so a wrong-but-plausible option is not harmful --
            # silently applying it would be.
            score = 30
        ranked.append({
            "title": row.get("title"),
            "cover": cover,
            "source": row.get("source"),
            "source_name": row.get("source_name") or row.get("source"),
            "url": row.get("url"),
            "score": score,
        })

    ranked.sort(key=lambda r: -r["score"])
    return ranked


def save_cover(url, directory, source_id=None, referer=None,
               filename="cover.jpg"):
    """Download one cover into ``directory``.

    Goes through the owning source so its Referer rules apply -- several
    cover CDNs answer 403 to a bare request.
    """
    from .sources import get_source, source_for_url

    os.makedirs(directory, exist_ok=True)
    destination = os.path.join(directory, filename)

    source = None
    try:
        source = (get_source(source_id) if source_id
                  else source_for_url(url))
    except Exception:
        try:
            source = source_for_url(url)
        except Exception:
            source = None

    if source is None:
        from .sources import get_source as _get
        source = _get()          # default source: plain requests session

    try:
        ok = source.download_file(url, destination, referer=referer)
    finally:
        try:
            source.close()
        except Exception:
            pass

    if not ok:
        return None
    return destination
