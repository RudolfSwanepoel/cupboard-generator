"""The solid back — ruling 4 of the cabinet round brief (3 October 2026).

What is pinned here, from the brief's "Done when" line and Rudolf's change 1:

  * a 600 x 2400 x 570 tall with a solid back cuts a 06 line of 568 x 2368 in
    the carcass board and NO backing line, and a shelf of 550 at 4 mm;
  * a 450 x 790 x 570 base with a solid back cuts 418 x 774 and keeps only
    its Top Front — the Top Rear and the Back rows stay in the file, greyed,
    and are not cut;
  * switching back to Four restores the support rows untouched (the dicts are
    byte-equal) and they cut again;
  * a drawer unit's runner is picked over D, the same as a four-back unit of
    the same depth (Rudolf's change 1: the 40 mm clearance already covers a
    back face at 16 or 19), so every drawer panel is the same either way;
  * every place that reads where the back is reads the back actually chosen:
    the shelf depth, `back_face_from_front`, the shelf-fouls-back limit, the
    support layout, `room.back_part` and the 3D scene;
  * the five fields are written only when set (a job that never heard of a
    solid back round-trips byte for byte), the board slots are known to the
    swap / rename / library scan, the editor is offered Solid, the validator
    backstops a thin board, and the benchmark does not move.
"""
import copy
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
from fixture_jobs import job_file  # noqa: E402
sys.path.insert(0, ROOT)

from app import api                                                      # noqa: E402
from cabinetgen import scene as SC                                       # noqa: E402
from cabinetgen.boards import cabinet_board_ids                          # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job             # noqa: E402
from cabinetgen.model import MATERIALS, Cabinet, Drawer, Job, Support    # noqa: E402
from cabinetgen.room import back_part, shelf_layout, support_layout      # noqa: E402
from cabinetgen.standard import STANDARD                                 # noqa: E402
from cabinetgen.store import cabinet_from_dict, cabinet_to_dict, job_to_dict, load  # noqa: E402
from cabinetgen.validate import CRITICAL, WARNING, validate              # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                             # noqa: E402

FAILS = []
std = STANDARD


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def mats():
    return {k: dict(v) for k, v in MATERIALS.items() if k in ("MEL", "BROOKHILL", "BACK")}


def job_of(*cabs):
    return Job(name="s", boards=["MEL", "BROOKHILL", "BACK"], cabinets=list(cabs), materials=mats())


def typed(front=0, top_rear=0, back=0):
    return [Support(type="front", qty=front, cut_board="MEL", board="BROOKHILL", kind="pvc", edges=["front"]),
            Support(type="top_rear", qty=top_rear, cut_board="MEL", board="MEL", kind="pvc", edges=["front"]),
            Support(type="back", qty=back, cut_board="MEL", board="MEL", kind="pvc", edges=[])]


