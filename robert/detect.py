import re
from robert.domain import Subject, SubjectKind, AssetClass, DetectionResult
from robert import bank, security

EVM_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
EVM_TX = re.compile(r"^0x[0-9a-fA-F]{64}$")
BTC_LEGACY = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
BTC_BECH32 = re.compile(r"^bc1[ac-hj-np-z02-9]{11,71}$")
TRON = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")

def _iban_candidate(s: str) -> Subject | None:
    try:
        iban = bank.normalize_iban(s)
    except ValueError:
        return None
    valid = bank.iban_is_valid(iban)
    return Subject(
        raw=s, kind=SubjectKind.IBAN, normalized=iban,
        asset_class=AssetClass.BANK,
        jurisdiction=bank.iban_country(iban),
        checksum_valid=valid,
        confidence=0.99 if valid else 0.6,
        notes=() if valid else ("mod-97 check failed",),
    )

def _bic_candidate(s: str) -> Subject | None:
    try:
        if not bank.bic_is_valid(s):
            return None
        return Subject(
            raw=s, kind=SubjectKind.BIC, normalized=s.upper(),
            asset_class=AssetClass.BANK,
            jurisdiction=bank.bic_country(s),
            checksum_valid=True, confidence=0.9,
        )
    except ValueError:
        return None

def _evm_address_candidate(s: str) -> Subject | None:
    if not EVM_ADDR.match(s):
        return None
    try:
        norm = security.validate_address(s)
        return Subject(raw=s, kind=SubjectKind.EVM_ADDRESS, normalized=norm,
                       asset_class=AssetClass.CRYPTO, chain="evm",
                       checksum_valid=True, confidence=0.99)
    except ValueError:
        return Subject(raw=s, kind=SubjectKind.EVM_ADDRESS, normalized=s.lower(),
                       asset_class=AssetClass.CRYPTO, chain="evm",
                       checksum_valid=False, confidence=0.7,
                       notes=("EIP-55 checksum invalid",))

def _evm_tx_candidate(s: str) -> Subject | None:
    if not EVM_TX.match(s):
        return None
    return Subject(raw=s, kind=SubjectKind.EVM_TX, normalized=s.lower(),
                   asset_class=AssetClass.CRYPTO, chain="evm",
                   confidence=0.99)

def _btc_candidate(s: str) -> Subject | None:
    if BTC_LEGACY.match(s) or BTC_BECH32.match(s):
        return Subject(raw=s, kind=SubjectKind.BTC_ADDRESS, normalized=s,
                       asset_class=AssetClass.CRYPTO, chain="bitcoin",
                       confidence=0.9)
    return None

def _tron_candidate(s: str) -> Subject | None:
    if TRON.match(s):
        return Subject(raw=s, kind=SubjectKind.TRON_ADDRESS, normalized=s,
                       asset_class=AssetClass.CRYPTO, chain="tron",
                       confidence=0.9)
    return None

_CANDIDATE_FNS = (
    _iban_candidate, _bic_candidate,
    _evm_tx_candidate, _evm_address_candidate,
    _btc_candidate, _tron_candidate,
)

def detect(raw: str) -> DetectionResult:
    s = (raw or "").strip()
    if not s:
        return DetectionResult(input=raw, error="empty input")
    candidates = [c for fn in _CANDIDATE_FNS if (c := fn(s))]
    if not candidates:
        return DetectionResult(input=raw, error="unrecognized format")
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return DetectionResult(input=raw, subject=candidates[0],
                           alternatives=candidates[1:])
