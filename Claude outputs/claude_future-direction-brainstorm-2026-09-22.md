# CupboardApp — Future Direction Brainstorm (22 Sept 2026)

**Status: planning/brainstorming only — no execution taken as a result of
this conversation.**

## Confirmed: this is a parametric model
Every panel size, hole, and edge is derived from rules and inputs rather
than drawn by hand. That's the correct foundation for everything below.

## Cross-platform target
Currently Windows-only (pywebview desktop shell wrapping the Python
engine). Longer-term goal: also ship as real App Store apps so the
designs can be done on iPad and Android, not just Windows. Not wanted
now — Windows stays the priority; this is direction-setting for later.

### Recommended path: split the engine from the interface
Rather than rewriting the app for each platform, separate it into three
layers:

1. **Engine (the brain)** — the existing Python: rules, geometry,
   nesting, cut list, validation. Runs as a service instead of being
   wired directly into a desktop window.
2. **API (the menu)** — a defined set of requests the interface can make
   ("compute this job," "drag this cabinet," "save this file") and what
   comes back. This is close to what already exists between the browser
   UI and the Python backend today, formalised so it doesn't assume a
   desktop window specifically.
3. **Front ends (one per platform)** — Windows keeps roughly what it has;
   iPad and Android get their own apps that just send requests to the
   same API and draw the results.

Benefit: the hard logic (rules, geometry, nesting) is written once and
reused everywhere.

### Hosting options for the engine, once split out
- **Bundled per device** — engine ships inside each platform's app,
  runs fully locally/offline. Simple, private, but the engine has to be
  maintained and shipped separately per platform.
- **Central server** — engine runs on one machine (cloud or local
  network); every device sends requests to it. Standard web-app model;
  one place to update the logic, needs connectivity. Given the engine's
  per-job workload isn't heavy, a small server would likely be enough.

No decision made — this is the shape of the choice, not a ruling.

## Realistic rendering + appliance models
Wants more realistic renders later (not now), and wants to create
appliance models to place in designs. This is a 3D rendering layer, and
it reinforces the case for the client-server split above, since a proper
renderer wants to sit close to whichever interface is drawing the
screen — it would plug in at the front-end layer per platform.

## New module idea: exploded-view build instructions
Idea raised: a further module that, per cabinet, produces an
exploded-view build instruction — so someone who isn't the designer
could take the plan, buy the boards, and build the cabinet from it.
Not divergent from the current build — panels already carry position
and identity data, so generating an assembly sequence per cabinet is a
reasonable module to add later.

## Open question raised: panel-level detail in Plan/Wall views
Currently only certain details show in the Wall and Plan views. Question
raised, not yet decided: should every panel — supports, tops, shelves,
doors, everything — be rendered as a visible detail in those views, or
does that add rendering weight without adding value? Needs weighing
before building it either way.