def cab(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    kw.setdefault("doors", 1)
    return Cabinet(**kw)


def lines(c, role=None):
    P = generate_cabinet(c, std, mats())
    return [(p.code, p.role, p.material, p.length, p.width, p.qty, p.edge_l, p.edge_w, p.edge_material)
            for p in P if role is None or p.role == role]


def issues(job, check_id=None, level=None):
    return [i for i in validate(job, generate_job(job))
            if (check_id is None or i.check == check_id) and (level is None or i.level == level)]


def main():
    print(__doc__.strip().splitlines()[0])

    print("\nthe tall: 600 x 2400 x 570, solid back, one shelf")
    tall = cab(width=600, height=2400, depth=570, kind="tall", back="solid", shelves=1,
               support_rows=typed(0, 0, 3))
    back6 = lines(tall, "Solid back")
    check("one 06 line, role Solid back, in the carcass board, 568 x 2368 (Length its height)",
          back6, [("06", "Solid back", "MEL", 2368, 568, 1, 0, 0, "")])
    check("no Backing line", lines(tall, "Backing"), [])
    check("the shelf is 550 deep at 4 mm (570 - 16 - 4)", [l[4] for l in lines(tall, "Shelve")], [550])
    check("its three Back rows are not cut", lines(tall, "Support"), [])
    check("the top and bottom keep their full depth", sorted(l[4] for l in lines(tall) if l[1] in ("Top", "Bottom")), [570, 570])
    check("the sides are unchanged", [l[3:6] for l in lines(tall, "Side")], [(2400, 570, 2)])

    print("\nthe base: 450 x 790 x 570, solid back, Front + Top Rear + Back x2 typed")
    base = cab(width=450, height=790, depth=570, kind="base", back="solid", support_rows=typed(1, 1, 2))
    check("06 Solid back 418 x 774 (standing on the bottom panel to the top of the sides)",
          [l[3:5] for l in lines(base, "Solid back")], [(774, 418)])
    sup = lines(base, "Support")
    check("only the Top Front is cut", [(l[5], l[6], l[8]) for l in sup], [(1, 1, "PVC BROOKHILL")])
    check("support_list is the Front alone", [r.type for r in base.support_list], ["front"])
    check("the rows are still all three in the cabinet", [(r.type, r.qty) for r in base.support_rows],
          [("front", 1), ("top_rear", 1), ("back", 2)])
    check("support_types_offered: front only", base.support_types_offered, ["front"])
    check("  and nothing on a tall", tall.support_types_offered, [])
    lay = support_layout(base, std, mats())
    check("support_layout draws the Front alone, where it always was",
          [(u["type"], u["y0"], u["y1"], u["z0"], u["z1"]) for u in lay], [("front", 0, 100, 774, 790)])

    print("\nswitching back to Four restores the rows untouched")
    before = cabinet_to_dict(base)
    base.back = "four"
    check("the rows cut again: Front, Top Rear, two Backs", [(l[5], l[6]) for l in lines(base, "Support")],
          [(1, 1), (1, 1), (2, 0)])
    check("and the backing is back", [l[1:5] for l in lines(base, "Backing")], [("Backing", "BACK", 770, 430)])
    base.back = "solid"
    check("the support rows' dicts are byte-equal before and after", cabinet_to_dict(base)["support_rows"],
          before["support_rows"])

    print("\nlegacy (untyped) rows under a solid back: the legacy rule (Rudolf's decision 3)")
    leg = cab(width=600, height=720, depth=560, kind="base", back="solid",
              supports=4, edged_supports=1, white_supports=0)
    check("a base keeps its one front-edged rail as the Top Front", [(r.edge, r.qty) for r in leg.support_list],
          [("front", 1)])
    legt = cab(width=600, height=2400, depth=560, kind="tall", back="solid", supports=4, edged_supports=1)
    check("a tall cuts none of them", leg_t := [(r.edge, r.qty) for r in legt.support_list], [])
    del leg_t

    print("\na drawer unit's runner is picked over D, the same as a four-back unit (change 1)")
    def drawer_unit(back, depth=556):
        return cab(width=600, height=720, depth=depth, kind="base", back=back, doors=0, has_doors=False,
                   drawers=[Drawer(face_height=200, box_height=150), Drawer(face_height=200, box_height=150)],
                   support_rows=typed(1, 1, 2))
    for depth in (556, 555, 500):
        four = [l for l in lines(drawer_unit("four", depth)) if l[1].startswith("Drawer")]
        sol = [l for l in lines(drawer_unit("solid", depth)) if l[1].startswith("Drawer")]
        check(f"D {depth}: every drawer panel identical either way", sol, four)
    check("pick_runner reads D and the 40 mm clearance only",
          (std.pick_runner(556, [350, 450, 500]), std.pick_runner(555, [350, 450, 500])), (500, 500))

    print("\nevery reader of the back's position reads the back actually chosen")
    check("back_face_from_front: four D - 19, solid D - 16, none as four",
          (std.back_face_from_front(570), std.back_face_from_front(570, "solid"),
           std.back_face_from_front(570, "none")), (551, 554, 551))
    check("shelf_depth: four 547, solid 550, fixed solid 553, typed clearance 2 solid 552",
          (std.shelf_depth(570), std.shelf_depth(570, back="solid"),
           std.shelf_depth(570, fixed=True, back="solid"), std.shelf_depth(570, back="solid", clearance=2)),
          (547, 550, 553, 552))
    check("shelf_layout's depth follows", [s["depth"] for s in shelf_layout(tall, std, mats())], [550])
    bp = back_part(tall, std, mats())
    xs = sorted({x for x, _ in bp.outline}); ys = sorted({y for _, y in bp.outline})
    check("room.back_part: role solid_back, between the sides, flush with their back edges, under the top",
          (bp.role, bp.board, xs, ys, bp.z0, bp.z1), ("solid_back", "MEL", [16, 584], [0, 16], 16, 2384))
    bpb = back_part(base, std, mats())
    check("  a base unit's stands on the bottom panel up to the top of the sides", (bpb.z0, bpb.z1), (16, 790))
    deep = cab(width=600, height=2400, depth=570, kind="tall", back="solid", template="none",
               bespoke=[])
    # the shelf-fouls-back limit: a bespoke shelf 555 deep in a 570 solid carcass fouls (554), 554 does not
    from cabinetgen.model import Panel
    def with_shelf(d):
        c = cab(number=1, width=600, height=2400, depth=570, kind="tall", back="solid")
        c.bespoke = [Panel(1, "05", "Shelve", "MEL", 568, d, 1)]
        return job_of(c)
    check("shelf-fouls-back: 555 fouls a solid back at 554, 554 clears it",
          (len(issues(with_shelf(555), "shelf-fouls-back", CRITICAL)), len(issues(with_shelf(554), "shelf-fouls-back", CRITICAL))),
          (1, 0))
    check("  (a grooved back's limit is still 551)", len(issues(
        job_of(cab(number=1, width=600, height=2400, depth=570, kind="tall", back="four",
                   bespoke=[Panel(1, "05", "Shelve", "MEL", 568, 552, 1)])), "shelf-fouls-back", CRITICAL)), 1)
    item = SC.build_cabinet(job_of(tall), 1)["items"][0]
    sb = [q for q in item["parts"] if q["role"] == "solid_back"]
    check("the 3D scene draws it, tied to its cut-list line", [(q["line"], q["board"]) for q in sb], [("106", "MEL")])
    check("  and no backing part", [q for q in item["parts"] if q["role"] == "back"], [])
    check("needs_back_board is off: nothing is cut from the backing board", tall.needs_back_board, False)
    check("no Top Rear / Back row is reported as off by the validator (the editor says why)",
          issues(job_of(base), "support-type-off"), [])

    print("\nthe board it is cut from, and its edging")
    check("blank follows the carcass board", (tall.solid_back_board, tall.solid_back_cut_board), ("", "MEL"))
    tall.solid_back_board = "BROOKHILL"
    check("its own board: cut in it, grain from it (BROOKHILL is grained: Length its height)",
          [l[2:5] for l in lines(tall, "Solid back")], [("BROOKHILL", 2368, 568)])
    check("unedged by default: counts 0, no tape", lines(tall, "Solid back")[0][6:], (0, 0, ""))
    tall.solid_back_long, tall.solid_back_short = 2, 1
    check("counted edges: 2 long (its height), 1 short, in the board's own PVC",
          lines(tall, "Solid back")[0][6:], (2, 1, "PVC BROOKHILL"))
    tall.solid_back_edge_kind, tall.solid_back_edge_board = "2mm", "MEL"
    check("a kind and a colour of its own", lines(tall, "Solid back")[0][8], "2mm WHITE")
    check("the slots are known: swap / rename / the library scan see both boards by name",
          sorted((lab, k) for k, lab in tall.board_refs() if lab.startswith("solid back")),
          [("solid back board", "BROOKHILL"), ("solid back edging board", "MEL")])
    check("  cabinet_board_ids agrees", {"BROOKHILL", "MEL", "BACK"} <= cabinet_board_ids(cabinet_to_dict(tall)), True)
    thin = cab(width=600, height=2400, depth=570, kind="tall", back="solid", solid_back_board="BACK")
    check("a thin board named for it is a warning (the editor never offers one)",
          [i.message[:16] for i in issues(job_of(thin), level=WARNING) if "solid back board" in i.message],
          ["solid back board"])

    print("\nthe job file")
    d = cabinet_to_dict(cab(width=600, height=2400, depth=570, kind="tall", back="four"))
    check("a cabinet with no solid back writes none of the five keys",
          [k for k in d if k.startswith("solid_back")], [])
    d2 = cabinet_to_dict(tall)
    check("one with them set writes them", sorted(k for k in d2 if k.startswith("solid_back")),
          ["solid_back_board", "solid_back_edge_board", "solid_back_edge_kind", "solid_back_long", "solid_back_short"])
    rt = cabinet_from_dict(json.loads(json.dumps(d2)))
    check("and reads them back", (rt.back, rt.solid_back_board, rt.solid_back_edge_kind, rt.solid_back_edge_board,
                                  rt.solid_back_long, rt.solid_back_short), ("solid", "BROOKHILL", "2mm", "MEL", 2, 1))
    for name in ("Test.json", "Test_Build.json", "Test_Panels.json", "Corner Unit Test.json"):
        j = load(job_file(name))
        check(f"{name} round-trips with no new key",
              sorted({k for c in job_to_dict(j)["cabinets"] for k in c if k.startswith("solid_back")}), [])

    print("\nthe editor and the engine agree on what is offered")
    d = api.defaults({})
    check("/api/defaults offers four, none and solid", d["backs"], ["four", "none", "solid"])
    r = api.what_if({"job": job_to_dict(job_of(copy.deepcopy(base))), "cabinet": 1, "set": {"back": "four"}})
    # 06 holds the backing again, the rows come back — and the one 04 line (the
    # Front alone) becomes 04a / 04b / 04c beside the Top Rear and the Backs,
    # which is `born_distinct` doing what it has always done when a second
    # distinct 04 appears; what-if names the plain 104 as leaving
    check("what-if, solid -> four on the base: only the plain 104 leaves (re-lettered beside the rows that come back)",
          [x["label"] for x in r["removed"]], ["104"])
    four_base = copy.deepcopy(base); four_base.back = "four"
    r = api.what_if({"job": job_to_dict(job_of(four_base)), "cabinet": 1, "set": {"back": "solid"}})
    check("what-if, four -> solid: the three lettered support lines are named before they go (the Front comes back as plain 104)",
          sorted(x["label"] for x in r["removed"]), ["104a", "104b", "104c"])
    g = api.compute({"job": job_to_dict(job_of(tall))})["geometry"]["1"]["solid_back"]
    check("the geometry payload says what it resolves to", (g["on"], g["cut_board"], g["kind"], g["edge_board"], g["tape"]),
          (True, "BROOKHILL", "2mm", "MEL", "2mm WHITE"))

    print("\nthe benchmark")
    P = generate_job(OCT)
    check("272 / 59 / 30", (sum(p.qty for p in P if p.material == "MEL"), sum(p.qty for p in P if p.material == "BROOKHILL"),
                            sum(p.qty for p in P if p.material == "BACK")), (272, 59, 30))
    check("no October cabinet has a solid back", [c.number for c in OCT.cabinets if c.solid_back], [])

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
