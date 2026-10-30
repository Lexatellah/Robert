import base64, hashlib, json, zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

class VerifyResult:
    def __init__(self):
        self.ok = False
        self.checks = []
        self.errors = []
    def add(self, name, passed, detail=""):
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            self.errors.append(f"{name}: {detail or 'failed'}")

def verify_bundle(path: Path) -> VerifyResult:
    r = VerifyResult()
    if not path.exists():
        r.add("file_exists", False, str(path)); return r
    r.add("file_exists", True, str(path))

    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        r.add("zip_readable", False, str(e)); return r
    r.add("zip_readable", True)

    names = set(zf.namelist())
    if "manifest.json" not in names:
        r.add("manifest_present", False); return r
    r.add("manifest_present", True)

    manifest = json.loads(zf.read("manifest.json"))
    r.add("manifest_parsed", True)

    files = manifest.get("files", {})
    r.add("files_listed", bool(files), f"{len(files)} entries")
    hash_failures = 0
    for name, expected in files.items():
        if name not in names:
            hash_failures += 1; continue
        if hashlib.sha256(zf.read(name)).hexdigest() != expected:
            hash_failures += 1
    r.add("file_hashes_match", hash_failures == 0, f"{hash_failures} mismatch(es)")

    if "audit.jsonl" in names:
        entries = [json.loads(l) for l in zf.read("audit.jsonl").decode().splitlines() if l.strip()]
        prev = "0" * 64
        chain_ok = True
        for e in entries:
            body = {"prev": e["prev"], "at": e["at"], "event": e["event"]}
            blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            if hashlib.sha256(blob).hexdigest() != e["hash"] or e["prev"] != prev:
                chain_ok = False; break
            prev = e["hash"]
        r.add("audit_chain_valid", chain_ok, f"{len(entries)} entries")
        r.add("audit_head_matches", manifest.get("audit_head") == prev,
              f"manifest={str(manifest.get('audit_head'))[:16]}... chain={prev[:16]}...")
    else:
        r.add("audit_present", False)

    sig_b64 = manifest.get("signature")
    pub_hex = manifest.get("signer_pubkey")
    payload_hash = manifest.get("signed_payload_sha256")
    if sig_b64 and pub_hex and payload_hash:
        try:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
            payload = json.dumps(
                {"files": manifest.get("files", {}),
                 "audit_head": manifest.get("audit_head"),
                 "meta": manifest.get("meta", {})},
                sort_keys=True, separators=(",", ":")).encode()
            actual_hash = hashlib.sha256(payload).hexdigest()
            if actual_hash != payload_hash:
                raise ValueError(
                    f"signed_payload_sha256 mismatch: "
                    f"manifest={payload_hash[:16]}... recomputed={actual_hash[:16]}...")
            pub.verify(base64.b64decode(sig_b64), payload)
            r.add("manifest_signature_valid", True, pub_hex[:16] + "...")
        except Exception as e:
            r.add("manifest_signature_valid", False, str(e))
    else:
        r.add("manifest_signed", False,
              "missing signature / signer_pubkey / signed_payload_sha256")

    r.ok = all(c["passed"] for c in r.checks)
    return r
