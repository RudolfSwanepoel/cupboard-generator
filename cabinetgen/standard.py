"""Construction standard — every settled constant lives here and nowhere else.

Agreed with Rudolf, September 2026. Changing a value here changes every job.
If a value needs to differ for one cabinet, it belongs on the Cabinet, not here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Standard:
    # ---- board -------------------------------------------------------------
    board_t: int = 16           # carcass / door board thickness
    back_t: int = 3             # backing board thickness
    sheet_l: int = 2750         # stock sheet, long side
    sheet_w: int = 1830         # stock sheet, short side
    kerf: int = 2               # saw blade

    # ---- grooves -----------------------------------------------------------
    groove_depth: int = 8       # how deep the cutter goes
    groove_engage: int = 6      # how far the board enters (2 mm clearance in the slot)
    back_cavity: int = 16       # clear space behind the back for a rail / stiffener / filler

    # ---- shelves -----------------------------------------------------------
    shelf_gap_adjustable: int = 4   # clearance in front of the back, adjustable shelf
    shelf_gap_fixed: int = 1        # clearance in front of the back, fixed shelf

    # ---- doors and fronts --------------------------------------------------
    door_height_gap: int = 3    # door height = H - this
    door_single_gap: int = 3    # single door width = W - this
    door_pair_gap: int = 6      # pair width = (W - this) / 2
    stack_gap: int = 2          # between stacked fronts in one opening

    # ---- drawers -----------------------------------------------------------
    runner_lengths: tuple = (350, 450, 500)
    runner_clearance: int = 40  # minimum space behind the runner
    drawer_front_deduct: int = 59   # front/back length = internal width - this
    drawer_base_offset: int = 16    # base groove sits this far up from the bottom edge

    # ---- exposed panels ----------------------------------------------------
    exposed_extra: int = 16     # exposed side depth = carcass depth + this (finishes flush with the door)

    # ---- hinges ------------------------------------------------------------
    hinge_threshold: int = 1600
    hinge_below: int = 2
    hinge_above: int = 4

    # ---- edging ------------------------------------------------------------
    edge_trim: int = 70         # Plazaboard's allowance per banded edge, mm

    # ---- room --------------------------------------------------------------
    closure_warn: int = 5       # mm the wall chain may miss closing by before it is queried
    closure_block: int = 20     # above this the measurements contradict each other
    corner_disagree: int = 5    # mm the two measurements of one corner may differ by

    # ---- fillers and scribes ----------------------------------------------
    # Ruled by Rudolf, 14 September 2026.
    scribe_allowance: int = 15  # oversize on a filler, to be trimmed on site
    taper_threshold: int = 6    # above this taper a parallel filler will not sit; scribe it
    filler_min: int = 50        # below this, grow a cabinet instead of fitting a filler
    filler_max: int = 150       # above this, a cabinet or a blind corner is the better answer

    # ---- legs and plinth ---------------------------------------------------
    # Ruled by Rudolf, 14 September 2026, and corrected the same day. Every carcass
    # that stands on the floor stands on adjustable legs — kitchen or wardrobe,
    # always. The plinth board that clips on across the legs is a separate choice,
    # made per run by the operator. So the height lift belongs to the legs, and the
    # board is only cut to cover it.
    leg_height: int = 100       # floor to the underside of every standing carcass;
                                # the spec's "plinth height", and the board's width
    plinth_setback: int = 50    # how far the plinth board sits behind the door face
    leg_min: int = 98           # adjustable leg range; leg_height must fall inside it
    leg_max: int = 122
    # Where the rear legs stand, in from the back face. Ruled 14 September 2026. It
    # is the pivot the tip-up check turns a carcass about once the rear feet touch
    # down, and it moves that result only within about a 12 mm band of ceiling
    # height — nothing else is built around it.
    leg_setback: int = 50

    # ---- placement ---------------------------------------------------------
    snap_tolerance: int = 20    # how near a snap target a drag has to get, in mm
    door_open_deg: int = 90     # the angle a swing is checked at; drawing convention,
                                # not a construction dimension — raise it if a real
                                # job needs 110 and the clash check follows

    # Drawn only. Ruled 14 September 2026 with low confidence: Plazaboard's hardware
    # spec governs where pot holes are really drilled, so nothing that orders,
    # drills or validates may read this — it positions marks on a drawing, no more.
    hinge_inset_drawn: int = 100

    # Panel codes 10 (Plinth) and 11 (Filler) follow the 09 precedent but
    # Plazaboard has not signed them off yet. Flip this when they do, and the
    # validator stops warning about it.
    codes_confirmed: bool = False

    # ==== derived ===========================================================

    def internal_width(self, w: int) -> int:
        return w - 2 * self.board_t

    def back_face_from_front(self, d: int) -> int:
        """Distance from the cabinet front to the front face of the backing board."""
        return d - self.back_cavity - self.back_t

    def shelf_depth(self, d: int, fixed: bool = False) -> int:
        gap = self.shelf_gap_fixed if fixed else self.shelf_gap_adjustable
        return self.back_face_from_front(d) - gap

    def back_size(self, w: int, h: int, style: str) -> tuple:
        """(length, width) of the backing board.

        'four'  - grooved into sides, top and bottom
        'three' - grooved into sides and top; runs down past the bottom panel
        """
        width = w - 2 * self.board_t + 2 * self.groove_engage          # W - 20
        if style == "four":
            height = h - 2 * self.board_t + 2 * self.groove_engage     # H - 20
        elif style == "three":
            height = h - self.board_t + self.groove_engage             # H - 10
        else:
            raise ValueError(f"unknown back style {style!r}")
        return width, height

    def door_width(self, w: int, n: int) -> int:
        if n == 1:
            return w - self.door_single_gap
        return (w - self.door_pair_gap) // n

    def hinges(self, door_length: int) -> int:
        return self.hinge_below if door_length <= self.hinge_threshold else self.hinge_above

    def hinge_positions(self, door_length: int) -> list:
        """Where the hinges are *drawn* along a door, in mm from its bottom edge.

        The outer two sit hinge_inset_drawn in from each end and any between them
        split the rest evenly. For drawings only: ruled with low confidence, and
        the pot holes are drilled to Plazaboard's hardware spec, not to this.
        """
        n = self.hinges(door_length)
        span = door_length - 2 * self.hinge_inset_drawn
        return [round(self.hinge_inset_drawn + span * i / (n - 1)) for i in range(n)]

    def pick_runner(self, depth: int):
        """Longest runner that leaves runner_clearance behind it. None if nothing fits."""
        usable = depth - self.runner_clearance
        fits = [r for r in self.runner_lengths if r <= usable]
        return max(fits) if fits else None

    def drawer_front_length(self, w: int) -> int:
        return self.internal_width(w) - self.drawer_front_deduct

    def drawer_base(self, front_len: int, runner: int, material: str) -> tuple:
        """(length, width) of the drawer base."""
        if material == "board":
            # grooved into all four panels
            return runner - 2 * self.board_t + 2 * self.groove_engage, front_len + 2 * self.groove_engage
        if material == "melamine":
            # housed between all four panels
            return runner - 2 * self.board_t, front_len
        raise ValueError(f"unknown drawer base material {material!r}")

    def edging_m(self, length: int, width: int, edge_l: int, edge_w: int, qty: int) -> float:
        """Plazaboard's own formula. Exact on all 166 edged rows of the Oct 2025 job."""
        run = edge_l * length + edge_w * width
        trim = self.edge_trim * (edge_l + edge_w)
        return (run + trim) * qty / 1000.0


STANDARD = Standard()
