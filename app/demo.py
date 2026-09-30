"""Demo mode: a build that stops working on a fixed date (29 September 2026 brief).

Off unless `Build Demo.bat` has written `app/_demo_build.py` beside this file —
`DEMO = True` and `EXPIRES = "YYYY-MM-DD"` — which it deletes again after the
build, and which git ignores. A normal `python run_app.py` has no such file, so
`DEMO` is False, `refusal()` returns None at once and nothing in the app behaves
differently. Nothing here touches geometry, nesting, costing or export.

In a demo build two things stop it, both said in words a person can act on:

- the date is after `EXPIRES` (the demo works ON the expiry date);
- the clock has been put back: the latest date the demo has run on is kept in
  `output/demo-seen.txt`, and a date more than `ROLLBACK_DAYS` before it is
  refused. Deliberately simple — it stops a casual clock change, nothing more.

`run_app.py` asks at start-up and shows the answer in a message box; the
server asks on every request (`api.Handler`), so leaving the app open past the
date does not get round it.
"""
import datetime
import os

try:
    from app._demo_build import DEMO, EXPIRES
except ImportError:
    DEMO, EXPIRES = False, None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEN = os.path.join(ROOT, "output", "demo-seen.txt")
ROLLBACK_DAYS = 1

_latest = None          # the latest date seen this run, once read from SEEN


def expires() -> datetime.date:
    return datetime.date.fromisoformat(EXPIRES)


def say(d: datetime.date) -> str:
    """28 Nov 2026."""
    return f"{d.day} {d.strftime('%b %Y')}"


def title() -> str:
    return f"Cupboard App — Demo (until {say(expires())})"


def expired_message() -> str:
    return (f"This demo of Cupboard App expired on {say(expires())}. "
            f"Contact Rudolf for a new copy.")


def _read_seen():
    try:
        with open(SEEN, encoding="utf-8") as fh:
            return datetime.date.fromisoformat(fh.read().strip())
    except (OSError, ValueError):
        return None


def _write_seen(d: datetime.date):
    try:
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        with open(SEEN, "w", encoding="utf-8") as fh:
            fh.write(d.isoformat())
    except OSError:
        pass


def refusal(today: datetime.date = None):
    """None when the app may run; otherwise the message that says why not."""
    global _latest
    if not DEMO:
        return None
    today = today or datetime.date.today()
    if _latest is None:
        _latest = _read_seen() or today
    if today < _latest - datetime.timedelta(days=ROLLBACK_DAYS):
        return (f"The date on this computer is {say(today)}, but this demo of "
                f"Cupboard App has already been used on {say(_latest)}. Set the "
                f"computer's clock to today's date and start it again.")
    if today > _latest or not os.path.exists(SEEN):
        _latest = max(today, _latest)
        _write_seen(_latest)
    if today > expires():
        return expired_message()
    return None
