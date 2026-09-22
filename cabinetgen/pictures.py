r"""Board pictures: where they live, what is stored, and what a page asks for.

A board picture is a swatch of the real sheet, so it is a file on disk. Three
things went wrong before this module existed and all three are answered here.

**It is stored relative to the repo, never absolutely.** ``Pictures/Storm
Grey.jpg``, not ``C:\Dev\CupboardApp\Pictures\Storm Grey.jpg``. An absolute path
is one machine's answer, and ``boards.json`` is shared through git, so the other
machine gets a path that does not exist. It is also what let a stray pair of
quote characters into the field in the first place: a path typed by hand is a
path somebody can mistype.

**It is fetched over the server, never off the filesystem.** The page is served
from ``http://127.0.0.1:<port>/``, so ``<img src="C:\...">`` resolves against
that origin and 404s, and a ``file:`` sub-resource is blocked from an ``http:``
page by every modern engine. ``url_for`` gives the one URL the server actually
answers -- see ``/pictures/<name>`` in ``app/api.py``.

**It is copied in, never referenced where it sits.** ``install`` puts the chosen
file into ``Pictures/``, so the picture cannot go missing when the folder it was
picked from is tidied up.

A ``data:`` URI is carried through all of this untouched: it is already the
picture rather than a pointer at one, and a board written before this module may
well hold one.
"""
import os
import re
import shutil
from urllib.parse import quote

# Where they live, relative to the repo root. One folder, flat: a board picture
# is a swatch, not a document tree, and a flat folder is what makes serving one
# a basename lookup rather than a path-traversal question.
DIRNAME = "Pictures"

# The one URL the server answers for a picture. Stated here rather than in
# `app/api.py` so the route and the `<img src>` that asks for it cannot drift
# apart -- the same bargain `TYPES` strikes for the content type.
ROUTE = "/pictures/"

# What the browser will actually draw, and therefore what may be stored or
# served. Extension -> content type; the server needs the type and the picker
# needs the extensions, so they are one table and cannot disagree.
TYPES = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".bmp":  "image/bmp",
    ".webp": "image/webp",
    ".svg":  "image/svg+xml",
}

# What the native Open dialog offers, built from the same table.
FILE_TYPES = ("Image files ({0})".format(";".join("*" + e for e in TYPES)),)

_DATA = re.compile(r"^data:image/", re.I)


def root_of(start: str) -> str:
    """The repo root, given any file inside it."""
    return os.path.dirname(os.path.dirname(os.path.abspath(start)))


def is_data_uri(raw) -> bool:
    """A picture that IS the picture rather than a pointer at one."""
    return bool(_DATA.match(str(raw or "").strip()))


def clean(raw, root: str = "") -> str:
    r"""What a typed, pasted or stored picture value reduces to.

    Strips the whitespace and the quote characters a pasted Windows path brings
    with it (Explorer's "Copy as path" wraps it in quotes, which is exactly how
    the STORMGREY value got its), squares the separators, and reduces a path
    inside the repo's ``Pictures/`` to the relative form. A path somewhere else
    is left alone for ``install`` to deal with; a ``data:`` URI is returned as it
    stands.

    >>> clean('"C:\\Dev\\CupboardApp\\Pictures\\Storm Grey.jpg"', r"C:\Dev\CupboardApp")
    'Pictures/Storm Grey.jpg'
    >>> clean("  Pictures\\Brookhill.png  ")
    'Pictures/Brookhill.png'
    >>> clean("")
    ''
    """
    s = str(raw or "").strip()
    if is_data_uri(s):
        return s
    s = s.strip().strip('"').strip("'").strip()
    if not s:
        return ""
    s = s.replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    # Already relative to the repo: `Pictures/<name>`, however it was cased.
    parts = [p for p in s.split("/") if p not in ("", ".")]
    if len(parts) == 2 and parts[0].lower() == DIRNAME.lower():
        return DIRNAME + "/" + parts[1]
    if root:
        here = os.path.normcase(os.path.abspath(os.path.join(root, DIRNAME)))
        try:
            owner = os.path.normcase(os.path.abspath(os.path.dirname(s)))
        except (OSError, ValueError):
            owner = ""
        if owner == here:
            return DIRNAME + "/" + os.path.basename(s)
    return s


