# Submission

One submission, under **Builder -> Intelligent Contracts**. This repository is
one standalone primitive.

---

## Before you submit, in order

1. **Measure, do not estimate.**

   ```bash
   python scripts/measure.py --write
   ```

   Runs the suite and the full mutation pass, renders the live record, and
   writes all three into README.md. It refuses to write anything if the suite
   is red, a mutation escapes, or the record is of a different contract file.

2. **Prove the address is evidence for this repository.**

   ```bash
   python scripts/verify_deployment.py <address>
   ```

   Reads the source back off chain, compares it with `contracts/tally.py` and
   runs `genvm-lint check` on those bytes. A submission is judged on the
   deployed source, so a correct repository proves nothing on its own if the
   address points at an earlier draft.

3. **Open the explorer page and check it.** It must show the deploy, the three
   matches with a consensus result beside them, the release, the close, and the
   five refusals, each with its reason.

---

## On chain

The address, every transaction, every match and every payment are in the
[README](README.md#it-is-live-and-every-path-is-on-chain), rendered from
[`deployments/studionet.json`](deployments/studionet.json), and every
transaction with the wallet that sent it is in [EVIDENCE.md](EVIDENCE.md).

## What to say in the portal

**What it does.** Tally is a purchase order with its money in it. The buyer
freezes the order's lines, quantities and unit prices and pays the whole order
in; the supplier invoices against it; validators decide, for each invoice line,
which order line it bills or none, reading descriptions only, in both
presentation orders. The contract then checks the quantity against what is
still open and the price against the price agreed, and pays every line that
passes in the same transaction.

**Why it needs GenLayer.** Deciding that "Copy paper A4 80g, 5-ream box" is
"A4 copier paper, 80 gsm, box of 5 reams" is a judgment in natural language
that neither party can be trusted to make for the other, and a single
off-chain model call is a party too. Independent validators must agree on
every line before any money moves, and the money moves in the same contract,
on arithmetic anyone can re-run.

**What it learned from earlier work.** The model is asked for an index into a
list the contract holds, never an amount; it is never shown a quantity or a
price. The uncertainty goes into the value (an order-dependent match is none,
and none is not paid) instead of into the comparison. Every waiting state has
a clock, and money moves at the root of the transaction.
