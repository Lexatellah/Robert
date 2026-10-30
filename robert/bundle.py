import hashlib, json, zipfile, base64
from pathlib import Path
from robert import assertions as A

def write_bundle(out_path, assertions, meta, audit=None, priv=None):
    manifest = {"meta": meta, "files": {}, "audit_head": None, "signature": None}
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

        manifest_blob = json.dumps(manifest, sort_keys=True, indent=2).encode()
        if priv is not None:
            sig = priv.sign(manifest_blob)
            manifest["signature"] = base64.b64encode(sig).decode()
            manifest["signer_pubkey"] = priv.public_key().public_bytes(
                encoding=__import__("cryptography.hazmat.primitives.serialization",
                                     fromlist=["Encoding"]).Encoding.Raw,
                format=__import__("cryptography.hazmat.primitives.serialization",
                                  fromlist=["PublicFormat"]).PublicFormat.Raw,
            ).hex()
            manifest_blob = json.dumps(manifest, sort_keys=True, indent=2).encode()

        z.writestr("manifest.json", manifest_blob)
    return out_path
