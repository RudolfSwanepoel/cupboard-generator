"""Ways to size a stack of drawer faces.

A stack fills one opening. The opening is whatever the door leaves over:

    opening = H - door_height_gap - door_height - stack_gap     (door above drawers)
    opening = H - door_height_gap                               (drawers only)

Faces are separated by stack_gap. Every helper here returns integers that sum,
with the gaps, to exactly the opening — so front_stack_check always passes.

Box height is a separate choice and is never derived. Real jobs have used
90, 116, 150 and 200 mm sides under faces of 120, 183, 195, 218, 296 and 787,
with no fixed relationship — it depends on the runner and what goes in the drawer.
"""
from typing import Dict, List, Optional, Sequence

from .model import Drawer
from .standard import STANDARD


def opening_for(height: int, door_height: int = 0, std=STANDARD) -> int:
    """The vertical space a drawer stack has to fill."""
    o = height - std.door_height_gap
    if door_height:
        o -= door_height + std.stack_gap
    return o


def _distribute(opening: int, weights: Sequence[float], gap: int) -> List[int]:
    """Split `opening` in the given proportions, absorbing rounding at the bottom."""
    n = len(weights)
    usable = opening - gap * (n - 1)
    if usable <= 0:
        raise ValueError(f"opening {opening} is too small for {n} faces")
    total = float(sum(weights))
    out = [int(usable * w / total) for w in weights]
    out[-1] += usable - sum(out)
    return out


def equal_faces(opening: int, n: int, gap: int = None, std=STANDARD) -> List[int]:
    """n faces of the same height. The bottom one carries any remainder."""
    return _distribute(opening, [1] * n, std.stack_gap if gap is None else gap)


def graduated_faces(opening: int, weights: Sequence[float], gap: int = None,
                    std=STANDARD) -> List[int]:
    """Faces in proportion, top to bottom.

    Shallow at the top, deep at the bottom is the usual shape:

        graduated_faces(787, [1, 1.5, 1.5, 2.4])  ->  [122, 183, 183, 293]
    """
    return _distribute(opening, weights, std.stack_gap if gap is None else gap)


def faces_with_fixed(opening: int, n: int, fixed: Dict[int, int], gap: int = None,
                     std=STANDARD) -> List[int]:
    """Pin some faces by index (0 = top), split what is left equally.

        faces_with_fixed(787, 4, {3: 300})   ->  [160, 160, 161, 300]
    """
    g = std.stack_gap if gap is None else gap
    free = [i for i in range(n) if i not in fixed]
    if not free:
        got = sum(fixed.values()) + g * (n - 1)
        if got != opening:
            raise ValueError(f"pinned faces total {got}, opening is {opening}")
        return [fixed[i] for i in range(n)]
    remainder = opening - sum(fixed.values()) - g * len(fixed)
    shares = _distribute(remainder, [1] * len(free), g)
    out = [0] * n
    for i, h in fixed.items():
        out[i] = h
    for i, h in zip(free, shares):
        out[i] = h
    return out


# --- one row per face: Share or Fixed ----------------------------------------
#
# The way a stack is authored now. Each row is either 'fixed' — the height as
# typed — or 'share', a slice of whatever the fixed rows leave, in proportion to
# its share number. Gaps come from Standard and are never typed per drawer.
#
# What is ordered is still a list of heights: `divide` produces them and the
# engine reads nothing else. The modes and shares ride along on the Drawer so a
# stack can be picked up and re-divided later instead of retyped.


def _gap(gap, std) -> int:
    return std.stack_gap if gap is None else gap


def remainder(opening: int, modes: Sequence[str], values: Sequence[float],
              gap: int = None, std=STANDARD) -> int:
    """What the share rows have left to divide, once the fixed rows and the gaps
    are taken out. Negative means the fixed rows over-run the opening.

        remainder(787, ["fixed", "share", "share"], [300, 1, 1])   ->   483
        remainder(790, ["fixed", "fixed"], [400, 400])   ->   -12
    """
    g = _gap(gap, std)
    fixed = sum(int(v) for m, v in zip(modes, values) if m == "fixed")
    return opening - fixed - g * max(len(modes) - 1, 0)


