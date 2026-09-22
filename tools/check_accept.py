"""Accepting a site-dependent critical, and the acceptance lapsing.

    python tools/check_accept.py

Ruled 22 September 2026. Some criticals say something about the SITE, not the
cut list, and the operator can accept one with a reason; the export then goes
ahead. Today that is the tip-up check alone. Everything held here:

  * every critical carries a stable check id, and only tip-up is acceptable;
  * an accepted tip-up stops blocking and says why, and every other critical
    blocks exactly as before — the mitre door swing above all, which was ruled
    blocking on purpose;
  * the acceptance is stored with a fingerprint of exactly what the check read,
    and LAPSES when the cabinet or the ceiling changes: change the height and
    it blocks again;
  * a job with no acceptances writes no key, so every job file on disk still
    round-trips byte for byte.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from app import api                                                         # noqa: E402
from cabinetgen.engine import generate_job                                  # noqa: E402
from cabinetgen.model import Acceptance, Cabinet, Job, Placement            # noqa: E402
from cabinetgen.room import rectangular                                     # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict, load               # noqa: E402
from cabinetgen.validate import (ACCEPTABLE, CRITICAL, blocking,            # noqa: E402
                                 fingerprint, lapsed_acceptances, report,
                                 validate)

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  want {want!r}"))
    if not ok:
        FAILS.append(name)


def tall_job(height=2400, ceiling=2540):
    """A 2400 tall unit on its legs stands at 2500 and needs 2556 to come up."""
    j = Job("accept")
    j.cabinets = [Cabinet(number=1, width=600, height=height, depth=580, kind="tall")]
    j.room = rectangular(4000, 3000, ceiling=ceiling)
    j.placements = [Placement(cabinet=1, wall="A", x=0)]
    return j


def issues(j):
    return validate(j, generate_job(j))


def tip(j):
    return [i for i in issues(j) if i.check == "tip-up"]


def main():
    print("every critical carries a stable check id")
    jobs = []
    for name in ("Test.json", "Test_Build.json", "Test_Panels.json", "Corner Unit Test.json"):
        path = os.path.join(ROOT, "jobs", name)
        if os.path.exists(path):
            jobs.append(load(path))
    jobs.append(tall_job())
    crits = [i for j in jobs for i in issues(j) if i.level == CRITICAL]
    check("criticals seen across the fixtures", len(crits) > 0, True)
    check("not one without an id", [str(i) for i in crits if not i.check], [])
    check("only tip-up is acceptable", sorted(ACCEPTABLE), ["tip-up"])
    check("and the mitre door swing is not",  "mitre-door-swing" in ACCEPTABLE, False)

    print("\nthe tip-up critical, before anything is accepted")
    j = tall_job()
    t = tip(j)
    check("one tip-up critical", [(i.level, i.where) for i in t], [(CRITICAL, "1")])
    check("it says it can be accepted", t[0].acceptable, True)
    check("and it blocks", blocking(issues(j)), True)

    print("\naccepting it, through /api/accept")
    wire = job_to_dict(j)
    r = api.accept({"job": wire, "check": "tip-up", "where": "1"})
    check("the engine hands back a fingerprint", r["ok"], True)
    check("of what the check read, geometry off the panels and the ceiling",
          r["fingerprint"],
          "height 2400 · depth 580 · legs 100 · setback 50 · underside 100 · ceiling 2540")
    refused = api.accept({"job": wire, "check": "mitre-door-swing", "where": "1"})
    check("a cut-list critical is refused", refused["ok"], False)
    refused = api.accept({"job": wire, "check": "overlap", "where": "1/2"})
    check("an overlap too", refused["ok"], False)

    j.acceptances = [Acceptance("tip-up", "1", "Assembled in place", r["fingerprint"])]
    t = tip(j)
    check("the critical is still listed", len(t), 1)
    check("marked accepted, with its reason", t[0].accepted, "Assembled in place")
    check("and no longer blocks", blocking(issues(j)), False)
    check("the report says ACCEPTED and why",
          "ACCEPTED" in report(issues(j)) and "Assembled in place" in report(issues(j)), True)
    check("nothing has lapsed", lapsed_acceptances(j), [])
    check("compute reports nothing lapsed", api.compute({"job": job_to_dict(j)})["lapsed"], [])
    check("compute says the export is not blocked",
          api.compute({"job": job_to_dict(j)})["blocking"], False)

    print("\nchange the cabinet height: the acceptance lapses")
    j.cabinets[0].height = 2420             # stands 2520, still under 2540, still cannot tip
    t = tip(j)
    check("the tip-up critical is back", len(t), 1)
    check("not accepted", t[0].accepted, "")
    check("marked lapsed", t[0].lapsed, True)
    check("and it blocks again", blocking(issues(j)), True)
    check("lapsed_acceptances names it", [(a.check, a.where) for a in lapsed_acceptances(j)],
          [("tip-up", "1")])
    check("compute hands it to the browser to drop",
          [(a["check"], a["where"]) for a in api.compute({"job": job_to_dict(j)})["lapsed"]],
          [("tip-up", "1")])
    check("the job itself is untouched by validating it", len(j.acceptances), 1)

    print("\nchange the ceiling: that lapses it too")
    j = tall_job()
    fp = fingerprint(j, "tip-up", "1")
    j.acceptances = [Acceptance("tip-up", "1", "Assembled in place", fp)]
    j.room.ceiling = 2530
    check("lapsed on a new ceiling", [i.lapsed for i in tip(j)], [True])
    check("blocks", blocking(issues(j)), True)

    print("\nan acceptance cannot reach a check that is not acceptable")
    j = tall_job()
    j.acceptances = [Acceptance("tip-up", "1", "x", fingerprint(j, "tip-up", "1")),
                     Acceptance("mitre-door-swing", "1", "forged", "anything")]
    others = [i for i in issues(j) if i.level == CRITICAL and i.check != "tip-up"]
    check("no other critical is ever marked accepted",
          [i.check for i in others if i.accepted], [])
    check("a stored acceptance for a blocking check is dropped as lapsed",
          [a.check for a in lapsed_acceptances(j)], ["mitre-door-swing"])

    print("\nwritten only when present")
    j = tall_job()
    check("no acceptances, no key", "acceptances" in job_to_dict(j), False)
    j.acceptances = [Acceptance("tip-up", "1", "Assembled in place",
                                fingerprint(j, "tip-up", "1"))]
    d = job_to_dict(j)
    check("one acceptance, one key", len(d["acceptances"]), 1)
    check("and it round-trips", job_to_dict(job_from_dict(json.loads(json.dumps(d)))), d)
    for name in ("Test.json", "Test_Build.json", "Test_Panels.json", "Corner Unit Test.json"):
        path = os.path.join(ROOT, "jobs", name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        again = json.dumps(job_to_dict(load(path)), indent=2, ensure_ascii=False)
        check(f"{name} still writes back byte for byte",
              again.replace("\r\n", "\n") == raw.replace("\r\n", "\n"), True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
