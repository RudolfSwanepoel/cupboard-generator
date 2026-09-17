"""Request handlers. Thin — they call cabinetgen and return JSON.

Nothing here decides a dimension. Every number in a response came out of the
engine; this module only moves it from a dataclass into a dict.
"""
import glob
import json
import os
import re
import threading
from dataclasses import asdict, fields as dc_fields
from http.server import BaseHTTPRequestHandler

from cabinetgen import nest as N
from cabinetgen.drawers import (divide, equal_shares, graduated_shares,
                                opening_for, remainder, split_pair, stack)
from cabinetgen.engine import generate_job
from cabinetgen.export_plaza import estimate_cost, summarise, write_csvs
from cabinetgen.model import CODES, hinge_side
from cabinetgen.render import elevation_svg, plan_svg, wall_elevation_svg
from cabinetgen.room import (LAYERS, add_wall, clashes as room_clashes, closure_error,
                             gaps as room_gaps, geometry, layer_of,
                             overlaps as room_overlaps, placement_for,
                             plinth_choice_for, plinth_lengths, rectangular,
                             runs as room_runs, snap_points)
from cabinetgen.standard import STANDARD
from cabinetgen.store import (job_from_dict, job_to_dict, load, next_number,
                              room_from_dict, room_to_dict, save)
from cabinetgen.validate import ALLOWED_EDGE, blocking, validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_DIR = os.path.join(ROOT, "jobs")
OUT_DIR = os.path.join(ROOT, "out")

# nest_job records its winning heuristic in module globals, so one nest at a time.
NEST_LOCK = threading.Lock()


# --- helpers ---------------------------------------------------------------

def _job(payload):
    """Build a fresh Job from the posted dict.

    Fresh every request on purpose: engine.suffix_labels rewrites panel codes in
    place, so a reused Job would grow a second suffix on every compute.
    """
    return job_from_dict(payload.get("job") or {})


def _panel_row(p, std):
    d = asdict(p)
    d["label"] = p.label
    d["edging_m"] = round(p.edging_m(std), 3)
    d["holes_total"] = p.pot_holes * p.qty      # Plazaboard's column is the line total
    return d


def _job_path(name):
    """A .json file inside jobs/ — basename() keeps a posted name from escaping."""
    base = os.path.basename(str(name or "").strip())
    if not base:
        raise ValueError("no job name given")
    if not base.endswith(".json"):
        base += ".json"
    return os.path.join(JOBS_DIR, base)


def _as_spec(v):
    """Drawer spec off the wire: a count, a list of weights, or a list of heights."""
    if isinstance(v, list):
        return [float(x) if float(x) != int(float(x)) else int(x) for x in v]
    return int(v)


# --- endpoints -------------------------------------------------------------

def defaults(payload):
    """Everything the front end would otherwise be tempted to hardcode."""
    return {
        "ok": True,
        "standard": {k: v for k, v in asdict(STANDARD).items()
                     if isinstance(v, (int, float, str))},
        "runner_lengths": list(STANDARD.runner_lengths),
        "codes": CODES,
        "edge_materials": sorted(x for x in ALLOWED_EDGE if x),
        "kinds": ["tall", "upper", "base"],
        "corner_styles": ["", "mitre", "ell"],
        "hinge_sides": ["L", "R"],
        "face_modes": ["share", "fixed"],
        "face_presets": ["equal", "graduated"],
        "backs": ["four", "three", "none"],
        "bases": ["board", "melamine"],
        "materials": ["MEL", "DECOR", "BACK"],
        "opening_kinds": ["door", "window", "arch"],
        "obstruction_kinds": ["plug", "isolator", "waste", "water", "pipe", "meter"],
        "layers": list(LAYERS),
    }


