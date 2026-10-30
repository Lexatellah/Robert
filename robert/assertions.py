from __future__ import annotations
import json, time, hashlib, base64
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

class Tier(str, Enum):
    FACT = "fact"
    OFFICIAL = "official"
    COMMUNITY = "community"
    VICTIM = "victim"
    UNVERIFIED = "unverified"

@dataclass
class Assertion:
    subject: str
    predicate: str
    obj: Any
    tier: Tier
    source: str
    observed_at: int = field(default_factory=lambda: int(time.time()))
    evidence: dict = field(default_factory=dict)
    signature: str | None = None
    signer_pubkey: str | None = None

    def canonical(self) -> bytes:
        d = asdict(self)
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def digest(self) -> str:
        return hashlib.sha256(self.canonical()).hexdigest()

def generate_keypair():
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return priv, pub

def sign(assertion, priv):
    assertion.signature = base64.b64encode(priv.sign(assertion.canonical())).decode()
    assertion.signer_pubkey = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return assertion