def resolve(stored, root: str) -> str:
    """The file on disk this value names, or '' when it names none.

    '' for a ``data:`` URI too: there is no file, and the caller wants the URI.
    """
    s = clean(stored, root)
    if not s or is_data_uri(s):
        return ""
    path = s if os.path.isabs(s) else os.path.join(root, s)
    return os.path.abspath(path)


def readable(stored, root: str) -> bool:
    """Is it a real, readable image file -- or a ``data:`` URI, which needs none."""
    if is_data_uri(clean(stored, root)):
        return True
    path = resolve(stored, root)
    if not path:
        return False
    if os.path.splitext(path)[1].lower() not in TYPES:
        return False
    return os.path.isfile(path) and os.access(path, os.R_OK)


def url_for(stored, root: str = "", base: str = ROUTE) -> str:
    """What an ``<img src>`` or an SVG ``<image>`` asks for. '' when there is
    nothing to draw.

    A ``data:`` URI is itself. Everything else is ``/pictures/<name>``, which is
    the one route the server answers -- including a stored ABSOLUTE path inside
    ``Pictures/``, so a job file written before this module still draws without
    being rewritten. Files on disk change only when saved.

    ``base`` is the one thing a caller may vary, and there is exactly one reason
    to: an exported drawing is a file on disk beside its pictures, not a page on
    the server, so ``export`` asks for ``""`` and gets the bare name. Everything
    on screen takes the route.
    """
    s = clean(stored, root)
    if not s:
        return ""
    if is_data_uri(s):
        return s
    return base + quote(os.path.basename(s))


def _free_name(folder: str, name: str) -> str:
    """``Storm Grey.jpg``, or ``Storm Grey-2.jpg`` when that is taken by a
    different file. Two boards may honestly be given two pictures of one name."""
    base, ext = os.path.splitext(name)
    candidate, n = name, 1
    while os.path.exists(os.path.join(folder, candidate)):
        n += 1
        candidate = "{0}-{1}{2}".format(base, n, ext)
    return candidate


def safe_name(raw) -> str:
    """A file name fit to sit in ``Pictures/``: the basename, nothing else.

    A name is data from outside, so it may not name a path, a parent or a drive
    -- the same discipline ``api._safe_name`` applies to a job name.
    """
    raw = str(raw or "").replace("\\", "/").strip().strip('"').strip("'")
    name = os.path.basename(raw)
    name = "".join(ch for ch in name
                   if ch not in '<>:"/\\|?*' and ord(ch) >= 32)
    return name.strip(" .")[:120]


def install(src: str, root: str) -> str:
    """Copy a chosen file into ``Pictures/`` and give back what to store.

    Raises ``ValueError`` with a sentence fit to show, rather than failing
    quietly -- a picture that silently does not arrive is the bug this whole
    module is here to end.
    """
    path = str(src or "").strip().strip('"').strip("'")
    if not path:
        raise ValueError("no file was chosen")
    ext = os.path.splitext(path)[1].lower()
    if ext not in TYPES:
        raise ValueError("{0} is not an image file -- expected one of {1}".format(
            os.path.basename(path) or "that file", ", ".join(sorted(TYPES))))
    if not os.path.isfile(path):
        raise ValueError("there is no file at {0}".format(path))
    if not os.access(path, os.R_OK):
        raise ValueError("{0} cannot be read".format(os.path.basename(path)))

    folder = os.path.join(root, DIRNAME)
    os.makedirs(folder, exist_ok=True)
    # Already in there: keep it where it is rather than making a second copy.
    if os.path.normcase(os.path.abspath(os.path.dirname(path))) == \
       os.path.normcase(os.path.abspath(folder)):
        return DIRNAME + "/" + os.path.basename(path)

    name = _free_name(folder, safe_name(os.path.basename(path)) or "picture" + ext)
    shutil.copyfile(path, os.path.join(folder, name))
    return DIRNAME + "/" + name


def install_bytes(name: str, blob: bytes, root: str) -> str:
    """The same, for a file that arrived as bytes rather than as a path.

    A drop on this backend hands over the file's CONTENTS and no path -- WebView2
    does not expose ``File.path`` and pywebview 6.2.1 has no file-drop event --
    so this is the one way a dropped picture can be taken in. Same folder, same
    naming, same answer.
    """
    clean_name = safe_name(name)
    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in TYPES:
        raise ValueError("{0} is not an image file -- expected one of {1}".format(
            clean_name or "that file", ", ".join(sorted(TYPES))))
    if not blob:
        raise ValueError("{0} is empty".format(clean_name))
    folder = os.path.join(root, DIRNAME)
    os.makedirs(folder, exist_ok=True)
    final = _free_name(folder, clean_name)
    with open(os.path.join(folder, final), "wb") as fh:
        fh.write(blob)
    return DIRNAME + "/" + final


