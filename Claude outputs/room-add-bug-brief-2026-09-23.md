# Bug brief — "Add a room" does nothing outside the 3D view

23 September 2026. Reproduced in Cowork against master 20e6d1e, headless
Chromium, real clicks. Not caused by the 3D work: the faulty line dates from
7daedb7 (17 September). The 3D view only made it visible, because it redraws
before the code that crashes.

## Symptom (Rudolf)

New project → Room tab → **Add a room**. The walls table appears, but the plan
stays "No room yet — add one below", and Placements, Gaps and Plinth do not
update. The 3D view shows the room.

## Cause

A new job — and any job file saved without a `placements` key
(`jobs/untitled.json`, `jobs/Test_Panels.json`) — has
`S.job.placements === undefined`. The **Add a room** handler sets
`S.job.room` and nothing else. Then:

```
TypeError: Cannot read properties of undefined (reading 'map')
    at renderPlaces   (index.html ~4571: S.job.placements.map)
    at renderTab      (~5088: renderRoom(); renderPlaces(); renderGaps(); renderPlinth(); renderPlan())
    at compute        (~644)
```

`renderPlaces` throws, so `renderGaps`, `renderPlinth` and `renderPlan` never
run — on every compute and every switch to the Room tab. `refreshScene` runs
earlier in `compute`, which is why 3D alone shows the room.

With `S.job.placements = []` set by hand, everything else checked works: add a
wall before/after, remove a wall, edit a length (focus kept), set the ceiling,
the plan draws, 3D and back, no page errors.

## Fix

1. Make `placements` always an array where a job enters the browser: New, Load,
   the fixture button, and **Add a room** (as **Remove room** already does with
   `S.job.placements = []`). One helper, not a guard at each use.
2. Also harden the unguarded uses (`S.job.placements.find/map/findIndex/push`,
   about 10 sites, e.g. ~3815, ~4339, ~4571-4678), because an old job file can
   still arrive without the key.
3. **Do not write `placements` to the job file when there is no room.** The
   room=None rule is that no `room` or `placements` key is written, and job
   files must still round-trip byte for byte. If the browser now always carries
   `[]`, check that saving a no-room job writes the file exactly as before
   (`store` may already drop it — confirm, do not assume).
4. One render failing must not stop the others. Consider wrapping each render in
   `renderTab` so an error is shown in its own card and in the console, rather
   than blanking the rest of the tab silently.

## Check before calling it fixed

- New → Room → Add a room: the plan, Walls, Placements, Gaps and Plinth all
  draw; no page errors.
- The same after loading `Test_Panels.json` and `jobs/untitled.json`.
- Add a cabinet to a new job with a room, place it from the Placements table,
  drag it in the plan and in 3D.
- Every job on disk round-trips byte for byte; the benchmark and all
  `check_*.py` pass; `snapshot.py --compare` shows no change.

## Seen while testing, worth a look (not confirmed as bugs)

- A closed 4-wall room with a wall added after D becomes 5 walls, reports
  "misses closing by 2500 mm", but the plan still looks like a closed
  rectangle with the E and A labels both on the top edge. The help text says a
  closed room shows the miss until it closes again, so check whether the plan
  should draw the gap.
