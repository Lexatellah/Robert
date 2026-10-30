"""Minimal Robert web UI. Local only. Not for production."""
from flask import Flask, request, render_template_string
from robert import assertions as A, bank, security
from robert.agents.runner import AgentRunner
from robert.correlate import correlate

app = Flask(__name__)

PAGE = """
<!doctype html><title>Robert</title>
<style>body{font-family:monospace;max-width:820px;margin:2em auto;padding:1em}
input{width:100%;padding:.4em;margin:.2em 0}pre{background:#f4f4f4;padding:1em;overflow:auto}</style>
<h2>Robert — evidence engine</h2>
<form method=post>
  Address <input name=address value="{{address}}">
  IBAN    <input name=iban value="{{iban}}">
  Amount  <input name=amount value="{{amount}}">
  When    <input name=when value="{{when}}">
  <button>Run report</button>
</form>
{% if error %}<pre style="color:#b00">{{error}}</pre>{% endif %}
{% if out %}<pre>{{out}}</pre>{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    ctx = {"address": "", "iban": "", "amount": "0.05", "when": "1730000000",
           "out": None, "error": None}
    if request.method == "POST":
        try:
            addr = security.validate_address(request.form["address"])
            iban = bank.normalize_iban(security.clean(request.form["iban"], "iban"))
            if not bank.iban_is_valid(iban):
                raise ValueError("IBAN fails mod-97")
            amount = float(request.form["amount"])
            when = int(request.form["when"])
            ctx.update(address=addr, iban=iban, amount=amount, when=when)

            txs, errors = AgentRunner().collect(addr, "ethereum")
            matches = correlate(
                {"amount": amount, "currency": "EUR", "sent_at": when, "iban": iban},
                txs,
            )
            lines = [
                f"IBAN valid: {iban} ({bank.iban_country(iban)})",
                f"Transactions fetched: {len(txs)}",
                f"Agent errors: {errors or 'none'}",
                f"Candidate matches: {len(matches)}",
            ]
            for m in matches[:10]:
                lines.append(f"  {m['tx_hash'][:18]}...  {m['value']}  {m['time']}")
            ctx["out"] = "\n".join(lines)
        except Exception as e:
            ctx["error"] = f"{type(e).__name__}: {e}"
    return render_template_string(PAGE, **ctx)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
