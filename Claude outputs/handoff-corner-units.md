# Corner-unit reconciliation — handoff for "UI build" session

Written by a Cowork session after comparing the two states directly (real diffs, not guesses). Nothing on disk has been changed or deleted.

## Background
Two Claude Code threads worked on this folder:
- **"CupboardApp corner units completion"** — did the 14 Sept corner-unit work, stopped mid-work (usage limit).
- **"UI build"** (this thread) — continued on 15 Sept, hit a session limit while it said "Edited 9 files +395/-78," and *also* showed "Can't reach your computer" right at that moment.

OneDrive preserved the 14 Sept file state under `*-DESKTOP-RL1ODQO.py/.html/.md` names (e.g. `cabinetgen/room-DESKTOP-RL1ODQO.py`) alongside the current plain-named files.

## What's confirmed identical / working in both
- Parametric corner units: `corner_style`, `arm_a`, `arm_b`, `face_a`, `face_b` on `Cabinet`, no angle field, angle always derived.
- `docs/ROOM-LAYOUT-SPEC.md` items 11-15 (spec) match the current implementation.
- `tools/regen_check.py` benchmark on current files: **272 MEL / 59 DECOR / 30 BACK, 92 pot holes, 18/9/6 boards, R28,363.50** — exact match, same as before this work started. One pre-existing unrelated critical (panel 1808) present in both, untouched.
- `overlaps()` in current `room.py` checks every cabinet pair in world coordinates across all walls — confirmed by reading the function body.

## The one real discrepancy — please resolve this first
The 14 Sept `cabinetgen/room-DESKTOP-RL1ODQO.py` has:
- `CabinetGeometry.faces` and `.sides` fields
- `@property face_lengths` and `@property mitre_deg` (the actual mitre angle in degrees, and each front face's length)
- `app/api-DESKTOP-RL1ODQO.py` sends `mitre_deg`, `face_lengths`, and `doors` in the geometry API response

The current `cabinetgen/room.py` **does not have these** — `CabinetGeometry` was simplified (no `faces`/`sides` fields, no `mitre_deg`/`face_lengths` properties), and `app/api.py` only sends `footprint`.

This session's own summary (before hitting the limit) said it left "the mitre angle and face lengths come out as read-only outputs" — which doesn't match what's currently on disk.

Neither version's `app/index.html` actually displays `mitre_deg` or `face_lengths` anywhere, and neither version of `CLAUDE.md` documents them as a feature — so this may just be an intentional simplification made during your own refactor into the generic `corner_outline(style, arm_a, arm_b, face_a, face_b)` function. But given the "can't reach your computer" warning at the exact moment you hit the session limit, **please verify your last save actually completed** rather than assuming it did.

## What to actually do
1. Check whether `mitre_deg`/`face_lengths` were dropped on purpose (as part of simplifying `corner_outline`) or whether that edit just never made it to disk. You'll know from your own reasoning at the time — we can't tell from the diff alone.
2. If they were meant to stay: re-add them to `CabinetGeometry` and `api.py`.
3. If dropping them was correct: no action needed, just confirm it here.
4. Re-run `tools/regen_check.py` to confirm the benchmark above still holds.
5. Do **not** delete the `-DESKTOP-RL1ODQO` files or touch git yet — report back first.
