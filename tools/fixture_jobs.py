"""Where the job files the checks read live.

`jobs/` holds exactly two things the checks depend on: `Test.json` — the live
working file, opened, edited and saved in the app, and the placed-panel
fixture — and `wardrobe_oct2025.py`, the benchmark. Every OTHER job a check
reads is FROZEN under `tools/fixtures/`, where nothing in the app can reach it.

That is the same lesson `Test_Build_pre_library.json` and
`Test_legacy_supports.json` already taught, learnt a third time on 28 September
2026: Rudolf deleted every project but Test.json in the app (an ordinary thing
to do — the files went to `jobs/_deleted/`), and check_boards, check_library,
check_scene and check_panels died while five more silently skipped the jobs
they could not find. A check never reads live workshop data to pin a fact
about the past, so `Test_Build.json`, `Test_Panels.json` and `Corner Unit
Test.json` live here now, taken verbatim from the tree before that delete.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES = os.path.join(ROOT, "tools", "fixtures")

# The jobs that stay in jobs/, read live.
LIVE = ("Test.json",)


def job_file(name, root=ROOT):
    """The path of a job the checks read: jobs/ for Test.json, tools/fixtures/ for the rest."""
    base = name if name.endswith(".json") else name + ".json"
    if base in LIVE:
        return os.path.join(root, "jobs", base)
    return os.path.join(root, "tools", "fixtures", base)
