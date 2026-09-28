"""Deploy Tally to StudioNet and put every path on the explorer.

    pip install genlayer-py==0.18.0
    python scripts/demo.py

The run deploys contracts/tally.py exactly as it is in this repository, then
sends the steps in scripts/demo_data.py (STEPS), including the ones that end
in a refusal, and writes what happened to deployments/studionet.json: every
transaction hash, its status, the refusal sentence where there was one, and
every order, order line and invoice line as the chain holds them. Nothing in
that file is typed by hand.

Why a script and not the genlayer CLI: `genlayer write` cannot attach value to
a call, and open() is payable. genlayer-py's write_contract can.

The three accounts are made in memory for this run and funded from StudioNet's
own faucet. They hold test GEN and nothing else, and no key is written to disk.
"""

import datetime
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent))
import demo_data as D                                       # noqa: E402
from studio import EXPLORER, Studio                         # noqa: E402

ROOT = pathlib.Path(__file__).absolute().parent.parent
SOURCE = ROOT / "contracts" / "tally.py"
OUT = ROOT / "deployments" / "studionet.json"


def utc_seconds(iso):
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return int(t.timestamp())


def wait_past(iso, label):
    """Sleep until the chain clock has passed `iso`, with a margin, because
    the contract compares against the time of the transaction that arrives."""
    target = utc_seconds(iso) + 20
    left = target - int(time.time())
    if left > 0:
        print(f"  waiting {left}s for {label} ({iso})")
        time.sleep(left)


def args_for(method, spec, supplier):
    if method == "open":
        title, lines, valid_for = spec
        descs, qtys, prices = D.joined(lines)
        return [title, supplier, descs, qtys, prices, valid_for], D.total(lines)
    if method == "invoice":
        oid, lines = spec
        descs, qtys, prices = D.joined(lines)
        return [oid, descs, qtys, prices], 0
    return list(spec), 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = SOURCE.read_text(encoding="utf-8")
    s = Studio()

    print("\naccounts (in memory, StudioNet test GEN only)")
    who = {
        "buyer": s.account("buyer", gen=5),
        "supplier": s.account("supplier"),
        "stranger": s.account("stranger"),
    }
    before = {name: s.balance(a.address) for name, a in who.items()}

    print("\ndeploy")
    address = s.deploy(who["buyer"], code, [D.GRACE_SECONDS])

    print("\nthe demo")
    for step in D.STEPS:
        actor, method, spec, expect, label = step[:5]
        if "after_end" in step[5:]:
            wait_past(s.read(address, "order", [spec[0]])["ends_at"], f"order {spec[0]} to end")
        args, value = args_for(method, spec, who["supplier"].address)
        s.write(who[actor], address, method, args, value=value, step=label, expect=expect)

    n = int(s.read(address, "count"))
    orders = [{
        "order": s.read(address, "order", [k]),
        "lines": s.read(address, "lines_of", [k])["lines"],
        "invoices": s.read(address, "invoices_of", [k])["invoices"],
    } for k in range(n)]
    record = {
        "network": "studionet",
        "chain_id": 61999,
        "contract": address,
        "explorer": f"{EXPLORER}/address/{address}",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "constructor": {"grace_seconds": D.GRACE_SECONDS},
        "accounts": {name: a.address for name, a in who.items()},
        "balances_before": {name: str(v) for name, v in before.items()},
        "held_after": str(s.read(address, "held_total")),
        "steps": s.log,
        "orders": orders,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")

    print(f"\n  contract   {address}")
    print(f"  explorer   {EXPLORER}/address/{address}")
    for k, o in enumerate(orders):
        print(f"  order {k}  {o['order']['status']:<10} paid {int(o['order']['paid']) / D.GEN:.3f} GEN  "
              f"refunded {int(o['order']['refunded']) / D.GEN:.3f} GEN  "
              f"matches {[ '|'.join(l['match'] for l in inv['lines']) for inv in o['invoices'] ]}")
    print(f"  held       {record['held_after']} wei")
    print(f"  written    {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
