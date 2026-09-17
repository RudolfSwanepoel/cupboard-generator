"""Plinth regression check.

    python tools/check_plinth.py

A plinth is a run-level part, which makes it the one panel whose length depends
on things no single cabinet knows about: what the run is made of, whether a gap
in it was filled or left open, and what happens where two runs meet.

The cases that matter, and why:

  * A run broken by an open gap is two runs. A plinth board cannot span an
    appliance space, so the boards must come out as two, not one long one.
  * Internal corners butt. One run continues past and the other stops square
    against it, so exactly one of the two boards loses a board thickness —
    never both, which would leave a gap, and never neither, which would not fit.
  * A run longer than a board splits at a cabinet division, so the joint falls
    behind a carcass side instead of wherever the arithmetic happened to land.
  * It is opt-in — the operator's choice per run, whatever the job — so nothing
    is made unless it was asked for. The legs are there either way; the board
    only covers them, and never moves a height.

Numbers are ruled: 100 mm high, 50 mm setback, legs 98-122 mm, carcass board,
banded on both long edges for water sealing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cabinetgen.engine import generate_job, plinth_panels                 # noqa: E402
from cabinetgen.model import (Cabinet, GapChoice, Job, Placement,         # noqa: E402
                              PlinthChoice)
from cabinetgen.room import plinth_lengths, rectangular, runs             # noqa: E402
from cabinetgen.standard import STANDARD                                  # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict                   # noqa: E402
from cabinetgen.validate import validate                                  # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def cab(n, w, d=580, h=720, kind="base"):
    return Cabinet(number=n, width=w, height=h, depth=d, kind=kind)


def job_on(wall="A", spec=((1, 900, 0), (2, 600, 900)), room=None, **kw):
    rm = room or rectangular(4000, 3000)
    return Job(name="p", room=rm,
               cabinets=[cab(n, w) for n, w, _ in spec],
               placements=[Placement(n, wall, x) for n, _, x in spec], **kw)


def main() -> int:
    std = STANDARD
    print("runs")
    j = job_on(spec=((1, 900, 0), (2, 600, 900), (3, 600, 1500)))
    r = runs(j)
    check("touching cabinets make one run", len(r), 1)
    check("which knows its cabinets", r[0].cabinets, [1, 2, 3])
    check("and spans them", (r[0].x0, r[0].x1), (0, 2100))
    check("and remembers the joins for splitting", r[0].divisions, [900, 1500])

    print("\na gap left open breaks the run; a filler does not")
    j = job_on(spec=((1, 900, 0), (2, 600, 1000)))
    j.gaps = [GapChoice("A", 1, 2, "base", "open")]
    check("open splits it in two", [x.cabinets for x in runs(j)], [[1], [2]])
    j.gaps = [GapChoice("A", 1, 2, "base", "filler")]
    check("a filler keeps it whole", [x.cabinets for x in runs(j)], [[1, 2]])
    j.gaps = [GapChoice("A", 1, 2, "base", "blind")]
    check("so does a blind corner", [x.cabinets for x in runs(j)], [[1, 2]])
    j.gaps = []
    check("an undecided gap breaks it, the safe way round",
          [x.cabinets for x in runs(j)], [[1], [2]])

    print("\nopt-in")
    j = job_on()
    check("no plinth unless asked for", plinth_panels(j), [])
    j.plinths = [PlinthChoice("A", "base", 1, fitted=False)]
    check("and 'fitted false' means no", plinth_panels(j), [])

    print("\none plinth board")
    j = job_on(spec=((1, 900, 0), (2, 600, 900)))
    j.plinths = [PlinthChoice("A", "base", 1)]
    ps = plinth_panels(j)
    check("one panel", len(ps), 1)
    p = ps[0]
    check("code 10", p.code, "10")
    check("belongs to no cabinet", p.cabinet, 0)
    check("length is the run", p.length, 1500)
    check("width is the ruled plinth height", p.width, 100)
    check("carcass board", p.material, "MEL")
    check("banded both long edges, not the ends", (p.edge_l, p.edge_w), (2, 0))
    check("in the carcass edging", p.edge_material, "PVC WOOD")
    check("and says which run it belongs to",
          "wall A" in p.note and "cabinets 1-2" in p.note, True)
    check("it reaches the cut list",
          [x.label for x in generate_job(j) if x.code == "10"], ["010"])

    print("\ntwo runs, two plinths")
    j = job_on(spec=((1, 900, 0), (2, 600, 1000)))
    j.gaps = [GapChoice("A", 1, 2, "base", "open")]
    j.plinths = [PlinthChoice("A", "base", 1), PlinthChoice("A", "base", 2)]
    check("a board each, not one spanning the gap",
          sorted(x.length for x in plinth_panels(j)), [600, 900])

    print("\ninternal corner butts, and only one side loses the thickness")
    rm = rectangular(4000, 3000)
    j = Job(name="c", room=rm,
            cabinets=[cab(1, 900), cab(2, 600)],
            placements=[Placement(1, "A", 3100), Placement(2, "B", 0)],
            plinths=[PlinthChoice("A", "base", 1), PlinthChoice("B", "base", 2)])
    lengths = {p.note.split("wall ")[1][0]: p.length for p in plinth_panels(j)}
    check("wall A's run reaches its end corner", lengths["A"], 900)
    check("wall B's run stops square against it, 16 mm off", lengths["B"], 584)
    check("exactly one board is shortened",
          sum(1 for p in plinth_panels(j) if "butts into" in p.note), 1)
    check("and the note names the run it butts into, not its own wall",
          [p.note.split("butts into the wall ")[1][0]
           for p in plinth_panels(j) if "butts into" in p.note], ["A"])

    j.plinths = [PlinthChoice("B", "base", 2)]
    check("no deduction when the other run has no plinth to butt into",
          [p.length for p in plinth_panels(j)], [600])

    print("\na run longer than a board splits at a cabinet division")
    spec = tuple((i + 1, 800, i * 800) for i in range(5))       # 4000 mm of cabinets
    j = job_on(spec=spec)
    j.plinths = [PlinthChoice("A", "base", 1)]
    r = runs(j)[0]
    check("the run is 4000 long", r.length, 4000)
    check("split at the last division that fits a 2750 board",
          plinth_lengths(j, r), [(2400, 0), (1600, 2400)])
    ps = plinth_panels(j)
    check("two boards", [p.length for p in ps], [2400, 1600])
    check("both within a board", all(p.length <= std.sheet_l for p in ps), True)
    check("and the joint is noted", "joint at a cabinet division" in ps[0].note, True)
    check("each division is a real cabinet edge",
          all(x in r.divisions + [r.x1] for _, x in
              [(l, a + l) for l, a in plinth_lengths(j, r)]), True)

    print("\na tall unit shares the floor run with the base units beside it")
    j = Job(name="t", room=rectangular(4000, 3000),
            cabinets=[cab(1, 900), cab(2, 600, h=2100, kind="tall")],
            placements=[Placement(1, "A", 0), Placement(2, "A", 900)],
            plinths=[PlinthChoice("A", "base", 1)])
    check("one run of both", [r.cabinets for r in runs(j)], [[1, 2]])
    check("so one plinth board spans both", [p.length for p in plinth_panels(j)], [1500])

    print("\na hung run stands on nothing")
    j = Job(name="h", room=rectangular(4000, 3000), cabinets=[cab(1, 900)],
            placements=[Placement(1, "A", 0, z=1500)],
            plinths=[PlinthChoice("A", "wall", 1)])
    check("no plinth is made", plinth_panels(j), [])
    check("and it says why",
          any("stands on nothing" in i.message for i in validate(j, generate_job(j))),
          True)

    print("\nthe legs have to reach")
    check("100 sits inside the 98-122 range",
          std.leg_min <= std.leg_height <= std.leg_max, True)
    check("and nothing complains",
          any("leg range" in i.message
              for i in validate(job_on(), [])), False)

    print("\nunconfirmed panel code")
    j = job_on()
    j.plinths = [PlinthChoice("A", "base", 1)]
    check("code 10 is flagged until Plazaboard signs it off",
          any("code 10" in i.message for i in validate(j, generate_job(j))), True)

    print("\nan orphaned choice makes nothing, and says so")
    j = job_on(spec=((1, 900, 0), (2, 600, 900)))
    j.plinths = [PlinthChoice("A", "base", 9)]
    check("no panel", plinth_panels(j), [])
    check("but a warning",
          any("no longer starts" in i.message for i in validate(j, generate_job(j))),
          True)

    print("\na job with no room is untouched by all of it")
    plain = Job(name="x", cabinets=[cab(1, 900)])
    check("no runs", runs(plain), [])
    check("no plinth panels", plinth_panels(plain), [])
    check("no plinths key in the job file", "plinths" in job_to_dict(plain), False)

    print("\njob files")
    j = job_on()
    j.plinths = [PlinthChoice("A", "base", 1, True, "kicks under the sink")]
    d1 = job_to_dict(j)
    check("round trip is identical",
          job_to_dict(job_from_dict(json.loads(json.dumps(d1)))), d1)
    check("the decision survives", job_from_dict(d1).plinths[0].fitted, True)

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
