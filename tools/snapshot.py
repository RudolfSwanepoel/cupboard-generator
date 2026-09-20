"""Regression snapshot for CupboardApp.

Dumps every panel, every validation issue, the cost summary and a hash of each
drawing for the three fixed jobs (the frozen October 2025 wardrobe, Test,
Test_Build), so a change can be compared with the untouched tree.

    python tools/snapshot.py --out baseline.json          # once, on the untouched tree
    python tools/snapshot.py --compare baseline.json      # after each part

--compare prints, per job, exactly what moved: panels (by designation), issues,
summary, total, and which drawings changed. It exits 1 if anything differs that
--allow does not name (e.g. --allow svg after the colour work, where drawings are
meant to change and nothing else is).

The benchmark itself (272 MEL / 59 DECOR / 30 BACK, 92 pot holes, 18/9/6 boards,
~R28,363.50) is regen_check.py's job. This is the wider net: it catches the
change that leaves those numbers alone and moves something else.

Repo root is the parent of tools/ unless --repo is given.
"""
import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--out", help="write the snapshot here")
ap.add_argument("--compare", help="compare the current tree with this earlier snapshot")
ap.add_argument("--allow", default="", help="comma list of keys allowed to differ: "
                "panels,issues,summary,total,svg")
args = ap.parse_args()
sys.path.insert(0, args.repo)

from cabinetgen.engine import generate_job                       # noqa: E402
from cabinetgen.validate import validate                         # noqa: E402
from cabinetgen import nest as N                                 # noqa: E402
from cabinetgen.export_plaza import summarise, estimate_cost     # noqa: E402
from cabinetgen.render import elevation_svg, wall_elevation_svg, plan_svg  # noqa: E402
from cabinetgen.store import load                                # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                     # noqa: E402


def keyed(panels):
    """Every panel, keyed by designation + role + occurrence, so two lines that share
    a designation are both kept and a change to either is seen."""
    seen, out = {}, {}
    for p in panels:
        base = p.label + "/" + p.role
        seen[base] = seen.get(base, 0) + 1
        out[f"{base}#{seen[base]}"] = asdict(p)
    return out


def take():
    jobs = {"oct2025": OCT}
    for n in ("Test", "Test_Build"):
        path = os.path.join(args.repo, "jobs", n + ".json")
        if os.path.exists(path):
            jobs[n] = load(path)
    snap = {}
    for name, job in jobs.items():
        panels = generate_job(job)
        issues = validate(job, panels)
        nested = N.nest_job(N.nestable(panels, job.std), job.std)
        s = summarise(job, panels, nested)
        est = estimate_cost(job, s)
        svgs = {"elev": elevation_svg(job)}
        if job.room:
            for w in job.room.walls:
                svgs["wall" + w.id] = wall_elevation_svg(job, w.id)
            svgs["plan"] = plan_svg(job)
        snap[name] = {
            "panels": keyed(panels),
            "issues": [asdict(i) for i in issues],
            "summary": json.loads(json.dumps(s, default=str)),
            "total": est["total_incl_vat"],
            "svg": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in svgs.items()},
        }
    return snap


now = take()
if args.out:
    with open(args.out, "w") as fh:
        json.dump(now, fh, indent=1, sort_keys=True, default=str)
    print({k: (len(v["panels"]), len(v["issues"]), v["total"]) for k, v in now.items()})

if args.compare:
    with open(args.compare) as fh:
        was = json.load(fh)
    allowed = {a.strip() for a in args.allow.split(",") if a.strip()}
    bad = False
    for name in sorted(set(was) | set(now)):
        a, b = was.get(name), now.get(name)
        if a is None or b is None:
            print(f"{name}: {'missing now' if b is None else 'new job'}")
            bad = True
            continue
        b = json.loads(json.dumps(b, default=str, sort_keys=True))
        for key in ("panels", "issues", "summary", "total", "svg"):
            if a[key] == b[key]:
                continue
            note = "  (allowed)" if key in allowed else ""
            if key not in allowed:
                bad = True
            if key == "panels":
                gone = sorted(set(a[key]) - set(b[key]))
                new = sorted(set(b[key]) - set(a[key]))
                moved = sorted(k for k in set(a[key]) & set(b[key]) if a[key][k] != b[key][k])
                print(f"{name}.panels: -{len(gone)} +{len(new)} changed {len(moved)}{note}")
                for k in moved[:8]:
                    diff = {f: (a[key][k][f], b[key][k][f]) for f in a[key][k]
                            if a[key][k][f] != b[key][k].get(f)}
                    print(f"    {k}: {diff}")
            elif key == "svg":
                ch = sorted(k for k in set(a[key]) | set(b[key]) if a[key].get(k) != b[key].get(k))
                print(f"{name}.svg changed: {', '.join(ch)}{note}")
            else:
                print(f"{name}.{key} changed{note}")
                if key == "issues":
                    was_i = {json.dumps(i, sort_keys=True) for i in a[key]}
                    now_i = {json.dumps(i, sort_keys=True) for i in b[key]}
                    for i in sorted(was_i - now_i)[:5]:
                        print("    - " + i[:160])
                    for i in sorted(now_i - was_i)[:5]:
                        print("    + " + i[:160])
    print("SNAPSHOT: " + ("DIFFERENT (see above)" if bad else "identical apart from what was allowed"))
    sys.exit(1 if bad else 0)