def _geometry_info(job, cab, std):
    g = geometry(cab, std)
    # One leaf per door panel that was actually cut, so a bespoke or corner unit
    # gets a hinge control too — cab.doors is 0 on those. The side is the engine's
    # own answer, the same one the plan swings from and the elevation draws.
    p = placement_for(job, cab.number)
    flip = bool(p.flip) if p is not None else False
    n = len(g.door_widths)
    return {"width": g.width, "depth": g.depth, "height": g.height,
            "source": g.source, "points": len(g.footprint),
            "footprint": [list(pt) for pt in g.footprint],
            "mitre_deg": g.mitre_deg,               # an output, never an input
            "face_lengths": g.face_lengths,
            "doors": g.door_widths,
            # what the two tickboxes actually resolve to, so the browser reads
            # the state back rather than working the rule out a second time
            "corner_on": cab.corner_on,
            "drawers_on": bool(cab.drawer_list),
            "hinges": [hinge_side(cab, i, n, flip) for i in range(n)],
            "hinges_set": [cab.door_hinges[i] if i < len(cab.door_hinges) else ""
                           for i in range(n)],
            "opening": opening_for(cab.height,
                                   (cab.door_height or (cab.height - std.door_height_gap))
                                   if cab.doors else 0, std)}


def _room_info(job):
    """Closure feedback and the layer census. Every number still from the engine."""
    rm = job.room
    if rm is None:
        return None
    counts = {lay: 0 for lay in LAYERS}
    unplaced = []
    places = {}
    for cab in job.cabinets:
        p = placement_for(job, cab.number)
        if p is None:
            unplaced.append(cab.number)
            continue
        lay = layer_of(cab, p)          # derived here, never in the browser
        counts[lay] = counts.get(lay, 0) + 1
        places[str(cab.number)] = {"wall": p.wall, "x": p.x, "z": p.z,
                                   "layer": lay, "override": bool(p.layer)}
    return {
        "name": rm.name,
        "walls": [{"id": w.id, "length": w.length} for w in rm.walls],
        "closed": rm.closed,
        "closure_error": closure_error(rm),
        "placed": len(job.placements),
        "layers": counts,
        "unplaced": unplaced,
        "placements": places,
        "gaps": [{"wall": g.wall, "layer": g.layer, "after": g.after,
                  "before": g.before, "width": g.width, "nominal": g.nominal,
                  "front": g.front, "taper": g.taper, "depth": g.depth,
                  "proposal": g.proposal, "treatment": g.treatment,
                  "filler_width": g.filler_width(job.std)}
                 for g in room_gaps(job, job.std)],
        "runs": [_run_info(job, r) for r in room_runs(job, job.std)],
        "overlaps": [{"a": o.a, "b": o.b, "wall": o.wall, "mm": o.mm}
                     for o in room_overlaps(job)],
        "clashes": [{"cabinet": c.cabinet, "kind": c.kind, "against": c.against}
                    for c in room_clashes(job, job.std)],
    }


def _run_info(job, r):
    choice = plinth_choice_for(job, r)
    fitted = bool(choice and choice.fitted)
    return {"wall": r.wall, "layer": r.layer, "z": r.z, "first": r.first,
            "cabinets": r.cabinets, "length": r.length,
            "on_floor": r.z == 0, "fitted": fitted,
            "boards": [ln for ln, _ in plinth_lengths(job, r, job.std)] if fitted else []}


