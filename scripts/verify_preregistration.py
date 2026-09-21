"""Verify the pre-registration has not been altered since it was frozen.

The hash cannot cover itself, so it is computed over the file with the S9 fenced block
replaced by a fixed marker. Everything scientific (S1-S8, S10) is therefore covered.

Run:  python scripts/verify_preregistration.py
Exit: 0 = intact, 1 = ALTERED
"""
import hashlib, json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "PREREGISTRATION.md"
REC = REPO / "results" / "preregistration.sha256"
MARK = "```\n<<FREEZE BLOCK CANONICALISED FOR HASHING>>\n```"

src = DOC.read_text()
canon = re.sub(r"```\nSHA-256 .*?\n```", MARK, src, flags=re.S)
actual = hashlib.sha256(canon.encode()).hexdigest()
rec = json.loads(REC.read_text())
expected = rec["sha256"]

print(f"  file     : {DOC.relative_to(REPO)}")
print(f"  frozen   : {rec['frozen_utc']}")
print(f"  expected : {expected}")
print(f"  actual   : {actual}")
chain_ok = True
CHAIN = REPO / "results" / "preregistration_chain.json"
if CHAIN.exists():
    import re as _re
    ch = json.loads(CHAIN.read_text())
    body = DOC.parent / "PREREGISTRATION_AMENDMENTS.md"
    parts = _re.split(r"^## (A-\d{3}) ", body.read_text(), flags=_re.M)
    live = {parts[i]: hashlib.sha256(parts[i + 1].encode()).hexdigest()
            for i in range(1, len(parts), 2)}
    link = ch["anchor_preregistration_sha256"]
    print(f"\n  amendment chain ({len(ch['chain'])}):")
    if link != expected:
        print("    BROKEN — chain anchor does not match the frozen hash"); chain_ok = False
    for e in ch["chain"]:
        same = live.get(e["id"]) == e["sha256"]
        linked = e["prev"] == link
        print(f"    {e['id']}  text={'ok' if same else 'ALTERED'}  link={'ok' if linked else 'BROKEN'}")
        chain_ok = chain_ok and same and linked
        link = e["sha256"]

if actual == expected and chain_ok:
    print("\n  INTACT — pre-registration matches its frozen hash; amendment chain verified.")
    sys.exit(0)
if actual == expected and not chain_ok:
    print("\n  PRE-REGISTRATION INTACT but the AMENDMENT CHAIN is broken.")
    print("  Amendments are append-only. Re-run scripts/seal_amendments.py to see the violation.")
    sys.exit(1)
print("\n  ALTERED — content differs from the frozen hash.")
print("  If this change is intentional it must be recorded as a DEVIATION in S10,")
print("  not as an edit. The frozen hash is never updated.")
sys.exit(1)
