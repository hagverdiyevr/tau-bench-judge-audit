"""Consistency check for the documentation system. Run after every iteration.

Catches the drift that prose checklists miss: stale spend figures, broken cross-links,
a tampered pre-registration, superseded facts left behind in one file.

Run:  python scripts/check_docs.py
Exit: 0 = aligned, 1 = drift found
"""

import hashlib
import json
import pathlib
import re
import subprocess
import sys


def subprocess_run_tracked_md():
    try:
        out = subprocess.run(["git", "ls-files", "*.md"], cwd=pathlib.Path(__file__).resolve().parents[1],
                             capture_output=True, text=True).stdout.split()
        root = pathlib.Path(__file__).resolve().parents[1]
        return [root / f for f in out if (root / f).exists()]
    except Exception:
        return []


REPO = pathlib.Path(__file__).resolve().parents[1]
# Corpus = ALL tracked markdown, not just docs/ + CLAUDE.md. The narrower corpus let
# RETAIL_AGENT_IMPLEMENTATION_PLAN.md drift unchecked while the checker reported "ALIGNED".
_tracked = subprocess_run_tracked_md()
DOCS = _tracked if _tracked else sorted((REPO / "docs").glob("*.md")) + [REPO / "CLAUDE.md"]
FROZEN = REPO / "docs" / "PREREGISTRATION.md"
LEDGER = REPO / "results" / "spend_ledger.json"

problems: list[str] = []
notes: list[str] = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{(' — ' + detail) if detail and not ok else ''}")
    if not ok:
        problems.append(f"{label}: {detail}")


# 1 — every relative markdown link resolves
broken = []
for f in DOCS:
    for target in re.findall(r"\]\(([^)#]+\.md)", f.read_text()):
        if not (f.parent / target).exists():
            broken.append(f"{f.name} -> {target}")
check("all cross-document links resolve", not broken, "; ".join(broken))

# 2 — pre-registration matches its frozen hash
MARK = "```\n<<FREEZE BLOCK CANONICALISED FOR HASHING>>\n```"
rec = json.loads((REPO / "results" / "preregistration.sha256").read_text())
canon = re.sub(r"```\nSHA-256[^\n]*\n.*?```", MARK, FROZEN.read_text(), flags=re.S)
actual = hashlib.sha256(canon.encode()).hexdigest()
check("pre-registration intact (frozen hash)", actual == rec["sha256"],
      f"expected {rec['sha256'][:12]}… got {actual[:12]}…")

# 3 — spend figures agree with the generated ledger
ledger = json.loads(LEDGER.read_text())
spend = f"{ledger['total_usd']:.2f}"
remaining = f"{ledger['remaining_usd']:.2f}"
for name in ("STATUS.md", "PLAN.md"):
    txt = (REPO / "docs" / name).read_text()
    check(f"{name} quotes current spend (${spend})", spend in txt,
          f"ledger says {spend}; file does not contain it")
    check(f"{name} quotes remaining (${remaining})", remaining in txt,
          f"ledger says {remaining}; file does not contain it")

# 4 — no superseded statements left behind
STALE = {
    "USD 25 cumulative": "budget was raised to USD 75 (D-001)",
    "non-zero temperature": "judge temperature is 0.0 (verified)",
    "10 dev / 10 held-out": "superseded by the shipped base split",
    "Two Gemini Flash candidates": "superseded by the judge-bias design",
    "DB × COMMUNICATE": "retail reward is DB × NL_ASSERTION (A1)",
}
# A stale claim is only a problem when ASSERTED. Citing it as corrected, rejected or
# historical is exactly what DECISIONS/FINDINGS are for, so those lines are exempt.
EXEMPT = ("not ", "no longer", "killed", "reject", "supersede", "falsifi", "was wrong",
          "the thesis", "historical", "stale", "instead of", "rather than", "~~")
for bad, why in STALE.items():
    hits = []
    for f in DOCS:
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if bad in line and not any(e in line.lower() for e in EXEMPT):
                hits.append(f"{f.name}:{i}")
    check(f"no stale claim ASSERTED: {bad!r}", not hits, f"at {hits} — {why}")

# 4a — claims corrected by the post-release review must not be re-asserted in the LIVE docs.
# The append-only records (FINDINGS, DECISIONS) and the filing record (UPSTREAM_ISSUES) keep the
# original wording beside its correction on purpose, so they are out of scope here, as are dated
# session-log rows, which are history by construction.
LIVE = [REPO / "CLAUDE.md", REPO / "README.md", REPO / "docs/STATUS.md", REPO / "docs/PLAN.md",
        REPO / "docs/REFERENCE.md"]
