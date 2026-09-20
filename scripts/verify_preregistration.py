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
if actual == expected:
    print("\n  INTACT — pre-registration matches its frozen hash.")
    sys.exit(0)
print("\n  ALTERED — content differs from the frozen hash.")
print("  If this change is intentional it must be recorded as a DEVIATION in S10,")
print("  not as an edit. The frozen hash is never updated.")
sys.exit(1)
