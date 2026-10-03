"""Build the demo: one zip a friend unzips and double-clicks (29 September 2026 brief).

    python tools/build_demo.py                   # what Build Demo.bat runs
    python tools/build_demo.py --test-expired    # a throwaway copy that expired yesterday

1. Installs Nuitka if it is missing. Nuitka compiles the Python into machine
   code, so the zip carries no readable source; it downloads its own C compiler
   the first time (`--assume-yes-for-downloads`).
2. Writes `app/_demo_build.py` — `DEMO = True`, `EXPIRES` = today + 60 days
   (yesterday with `--test-expired`) — which turns `app/demo.py` on.
3. Builds `run_app.py` in standalone FOLDER mode, not onefile: onefile unpacks
   to a temp folder on every run, and since `ROOT` comes from `__file__`, saved
   jobs, `output/` and new board pictures would vanish with it. A Windows app
   with no console, the icon, `Cupboard App Demo.exe`.
4. Deletes `app/_demo_build.py` again, whatever happened, so a normal
   `python run_app.py` is never in demo mode.
5. Copies in the data the app reads (ruling 3: nothing held back) and zips it
   to `demo/Cupboard App Demo <build date>.zip`, `READ ME FIRST.txt` beside the
   app folder.
6. Lists the zip: no `.py` / `.pyc` of this repo may be in it, and nothing the
   brief keeps out. Then says where the zip is, its size and the expiry date.

The data is copied by name, never by exclusion, so nothing new in the repo can
reach the zip by accident. `jobs/_deleted/` (the app's bin) stays out — ruled by
Rudolf, 30 September 2026.
"""
import argparse
import datetime
import glob
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from app.demo import say  # noqa: E402

DAYS = 60
EXE = "Cupboard App Demo.exe"
APP_FOLDER = "Cupboard App Demo"
BUILD_DIR = os.path.join(REPO, "build-demo")          # Nuitka's working folders
DEMO_DIR = os.path.join(REPO, "demo")                 # the zips
STAMP = os.path.join(REPO, "app", "_demo_build.py")

# What the app reads while it runs (ruling 3). Files, and folders copied whole.
DATA_FILES = ["boards.json", "hardware.json",
              os.path.join("app", "index.html"), os.path.join("app", "view3d.js"),
              os.path.join("app", "cupboard.ico")]
DATA_DIRS = ["Pictures", os.path.join("app", "vendor")]
# jobs/: the saved jobs only — Test.json today — not the bin, not the benchmark's
# source, which is compiled in as the module `jobs.wardrobe_oct2025`.
JOBS_GLOB = "*.json"

# What must never be in the zip (brief, section 3).
KEPT_OUT = ("tools/", "docs/", "CLAUDE.md", "Claude outputs/", "claude/", "Reference/",
            "Sample Plaza cutlist and quote/", "_to_delete/", "baseline.json",
            "output/", "out/", ".git/", "jobs/_deleted/")
KEPT_OUT_SUFFIX = (".bat",)
REPO_CODE = ("app/", "cabinetgen/", "jobs/", "run_app")

README = """Cupboard App — Demo
This demo works until {expiry}.

1. Unzip this whole folder into Documents (not Program Files, and don't run it from inside the zip).
2. Open the folder and double-click "Cupboard App Demo.exe".
3. If Windows says "Windows protected your PC": click "More info", then "Run anyway".
   It only asks the first time.
4. Needs Windows 10 or 11.

Your jobs and exports are saved inside this folder, so keep it together.

Moving to a new demo: unzip it, start it, and press Import project.
Pick this old folder (it is only read, never changed).
Your jobs, boards, runners and pictures come across, even after this demo has expired.
"""


def step(msg):
    print(f"\n=== {msg}", flush=True)


def ensure_nuitka():
    try:
        import nuitka  # noqa: F401
        return
    except ImportError:
        pass
    step("Installing Nuitka (pip install nuitka)")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka"])


def ensure_webview():
    """The demo is a window, so the Python building it must have pywebview —
    without it the build would quietly fall back to opening a browser."""
    try:
        import webview  # noqa: F401
    except ImportError:
        sys.exit("pywebview is not installed for this Python (pip install pywebview). "
                 "The demo needs it for its window.")


def nuitka(expires: datetime.date):
    with open(STAMP, "w", encoding="utf-8") as fh:
        fh.write("# Written by tools/build_demo.py for one build, then deleted. Never commit.\n"
                 f"DEMO = True\nEXPIRES = {expires.isoformat()!r}\n")
    # Store Python keeps what it writes under AppData in a private folder that
    # Nuitka's downloaded compiler cannot see (it then cannot find windows.h),
    # so the cache goes somewhere ordinary. Harmless on any other Python.
    env = dict(os.environ)
    env.setdefault("NUITKA_CACHE_DIR", os.path.join(os.path.expanduser("~"), "NuitkaCache"))
    cmd = [sys.executable, "-m", "nuitka",
           "--mode=standalone",
           "--assume-yes-for-downloads",
           "--windows-console-mode=disable",
           "--windows-icon-from-ico=" + os.path.join("app", "cupboard.ico"),
           "--output-filename=" + EXE,
           "--output-dir=" + BUILD_DIR,
           "--include-module=app._demo_build",
           "--include-module=jobs.wardrobe_oct2025",     # imported by name, inside a function
           "--nofollow-import-to=tools",
           "--product-name=Cupboard App Demo",
           "--file-description=Cupboard App Demo",
           "--product-version=1.0",
           "run_app.py"]
    try:
        subprocess.check_call(cmd, cwd=REPO, env=env)
    finally:
        os.remove(STAMP)
        cache = os.path.join(REPO, "app", "__pycache__")
        for name in os.listdir(cache) if os.path.isdir(cache) else []:
            if name.startswith("_demo_build."):
                os.remove(os.path.join(cache, name))
    return os.path.join(BUILD_DIR, "run_app.dist")


