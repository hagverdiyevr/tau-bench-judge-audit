"""STEP 1 — verify the Gemini key works and see which models the account can reach.

COST: USD 0.00 — the models-list endpoint is free. No generation happens here.

Run:  cd vendor/tau2-bench && uv run python ../../scripts/phase_b/step1_verify_access.py
"""

import json
import os
import pathlib as _pl

import httpx
from dotenv import load_dotenv

_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_b"
_OUT.mkdir(parents=True, exist_ok=True)

load_dotenv(_REPO / ".env")

KEY = os.environ.get("GEMINI_API_KEY", "").strip()

print("=" * 72)
print("STEP 1 — credential + model access check      (cost: USD 0.00)")
print("=" * 72)

if not KEY or KEY.startswith("<"):
    print("\n  NO KEY FOUND.")
    print(f"  Create {_REPO / '.env'} containing:")
    print("      GEMINI_API_KEY=your_actual_key")
    print("  (copy .env.example, fill it in — it is gitignored)")
    raise SystemExit(1)

# Never print the key. Fingerprint only, enough to tell two keys apart.
print(f"\n  key loaded: len={len(KEY)}, starts {KEY[:4]}…{KEY[-2:]}  (never logged in full)")

r = httpx.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    params={"key": KEY, "pageSize": 1000},
    timeout=30,
)
if r.status_code != 200:
    body = r.text.replace(KEY, "<REDACTED>")
    print(f"\n  REQUEST FAILED  HTTP {r.status_code}")
    print(f"  {body[:400]}")
    raise SystemExit(1)

models = r.json().get("models", [])
names = sorted(m["name"].removeprefix("models/") for m in models)
gen = sorted(
    m["name"].removeprefix("models/")
    for m in models
    if "generateContent" in m.get("supportedGenerationMethods", [])
)

print(f"  API reachable. {len(names)} models visible, {len(gen)} support generateContent.")

# Candidates named in docs/PLAN.md and docs/REFERENCE.md
CANDIDATES = {
    "gemini-3.1-flash-lite": "planned AGENT arm (cheapest Google, minimal thinking default)",
    "gemini-3.5-flash-lite": "documented substitution ladder rung",
    "gemini-3.8-flash": "expensive Google arm / thinking comparison",
    "gemini-3.1-flash-lite-preview": "SHUT DOWN upstream - must NOT be available",
}

print("\n--- candidate models from our plan ---")
avail = {}
for mid, why in CANDIDATES.items():
    ok = mid in gen
    avail[mid] = ok
    flag = "OK " if ok else "-- "
    print(f"  {flag} {mid:<32} {why}")

print("\n--- all generateContent models visible to this account ---")
for n in gen:
    print(f"      {n}")

print("\n" + "=" * 72)
ready = avail.get("gemini-3.1-flash-lite") or avail.get("gemini-3.5-flash-lite")
if ready:
    print("  STEP 1 PASS — at least one planned agent arm is reachable.")
    print("  Next: step2_verify_billing.py (one tiny call, ~USD 0.0001)")
else:
    print("  STEP 1 BLOCKED — none of the planned agent arms are reachable.")
    print("  Pick a substitute from the list above and record it in docs/DECISIONS.md.")
if avail.get("gemini-3.1-flash-lite-preview"):
    print("  WARNING: the shut-down -preview ID appears available; prefer the un-suffixed GA ID.")
print("=" * 72)

json.dump(
    {"n_models": len(names), "generate_capable": gen, "candidates": avail},
    open(_OUT / "step1_access.json", "w"),
    indent=1,
)
print(f"\nwrote {_OUT / 'step1_access.json'}")