STALE_LIVE = {
    "~40% understatement": "an estimate; measured judge share is 32.8% (R-L4)",
    "python3` is **3.9.6**": "bare python3 is not a fixed interpreter here (R-L10)",
    "reproduces, in the *judge* role": "one flip in 256 is not an asymmetry (R-L8)",
    "4–11 literal": "measured at n=320: 19.9% of lines, 0–15 per trajectory (B4, #553)",
    "uv run python ": "plain `uv run` rewrites upstream's uv.lock; use --frozen (R-L11)",
    "half-applied target": "task 64's target is correct; only 105 is a defect (R-L13)",
    "live on 32 telecom": "no ACTION-scored task compares a reorderable list; no score changes (R-L14)",
}
for bad, why in STALE_LIVE.items():
    hits = []
    for f in LIVE:
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if bad in line and not line.startswith("| 20") and not any(e in line.lower() for e in EXEMPT):
                hits.append(f"{f.name}:{i}")
    check(f"live docs do not re-assert a corrected claim: {bad!r}", not hits, f"at {hits} — {why}")

# 4b — git provenance: STATUS must not claim a stale commit or a clean tree when it is dirty
head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                       capture_output=True, text=True).stdout.strip()
status_txt = (REPO / "docs" / "STATUS.md").read_text()
import re as _re2
# Only the CURRENT-STATE sections make claims about HEAD. The session log is a historical
# record — citing the commit a past session made is correct, not drift. (Same distinction as
# the stale-claim check: assertion vs citation.)
current_state = status_txt.split("## Session log", 1)[0]
claimed = _re2.findall(r"commit `([0-9a-f]{7,})`", current_state)
check("STATUS.md does not cite a stale commit", not claimed or any(c.startswith(head) for c in claimed),
      f"STATUS cites {claimed}; HEAD is {head}")
if dirty:
    check("STATUS.md does not claim a clean tree while dirty", "working tree clean" not in status_txt,
          f"tree has {len(dirty.splitlines())} dirty path(s)")

# 4c — amendment chain verifies
amd = subprocess.run([sys.executable, str(REPO / "scripts/verify_preregistration.py")],
                     cwd=REPO, capture_output=True, text=True)
check("pre-registration + amendment chain verify", amd.returncode == 0, amd.stdout.strip()[-200:])

# 5 — pre-registration declares itself frozen, and S10 discipline holds
pr = FROZEN.read_text()
check("pre-registration marked FROZEN", "Status: FROZEN" in pr)

# ---- README: the public artifact's load-bearing numbers must match the raw results -----------
# The README is the only document most readers will see. Every headline number in it is
# regenerated by scripts/phase_d/analyze_phase_d.py, so it can be checked rather than trusted.
README = REPO / "README.md"
ANALYSIS = REPO / "results" / "phase_d" / "analysis.json"
if README.exists() and ANALYSIS.exists():
    rd = README.read_text()
    an = json.loads(ANALYSIS.read_text())
    fb = an.get("family_bias") or {}
    wants = [
        ("FamilyBias point estimate", f"{fb.get('point', 0):+.4f}"),
        ("CI lower bound", f"{fb.get('ci_low', 0):+.4f}".replace("+", "")),
        ("CI upper bound", f"{fb.get('ci_high', 0):+.4f}"),
        ("realized MDE", f"{fb.get('realized_mde', 0):.4f}"),
        ("between-task SD", f"{fb.get('between_task_sd', 0):.4f}"),
        ("total evaluations", f"{an.get('planned', 0):,}"),
    ]
    for label, token in wants:
        check(f"README states the measured {label} ({token})", token in rd,
              f"'{token}' absent — README has drifted from analysis.json")
    # The null must never be presented as equivalence.
    for banned in ("judge is unbiased", "judge is fair", "no bias found", "proves fairness"):
        check(f"README does not overclaim: '{banned}'", banned.lower() not in rd.lower(),
              "D-021 forbids presenting an underpowered null as equivalence")
    check("README keeps the MDE beside the null (D-021)",
          "MDE" in rd and "underpowered" in rd.lower())
dev = pr.split("## 10. Deviation log", 1)[-1]
if "*Empty at freeze." not in dev:
    notes.append("PREREGISTRATION §10 contains deviations — confirm each is justified.")

# 6 — findings/decisions are append-only in git history
import subprocess
for name in ("docs/FINDINGS.md", "docs/DECISIONS.md"):
    try:
        out = subprocess.run(["git", "log", "--oneline", "--", name], cwd=REPO,
                             capture_output=True, text=True).stdout
        notes.append(f"{name}: {len(out.splitlines())} commit(s) in history")
    except Exception:
        pass

print()
for n in notes:
    print(f"  note: {n}")
print()
if problems:
    print(f"  {len(problems)} DRIFT ISSUE(S) — fix before proceeding.")
    sys.exit(1)
print("  DOCS ALIGNED — safe to proceed.")
sys.exit(0)
