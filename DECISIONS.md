# DECISIONS

Why Tally is built the way it is. Each section names the alternative that was
rejected and what it would have cost.

## The model is asked which line, never how much

The obvious design asks "how much of this invoice should be paid?" and stores
the number. It hands the model two jobs at once, recognising items and doing
arithmetic, and the second is the one models are worst at and the one nobody
can audit afterwards. A model that is slightly generous about a quantity pays
the supplier for goods that were never ordered.

So the model answers an index into a list the contract already holds: for each
invoice line, which order line it bills, or none. The quantity check, the
price check, the running count of what is still open and the payment are all
the contract's own arithmetic, in the same transaction, from storage the block
never saw. `tests/test_e2e.py::TestStorageShape::test_quantities_and_prices_never_enter_the_block`
fails if a quantity or a price is ever passed into the block, and
`test_the_model_is_never_shown_a_quantity_or_a_price` checks every prompt of a
real match.

## Both lists are reversed together

A match between two lists has two position biases: the model may prefer the
first order line, and it may read the first invoice line more carefully. The
reversed pass reverses **both** lists and renumbers both, and `unreverse()`
maps the answer back on both axes: slot *i* of the reversed answer is invoice
line *m-1-i*, and order row *k* in it is order row *n-1-k*. Reversing only
one list would test one bias and hide the other.

## A match that depends on the order is none, and none is not paid

When the two orders disagree about a line, the folded value is `none`. The
alternatives were to keep the forward answer (the bias the reversed pass exists
to catch would decide), or to split the difference (there is no half of a
toner cartridge). `none` costs the supplier one more invoice, described so the
item can be recognised; paying for an item nobody could defend costs the
buyer money that does not come back.

## Overpriced and over-quantity lines are refused, not trimmed

A line billing 5 boxes when 4 are open could be paid for 4. It is refused
whole instead: an invoice is the supplier's statement of what it delivered, and
silently paying a different amount than it asked would make the record say
something neither party said. The supplier invoices what is open, at the
agreed price, and the record shows both attempts. A line below the agreed
price is paid at the invoiced price, and the difference returns to the buyer
when the order is fulfilled or closed.

## Lines are priced in the order invoiced

`price_lines()` reduces what is open on an order line before it looks at the
next invoice line, so two lines on one invoice (or two invoices) can never be
paid for the same units. The order is the supplier's own, so there is nothing
for anyone to argue about in it.

## The whole order is paid in at open

An order that is only partly funded turns every match into a question of
whether the money is there. Requiring `value == sum(quantity x price)` makes
every accepted line payable at once, and makes `held_total()` equal the
contract's balance while the accounting is right.

## One invoice waits at a time, at most four per order

A waiting invoice is the only thing `match()` reads, so no invoice id is taken
and none can be matched out of turn. Four invoices bound the work a supplier
can create on one order, and the same invoice (same lines, same quantities,
same prices, whatever the spacing or capitals) is refused once it has been
matched.

## Every waiting state has a clock

`close()` is open to anyone after `ends_at`, and returns to the buyer whatever
no invoice can claim any more. An invoice filed in time holds the order open
for a grace window frozen at deploy, so a supplier who invoiced on the last day
is not closed out before either party could ask for the match; after the grace,
the waiting invoice lapses unpaid. Nothing can hold the buyer's money forever.

## Money moves at the root of the transaction

Every payout goes through `_send()`, which checks it against the `held`
counter and then sends through the external EVM message form with `value`
only, the form Tranche and Recourse pay with on studionet. The state is written
first: `match()` records what was paid before it pays it, and `_end()` records
the refund before it sends it. A static test pins both orders.

## invoice() and match() are two transactions

The invoice is on the record, with the chain's time on it, whatever happens to
the match. A match that never reaches consensus leaves the invoice waiting and
the money where it was.

## Tagging untrusted text is not a fence

Descriptions are caller text on both sides. `fence()` replaces `< > [ ]` at the
prompt boundary, and the contract labels the rows itself: `[0]` for order
lines, `[I0]` for invoice lines. A description carrying `[1]` or `</invoice>`
cannot forge a row or close a block. Storage keeps what was submitted. A static
test fails on any value interpolated into the prompt that is neither fenced nor
the contract's own.

## The reason string is leader-supplied

`because` is shown next to each invoice, sanitised and capped, and is not part
of consensus: two honest readers describe the same match differently, and
comparing prose would stall every match. Nothing in the contract acts on it,
and the view says so.

## Why the tests are built the way they are

- **Each node gets its own answers**, so a contract that assumes both nodes read the same thing is caught offline.
- **A leader can lie**, so the validator's checks are reachable, and the free layer is measured: a malformed proposal must cost the validator zero prompts.
- **The runbook is a test.** The demo is replayed offline from `scripts/demo_data.py` before a transaction is spent, and once `deployments/studionet.json` exists the validators' real matches are replayed through this file, which must pay and refund exactly what the deployed contract did.
- **Mutation testing.** `scripts/mutate.py` removes each defence and names the test that caught it.

## GenVM constraints this contract obeys

- the runner is pinned (`py-genlayer:1jb45aa8...`), never `test` or `latest`
- the class is named after the product, because `genvm-lint validate` does not see a class named `Contract`
- no `int`, `list`, `dict` or `tuple` as a storage type, and no collection inside a storage dataclass; lines are contiguous rows, invoices are linked
- every persistent field is declared in the class body, and every stored field is read somewhere
- the block returns a flat dict of strings
- `gl.nondet` is reached only from `read_once`, called only from inside the block
- the file is pure ASCII
- `genvm-lint` validates against GenVM `v0.3.0-rc7`, the release that ships the pinned runner; `scripts/verify_deployment.py` sets `GENVM_VERSION` accordingly
- `scripts/schema_check.py` validates the file against the live studionet runtime with `gen_getContractSchemaForCode` before a deploy is spent

## Not upgradable

There is no owner and no admin method. An order's lines, quantities and prices
are frozen at `open()`, and a match on record stays the match.