def divide(opening: int, modes: Sequence[str], values: Sequence[float],
           gap: int = None, std=STANDARD) -> List[int]:
    """Face heights, top to bottom, for a stack described row by row.

    Fixed rows take their millimetres as typed. Whatever is left after them and
    the gaps is split among the share rows in proportion to their share numbers,
    the bottom-most share row carrying the rounding.

        divide(787, ["share", "share", "share", "share"], [1, 1, 1, 1])   ->   [195, 195, 195, 196]
        divide(787, ["fixed", "share", "share"], [300, 1, 1])   ->   [300, 241, 242]
        divide(787, ["fixed", "fixed"], [400, 400])   ->   [400, 400]

    A fixed-only stack is honoured exactly as given even when it does not fill
    the opening — the shortfall is reported by the validator, never silently
    corrected, the same discipline `stack`'s exact heights have always had. When
    the fixed rows over-run, the share rows come back at zero, which the
    validator turns into a critical rather than inventing a negative face.
    """
    out = [int(v) for v in values]
    share_at = [i for i, m in enumerate(modes) if m != "fixed"]
    if not share_at:
        return out
    left = remainder(opening, modes, values, gap, std)
    if left <= 0:
        for i in share_at:
            out[i] = 0
        return out
    weights = [max(float(values[i]), 0.0) for i in share_at]
    if not sum(weights):
        weights = [1.0] * len(weights)
    total = sum(weights)
    got = [int(left * w / total) for w in weights]
    got[-1] += left - sum(got)
    for i, h in zip(share_at, got):
        out[i] = h
    return out


def equal_shares(n: int) -> List[float]:
    """Every face the same.

        equal_shares(4)   ->   [1.0, 1.0, 1.0, 1.0]
    """
    return [1.0] * n


def graduated_shares(n: int, std=STANDARD) -> List[float]:
    """Smallest face at the top, each one a step more than the one above.

        graduated_shares(4)   ->   [1.0, 1.5, 2.0, 2.5]
    """
    return [round(1.0 + i * std.graduated_step, 3) for i in range(n)]


def split_pair(top_h: int, bottom_h: int, at: int, top_box: int = 0,
               bottom_box: int = 0, gap: int = None, std=STANDARD) -> tuple:
    """Move the join between two faces, leaving the rest of the stack alone.

    The pair's own span — the two faces and the gap between them — does not
    change, so whatever the top face gains the bottom one loses. `at` is how far
    down that span the join was dragged to.

    Each face is held back far enough to still clear its own box side, which is
    a rule that was already there rather than a new number: a box the same height
    as its face shows above the drawer front, and the validator calls it a
    critical. With no box heights given the join may go anywhere in the span.

        split_pair(200, 300, 250)   ->   (250, 250)
        split_pair(200, 300, 10, 90, 116)   ->   (91, 409)
    """
    g = _gap(gap, std)
    span = int(top_h) + g + int(bottom_h)
    lo, hi = top_box + 1, span - g - (bottom_box + 1)
    if lo > hi:                      # the pair cannot house both boxes; split it evenly
        lo, hi = 0, span - g
    top = max(lo, min(int(at), hi))
    return top, span - g - top


def make_drawers(faces: Sequence[int], boxes, base: str = "board") -> List[Drawer]:
    """Pair face heights with box heights.

    `boxes` is either one height for the whole stack, or one per face.

        make_drawers([120, 183, 183, 296], [90, 116, 116, 200])
        make_drawers(equal_faces(1090, 5), 150)
    """
    if isinstance(boxes, int):
        boxes = [boxes] * len(faces)
    if len(boxes) != len(faces):
        raise ValueError(f"{len(faces)} faces but {len(boxes)} box heights")
    return [Drawer(f, b, base) for f, b in zip(faces, boxes)]


def stack(height: int, spec, boxes, door_height: int = 0, base: str = "board",
          std=STANDARD) -> List[Drawer]:
    """One call from cabinet height to a list of Drawers.

    `spec` is one of:
      int                that many equal faces
      list of weights    proportions, any value under 50 marks it as weights
      list of heights    exact face heights, used as given

        stack(2400, 5, 150, door_height=1297)                  five equal
        stack(790, [1, 1.5, 1.5, 2.4], [90, 116, 116, 200])    graduated
        stack(790, [120, 183, 183, 296], [90, 116, 116, 200])  exactly these

    Exact heights are honoured even if they do not fill the opening — validation
    reports the shortfall rather than silently adjusting your numbers. That is
    how cabinet 30's 75 mm gap gets caught instead of quietly corrected.
    """
    opening = opening_for(height, door_height, std)
    if isinstance(spec, int):
        faces = equal_faces(opening, spec, std=std)
    elif all(v >= 50 for v in spec):
        faces = [int(v) for v in spec]
    else:
        faces = graduated_faces(opening, spec, std=std)
    return make_drawers(faces, boxes, base)