def assemble(dist: str, stage: str, expires: datetime.date):
    if os.path.exists(stage):
        shutil.rmtree(stage)
    app_dir = os.path.join(stage, APP_FOLDER)
    shutil.copytree(dist, app_dir)
    for rel in DATA_FILES:
        os.makedirs(os.path.dirname(os.path.join(app_dir, rel)) or app_dir, exist_ok=True)
        shutil.copy2(os.path.join(REPO, rel), os.path.join(app_dir, rel))
    for rel in DATA_DIRS:
        shutil.copytree(os.path.join(REPO, rel), os.path.join(app_dir, rel),
                        ignore=shutil.ignore_patterns("__pycache__", "*.py", "*.pyc"))
    jobs = os.path.join(app_dir, "jobs")
    os.makedirs(jobs, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(REPO, "jobs", JOBS_GLOB))):
        shutil.copy2(path, jobs)
    with open(os.path.join(stage, "READ ME FIRST.txt"), "w", encoding="utf-8-sig",
              newline="\r\n") as fh:
        fh.write(README.format(expiry=say(expires)))


def make_zip(stage: str, zpath: str):
    os.makedirs(os.path.dirname(zpath), exist_ok=True)
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, dirs, files in os.walk(stage):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(base, name)
                z.write(full, os.path.relpath(full, stage))


def inspect(zpath: str) -> bool:
    """List the zip. False if any of this repo's code, or anything kept out, is in it."""
    with zipfile.ZipFile(zpath) as z:
        names = [n.replace("\\", "/") for n in z.namelist()]
    inner = [n.split("/", 1)[1] if n.startswith(APP_FOLDER + "/") else n for n in names]
    source = [n for n in names if n.lower().endswith((".py", ".pyc", ".pyo", ".pyw"))]
    repo_code = [n for n, i in zip(names, inner) if n in source and i.startswith(REPO_CODE)]
    kept_out = [n for n, i in zip(names, inner)
                if i.startswith(KEPT_OUT) or i.lower().endswith(KEPT_OUT_SUFFIX)
                or os.path.basename(i).startswith("snapshot-")]
    runtime = sorted(i for i in inner if i.lower().endswith((".pyd", ".dll", ".exe")))
    print(f"\n  {len(names)} files in the zip.")
    print(f"  .py / .pyc / .pyo files of any kind: {len(source)}"
          + ("" if not source else "\n    " + "\n    ".join(source)))
    print(f"  of them this repo's own code: {len(repo_code)}")
    print(f"  things the brief keeps out: {len(kept_out)}"
          + ("" if not kept_out else "\n    " + "\n    ".join(kept_out)))
    print(f"  compiled runtime pieces (.exe / .dll / .pyd): {len(runtime)}")
    for r in runtime:
        print(f"    {r}")
    return not repo_code and not kept_out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-expired", action="store_true",
                    help="a throwaway copy whose expiry was yesterday, to see it refuse")
    args = ap.parse_args(argv)

    built = datetime.date.today()
    expires = built - datetime.timedelta(days=1) if args.test_expired \
        else built + datetime.timedelta(days=DAYS)
    tag = " TEST-EXPIRED" if args.test_expired else ""

    ensure_webview()
    ensure_nuitka()
    step(f"Compiling with Nuitka (expires {say(expires)}). The first build takes a while.")
    dist = nuitka(expires)
    step("Copying in the data the app reads")
    stage = os.path.join(BUILD_DIR, "stage" + tag.replace(" ", "-").lower())
    assemble(dist, stage, expires)
    zpath = os.path.join(DEMO_DIR, f"Cupboard App Demo {built.isoformat()}{tag}.zip")
    step("Zipping")
    make_zip(stage, zpath)
    step("Checking what is in the zip")
    clean = inspect(zpath)

    size = os.path.getsize(zpath) / 1e6
    print("\n---------------------------------------------")
    if args.test_expired:
        print("TEST COPY ONLY. It expired yesterday on purpose. Do not send it.")
    print(f"Zip:     {zpath}")
    print(f"Size:    {size:.0f} MB")
    print(f"Expires: {say(expires)} (it works up to and including that day)")
    if not clean:
        print("\nNOT CLEAN: the zip carries something it must not (listed above). Do not send it.")
        print("---------------------------------------------")
        return 1
    print("Check:   no .py or .pyc of this repo inside")
    print("---------------------------------------------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
