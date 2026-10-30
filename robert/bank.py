import re
_IBAN_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")
_BIC_RE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")

def normalize_iban(raw: str) -> str:
    s = re.sub(r"\s+", "", raw).upper()
    if not _IBAN_RE.match(s):
        raise ValueError("IBAN format invalid")
    return s

def iban_is_valid(iban: str) -> bool:
    s = normalize_iban(iban)
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return int(digits) % 97 == 1

def iban_country(iban: str) -> str:
    return normalize_iban(iban)[:2]

def bic_is_valid(bic: str) -> bool:
    return bool(_BIC_RE.match(bic.upper()))

def bic_country(bic: str) -> str:
    if not bic_is_valid(bic):
        raise ValueError("BIC format invalid")
    return bic.upper()[4:6]
