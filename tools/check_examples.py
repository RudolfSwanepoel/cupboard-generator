"""Verify every worked example in the docstrings actually evaluates to what it claims.

The convention is one example per line:

    some_call(args)   ->   [expected]

A wrong number in a comment is the same class of mistake this whole project
exists to stop, so it gets checked rather than trusted. Run it with the tests:

    python tools/check_examples.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cabinetgen.drawers as drawers        # noqa: E402
import cabinetgen.room as room              # noqa: E402
import cabinetgen.standard as standard      # noqa: E402

MODULES = {"drawers": drawers, "room": room, "standard": standard}
PATTERN = re.compile(r"^\s{4,}([A-Za-z_]\w*\([^)]*\))\s+->\s+(\[[^\]]*\]|\(.*?\)|-?\d+)\s*$", re.M)


def main() -> int:
    root = os.path.join(os.path.dirname(__file__), "..", "cabinetgen")
    bad = 0
    checked = 0
    for name, mod in MODULES.items():
        src = open(os.path.join(root, f"{name}.py"), encoding="utf-8").read()
        for call, claimed in PATTERN.findall(src):
            fn = call.split("(", 1)[0]
            if not hasattr(mod, fn):
                continue
            checked += 1
            try:
                got = eval(call, vars(mod))            # noqa: S307 - our own docstrings
                want = eval(claimed)                   # noqa: S307
            except Exception as exc:                   # noqa: BLE001
                print(f"  ERROR {name}.{call}: {exc}")
                bad += 1
                continue
            if got == want:
                print(f"  ok    {name}.{call} -> {got}")
            else:
                print(f"  WRONG {name}.{call} -> {got}, docstring claims {claimed}")
                bad += 1
    print(f"\n{checked} worked examples checked, {bad} wrong")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
