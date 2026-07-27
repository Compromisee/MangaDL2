"""Shared helpers: sorting, sanitising, chapter parsing."""

import re


def natural_sort_key(text):
    """Key for natural sorting: '2.jpg' < '10.jpg'."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", str(text))]


def sanitize(name: str) -> str:
    """Make a string safe for use as a file / directory name."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return re.sub(r"\s+", " ", name) or "untitled"


def chapter_number(chapter_name: str) -> float:
    """Extract a numeric chapter number from a chapter name (supports decimals)."""
    match = re.search(r"(?:chapter|episode|ch\.?|ep\.?)?\s*(\d+(?:\.\d+)?)", chapter_name, re.I)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return 0.0


def format_chapter_number(value: float) -> str:
    """Format a chapter number as a zero padded label, e.g. 5 -> '005', 23.5 -> '023.5'."""
    if value == int(value):
        return f"{int(value):03d}"
    whole = int(value)
    frac = str(value).split(".", 1)[1]
    return f"{whole:03d}.{frac}"


def parse_selection(spec: str, chapters: list) -> list:
    """Parse a chapter selection string against a chapter list.

    Supported syntax (chapter numbers, not indices):
        ""            -> all chapters
        "all"         -> all chapters
        "5"           -> chapter 5
        "23.5"        -> chapter 23.5
        "1-20"        -> chapters 1 through 20 (inclusive)
        "1,5,10-20"   -> combination
        "50-"         -> chapter 50 to the end
        "-10"         -> start to chapter 10
        "latest"      -> the newest chapter
        "first"       -> the oldest chapter

    Returns the selected chapter dicts in reading order.
    """
    spec = (spec or "").strip().lower()
    if not spec or spec == "all":
        return list(chapters)
    if spec == "latest":
        return [chapters[-1]] if chapters else []
    if spec == "first":
        return [chapters[0]] if chapters else []

    numbered = [(chapter_number(c["name"]), c) for c in chapters]
    selected, seen = [], set()

    def add(chapter):
        key = id(chapter)
        if key not in seen:
            seen.add(key)
            selected.append(chapter)

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, _, right = part.partition("-")
            try:
                lo = float(left) if left.strip() else float("-inf")
                hi = float(right) if right.strip() else float("inf")
            except ValueError:
                raise ValueError(f"Invalid range: '{part}'")
            if lo > hi:
                lo, hi = hi, lo
            for num, chapter in numbered:
                if lo <= num <= hi:
                    add(chapter)
        else:
            try:
                target = float(part)
            except ValueError:
                raise ValueError(f"Invalid chapter: '{part}'")
            hit = False
            for num, chapter in numbered:
                if num == target:
                    add(chapter)
                    hit = True
            if not hit:
                raise ValueError(f"Chapter {part} not found")

    selected.sort(key=lambda c: chapter_number(c["name"]))
    return selected


def chunk(items: list, size: int) -> list:
    """Split a list into consecutive chunks of `size`. size <= 0 -> one chunk."""
    if size <= 0:
        return [list(items)] if items else []
    return [items[i:i + size] for i in range(0, len(items), size)]
