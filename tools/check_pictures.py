r"""Board pictures: what is stored, what is served, and what cannot be.

The bug this is here to stop coming back: STORMGREY's picture was a quoted
absolute Windows path written straight into an ``<img src>`` on a page served
over http, so it 404'd, and taking the quotes out changed nothing because the
path form was never the problem. Three separate facts have to hold for a picture
to appear, and each one is checked here.

    python tools/check_pictures.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cabinetgen import pictures as P                          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAILED = []


def check(label, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        print("         got  {0!r}".format(got))
        print("         want {0!r}".format(want))
        FAILED.append(label)


def truthy(label, got, want=True):
    check(label, bool(got), bool(want))


print("cleaning a typed or pasted value")
# Explorer's "Copy as path" wraps it in quote characters. That is how STORMGREY
# got its, and a picker is what stops it happening again -- but the cleaning has
# to hold regardless, because the field is still typeable.
check("quoted absolute path inside the repo reduces to the relative form",
      P.clean('"' + os.path.join(ROOT, "Pictures", "Storm Grey.jpg") + '"', ROOT),
      "Pictures/Storm Grey.jpg")
check("bare absolute path inside the repo reduces the same way",
      P.clean(os.path.join(ROOT, "Pictures", "Brookhill.png"), ROOT),
      "Pictures/Brookhill.png")
check("a backslash relative path squares up",
      P.clean("Pictures\\Brookhill.png"), "Pictures/Brookhill.png")
check("whitespace and single quotes go too",
      P.clean("  'Pictures/Brookhill.png'  "), "Pictures/Brookhill.png")
check("already relative is left exactly as it is",
      P.clean("Pictures/Storm Grey.jpg"), "Pictures/Storm Grey.jpg")
check("empty stays empty", P.clean("   "), "")
check("None stays empty", P.clean(None), "")
# A data: URI is the picture rather than a pointer at one, and a board written
# before this module may hold one. It must survive untouched.
check("a data: URI is carried through untouched",
      P.clean(" data:image/png;base64,AAAA "), "data:image/png;base64,AAAA")
truthy("a data: URI is recognised as one", P.is_data_uri("data:image/gif;base64,x"))
truthy("an ordinary path is not a data: URI", P.is_data_uri("Pictures/x.png"), False)

print()
print("what an <img src> asks for")
# The whole cause of the original bug: a page served from http://127.0.0.1:<port>/
# resolves a Windows path against that origin, and the server answers 404. There
# is exactly one URL the server does answer.
check("a relative picture becomes the served route",
      P.url_for("Pictures/Brookhill.png", ROOT), "/pictures/Brookhill.png")
check("a space is escaped, so the URL is a URL",
      P.url_for("Pictures/Storm Grey.jpg", ROOT), "/pictures/Storm%20Grey.jpg")
check("a stored ABSOLUTE path still draws -- an old job file is not rewritten",
      P.url_for(os.path.join(ROOT, "Pictures", "Storm Grey.jpg"), ROOT),
      "/pictures/Storm%20Grey.jpg")
check("a data: URI is its own src",
      P.url_for("data:image/png;base64,AAAA", ROOT), "data:image/png;base64,AAAA")
check("nothing set asks for nothing", P.url_for("", ROOT), "")
truthy("no url_for answer is ever a bare drive path",
       not P.url_for("Pictures/x.png", ROOT).startswith("C:"))

print()
print("is it a real, readable image")
truthy("a picture that is really there reads",
       P.readable("Pictures/Storm Grey.jpg", ROOT))
truthy("a picture that is not there does not",
       P.readable("Pictures/NoSuchBoard.jpg", ROOT), False)
truthy("a real file that is not an image does not",
       P.readable("README.md", ROOT), False)
truthy("a data: URI needs no file", P.readable("data:image/png;base64,AAAA", ROOT))
truthy("nothing set is not readable", P.readable("", ROOT), False)

print()
print("a name from outside can name nothing but a file in Pictures/")
# The route serves off the basename and nothing else, so a traversal has to be
# impossible before it gets there as well as at the route.
check("a parent traversal is flattened", P.safe_name("../../evil.png"), "evil.png")
check("a drive letter is flattened", P.safe_name("C:\\windows\\evil.png"), "evil.png")
check("a forward-slash path is flattened", P.safe_name("/etc/passwd"), "passwd")
check("a quoted name unquotes", P.safe_name('"Storm Grey.jpg"'), "Storm Grey.jpg")
truthy("a name is never a path", "/" not in P.safe_name("a/b/c.png")
       and "\\" not in P.safe_name("a\\b\\c.png"))

print()
print("only the extensions the browser will draw")
truthy(".png is offered", ".png" in P.TYPES)
truthy(".exe is not", ".exe" not in P.TYPES)
check("the type table answers the route", P.content_type("x.JPG"), "image/jpeg")
truthy("the Open dialog filter is built from the same table",
       all(e in P.FILE_TYPES[0] for e in P.TYPES))

print()
print("installing a file")
src = os.path.join(ROOT, "Pictures", "Storm Grey.jpg")
if os.path.isfile(src):
    check("a file already in Pictures/ is not copied again",
          P.install(src, ROOT), "Pictures/Storm Grey.jpg")
else:
    print("  --   Pictures/Storm Grey.jpg is not here; skipping the no-copy case")
for bad, why in ((os.path.join(ROOT, "README.md"), "not an image"),
                 (os.path.join(ROOT, "Pictures", "NoSuchBoard.png"), "not there"),
                 ("", "nothing chosen")):
    try:
        P.install(bad, ROOT)
        check("install refuses what is " + why, "accepted it", "ValueError")
    except ValueError as exc:
        truthy("install refuses what is " + why + ", and says why", str(exc).strip())
for bad, why in (("notes.txt", "not an image"), ("x.png", "empty")):
    try:
        P.install_bytes(bad, b"" if why == "empty" else b"x", ROOT)
        check("install_bytes refuses what is " + why, "accepted it", "ValueError")
    except ValueError as exc:
        truthy("install_bytes refuses what is " + why + ", and says why",
               str(exc).strip())

print()
print("the library names nothing absolute")
# boards.json is shared through git, so an absolute path in it is one machine's
# answer written down as if it were everybody's. This is a hard check on the
# LIBRARY only. A saved job is a price capture and is never rewritten under the
# operator, so one carrying an old absolute path is reported and not failed --
# `url_for` draws it anyway, and it squares up the next time it is saved.
import json                                                      # noqa: E402
import glob                                                      # noqa: E402


def _records(raw):
    out = [r for r in (raw.get("boards") or []) if isinstance(r, dict)]
    mats = raw.get("materials")
    if isinstance(mats, dict):
        out += [m for m in mats.values() if isinstance(m, dict)]
    return out


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


lib_raw = _read(os.path.join(ROOT, "boards.json")) or {}
for rec in _records(lib_raw):
    pic = str(rec.get("picture") or "")
    if not pic or P.is_data_uri(pic):
        continue
    who = rec.get("id") or rec.get("name") or "?"
    truthy("boards.json: {0} names its picture relative to the repo".format(who),
           not os.path.isabs(pic) and '"' not in pic and "'" not in pic)
    truthy("boards.json: {0}'s picture is really there".format(who),
           P.readable(pic, ROOT))

print()
print("saved jobs draw whatever they carry (reported, never failed)")
for path in sorted(glob.glob(os.path.join(ROOT, "jobs", "*.json"))):
    raw = _read(path)
    if raw is None:
        continue
    for rec in _records(raw):
        pic = str(rec.get("picture") or "")
        if not pic or P.is_data_uri(pic):
            continue
        who = rec.get("id") or rec.get("name") or "?"
        shape = "relative" if not os.path.isabs(pic) else "absolute (squares up on save)"
        print("  --   {0}: {1} -> {2}  [{3}]".format(
            os.path.basename(path), who, P.url_for(pic, ROOT) or "nothing", shape))
        truthy("{0}: {1} still resolves to a URL".format(os.path.basename(path), who),
               P.url_for(pic, ROOT))

print()
if FAILED:
    print("FAILED {0}: {1}".format(len(FAILED), "; ".join(FAILED)))
    sys.exit(1)
print("check_pictures: all good")
