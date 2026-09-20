"""Swapping a board moves every use of it, and says what that does.

    python tools/check_swap.py

What is pinned here, and why:

  * **A swap moves EVERY use of the old board** (ruled 20 September 2026, which
    overrode an earlier choice to leave hand-specified panels alone). Every field
    `Cabinet.board_refs` knows about — doors, drawers, back, edging boards,
    support rows — plus every bespoke panel and every loose panel. A board being
    swapped out must not still be named anywhere, or the cut list quotes a board
    the project no longer carries.

  * **A panel is never renamed by a swap.** It keeps its designation and changes
    what it is cut from (the 14 September 2026 rule). Checked on a full merge of
    the October job, where 254 panels change board.

  * **Bespoke and loose panels store grain and edging as TYPED values.**
    `generate_job` is read-only with respect to them, so moving the board alone
    would leave a woodgrain panel at grain 0 — which is W8/D9 exactly, 60 décor
    panels that went out unlocked and were caught by Plazaboard's counter rather
    than by us. Grain is re-read from the new board; the edging is matched by
    KIND, so a panel edged in the old board's PVC is edged in the new board's
    PVC. An edging that never matched the old board is a literal somebody typed
    and is left alone.

  * **What cannot be mapped is not carried over and not silent.** If the new
    board does not offer the kind, the edging is cleared and the bands are left,
    so the panel still says it wants edging and the EDGING critical fires.

  * **A swap reports what it does to the VALIDATION**, not only to the cost. It
    is how a design gets previewed, so a grain lock that no longer fits a sheet
    or an edging the new board cannot supply has to be visible before anything is
    written.

  * **A grain-locked panel is measured as it will be cut.** One that only fits
    turned fits on a plain board and does not fit on a grained one, and the
    nester would drop it without a word.

  * **Swapping onto a board the project already carries MERGES them**, and that
    cannot be undone by swapping back — nothing records which panels used to be
    which. The caller is told before it writes.
"""
import copy
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "app"))

import api                                                                    # noqa: E402
from cabinetgen import boards as B                                            # noqa: E402
from cabinetgen.engine import generate_job                                    # noqa: E402
from cabinetgen.model import (MATERIALS, Cabinet, Drawer, Job,                # noqa: E402
                              Panel, Support)
from cabinetgen.standard import STANDARD as S                                 # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict                       # noqa: E402
from cabinetgen.validate import _panel_fits_board                             # noqa: E402
from jobs.wardrobe_oct2025 import JOB                                         # noqa: E402

NL = chr(10)
FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def mats(*ids, **over):
    m = {k: dict(v) for k, v in MATERIALS.items() if not ids or k in ids}
    for key, patch in over.items():
        m.setdefault(key, {}).update(patch)
    return m


