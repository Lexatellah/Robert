"""Robert demo: run one report, verify the bundle, print the audit chain."""
import json, subprocess, sys, tempfile, zipfile
from pathlib import Path

ADDR = "0x28C6c06298d514Db089934071355E5743bf21d60"
IBAN = "DE89370400440532013000"
out = Path(tempfile.gettempdir()) / "robert_demo.zip"

cmd = [sys.executable, "-m", "robert.cli", "report",
       "--address", ADDR, "--iban", IBAN, "--amount", "0.05",
       "--when", "1730000000", "--out", str(out)]
print(">>", " ".join(cmd), "\n")
subprocess.run(cmd, check=True)

print("\n>> bundle contents:")
with zipfile.ZipFile(out) as z:
    for name in z.namelist()[:8]:
        print("   ", name)
    manifest = json.loads(z.read("manifest.json"))

print("\n>> manifest:")
for k in ("meta", "audit_head", "audit_ok", "signature", "signer_pubkey"):
    v = manifest.get(k)
    if isinstance(v, str) and len(v) > 40:
        v = v[:40] + "..."
    print(f"   {k}: {v}")

# verify the audit chain independently
from robert.audit import AuditLog
a = AuditLog()
with zipfile.ZipFile(out) as z:
    a.entries = [json.loads(l) for l in z.read("audit.jsonl").decode().splitlines() if l.strip()]
print(f"\n>> audit chain verified: {a.verify()}")
print(f">> head: {a.head()}")