def content_type(path: str) -> str:
    """What to serve it as. An unknown extension never reaches here -- the route
    checks against ``TYPES`` first -- so the fallback is belt and braces."""
    return TYPES.get(os.path.splitext(path)[1].lower(), "application/octet-stream")


# --- which way the grain runs -----------------------------------------------
#
# A board picture is supplied with the grain running VERTICALLY (ruled 22 Sept
# 2026). That convention is the whole reason a drawing can put a board's real
# texture on a panel: it turns the tile through 0 or 90 degrees onto the panel's
# length direction, instead of trying to work an arbitrary angle out of a
# photograph. So the one thing worth asking of a picture as it arrives is
# whether it honours the convention.
#
# It is asked of a GRID, not of a file. Decoding a JPEG is the browser's job --
# it has a decoder and this module does not, and adding one to take a dependency
# on would be a large price for an advisory. The browser draws the picture into
# a small canvas, which area-averages it, and hands the luminance over; the
# verdict is reached here, so it is one answer, testable without a picture at
# all. Measured on the real `Pictures/Brookhill.png`: +0.29 as supplied, -0.29
# turned on its side, and stable from a 32-square grid to a 128-square one.

# Below this there is no texture to have a direction -- a flat colour, a plain
# white melamine. Mean absolute difference between neighbouring samples, out of
# 255; a flat fill is 0 and Brookhill is 3.4.
GRAIN_TEXTURE_MIN = 1.0

# And below this the texture has no direction worth calling one. Nothing is said
# either way: a warning nobody can act on is worse than silence.
GRAIN_DECISIVE = 0.15


def _gradient_energy(rows):
    """Mean absolute difference between neighbours, along x and along y.

    Grain running up the picture varies fast ACROSS it and slowly ALONG it, so
    vertical grain is `x` large and `y` small. Nothing here knows about wood --
    it is the direction the texture is coherent in, which is what the convention
    is actually about.
    """
    h = len(rows)
    w = len(rows[0]) if h else 0
    if h < 2 or w < 2:
        return 0.0, 0.0
    gx = sum(abs(rows[y][x + 1] - rows[y][x])
             for y in range(h) for x in range(w - 1)) / float(h * (w - 1))
    gy = sum(abs(rows[y + 1][x] - rows[y][x])
             for y in range(h - 1) for x in range(w)) / float((h - 1) * w)
    return gx, gy


def grain_verdict(rows) -> dict:
    """Does this picture's texture run vertically? A grid of luminance in, a
    sentence out.

    `checked` False means nothing was decided and nothing should be said -- the
    grid was unusable, there is no texture, or the texture has no clear
    direction. `ok` False is the one case that warns, and it never blocks: the
    picture is taken in either way, the same bargain the validator strikes
    everywhere but a critical.

    >>> grain_verdict([[0, 90, 0, 90]] * 4)["ok"]
    True
    >>> grain_verdict([[0, 0, 0, 0], [90, 90, 90, 90]] * 2)["ok"]
    False
    >>> grain_verdict([[60] * 4] * 4)["checked"]
    False
    """
    blank = {"checked": False, "ok": True, "vertical": None,
             "strength": 0.0, "message": ""}
    try:
        grid = [[float(v) for v in row] for row in rows]
    except (TypeError, ValueError):
        return blank
    if len(grid) < 2 or len(grid[0]) < 2:
        return blank
    if any(len(row) != len(grid[0]) for row in grid):
        return blank

    gx, gy = _gradient_energy(grid)
    if max(gx, gy) < GRAIN_TEXTURE_MIN:
        return blank                       # a flat colour has no grain to place
    strength = (gx - gy) / (gx + gy)
    if abs(strength) < GRAIN_DECISIVE:
        return blank                       # no direction worth calling one

    vertical = strength > 0
    return {"checked": True, "ok": vertical, "vertical": vertical,
            "strength": round(strength, 3),
            "message": "" if vertical else
                       "the grain does not look vertical — rotate the picture "
                       "and upload it again. Drawings turn a board's grain onto "
                       "each panel from vertical, so a picture on its side puts "
                       "it the wrong way round on every panel."}