def compute(payload):
    """Panels, issues, summary, cost, elevation and nest layouts in one payload."""
    job = _job(payload)
    out = {
        "ok": True, "error": "",
        "name": job.name,
        "room": _room_info(job),
        "elevation": elevation_svg(job),
        "panels": [], "issues": [], "blocking": False,
        "summary": {"materials": {}, "edging": {}, "potholes": 0},
        "cost": {"lines": [], "total_incl_vat": 0.0},
        "nest": {}, "rejects": [],
    }

    try:
        panels = generate_job(job)
    except Exception as exc:
        # A cabinet the engine refuses to build — too shallow for any runner, a
        # drawer opening that will not divide. Keep the elevation so the user can
        # see what they were building when it broke.
        out["ok"] = False
        out["error"] = str(exc)
        return out

    issues = validate(job, panels)
    out["issues"] = [asdict(i) for i in issues]
    out["blocking"] = blocking(issues)
    out["panels"] = [_panel_row(p, job.std) for p in panels]
    # what each cabinet actually is, off its panels — the editor shows it beside
    # the declared figures so a bespoke cabinet's label cannot pass for its size
    out["geometry"] = {str(c.number): _geometry_info(job, c, job.std)
                       for c in job.cabinets}

    with NEST_LOCK:
        nested = N.nest_job(N.nestable(panels, job.std), job.std)
        rejects = list(N.NEST_REJECTS)
        choice = dict(N.NEST_CHOICE)
        for mat, sheets in nested.items():
            used = sum(s.used_area for s in sheets)
            area = sum(s.area for s in sheets) or 1
            out["nest"][mat] = {
                "sheets": len(sheets),
                "yield": round(100.0 * used / area, 1),
                "used_m2": round(used / 1e6, 2),
                "area_m2": round(area / 1e6, 2),
                "sort": choice.get(mat, ("", ""))[0],
                "rule": choice.get(mat, ("", ""))[1],
                "detail": [{"panels": len(s.placements), "yield": round(s.yield_pct, 1)}
                           for s in sheets],
                "svg": N.sheets_svg(sheets, mat),
            }
        summary = summarise(job, panels, nested)

    out["rejects"] = [{"label": r[0], "length": r[1], "width": r[2]} for r in rejects]
    out["summary"] = summary
    out["cost"] = estimate_cost(job, summary)
    return out


def drawer_stack(payload):
    """Face heights for a stack. The arithmetic stays in cabinetgen.drawers."""
    height = int(payload["height"])
    door_height = int(payload.get("door_height") or 0)
    boxes = payload.get("boxes")
    boxes = [int(b) for b in boxes] if isinstance(boxes, list) else int(boxes)
    ds = stack(height, _as_spec(payload["spec"]), boxes,
               door_height=door_height, base=payload.get("base") or "board")
    return {
        "ok": True,
        "opening": opening_for(height, door_height),
        "drawers": [asdict(d) for d in ds],
    }


def drawer_solve(payload):
    """Face heights for a stack described row by row — Share or Fixed.

    Every number in the reply is drawers.divide's, including the running total
    and what is left over. The browser shows them; it works none of them out.
    """
    height = int(payload["height"])
    door_height = int(payload.get("door_height") or 0)
    rows = payload.get("rows") or []
    modes = ["fixed" if str(r.get("mode")) == "fixed" else "share" for r in rows]
    values = [float(r.get("value") or 0) for r in rows]
    opening = opening_for(height, door_height)
    heights = divide(opening, modes, values)
    used = sum(heights) + STANDARD.stack_gap * max(len(heights) - 1, 0)
    return {"ok": True, "opening": opening, "heights": heights,
            "used": used, "left": opening - used,
            "share_left": remainder(opening, modes, values),
            "gap": STANDARD.stack_gap}


def drawer_preset(payload):
    """Share numbers for the Equal and Graduated buttons. Both come from
    Standard, so the browser is not the one deciding what 'graduated' means."""
    n = max(int(payload.get("count") or 0), 0)
    which = str(payload.get("preset") or "equal")
    shares = graduated_shares(n) if which == "graduated" else equal_shares(n)
    return {"ok": True, "preset": which, "shares": shares}


def drawer_divider(payload):
    """Where a dragged join between two faces actually lands.

    The browser projects the pointer onto the pair's span, exactly as a plan drag
    projects onto a wall track, and posts the millimetre it reached. The two
    heights come back from drawers.split_pair; the rest of the stack is untouched.
    """
    top, bottom = split_pair(int(payload["top"]), int(payload["bottom"]),
                             int(payload["at"]),
                             int(payload.get("top_box") or 0),
                             int(payload.get("bottom_box") or 0))
    return {"ok": True, "top": top, "bottom": bottom}


