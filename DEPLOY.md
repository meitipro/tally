# Deploying Tally

Everything here runs on StudioNet. It is gasless, but `open()` is payable, so
the buyer needs StudioNet test GEN. `scripts/demo.py` takes it from StudioNet's
own faucet. Nothing needs a private key in a file.

## 1 - Check the contract

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python scripts/schema_check.py contracts/tally.py
GENVM_VERSION=v0.3.0-rc7 genvm-lint check contracts/tally.py
```

`schema_check.py` runs the file through the live studionet runtime with
`gen_getContractSchemaForCode`, without deploying it. On Windows, set
`PYTHONIOENCODING=utf-8` first, or the linter dies printing its own tick.

## 2 - Run the demo

```bash
python scripts/demo.py
```

The genlayer CLI cannot attach value to a write, and `open()` is payable, so
the demo uses genlayer-py, whose `write_contract` takes `value`. It makes three
accounts in memory (`buyer`, `supplier`, `stranger`), funds the buyer with 5
test GEN, and deploys `contracts/tally.py` exactly as it is in this repository,
with a grace window of 300 seconds.

The data and the steps are in [`scripts/demo_data.py`](scripts/demo_data.py);
the same list drives the demo and `tests/test_runbook.py`. The order:

| Order line | Quantity | Unit price |
|---|---|---|
| [0] A4 copier paper, 80 gsm, box of 5 reams | 10 | 0.05 GEN |
| [1] Black toner cartridge for HP LaserJet M404 | 2 | 0.2 GEN |
| [2] Full-strip metal desk stapler | 3 | 0.02 GEN |

The writes, in order:

| # | From | Call | Expected |
|---|---|---|---|
| 1 | buyer | `open(office supplies, 3 lines, 3600)` with 0.96 GEN | ok: order 0 |
| 2 | buyer | `open(printer service visit, 1 line, 300)` with 0.1 GEN | ok: order 1, five minutes |
| 3 | stranger | `close(1)` | refused: the order runs until its end |
| 4 | buyer | `open(spare toner, 1 line, 3600)` with 0.2 GEN | ok: order 2 |
| 5 | stranger | `invoice(0, ...)` | refused: only the supplier may invoice |
| 6 | supplier | `invoice(0, paper x6, toner x2, desk lamp x1)` | ok |
| 7 | supplier | `invoice(0, ...)` | refused: an invoice is waiting |
| 8 | stranger | `match(0)` | refused: only the buyer or the supplier |
| 9 | buyer | `match(0)` | ok: `0\|1\|none`, paper and toner paid, the lamp was never ordered |
| 10 | supplier | `invoice(0, <invoice 1 again>)` | refused: already matched |
| 11 | supplier | `invoice(0, paper x5, stapler x3 at 0.025)` | ok |
| 12 | supplier | `match(0)` | ok: `0\|2`, **over_quantity** and **overpriced**, nothing paid |
| 13 | supplier | `invoice(0, paper x4, stapler x3 at 0.018)` | ok |
| 14 | buyer | `match(0)` | ok: both accepted, order 0 fulfilled, 0.006 GEN back to the buyer |
| 15 | supplier | `release(2)` | ok: order 2's 0.2 GEN back to the buyer |
| 16 | stranger | `close(1)` after its end | ok: order 1's 0.1 GEN back to the buyer |

The script waits order 1's window out before the last step, and stops at the
first step that does not do what the table says, because the demo claims
whatever it records.

It writes [`deployments/studionet.json`](deployments/studionet.json): every
transaction hash, its status, each refusal's sentence, and every order, order
line and invoice line as the chain holds them. Then:

```bash
pytest tests/test_runbook.py -v
```

`TestTheRecord` replays the matches the validators agreed on through this
repository's contract and fails unless it pays and refunds exactly what the
deployed one did, and refuses exactly where it refused.

## 3 - Reads - free, no transaction

```bash
genlayer network set studionet
genlayer call <address> count
genlayer call <address> order --args 0
genlayer call <address> lines_of --args 0
genlayer call <address> invoices_of --args 0
genlayer call <address> held_total
```

## 4 - Before the portal

```bash
python scripts/verify_deployment.py <address>
python scripts/measure.py --write
```

The first reads the deployed source back off chain, compares it with
`contracts/tally.py` and lints the deployed bytes. The second runs the suite
and the mutation pass and writes the measured numbers and the live record into
README.md. Neither writes anything unless every check passes.
