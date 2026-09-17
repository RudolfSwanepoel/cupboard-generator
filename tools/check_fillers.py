"""Filler and scribe regression check.

    python tools/check_fillers.py

A filler is the one panel the app invents rather than derives from a cabinet, so
it is the one most able to go out wrong without anybody noticing. Two facts
drive every number here and neither is negotiable:

  * Plazaboard cut on a beam saw. Guillotine only. A tapered panel cannot be
    ordered, so a tapered gap ships as a rectangle at its widest plus the scribe
    allowance, marked trim on site.
  * The app proposes a treatment and never inserts one. A gap nobody has ruled
    on produces no panel — and a warning, so it cannot leave quietly.

The taper cases use offsets that divide exactly into the 600 mm measuring depth,
so the expected answer is arithmetic anyone can check on paper rather than
whatever the code happened to return.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cabinetgen.engine import generate_job, room_panels                   # noqa: E402
from cabinetgen.model import Cabinet, GapChoice, Job, Placement           # noqa: E402
from cabinetgen.room import gaps, rectangular                             # noqa: E402
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


def kitchen(offset_start=0, widths=((1, 900, 0), (2, 600, 1000)), wall="A"):
    """A room with a base run on wall A, positioned exactly where asked."""
    rm = rectangular(4000, 3000)
    rm.walls[0].offset_start = offset_start
    cabs = [cab(n, w) for n, w, _ in widths]
    places = [Placement(n, wall, x) for n, _, x in widths]
    return Job(name="k", cabinets=cabs, room=rm, placements=places)


def main() -> int:
    std = STANDARD
    print("a square room: gaps are parallel")
    j = kitchen(widths=((1, 900, 0), (2, 600, 1000)))
    g = gaps(j)
    check("one gap between the two cabinets, one at the wall end", len(g), 2)
    mid = [x for x in g if x.after == 1][0]
    check("gap between 1 and 2 is 100 wide", mid.nominal, 100)
    check("and parallel", mid.taper, 0)
    check("so front equals the wall face", mid.front, mid.nominal)
    check("100 mm suggests a filler", mid.proposal, "filler")
    check("nothing is decided yet", mid.treatment, "")

    print("\nproposal thresholds: 50 and 150, ruled 14 Sept 2026")
    for gap_w, want in [(40, "grow"), (50, "filler"), (150, "filler"), (151, "cabinet")]:
        jj = kitchen(widths=((1, 900, 0), (2, 600, 900 + gap_w)))
        mid = [x for x in gaps(jj) if x.after == 1][0]
        check(f"a {gap_w} mm gap suggests {want}", mid.proposal, want)

    print("\nan out-of-square corner tapers the gap it touches")
    # 30 mm out at the 600 mm measuring depth, over a 580 deep run:
    # taper = 580 * 30/600 = 29 mm exactly
    j = kitchen(offset_start=30, widths=((1, 900, 60),))
    lead = [x for x in gaps(j) if x.after is None][0]
    check("gap at the wall face", lead.nominal, 60)
    check("gap at the front of the run", lead.front, 89)
    check("taper is depth x offset / offset_depth", lead.taper, 29)
    check("the filler is cut at the widest point", lead.width, 89)
    check("plus the 15 mm scribe allowance", lead.filler_width(std), 104)
    mid = [x for x in gaps(j) if x.after == 1][0]
    check("the gap away from the corner stays parallel", mid.taper, 0)

    print("\nthe taper threshold is 6 mm")
    # 5 mm out over 600, on a 580 deep run: 580 * 5/600 = 4.83 -> 5 mm
    j5 = kitchen(offset_start=5, widths=((1, 900, 60),))
    small = [x for x in gaps(j5) if x.after is None][0]
    check("a 5 mm taper is under the threshold", small.taper, 5)
    j5.gaps = [GapChoice("A", None, 1, "base", "filler")]
    check("so the panel is not marked as a scribe",
          "SCRIBE" in room_panels(j5)[0].note, False)
    check("and the validator says nothing about it",
          any("taper" in i.message for i in validate(j5, generate_job(j5))), False)

    j29 = kitchen(offset_start=30, widths=((1, 900, 60),))
    j29.gaps = [GapChoice("A", None, 1, "base", "filler")]
    p = room_panels(j29)[0]
    check("a 29 mm taper is marked SCRIBE on the panel", "SCRIBE" in p.note, True)
    check("and the validator warns",
          any("taper" in i.message for i in validate(j29, generate_job(j29))), True)

    print("\nnothing is inserted on its own")
    j = kitchen(widths=((1, 900, 0), (2, 600, 1000)))
    check("an undecided gap makes no panel", room_panels(j), [])
    msgs = [i.message for i in validate(j, generate_job(j))]
    check("but it does warn, twice, once per gap",
          sum(1 for m in msgs if "no treatment chosen" in m), 2)
    check("and the warning carries the suggestion",
          any("suggest filler" in m for m in msgs), True)

    for treatment in ("open", "blind"):
        jj = kitchen(widths=((1, 900, 0), (2, 600, 1000)))
        jj.gaps = [GapChoice("A", 1, 2, "base", treatment)]
        check(f"'{treatment}' makes no panel either",
              len(room_panels(jj)), 0)

    print("\na filler that was actually chosen")
    j = kitchen(widths=((1, 900, 0), (2, 600, 1000)))
    j.gaps = [GapChoice("A", 1, 2, "base", "filler")]
    ps = room_panels(j)
    check("one panel", len(ps), 1)
    p = ps[0]
    check("code 11", p.code, "11")
    check("belongs to no cabinet", p.cabinet, 0)
    check("length is the run height", p.length, 720)
    check("width is the gap plus the scribe", p.width, 115)
    check("decor, so grain must be set", (p.material, p.grain), ("DECOR", 1))
    check("no edging, following the October job's fillers",
          (p.edge_l, p.edge_w, p.edge_material), (0, 0, ""))
    check("the note says where it goes and what to do",
          "wall A" in p.note and "trim on site" in p.note, True)
    check("it reaches the cut list",
          [x.label for x in generate_job(j) if x.code == "11"], ["011"])

    print("\ntwo fillers of different sizes get told apart")
    j = kitchen(offset_start=0, widths=((1, 900, 100), (2, 600, 1200)))
    j.gaps = [GapChoice("A", None, 1, "base", "filler"),
              GapChoice("A", 1, 2, "base", "filler")]
    labels = sorted(x.label for x in generate_job(j) if x.code.startswith("11"))
    check("suffixed, so one label never covers two panels", labels, ["011a", "011b"])

    print("\nruns are per wall and per layer")
    j = Job(name="l", room=rectangular(4000, 3000),
            cabinets=[cab(1, 900), cab(2, 900, d=330, h=700, kind="upper")],
            placements=[Placement(1, "A", 0), Placement(2, "A", 1200)])
    lay = sorted({g.layer for g in gaps(j)})
    check("the base run and the overheads gap separately", lay, ["base", "wall"])
    check("a base cabinet does not close a gap in the wall run",
          len([g for g in gaps(j) if g.layer == "wall" and g.after is None]), 1)

    print("\nunconfirmed panel code")
    j = kitchen(widths=((1, 900, 0), (2, 600, 1000)))
    j.gaps = [GapChoice("A", 1, 2, "base", "filler")]
    check("code 11 is flagged until Plazaboard signs it off",
          any("not been confirmed" in i.message for i in validate(j, generate_job(j))),
          True)

    print("\na job with no room is untouched by all of it")
    plain = Job(name="p", cabinets=[cab(1, 900)])
    check("no gaps", gaps(plain), [])
    check("no filler panels", room_panels(plain), [])
    check("no gaps key in the job file", "gaps" in job_to_dict(plain), False)

    print("\njob files")
    j = kitchen(widths=((1, 900, 0), (2, 600, 1000)))
    j.gaps = [GapChoice("A", 1, 2, "base", "filler", "agreed on site")]
    d1 = job_to_dict(j)
    check("round trip is identical",
          job_to_dict(job_from_dict(json.loads(json.dumps(d1)))), d1)
    check("the decision survives",
          job_from_dict(d1).gaps[0].treatment, "filler")

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
