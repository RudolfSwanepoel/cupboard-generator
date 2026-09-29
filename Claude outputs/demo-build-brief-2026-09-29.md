# Demo build brief — 29 September 2026

**Goal:** build a Windows demo of CupboardApp that Rudolf can send to a friend
as one zip. The friend unzips it and double-clicks an .exe. They need no Python
and get no readable source. The demo stops working 60 days after the build date.

Run this in a **Local** session on Rudolf's Windows laptop. The cloud machine
is Linux and cannot build a Windows .exe.

## Rulings (Rudolf, 29 Sept) — don't reopen these

1. **Name:** "Demo". Window title: `Cupboard App — Demo (until 28 Nov 2026)`,
   with the date taken from the build.
2. **Expiry:** a fixed date, build date + 60 days, baked into the build.
3. **Nothing is held back.** Every feature and every data file the app uses
   ships: `boards.json` with prices, `hardware.json`, all of `jobs/` (Test.json
   and the Oct 2025 benchmark), `Pictures/`, `app/` including `vendor/`, and the icon.
   The demo is the full app with an end date and nothing else changed.
4. **Tool:** Nuitka, not PyInstaller. It compiles the Python to machine code, and
   hiding the code is the point of this exercise.

## What to build

### 1. Demo mode (small, inert outside a build)

- Add `app/demo.py`. The build writes one generated file next to it,
  `app/_demo_build.py`, containing `DEMO = True` and `EXPIRES = "YYYY-MM-DD"`.
  That file is gitignored and never committed.
- If `_demo_build.py` is missing (a normal `python run_app.py` run), demo mode is
  off and **nothing** in the app behaves differently. `Check It Still Works.bat`
  must pass unchanged.
- In demo mode:
  - At startup, if today is after `EXPIRES`, show a message box: *"This demo of
    Cupboard App expired on <date>. Contact Rudolf for a new copy."* Then exit.
  - Check again on every API request, so leaving the app open past the date
    doesn't get around it. After the date, return an error the UI shows as the
    same message.
  - Clock roll-back guard: store the latest date seen in a small file under
    `output/` and refuse to run if the system date is more than 1 day before it.
    Keep this simple; it only needs to stop casual clock changes.
  - Window title as in ruling 1.
- Geometry, nesting, costing and export are not touched.

### 2. `Build Demo.bat` (repo root, one click)

In plain words, it must do this:
1. Install Nuitka if it's missing (`pip install nuitka`). Accept Nuitka's
   offer to download its C compiler automatically (`--assume-yes-for-downloads`).
2. Write `app/_demo_build.py` with today + 60 days.
3. Build with Nuitka in **standalone (folder) mode, not onefile**. Onefile unpacks
   to a temp folder on each run, and because `ROOT` comes from `__file__`, saved
   jobs, `output/` and new board pictures would be lost. The folder build keeps
   them beside the .exe.
   - Windows GUI app, no console window; icon `app/cupboard.ico`; exe name
     `Cupboard App Demo.exe`.
   - Include everything pywebview needs on Windows (WebView2 via pythonnet /
     clr_loader). Get it working and test it; don't assume the flags are right.
   - Include `jobs.wardrobe_oct2025`, which is imported by name, plus every
     data folder listed in ruling 3.
4. Delete `app/_demo_build.py` afterwards, so a normal run is not in demo mode.
5. Zip the result to `demo\Cupboard App Demo <build date>.zip` and add
   `READ ME FIRST.txt` inside (text below).
6. End with a plain summary: where the zip is, its size, and the expiry date.

Add `demo/` and the Nuitka build folders to `.gitignore`. Never commit an
.exe or a zip.

### 3. What must NOT be in the zip

Leave out: `tools/`, `docs/`, `CLAUDE.md`, `Claude outputs/`, `claude/`,
`Reference/`, `Sample Plaza cutlist and quote/`, `_to_delete/`, `snapshot-*.json`,
`baseline.json`, the .bat files, `.git`, and any `output/` or `out/` contents.
If the app turns out to read any of these while running, stop and ask. Don't
silently include or exclude it.

**No `.py` or `.pyc` files from this repo may be in the zip.** Check by listing
the zip and report the result. Third-party runtime pieces Nuitka keeps as
files are fine; name them in the report.

### 4. `READ ME FIRST.txt` (goes in the zip, exactly this)

```
Cupboard App — Demo
This demo works until <expiry date>.

1. Unzip this whole folder into Documents (not Program Files, and don't run it from inside the zip).
2. Open the folder and double-click "Cupboard App Demo.exe".
3. If Windows says "Windows protected your PC": click "More info", then "Run anyway".
   It only asks the first time.
4. Needs Windows 10 or 11.

Your jobs and exports are saved inside this folder, so keep it together.
```

## Tests (all required; report each)

1. `Check It Still Works.bat` passes with demo mode off, and the benchmark holds:
   272 / 59 / 30 panels, 92 pot holes, 18/9/6 boards, R28,363.50. Quote the figures.
2. Build with `Build Demo.bat`. Copy the zip to a new folder outside the repo
   (e.g. `%USERPROFILE%\Desktop\demo-test`), unzip it, and run the .exe from
   there, **with the repo's Python kept off the path if you can**, to prove it
   stands alone. Confirm that:
   - the window opens with the Demo title and date;
   - Test.json opens; the Cut list, Nesting, Validation, Room, 3D and Cabinets
     3D all work;
   - a saved job, an export and a new board picture all land in the unzipped
     folder, not the repo;
   - the Oct 2025 benchmark job loads.
3. Expiry: build a throwaway copy with `EXPIRES` set to yesterday (a switch on the
   bat, e.g. `Build Demo.bat --test-expired`) and confirm it refuses with the
   message. Then confirm the clock roll-back guard trips.
4. The zip listing shows no repo `.py`/`.pyc` files.
5. Delete the test folders afterwards.

## Finish

- Update CLAUDE.md: a short "Demo build" section (what `Build Demo.bat` does and
  how to extend the expiry, which is just a rebuild), and the Status section.
- Report in plain language. Rudolf is not a packaging expert, so no jargon
  without a one-line explanation.
- Give Rudolf the exact commit message to paste into Finish Session.bat.

If Nuitka's compiler download is blocked (the work laptop may block it), stop
and say so. Rudolf will run it on the home laptop instead. Don't switch to
PyInstaller without asking.
