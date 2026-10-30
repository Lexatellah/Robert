import base64, hashlib, json, zipfile
from pathlib import Path

def _signed_payload(manifest):
    """The exact bytes that get signed and verified. Never changes shape."""
    payload = {
        "files": manifest.get("files", {}),
        "audit_head": manifest.get("audit_head"),
        "meta": manifest.get("meta", {}),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

def write_bundle(out_path, assertions, meta, audit=None, priv=None):
    manifest = {"meta": meta, "files": {}, "audit_head": None,
                "audit_ok": None, "signature": None,
                "signer_pubkey": None, "signed_payload_sha256": None}

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for i, a in enumerate(assertions):
            name = f"assertions/{i:04d}_{a.digest()[:12]}.json"
            blob = json.dumps(a.__dict__, sort_keys=True, indent=2, default=str).encode()
            z.writestr(name, blob)
            manifest["files"][name] = hashlib.sha256(blob).hexdigest()

        if audit is not None:
            lines = [json.dumps(e, sort_keys=True) for e in audit.entries]
            body = ("\n".join(lines) + "\n").encode()
            z.writestr("audit.jsonl", body)
            manifest["audit_head"] = audit.head()
            manifest["audit_ok"] = audit.verify()

        # sign a deterministic payload independent of manifest serialization
        payload = _signed_payload(manifest)
        manifest["signed_payload_sha256"] = hashlib.sha256(payload).hexdigest()
        if priv is not None:
            sig = priv.sign(payload)
            manifest["signature"] = base64.b64encode(sig).decode()
            from cryptography.hazmat.primitives import serialization
            manifest["signer_pubkey"] = priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            ).hex()

        z.writestr("manifest.json",
                   json.dumps(manifest, sort_keys=True, indent=2).encode())
    return out_path
