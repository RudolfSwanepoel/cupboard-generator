"""Run every check: regen_check first, then every tools/check_*.py in name order.

    python tools/check_all.py

The list is found, not kept: a check_*.py added to tools/ is run the next time
this is, so the list cannot drift the way `Check It Still Works.bat`'s did (it
had stopped running check_room, check_fillers, check_plinth, check_fronts and
check_export). Each script runs in its own process with this same Python, its
output shown as it goes, and its exit code is its verdict — every check_*.py
exits non-zero when a check fails (checked 29 September 2026 by forcing the
first and the last check of each to fail).

regen_check is a report, not a pass/fail: it fails here only if it crashes, so
its benchmark lines are repeated in the summary to be read.
"""
import glob
import os
import re
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

NOT_INCLUDED = (
    "ui_check_*.py (Playwright) - they need the app running: see CLAUDE.md",
    "snapshot.py --compare baseline.json - baseline.json is per-machine and "
    "known to be stale, deliberately not regenerated",
)

# regen_check's lines worth reading again at the bottom (the benchmark).
BENCHMARK = re.compile(r"^\s*(MEL|BROOKHILL|DECOR|BACK)\s+\d+ panels|pot holes|"
                       r"estimated total|cabinets reproduce exactly|cut list not found|"
                       r"NOT NESTED")


def scripts():
    found = sorted(glob.glob(os.path.join(TOOLS, "check_*.py")))
    me = os.path.abspath(__file__)
    return [os.path.join(TOOLS, "regen_check.py")] + [f for f in found if os.path.abspath(f) != me]


def run(path):
    """Run one script, echoing its output; hand back (exit code, lines, seconds)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    t0 = time.perf_counter()
    proc = subprocess.Popen([sys.executable, path], cwd=ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = []
    for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        lines.append(line)
        print(line, flush=True)
    return proc.wait(), lines, time.perf_counter() - t0


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    results, bench = [], []
    for path in scripts():
        name = os.path.basename(path)
        print("\n" + "#" * 78 + f"\n# {name}\n" + "#" * 78, flush=True)
        code, lines, secs = run(path)
        results.append((name, code, secs))
        if name == "regen_check.py":
            bench = [ln.strip() for ln in lines if BENCHMARK.search(ln)]

    failed = [r for r in results if r[1] != 0]
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    if bench:
        print("the benchmark (from regen_check - read these):")
        for ln in bench:
            print(f"    {ln}")
        print()
    for name, code, secs in results:
        verdict = "PASS" if code == 0 else f"FAIL (exit {code})"
        print(f"  {verdict:<14} {name:<26} {secs:6.1f} s")
    print()
    for line in NOT_INCLUDED:
        print(f"  not included: {line}")
    print()
    print(f"{len(results) - len(failed)} of {len(results)} passed"
          + (f", {len(failed)} FAILED: " + ", ".join(r[0] for r in failed) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