def what_if(payload):
    """Which cut-list lines a change to one cabinet would take away.

    Asked before a tickbox is turned off, so nothing leaves the order without
    being named. It answers in designations and never proposes a new one: a
    designation belongs to its panel for good, so a change either leaves a panel
    alone or removes it — it never renames or reuses one.
    """
    job = _job(payload)
    number = int(payload["cabinet"])
    before = {}
    for p in generate_job(job):
        if p.cabinet == number:
            before.setdefault(p.label, p)

    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        return {"ok": False, "error": f"no cabinet {number}"}
    for k, v in (payload.get("set") or {}).items():
        # fields only: the resolved properties are read-only by design
        if any(f.name == k for f in dc_fields(cab)):
            setattr(cab, k, v)

    after = {p.label for p in generate_job(job) if p.cabinet == number}
    gone = [before[lab] for lab in before if lab not in after]
    return {"ok": True,
            "removed": [{"label": p.label, "role": p.role, "material": p.material,
                         "length": p.length, "width": p.width, "qty": p.qty}
                        for p in gone],
            "kept": sorted(after)}


def export(payload):
    """Plazaboard CSVs and the sheet layouts. Criticals block it — that is the point."""
    job = _job(payload)
    panels = generate_job(job)
    issues = validate(job, panels)
    if blocking(issues):
        crit = [asdict(i) for i in issues if i.level == "critical"]
        return {"ok": False,
                "error": f"Export blocked by {len(crit)} critical issue(s).",
                "issues": crit}

    job.name = _safe_name(job.name)          # it names files; it must not name paths
    outdir = os.path.join(OUT_DIR, job.name)
    written = write_csvs(job, panels, outdir)
    with NEST_LOCK:
        nested = N.nest_job(N.nestable(panels, job.std), job.std)
        for mat, sheets in nested.items():
            path = os.path.join(outdir, f"nest_{mat}.svg")
            N.write_svg(sheets, path, title=mat)
            written.append(path)

    drawings = [(f"{job.name}_elevation.svg", elevation_svg(job))]
    if job.room is not None:
        # one face-on drawing per wall: the sheet that goes to site with the order
        drawings += [(f"{job.name}_elevation_{_safe_name(w.id)}.svg",
                      wall_elevation_svg(job, w.id)) for w in job.room.walls]
    for name, svg in drawings:
        path = os.path.join(outdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        written.append(path)
    return {"ok": True, "dir": outdir, "files": [os.path.basename(p) for p in written]}


def job_list(payload):
    os.makedirs(JOBS_DIR, exist_ok=True)
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(JOBS_DIR, "*.json")))
    return {"ok": True, "jobs": names}


def job_save(payload):
    job = _job(payload)
    path = _job_path(payload.get("path") or job.name)
    os.makedirs(JOBS_DIR, exist_ok=True)
    save(job, path)
    return {"ok": True, "path": os.path.basename(path)}


def job_load(payload):
    path = _job_path(payload.get("path"))
    if not os.path.exists(path):
        return {"ok": False, "error": f"no job file {os.path.basename(path)}"}
    return {"ok": True, "job": job_to_dict(load(path))}


def job_fixture(payload):
    """The October 2025 wardrobe, as JSON. The regression fixture, openable in the UI."""
    from jobs.wardrobe_oct2025 import JOB
    return {"ok": True, "job": job_to_dict(JOB)}


def job_next_number(payload):
    return {"ok": True, "number": next_number(_job(payload))}


