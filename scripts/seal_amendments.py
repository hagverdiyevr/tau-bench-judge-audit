"""Seal the pre-registration amendments into an append-only hash chain.

Each amendment section (## A-NNN ...) is hashed and linked to the previous one. The first link
is the frozen pre-registration hash, so the chain is anchored to the immutable document.

REFUSES to seal if an already-sealed amendment's text changed — that is the append-only guarantee.
Run it after appending a new amendment, then commit BEFORE generating the data it affects.

Run:  python scripts/seal_amendments.py
Exit: 0 = sealed (or already current), 1 = append-only violation
"""

import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "PREREGISTRATION_AMENDMENTS.md"
CHAIN = REPO / "results" / "preregistration_chain.json"
ANCHOR = json.loads((REPO / "results" / "preregistration.sha256").read_text())["sha256"]


def sections(text):
    """Split into (id, body) per '## A-NNN' heading.

    Bodies are rstrip()ed before hashing. This is REQUIRED for append-stability: a section's
    extent is 'text until the next ## A-NNN heading', so the LAST section's trailing whitespace
    changes from 'newlines to EOF' to 'separator before the next heading' the moment a new
    amendment is appended. Without normalization, every append would break the previous seal —
    which it did, and was initially misread as tampering.
    """
    parts = re.split(r"^## (A-\d{3}) ", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i], parts[i + 1].rstrip()))
    return out


found = sections(DOC.read_text())
if not found:
    print("  no amendments found — nothing to seal")
    sys.exit(0)

prev = json.loads(CHAIN.read_text())["chain"] if CHAIN.exists() else []
prev_by_id = {e["id"]: e for e in prev}

chain, link = [], ANCHOR
violations = []
for aid, body in found:
    h = hashlib.sha256(body.encode()).hexdigest()
    was = prev_by_id.get(aid)
    if was and was["sha256"] != h:
        violations.append(f"{aid}: sealed as {was['sha256'][:12]}… but is now {h[:12]}…")
    chain.append({"id": aid, "sha256": h, "prev": link,
                  "sealed": bool(was), "anchor": link == ANCHOR})
    link = h

print(f"  anchor (frozen pre-registration): {ANCHOR[:16]}…")
for e in chain:
    mark = "already sealed" if e["sealed"] else "NEW — seal and commit before the data it affects"
    print(f"  {e['id']}  {e['sha256'][:16]}…  prev={e['prev'][:12]}…  {mark}")

if violations:
    print("\n  APPEND-ONLY VIOLATION — an already-sealed amendment was edited:")
    for v in violations:
        print(f"    {v}")
    print("  Amendments are immutable. Supersede with a new A-NNN; do not edit in place.")
    sys.exit(1)

CHAIN.write_text(json.dumps({"anchor_preregistration_sha256": ANCHOR, "chain": chain}, indent=1) + "\n")
print(f"\n  sealed {len(chain)} amendment(s) -> {CHAIN.relative_to(REPO)}")
sys.exit(0)
