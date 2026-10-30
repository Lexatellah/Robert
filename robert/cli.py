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

def _print_subject(s, stream=sys.stdout):
    print(f"CLASS      {s.label()}", file=stream)
    print(f"  raw          {s.raw}", file=stream)
    print(f"  normalized   {s.normalized}", file=stream)
    if s.jurisdiction:
        print(f"  jurisdiction {s.jurisdiction}", file=stream)
    if s.checksum_valid is not None:
        print(f"  checksum     {'valid' if s.checksum_valid else 'INVALID'}",
              file=stream)
    print(f"  confidence   {s.confidence:.2f}", file=stream)
    for n in s.notes:
        print(f"  note         {n}", file=stream)
    if s.asset_class.value == "bank":
        print("  => this is a BANK identifier, not a crypto address", file=stream)
    elif s.asset_class.value == "crypto":
        print(f"  => this is a CRYPTO identifier on {s.chain}", file=stream)

def cmd_detect(args):
    rc = EXIT_OK
    results = []
    for raw in args.inputs:
        r = detect(raw)
        results.append(r)
        if args.json:
            continue
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
        print(f"INVALID: {r.error}", file=sys.stderr)
        return EXIT_INVALID
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
        print(f"address rejected: {crypto.error}", file=sys.stderr)
        return EXIT_INVALID
    if bank_sub and (not bank_sub.ok() or bank_sub.subject.checksum_valid is False):
        print("IBAN rejected", file=sys.stderr)
        return EXIT_INVALID

    if crypto:
        audit.append({"step": "crypto_detected", "kind": crypto.subject.kind.value,
                      "normalized": crypto.subject.normalized})
    if bank_sub:
        audit.append({"step": "bank_detected", "kind": bank_sub.subject.kind.value,
                      "normalized": bank_sub.subject.normalized})

    chain = CHAIN_MAP.get(args.chain, "ethereum")
    txs, errors = [], []
    if crypto and crypto.subject.kind.value in ("crypto.evm.address", "crypto.evm.tx"):
        runner = AgentRunner()
        txs, errors = runner.collect(crypto.subject.normalized, chain)
        audit.append({"step": "collected", "chain": chain, "count": len(txs),
                      "errors": errors})
        if not txs:
            try:
                bal = RPC.get_balance(crypto.subject.normalized, chain)
                audit.append({"step": "rpc_balance", "wei": bal})
            except Exception as e:
                audit.append({"step": "rpc_balance_failed", "error": str(e)})

    matches = []
    if bank_sub and txs:
        matches = correlate(
            {"amount": args.amount, "currency": args.currency,
             "sent_at": args.when, "iban": bank_sub.subject.normalized},
            txs)
    audit.append({"step": "correlated", "matches": len(matches)})

    ass = []
    if crypto:
        for tx in txs[:50]:
            if tx.get("from", "").lower() == crypto.subject.normalized:
                ass.append(A.Assertion(
                    subject=crypto.subject.normalized, predicate="sent_to",
                    obj=tx.get("to"), tier=A.Tier.FACT,
                    source=f"https://{chain}.blockscout.com/tx/{tx['hash']}",
                    evidence={"value": tx["value"], "hash": tx["hash"], "chain": chain}))
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
    write_bundle(out, ass, meta={"tool": "robert", "version": "0.3.0",
                                 "chain": chain,
                                 "generated_at": int(time.time())},
                 audit=audit, priv=priv)
    print(f"[bundle] {out} ({out.stat().st_size} bytes)")
    print(f"[audit]  head={audit.head()[:16]}... verified={audit.verify()}")
    return EXIT_OK

def build_parser():
    p = argparse.ArgumentParser(prog="robert",
                                description="Robert — evidence engine")
    sub = p.add_subparsers(required=True, dest="cmd")

    d = sub.add_parser("detect", help="classify inputs (bank vs crypto)")
    d.add_argument("inputs", nargs="+")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_detect)

    v = sub.add_parser("validate", help="validate a single identifier")
    v.add_argument("input")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("report", help="build a signed evidence bundle")
    r.add_argument("--address")
    r.add_argument("--chain", default="1")
    r.add_argument("--iban")
    r.add_argument("--amount", type=float, default=0.0)
    r.add_argument("--currency", default="EUR")
    r.add_argument("--when", type=int, default=0)
    r.add_argument("--out", default="robert_bundle.zip")
    r.set_defaults(func=cmd_report)
    return p

def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
