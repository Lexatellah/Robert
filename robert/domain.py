from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class AssetClass(str, Enum):
    BANK = "bank"
    CRYPTO = "crypto"
    UNKNOWN = "unknown"

class SubjectKind(str, Enum):
    IBAN = "bank.iban"
    BIC = "bank.bic"
    EVM_ADDRESS = "crypto.evm.address"
    EVM_TX = "crypto.evm.tx"
    BTC_ADDRESS = "crypto.btc.address"
    TRON_ADDRESS = "crypto.tron.address"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class Subject:
    raw: str
    kind: SubjectKind
    normalized: str
    asset_class: AssetClass
    chain: Optional[str] = None
    jurisdiction: Optional[str] = None
    checksum_valid: Optional[bool] = None
    confidence: float = 0.0
    notes: tuple[str, ...] = ()

    def label(self) -> str:
        if self.asset_class == AssetClass.BANK:
            return f"BANK ACCOUNT ({self.kind.value})"
        if self.asset_class == AssetClass.CRYPTO:
            return f"CRYPTO ({self.kind.value}, chain={self.chain})"
        return "UNKNOWN"

@dataclass
class DetectionResult:
    input: str
    subject: Optional[Subject] = None
    alternatives: list[Subject] = field(default_factory=list)
    error: Optional[str] = None

    def ok(self) -> bool:
        return self.subject is not None