def box(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("width", 600)
    kw.setdefault("height", 720)
    kw.setdefault("depth", 580)
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    return Cabinet(**kw)


def swap(job, frm, to, apply=False):
    payload = {"job": job_to_dict(job), "from": frm, "to": to}
    if apply:
        payload["apply"] = True
    return api.board_swap(payload)


def main():
    print(__doc__.strip().splitlines()[0])

    # --- every use moves ----------------------------------------------------
    print(NL + "a board named ONLY in one out-of-the-way place is still moved")
    grey = {"name": "Grey", "board": "Grey", "tape": "Grey",
            "thickness": 16, "grain": "plain", "price": 1100.0}
    for label, cab in (
            ("a door leaf", box(doors=2, door_boards=["", "GREY"])),
            ("a back board", box(back_board="GREY")),
            ("a drawer face", box(drawers=[Drawer(face_height=150, box_height=120,
                                                  face_board="GREY")],
                                  has_drawers=True)),
            ("an edging colour", box(doors=1, door_edge_board="GREY")),
            ("a support row", box(support_rows=[Support(edge="none", qty=1,
                                                        board="GREY", kind="pvc")])),
            ("a bespoke panel", box(template="none",
                                    bespoke=[Panel(cabinet=1, code="01", role="Side",
                                                   material="GREY", length=700,
                                                   width=500)])),
    ):
        j = Job(name="s", boards=["MEL", "BROOKHILL", "BACK", "GREY"],
                cabinets=[cab], materials=mats(GREY=grey))
        r = swap(j, "GREY", "WHITEMEL" if False else "MEL")
        moved = [f for c in r["cabinets"] for f in c["fields"]]
        check(f"{label} moves", bool(moved) or bool(r["retyped"]), True)

    print(NL + "a LOOSE panel moves too, and it is not attached to any cabinet")
    j = Job(name="l", boards=["MEL", "BROOKHILL", "BACK", "GREY"],
            cabinets=[box()], materials=mats(GREY=grey),
            loose=[Panel(cabinet=0, code="11", role="Filler", material="GREY",
                         length=600, width=100)])
    r = swap(j, "GREY", "MEL", apply=True)
    after = job_from_dict(r["job"])
    check("the loose panel is on the new board",
          [p.material for p in after.loose], ["MEL"])
    check("and GREY is named nowhere in the job",
          [b for c in after.cabinets for b, _ in c.board_refs() if b == "GREY"]
          + [p.material for p in after.loose if p.material == "GREY"], [])

    # --- typed panels are re-derived ---------------------------------------
    print(NL + "a hand-specified panel's GRAIN follows its new board")
    j = Job(name="g", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="MEL", length=700, width=500,
                                         grain=0)])])
    r = swap(j, "MEL", "BROOKHILL", apply=True)
    panel = job_from_dict(r["job"]).cabinets[0].bespoke[0]
    check("plain -> grained locks it", (panel.material, panel.grain), ("BROOKHILL", 1))
    check("and the swap says so",
          [(x["label"], x.get("grain_from"), x.get("grain_to")) for x in r["retyped"]],
          [("101", 0, 1)])

    print(NL + "and back the other way, a grained board's lock is released")
    j = Job(name="g2", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="BROOKHILL", length=700,
                                         width=500, grain=1)])])
    r = swap(j, "BROOKHILL", "MEL", apply=True)
    panel = job_from_dict(r["job"]).cabinets[0].bespoke[0]
    check("grained -> plain unlocks it", (panel.material, panel.grain), ("MEL", 0))

    print(NL + "its EDGING is matched by kind, not carried over as a name")
    j = Job(name="e", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="MEL", length=700, width=500,
                                         edge_l=1, edge_material="PVC WHITE")])])
    r = swap(j, "MEL", "BROOKHILL", apply=True)
    panel = job_from_dict(r["job"]).cabinets[0].bespoke[0]
    check("the old board's PVC becomes the new board's PVC",
          panel.edge_material, "PVC WOOD")
    check("nothing is left unmapped", r["unmapped"], [])

    print(NL + "an edging that never matched the old board is left alone")
    j = Job(name="e2", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="MEL", length=700, width=500,
                                         edge_l=1, edge_material="SOMETHING TYPED")])])
    r = swap(j, "MEL", "BROOKHILL", apply=True)
    check("a literal is not a derived value, so it does not follow",
          job_from_dict(r["job"]).cabinets[0].bespoke[0].edge_material,
          "SOMETHING TYPED")

    print(NL + "what the new board cannot supply is cleared, and blocks the export")
    m = mats(BROOKHILL={"edging_kinds": ["2mm"]})
    j = Job(name="u", boards=["MEL", "BROOKHILL", "BACK"], materials=m,
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="MEL", length=700, width=500,
                                         edge_l=1, edge_material="PVC WHITE")])])
    r = swap(j, "MEL", "BROOKHILL")
    check("the panel is reported as unmapped",
          [(u["label"], u["kind"]) for u in r["unmapped"]], [("101", "pvc")])
    fresh = [i for i in r["new_issues"] if i["ref"] == "EDGING"]
    check("and an EDGING critical is raised", [i["level"] for i in fresh], ["critical"])
    check("naming the panel, not guessing a tape", fresh[0]["where"], "101")

    # --- grain and the sheet ------------------------------------------------
    print(NL + "a grain-locked panel is measured as it will be cut, not turned")
    fits_turned = Panel(cabinet=1, code="07", role="Door", material="X",
                        length=1000, width=1900, grain=0)
    locked = Panel(cabinet=1, code="07", role="Door", material="X",
                   length=1000, width=1900, grain=1)
    check("1000x1900 fits a plain board, turned", _panel_fits_board([fits_turned], S), [])
    check("the same panel grain-locked does not",
          len(_panel_fits_board([locked], S)), 1)
    check("and the message says why the grain is the reason",
          "grain locked" in _panel_fits_board([locked], S)[0].message, True)
    still = Panel(cabinet=1, code="08", role="Exposed Panel", material="X",
                  length=2882, width=50, grain=1)
    check("a panel too big either way keeps its original wording",
          _panel_fits_board([still], S)[0].message,
          f"2882x50 does not fit a {S.sheet_l}x{S.sheet_w} board")

    print(NL + "so a swap onto a grained board surfaces it as a NEW critical")
    j = Job(name="f", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="MEL", length=1000, width=1900,
                                         grain=0)])])
    r = swap(j, "MEL", "BROOKHILL")
    w2 = [i for i in r["new_issues"] if i["ref"] == "W2"]
    check("it did not fit before and does now", len(w2), 1)
    check("as a critical that blocks", (w2[0]["level"], r["blocks"]),
          ("critical", True))

    # --- merging ------------------------------------------------------------
    print(NL + "swapping onto a board the project already has MERGES them")
    j = Job(name="m", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(doors=1)])
    check("merged is flagged", swap(j, "MEL", "BROOKHILL")["merged"], True)
    j2 = Job(name="m2", boards=["MEL", "BACK"], materials=mats("MEL", "BACK"),
             cabinets=[box(exterior_board="MEL", doors=1)])
    check("bringing in a board it does not have is not a merge",
          swap(j2, "MEL", "BROOKHILL")["merged"], False)

    # --- the October job, end to end ---------------------------------------
    print(NL + "the October job: a full merge of MEL into BROOKHILL")
    before = generate_job(JOB)
    r = swap(JOB, "MEL", "BROOKHILL", apply=True)
    after = generate_job(job_from_dict(r["job"]))
    check("NO panel is renamed",
          ({p.label for p in after} - {p.label for p in before},
           {p.label for p in before} - {p.label for p in after}), (set(), set()))
    check("nothing is cut from MEL any more",
          sorted({p.material for p in after}), ["BACK", "BROOKHILL"])
    check("every hand-specified panel was re-derived, none left at grain 0",
          [p.label for p in after if p.material == "BROOKHILL" and not p.grain], [])
    check("and the swap said how many it re-typed", len(r["retyped"]), 9)
    check("it reports the panels each board gains and loses",
          {m["board"]: (m["before"], m["after"]) for m in r["moved_by_board"]},
          {"MEL": (254, 0), "BROOKHILL": (77, 331)})

    print(NL + "the diff reports a hand-specified panel's REAL before value")
    # engine.resolved hands a bespoke or loose panel back as the very same object
    # the job holds, so the swap's in-place re-derivation rewrites the records the
    # "before" list points at. Taken afterwards, the diff compared the new values
    # with themselves and reported that nothing had moved.
    j = Job(name="alias", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(template="none",
                          bespoke=[Panel(cabinet=1, code="01", role="Side",
                                         material="MEL", length=700, width=500,
                                         edge_l=1, edge_material="PVC WHITE")])])
    r = swap(j, "MEL", "BROOKHILL")
    check("the panel is in the diff at all",
          [p["label"] for p in r["panels"]], ["101"])
    check("with the board it was really cut from before",
          (r["panels"][0]["from"], r["panels"][0]["to"]), ("MEL", "BROOKHILL"))
    check("and the edging it really had before",
          (r["panels"][0]["tape_from"], r["panels"][0]["tape_to"]),
          ("PVC WHITE", "PVC WOOD"))

    print(NL + "on the October job that is the 102 generated plus the 9 typed")
    oct_pre = api.board_swap({"job": job_to_dict(JOB), "from": "MEL",
                              "to": "BROOKHILL"})
    check("111 panels change board or edging", len(oct_pre["panels"]), 111)

    print(NL + "a preview writes nothing")
    d = job_to_dict(JOB)
    pre = api.board_swap({"job": d, "from": "MEL", "to": "BROOKHILL"})
    check("no job comes back", "job" in pre, False)
    check("and the dict it was handed is untouched",
          sorted({c["carcass_board"] for c in d["cabinets"]}), ["MEL"])
    # MEL still present is the point: a preview that had mutated would show
    # BROOKHILL here. (DECOR is the pre-rename id the frozen job names its own
    # bespoke panels by — model.BOARD_ALIASES resolves it.)
    check("its bespoke panels are untouched too",
          sorted({p["material"] for c in d["cabinets"] for p in c["bespoke"]}),
          ["DECOR", "MEL"])
    check("and so are its loose panels",
          sorted({p["material"] for p in d["loose"]}), ["DECOR", "MEL"])

    # --- grain is listed, never judged --------------------------------------
    print(NL + "a swap says which panels lock, which come free, and which way")
    r = swap(JOB, "MEL", "BROOKHILL")
    g = r["grain"]
    check("every one of them changes grain", bool(g), True)
    check("all of these lock, because Brookhill is the grained board",
          sorted({x["locked"] for x in g}), [True])
    one = g[0]
    check("each carries its size", (one["length"] > 0, one["width"] > 0), (True, True))
    check("and the direction, said out loud",
          one["runs"], f"along Length, {one['length']} mm")
    check("and which board it is now cut from", one["board"], "BROOKHILL")

    print(NL + "and back the other way they come free")
    j = Job(name="free", boards=["MEL", "BROOKHILL", "BACK"], materials=mats(),
            cabinets=[box(carcass_board="BROOKHILL", doors=1)])
    back = swap(j, "BROOKHILL", "MEL")["grain"]
    check("nothing is locked any more", sorted({x["locked"] for x in back}), [False])
    check("and it says the nester may turn them",
          "either way" in back[0]["runs"], True)

    print(NL + "what the lost rotation costs is separated from the board price")
    rot = r["rotation"]
    check("the locked nest is the one being quoted",
          rot["cost_with_lock"], r["after"]["cost"])
    check("freeing the grain is re-nested, not guessed",
          rot["cost_if_free"] < rot["cost_with_lock"], True)
    check("and the difference is reported",
          rot["cost_of_lock"], round(rot["cost_with_lock"] - rot["cost_if_free"], 2))
    check("on the October job the lock costs a whole extra board",
          rot["boards_with_lock"]["BROOKHILL"] - rot["boards_if_free"]["BROOKHILL"], 1)

    # --- deleting a project -------------------------------------------------
    print(NL + "deleting a project moves it aside; it is never unlinked")
    import shutil, tempfile                                          # noqa: E402
    tmp = tempfile.mkdtemp()
    real_jobs, real_del = api.JOBS_DIR, api.DELETED_DIR
    api.JOBS_DIR = tmp
    api.DELETED_DIR = os.path.join(tmp, "_deleted")
    try:
        for name in ("Keep.json", "Test.json"):
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write('{"name": "x", "cabinets": []}')
        info = api.job_delete_info({"path": "Keep.json", "open": "Other.json"})
        check("it knows the file is there", info["exists"], True)
        check("and that it is not the one open", info["is_open"], False)
        check("a fixture job says so", api.job_delete_info(
            {"path": "Test.json", "open": ""})["fixture"], True)
        check("an ordinary one does not", info["fixture"], False)

        open_now = api.job_delete({"path": "Keep.json", "open": "Keep.json"})
        check("the job on screen cannot be deleted", open_now["ok"], False)
        check("and it says why", "open here" in open_now["error"], True)
        check("so the file is still there",
              os.path.exists(os.path.join(tmp, "Keep.json")), True)

        gone = api.job_delete({"path": "Keep.json", "open": "Other.json"})
        check("deleting moves it", gone["ok"], True)
        check("out of jobs/", os.path.exists(os.path.join(tmp, "Keep.json")), False)
        check("and into _deleted/, still readable",
              os.path.exists(os.path.join(tmp, "_deleted", "Keep.json")), True)
        check("a job that is not there is refused, not invented",
              api.job_delete({"path": "Nope.json", "open": ""})["ok"], False)

        # a second delete of the same name must not overwrite the first
        with open(os.path.join(tmp, "Keep.json"), "w", encoding="utf-8") as fh:
            fh.write('{"name": "second", "cabinets": []}')
        again = api.job_delete({"path": "Keep.json", "open": ""})
        check("a second one of the same name is kept too", again["ok"], True)
        check("under a stamped name, so the first survives",
              len(os.listdir(os.path.join(tmp, "_deleted"))), 2)
    finally:
        api.JOBS_DIR, api.DELETED_DIR = real_jobs, real_del
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + ", ".join(FAILS))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