def plan(payload):
    """The plan view. Separate from /api/compute so flipping a layer costs a
    redraw and not a whole re-nest."""
    job = _job(payload)
    keep = lambda v: tuple(x for x in (v or ()) if x in LAYERS)   # noqa: E731
    show = keep(payload.get("show")) or LAYERS
    return {"ok": True, "svg": plan_svg(job, show=show, ghost=keep(payload.get("ghost")))}


def elevation(payload):
    """One wall face on, or the whole job side by side when no wall is named.

    Separate from /api/compute for the same reason as /api/plan: switching which
    wall you are looking at should cost a redraw, not a re-nest.
    """
    job = _job(payload)
    wall = payload.get("wall")
    svg = wall_elevation_svg(job, str(wall)) if wall else elevation_svg(job)
    return {"ok": True, "svg": svg}


def _safe_name(name) -> str:
    """A job or wall name fit to go into a file name inside out/.

    Both come from the job file, and a name like '../x' must not be able to
    write outside the export folder.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", str(name or "")).strip(".")
    return cleaned or "untitled"


def drag(payload):
    """Everything a drag needs, worked out once when it starts.

    The browser projects the pointer onto a wall track and picks the nearest of
    these snap points. It invents no position of its own, and on drop the whole
    job is recomputed server-side, so what ends up on the cut list is the
    engine's answer and not the interface's.
    """
    job = _job(payload)
    number = int(payload["cabinet"])
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None or job.room is None:
        return {"ok": False, "error": "no such cabinet, or the job has no room"}
    here = placement_for(job, number)
    return {
        "ok": True,
        "cabinet": number,
        "width": geometry(cab, job.std).width,      # its real extent, off the panels
        "layer": layer_of(cab, here),
        "tolerance": job.std.snap_tolerance,
        "walls": {w.id: {"length": w.length,
                         "max_x": max(w.length - cab.width, 0),
                         "snaps": snap_points(job, number, w.id, job.std)}
                  for w in job.room.walls},
    }


def room_extend(payload):
    """Add a wall at either end of the room's wall sequence — how a straight run
    becomes an L or a U. The length is a starting figure to be measured, like the
    pre-filled room's walls."""
    rm = room_from_dict(payload.get("room") or {})
    add_wall(rm, str(payload.get("at") or "end"), int(payload.get("length") or 3000))
    return {"ok": True, "room": room_to_dict(rm)}


def room_new(payload):
    """A fresh square room to start measuring from. The browser does not invent
    wall lists any more than it invents panel sizes."""
    return {"ok": True, "room": room_to_dict(rectangular(
        int(payload.get("length") or 4000),
        int(payload.get("width") or 3000),
        name=str(payload.get("name") or "room")))}


ROUTES = {
    "/api/defaults": defaults,
    "/api/compute": compute,
    "/api/drawers": drawer_stack,
    "/api/drawer-solve": drawer_solve,
    "/api/drawer-preset": drawer_preset,
    "/api/drawer-divider": drawer_divider,
    "/api/what-if": what_if,
    "/api/export": export,
    "/api/jobs": job_list,
    "/api/save": job_save,
    "/api/load": job_load,
    "/api/fixture": job_fixture,
    "/api/next-number": job_next_number,
    "/api/room-new": room_new,
    "/api/plan": plan,
    "/api/drag": drag,
    "/api/elevation": elevation,
    "/api/room-extend": room_extend,
}


# --- server ----------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "CupboardApp"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(ROOT, "app", "index.html"), encoding="utf-8") as fh:
                    return self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError as exc:
                return self._send(500, f"cannot read index.html: {exc}", "text/plain")
        if path in ROUTES:
            return self._dispatch(path, {})
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path not in ROUTES:
            return self._send(404, "not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, TypeError) as exc:
            return self._json(400, {"ok": False, "error": f"bad request body: {exc}"})
        self._dispatch(path, payload)

    def _dispatch(self, path, payload):
        try:
            self._json(200, ROUTES[path](payload))
        except Exception as exc:
            self._json(200, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})
