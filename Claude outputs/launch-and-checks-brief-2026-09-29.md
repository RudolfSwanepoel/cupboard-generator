# Brief: one window, maximised, and a complete check (29 September 2026)

Agreed with Rudolf in Cowork. Two small jobs, one session, run **Local**, because
the launcher has to be tested on Windows. Nothing in `cabinetgen/` changes. The
benchmark must be unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50): quote it in the report.

## Part A: `Check It Still Works.bat` runs every check

**The fault.** The batch file is a hand-kept list and has drifted. It does not
run `check_room`, `check_fillers`, `check_plinth`, `check_fronts` or
`check_export`, so a clean run there proves less than it looks. CLAUDE.md's
"Check before you commit" list has drifted the other way: it leaves out
`check_boards`.

**The fix: one runner that finds the checks itself, so the list cannot drift again.**

1. New `tools/check_all.py`. It runs `tools/regen_check.py` first, then every
   `tools/check_*.py` in name order, each in its own process with the same
   Python. It captures each script's exit code and ends with a summary: one line
   per script (PASS / FAIL) and a final count. It exits non-zero if any failed.
   No hand-kept list anywhere.
2. Not run by it:
   - the `ui_check_*.py` Playwright scripts, which need the app running;
   - `snapshot.py --compare`, which needs the per-machine `baseline.json`. That
     file is known to be stale and is deliberately not regenerated.

   The summary says both are not included and why, in one line each.
3. **Confirm that every `check_*.py` exits non-zero when a check fails.** A
   script that prints FAIL and exits 0 would read as PASS in the summary. Fix
   any that do. That changes only the exit code, never what is checked. List in
   the report which scripts needed it.
4. `Check It Still Works.bat` calls `python tools\check_all.py`, keeps its title,
   the `cd /d "%~dp0"` and the closing `pause`, and keeps the "22 cabinets
   reproduce exactly / 0 wrong" reminder (that line needs the Wardrobes xlsx,
   which is only on the laptops). The last thing on screen is the summary, with
   the reminder under it.
5. In CLAUDE.md, the "Check before you commit" block becomes
   `python tools/check_all.py` plus the optional Playwright scripts and the
   snapshot compare, as now.

## Part B: the app opens as one window, maximised

**The fault.** `Start Cupboard App.bat` runs `python run_app.py` in a console,
so two windows open: the console (which holds the web server; closing it kills
the app) and the pywebview window.

1. **Maximised at start.** In `run_app.py`, pass `maximized=True` to
   `webview.create_window`, keeping `width=1360, height=900` as the restore size.
   Use maximised, not full screen: the title bar and taskbar stay. Check that
   pywebview 6.2.1 on WebView2 honours it. If it does not, say so and use the
   documented way to maximise after the window is shown.
2. **No console: launch with `pythonw.exe`.** Under pythonw, `sys.stdout` and
   `sys.stderr` are `None`. `http.server`'s `log_message` writes to
   `sys.stderr`, so every request would raise in the handler thread. So, at the
   top of `main()`: when either stream is `None`, point both at a log file,
   **`output/app.log`**, overwritten at each start (keeping only the last run's
   log is enough), line-buffered. Under `python.exe` nothing changes: output
   still goes to the console.
3. **A failure to start must still be seen.** With no console, an exception at
   start-up (port in use, pywebview missing, an import error) would vanish.
   Catch it in `main()`, write the traceback to the log, and when running without
   a console show a Windows message box (`ctypes.windll.user32.MessageBoxW`)
   saying it did not start and where the log is. **Port 8765 already taken**
   almost always means the app is already open. The message box says exactly
   that ("The Cupboard App is already running, or port 8765 is in use"). Do not
   start a second server on another port.
4. **The launcher: a desktop shortcut.** New `Make Desktop Shortcut.bat` (run
   once per laptop, since pythonw's path differs between the two machines). It
   creates `Cupboard App.lnk` on the desktop. The shortcut's target is that
   machine's `pythonw.exe` (found with `where pythonw`, or beside `python`), its
   argument is `run_app.py`, its start-in folder is the repo, and it has an icon.
   Use PowerShell's `WScript.Shell` `CreateShortcut`, called from the .bat. No
   new Python package. For the icon, use a small `.ico` committed in `app/` if
   one is simple to make; otherwise a stock Windows icon, and say which. The
   shortcut can be pinned to the taskbar by hand.
5. **Keep `Start Cupboard App.bat` as it is**: the console launch is the one to
   use when something breaks, because the error is on screen. It gains the
   maximised window from step 1 and nothing else. Add one `echo` line saying
   that normal use is the desktop shortcut.
6. The browser fallback (`pywebview` not installed) and `--no-window` are
   unchanged. `--no-window` is what the Playwright scripts use.

**Check (new, `tools/check_launch.py`, so `check_all` picks it up):**
- with `sys.stdout` / `sys.stderr` set to `None`, the redirection sends them to a
  log file and a request to the running server does not raise;
- the port-in-use path is reached and reports "already running" (bind the port
  first, then start);
- `run_app.py`'s window call asks for maximised (read the arguments;
  don't open a window).

**Tested by hand in the report:** double-click the shortcut → one window,
maximised, no console; start it again while it is open → the "already running"
message box; `Start Cupboard App.bat` still shows the console and the app.

## Housekeeping

`.git/index.lock.stale-from-claude` is an empty lock file a Cowork session left
behind and moved aside so it would not block git. Delete it.

## Report and commit

Update CLAUDE.md: the Status entry, the check list (Part A 5), and the
Layout entries for `check_all.py`, `check_launch.py`, `app.log` and the
shortcut. Give Rudolf the exact commit message to paste into Finish Session.bat.
