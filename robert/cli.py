import argparse, json, sys, time
from pathlib import Path
from robert import assertions as A, bank, security
from robert.agents.runner import AgentRunner, RPC
from robert.audit import AuditLog
from robert.bundle import write_bundle
from robert.correlate import correlate
from robert.detect import detect

CHAIN_MAP = {"1": "ethereum", "8453": "base", "42161": "arbitrum",
             "10": "optimism", "137": "polygon"}
EXIT_OK, EXIT_INVALID, EXIT_NO_DATA = 0, 2, 3

def _human(value: str, decimals: int) -> str:
    try:
        return f"{int(value) / 10**decimals:.8f}".rstrip("0").rstrip(".") or "0"
    except Exception:
        return value

def _print_subject(s):
    print(f"CLASS      {s.label()}")
    print(f"  raw          {s.raw}")
    print(f"  normalized   {s.normalized}")
    if s.jurisdiction:
        print(f"  jurisdiction {s.jurisdiction}")
    if s.checksum_valid is not None:
        print(f"  checksum     {'valid' if s.checksum_valid else 'INVALID'}")
    print(f"  confidence   {s.confidence:.2f}")
    if s.asset_class.value == "bank":
        print("  => this is a BANK identifier, not a crypto address")
    elif s.asset_class.value == "crypto":
        print(f"  => this is a CRYPTO identifier on {s.chain}")

def cmd_detect(args):
    rc = EXIT_OK
    results = []
    for raw in args.inputs:
        r = detect(raw)
        results.append(r)
        if args.json: continue
        if r.ok():
            _print_subject(r.subject)
            for alt in r.alternatives:
                print(f"  alt: {alt.kind.value} (confidence {alt.confidence:.2f})")
        else:
            print(f"CLASS      UNKNOWN\n  input        {r.input}\n  error        {r.error}")
            rc = EXIT_INVALID
        print()
    if args.json:
        print(json.dumps([{
            "input": r.input,
            "subject": r.subject.__dict__ if r.subject else None,
            "alternatives": [a.__dict__ for a in r.alternatives],
            "error": r.error,
        } for r in results], indent=2, default=str))
    return rc

def cmd_validate(args):
    r = detect(args.input)
    if not r.ok():
        print(f"INVALID: {r.error}", file=sys.stderr); return EXIT_INVALID
    if r.subject.checksum_valid is False:
        print(f"INVALID checksum for {r.subject.kind.value}", file=sys.stderr)
        return EXIT_INVALID
    print(f"OK: {r.subject.label()}")
    return EXIT_OK

def cmd_report(args):
    audit = AuditLog()
    crypto = detect(args.address) if args.address else None
    bank_sub = detect(args.iban) if args.iban else None
    if crypto and not crypto.ok():
        print(f"address rejected: {crypto.error}", file=sys.stderr); return EXIT_INVALID
    if bank_sub and (not bank_sub.ok() or bank_sub.subject.checksum_valid is False):
        print("IBAN rejected", file=sys.stderr); return EXIT_INVALID

    chain = None
    if crypto:
        kind = crypto.subject.kind.value
        if kind == "crypto.btc.address":
            chain = "bitcoin"
        elif kind in ("crypto.evm.address", "crypto.evm.tx"):
            chain = CHAIN_MAP.get(args.chain, "ethereum")
        audit.append({"step": "crypto_detected", "kind": kind, "chain": chain,
                      "normalized": crypto.subject.normalized})
    if bank_sub:
        audit.append({"step": "bank_detected", "kind": bank_sub.subject.kind.value,
                      "normalized": bank_sub.subject.normalized})

    runner = AgentRunner()
    txs, tokens, errors = [], [], []
    if chain:
        txs, errs1 = runner.collect(crypto.subject.normalized, chain)
        errors.extend(errs1)
        if chain != "bitcoin":
            tokens, errs2 = runner.collect_tokens(crypto.subject.normalized, chain)
            errors.extend(errs2)
        audit.append({"step": "collected", "chain": chain,
                      "txs": len(txs), "tokens": len(tokens), "errors": errors})

    matches = []
    if bank_sub and (txs or tokens):
        combined = txs + tokens
        for t in combined:
            if "decimals" not in t:
                t["decimals"] = 18
        matches = correlate(
            {"amount": args.amount, "currency": args.currency,
             "sent_at": args.when, "iban": bank_sub.subject.normalized},
            combined)
    audit.append({"step": "correlated", "matches": len(matches)})

    ass = []
    if crypto:
        explorer = ("https://blockchair.com/bitcoin/transaction/"
                    if chain == "bitcoin"
                    else f"https://{chain}.blockscout.com/tx/")
        for t in (txs + tokens)[:50]:
            if (t.get("from") or "").lower() == crypto.subject.normalized:
                decimals = int(t.get("decimals", 18))
                ass.append(A.Assertion(
                    subject=crypto.subject.normalized, predicate="sent_to",
                    obj=t.get("to"), tier=A.Tier.FACT,
                    source=explorer + t["hash"],
                    evidence={"raw_value": t["value"],
                              "human_value": _human(t["value"], decimals),
                              "symbol": t.get("symbol", "native"),
                              "decimals": decimals,
                              "kind": t.get("kind", "native"),
                              "chain": chain}))

    priv, pub = A.generate_keypair()
    if bank_sub and crypto:
        victim = A.Assertion(
            subject=bank_sub.subject.normalized, predicate="reported_mule",
            obj=crypto.subject.normalized, tier=A.Tier.VICTIM,
            source="victim-statement",
            evidence={"amount": args.amount, "currency": args.currency,
                      "correlation": matches})
        A.sign(victim, priv)
        ass.append(victim)
        audit.append({"step": "victim_signed", "pubkey": pub})

    out = Path(args.out)
    write_bundle(out, ass, meta={"tool": "robert", "version": "0.5.0",
                                 "chain": chain,
                                 "generated_at": int(time.time())},
                 audit=audit, priv=priv)
    print(f"[bundle] {out} ({out.stat().st_size} bytes)")
    print(f"[audit]  head={audit.head()[:16]}... verified={audit.verify()}")
    return EXIT_OK

def build_parser():
    p = argparse.ArgumentParser(prog="robert", description="Robert — evidence engine")
    sub = p.add_subparsers(required=True, dest="cmd")
    d = sub.add_parser("detect", help="classify inputs (bank vs crypto)")
    d.add_argument("inputs", nargs="+"); d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_detect)
    v = sub.add_parser("validate", help="validate a single identifier")
    v.add_argument("input"); v.set_defaults(func=cmd_validate)
    r = sub.add_parser("report", help="build a signed evidence bundle")
    r.add_argument("--address"); r.add_argument("--chain", default="1")
    r.add_argument("--iban"); r.add_argument("--amount", type=float, default=0.0)
    r.add_argument("--currency", default="EUR"); r.add_argument("--when", type=int, default=0)
    r.add_argument("--out", default="robert_bundle.zip")
    r.set_defaults(func=cmd_report)
    return p

def main(argv=None):
    return build_parser().parse_args(argv).func(
        build_parser().parse_args(argv))

if __name__ == "__main__":
    sys.exit(main())
