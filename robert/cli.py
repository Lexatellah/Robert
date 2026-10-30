import argparse, json, sys, time
from pathlib import Path
from robert import assertions as A
from robert import bank
from robert.agents.runner import AgentRunner, RPC
from robert.correlate import correlate
from robert.bundle import write_bundle

CHAIN_MAP = {"1": "ethereum", "8453": "base", "42161": "arbitrum",
             "10": "optimism", "137": "polygon"}

def cmd_report(args):
    iban = bank.normalize_iban(args.iban)
    if not bank.iban_is_valid(iban):
        sys.exit("IBAN fails mod-97 check")
    print(f"[bank] IBAN {iban} valid, country={bank.iban_country(iban)}")

    chain_name = CHAIN_MAP.get(args.chain, "ethereum")
    runner = AgentRunner()
    print(f"[agents] collecting {chain_name} history for {args.address} ...")
    txs, errors = runner.collect(args.address, chain_name)
    if not txs:
        print("[agents] no tx history; trying balance only")
        try:
            bal = RPC.get_balance(args.address, chain_name)
            print(f"[rpc] balance = {bal / 10**18:.6f} native")
        except Exception as e:
            print(f"[rpc] balance failed too: {e}")

    bank_leg = {"amount": float(args.amount), "currency": args.currency,
                "sent_at": int(args.when), "iban": iban}
    matches = correlate(bank_leg, txs)
    print(f"[correlate] {len(matches)} candidate match(es)")
    for m in matches:
        print("   ", json.dumps(m))

    ass = []
    for tx in txs[:50]:
        if tx.get("from") and tx["from"].lower() == args.address.lower():
            ass.append(A.Assertion(
                subject=args.address, predicate="sent_to", obj=tx.get("to"),
                tier=A.Tier.FACT,
                source=f"https://{chain_name}.blockscout.com/tx/{tx['hash']}",
                evidence={"value": tx["value"], "hash": tx["hash"], "chain": chain_name},
            ))

    priv, pub = A.generate_keypair()
    victim = A.Assertion(
        subject=iban, predicate="reported_mule", obj=args.address,
        tier=A.Tier.VICTIM, source="victim-statement",
        evidence={"amount": args.amount, "currency": args.currency, "correlation": matches},
    )
    A.sign(victim, priv)
    ass.append(victim)
    print(f"[sign] victim report signed with pubkey {pub[:16]}...")

    out = Path(args.out)
    write_bundle(out, ass, meta={"tool": "robert", "version": "0.1.0",
                                 "chain": chain_name, "agent_errors": errors,
                                 "generated_at": int(time.time())})
    print(f"[bundle] wrote {out}  ({out.stat().st_size} bytes)")

def main():
    p = argparse.ArgumentParser(prog="robert")
    sub = p.add_subparsers(required=True)
    r = sub.add_parser("report")
    r.add_argument("--address", required=True)
    r.add_argument("--chain", default="1")
    r.add_argument("--iban", required=True)
    r.add_argument("--amount", required=True)
    r.add_argument("--currency", default="EUR")
    r.add_argument("--when", required=True)
    r.add_argument("--out", default="robert_bundle.zip")
    r.set_defaults(func=cmd_report)
    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
