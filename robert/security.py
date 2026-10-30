import re

_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_SAFE_STR = re.compile(r"^[\w \-.,:/@#]{0,512}$")

def clean(s, field="input"):
    """Reject control chars, cap length, allow common punctuation only."""
    if not isinstance(s, str):
        raise ValueError(f"{field}: not a string")
    s = s.strip()
    if not _SAFE_STR.match(s):
        raise ValueError(f"{field}: illegal characters")
    return s

def _keccak(data: bytes) -> bytes:
    try:
        from Crypto.Hash import keccak
        h = keccak.new(digest_bits=256)
        h.update(data)
        return h.digest()
    except ImportError:
        return None

def validate_address(addr: str) -> str:
    """Format check + optional EIP-55 checksum if pycryptodome is installed."""
    addr = clean(addr, "address")
    if not _ADDR_RE.match(addr):
        raise ValueError("address: not a 20-byte hex address")
    if addr == addr.lower() or addr == addr.upper():
        return addr.lower()
    k = _keccak(addr.lower().encode("ascii"))
    if k is None:
        return addr.lower()
    h = k.hex()
    for i, ch in enumerate(addr[2:]):
        if ch.isalpha():
            want_upper = int(h[i], 16) >= 8
            if ch.isupper() != want_upper:
                raise ValueError("address: EIP-55 checksum mismatch")
    return addr.lower()
