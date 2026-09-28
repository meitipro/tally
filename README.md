# Tally - an invoice is paid line by line, only for what the order ordered

A GenLayer Intelligent Contract for paying invoices against a purchase order.
The buyer opens an order with its lines (what, how many, at what unit price)
and pays the whole order in. The supplier invoices against it. Validators
decide **one thing per invoice line: which order line it bills, or none**. The
contract then does what an accounts payable clerk does by hand, in code: it
checks the quantity against what is still open, checks the price against the
price agreed, and pays the supplier for every line that passes, in the same
transaction. The model is never shown a quantity or a price.

- **Contract:** [`contracts/tally.py`](contracts/tally.py)
- **Tests:** `pip install pytest && pytest tests/ -q` - nothing else to install
- **Deployed:** see [It is live](#it-is-live-and-every-path-is-on-chain) below, and [`deployments/studionet.json`](deployments/studionet.json)
- **Every transaction and the wallet that sent it:** [EVIDENCE.md](EVIDENCE.md), read back from the chain
- **Run the demo yourself:** [DEPLOY.md](DEPLOY.md)
- **Verify a deployment:** `python scripts/verify_deployment.py 0x...` - compares the on-chain source with this file and lints it
- **Decisions:** [DECISIONS.md](DECISIONS.md)
- **License:** MIT

---

## It is live, and every path is on chain

<!-- measured:deployment:start -->
Deployed on studionet at [`0xd8083238c9b62e06A793cc7a0d663E34d77B8639`](https://explorer-studio.genlayer.com/address/0xd8083238c9b62e06A793cc7a0d663E34d77B8639) (deploy [`0xf794fd38...`](https://explorer-studio.genlayer.com/tx/0xf794fd389d116676378edde3628749d76bdbf9df659ebf35bc58466e9aa71b2e)), with a grace window of 300 s. Every value below was read back from the chain by `scripts/demo.py` and written to [`deployments/studionet.json`](deployments/studionet.json); none of it is typed by hand.

| Order | Ended | Paid to the supplier | Returned to the buyer |
|---|---|---|---|
| 0: Office supplies for the Harbour branch, Q4 | fulfilled | 0.954 GEN | 0.006 GEN |
| 1: Printer service visit, Harbour branch | closed | 0 GEN | 0.1 GEN |
| 2: Spare toner for the second office | released | 0 GEN | 0.2 GEN |

Every invoice line, what the validators matched it to, and what the contract decided:

| Invoice | Line | Qty | Unit price | Matched to order line | Decided | Paid |
|---|---|---|---|---|---|---|
| order 0, invoice 1 | Copy paper A4 80g, 5-ream box | 6 | 0.05 GEN | [0] A4 copier paper, 80 gsm, box of 5 reams | **accepted** | 0.3 GEN |
| order 0, invoice 1 | HP LaserJet M404 black toner cartridge | 2 | 0.2 GEN | [1] Black toner cartridge for HP LaserJet M404 | **accepted** | 0.4 GEN |
| order 0, invoice 1 | LED desk lamp with USB charging port | 1 | 0.1 GEN | none | **unmatched** | 0 GEN |
| order 0, invoice 2 | Copy paper A4 80 gsm, box of five reams | 5 | 0.05 GEN | [0] A4 copier paper, 80 gsm, box of 5 reams | **over_quantity** | 0 GEN |
| order 0, invoice 2 | Metal stapler, full strip | 3 | 0.025 GEN | [2] Full-strip metal desk stapler | **overpriced** | 0 GEN |
| order 0, invoice 3 | Copier paper, A4, 80 gsm (5 reams per box) | 4 | 0.05 GEN | [0] A4 copier paper, 80 gsm, box of 5 reams | **accepted** | 0.2 GEN |
| order 0, invoice 3 | Full strip metal stapler for desks | 3 | 0.018 GEN | [2] Full-strip metal desk stapler | **accepted** | 0.054 GEN |

Every transaction, in order, refusals included:

| Step | Outcome | Transaction |
|---|---|---|
| order 0 opened: office supplies, three lines | ok | [`0x2c7289e4...`](https://explorer-studio.genlayer.com/tx/0x2c7289e460bd06f99e8c6a865c96283258112cfbc331e8d80a82ceb94571ac57) |
| order 1 opened: runs five minutes | ok | [`0x1b460f3e...`](https://explorer-studio.genlayer.com/tx/0x1b460f3e6018886c07bcee0cfd7cbc8d3c14c9e4efb5e74846b0631ccdc7fe8b) |
| order 1 closed before it ends | refused: the order runs until 2026-09-28T01:52:59Z | [`0xfe6b986c...`](https://explorer-studio.genlayer.com/tx/0xfe6b986c2db0a8b03c37acaa59a0ded63f97afd8a6b5d6dc9d953bac3ab30ece) |
| order 2 opened: spare toner | ok | [`0x6deed466...`](https://explorer-studio.genlayer.com/tx/0x6deed466d5b494385d6f5775eaf3bcd686b5d0a94829460406bb0d7bef0d2e21) |
| a stranger invoices order 0 | refused: only the supplier may invoice this order | [`0x67e14aa2...`](https://explorer-studio.genlayer.com/tx/0x67e14aa2bce717d7fe42992f4ae892d13c60f1becc1d157f9dd533fd6892233c) |
| invoice 1: paper, toner and a desk lamp | ok | [`0x76646096...`](https://explorer-studio.genlayer.com/tx/0x766460965508af9fb83b53b5723f5ef3cd76ae0f2920ea748de60e2dc04f9a25) |
| a second invoice while one waits | refused: an invoice is waiting to be matched; either party may ask for it | [`0xf7a34208...`](https://explorer-studio.genlayer.com/tx/0xf7a34208683f23b8d0c04a1e9ed2b5a0309e6e8ddd32a578d376f1557ba29a7a) |
| a stranger asks for the match | refused: only the buyer or the supplier may ask for a match | [`0xb16e9628...`](https://explorer-studio.genlayer.com/tx/0xb16e96284fbb6a04031feb85b8cd629549bdc65863b3c91ea734dde2aedca20a) |
| matched: paper and toner paid, the lamp was never ordered | ok | [`0x0b579264...`](https://explorer-studio.genlayer.com/tx/0x0b57926409c3a61324a11cc3284f3152210e857dcc3a1047bbec77574e00df59) |
| the same invoice again | refused: this invoice was already matched as invoice 1; change it to invoice what is still open | [`0x61fbde1e...`](https://explorer-studio.genlayer.com/tx/0x61fbde1e0236140372459cb57b7ad6ad462daf04f0f9bd55a45ebff64efaea8f) |
| invoice 2: too much paper, stapler above price | ok | [`0xea60781b...`](https://explorer-studio.genlayer.com/tx/0xea60781b87ee7c5bac4323161ae6fa347405a98b068ee70001e1936cab226646) |
| matched: both lines refused by the arithmetic | ok | [`0x12aca38f...`](https://explorer-studio.genlayer.com/tx/0x12aca38f3ef0437c5784c332b3a9447d7a03db8598ab26246fadac4fdebf6ae8) |
| invoice 3: the rest, stapler below price | ok | [`0x2ad3401f...`](https://explorer-studio.genlayer.com/tx/0x2ad3401fe0cf99d87eb74c2171746db86b2877491c817aa0107a2849ea186499) |
| matched: order 0 fulfilled, the difference back | ok | [`0x9209ca46...`](https://explorer-studio.genlayer.com/tx/0x9209ca46230c69fc15481254d46ee15a12ec1f163f7671b16fd07f3d94de1cee) |
| order 2 released by the supplier | ok | [`0xe207bded...`](https://explorer-studio.genlayer.com/tx/0xe207bdedbfe27eebce1cf50039ce9fab4900a9299cd1416e6cb33e930b243d5c) |
| order 1 closed after it ended | ok | [`0x12ff7f7f...`](https://explorer-studio.genlayer.com/tx/0x12ff7f7fbe498c86dbcd7e912aa91a34d45517b7dd90440b589cbde2a0593365) |

After the last step the contract holds `0` wei for live orders.
`tests/test_runbook.py::TestTheRecord` replays these matches through this repository's contract and fails unless it pays and refunds exactly what the deployed one did.
<!-- measured:deployment:end -->

## The problem

Matching an invoice to a purchase order is the dullest dispute in commerce and
one of the most expensive. The invoice says "Copy paper A4 80g, 5-ream box",
the order says "A4 copier paper, 80 gsm, box of 5 reams", and a person has to
decide that these are the same thing before anyone can check a single number.
That judgment is why invoices wait thirty days, and why suppliers get paid for
the lines nobody argues about weeks after they were delivered.

Asking a model "should this invoice be paid?" does not fix it. It hands the
model the judgment **and** the arithmetic, and gets back an amount nobody can
audit. Tally splits them: the model answers the one question a clerk actually
needs help with, *which line is this*, and everything that can be counted is
counted by the contract.

## How consensus is used

The block sees the order's numbered lines and the invoice's labelled lines,
**descriptions only**, and gives one token per invoice line: the number of the
order line it bills, or `none`.

```
<order>                                   <invoice>
[0] A4 copier paper, 80 gsm, box of 5     [I0] Copy paper A4 80g, 5-ream box
[1] Black toner cartridge for HP ... M404 [I1] HP LaserJet M404 black toner cartridge
[2] Full-strip metal desk stapler         [I2] LED desk lamp with USB charging port

answer: {"matches": "0|1|none", "because": "..."}
```

### Both orders, both lists reversed together

The leader asks **twice**: once in the filed order, and once with the order
lines and the invoice lines both reversed and renumbered, and maps the second
answer back. The same order line in both orders stands; anything else is
`none`. A match that depends on where a line happened to sit in a list is not
a match anyone could defend, and an unmatched line is simply not paid: the
supplier can invoice it again, described so it can be recognised. The
uncertainty goes into the **value**, never into the comparison.

### The validator, in two layers

1. **Structural, and free.** One slot per invoice line, each `none` or an order
   line that exists. A malformed vector is refused before the validator spends
   a single prompt.
2. **Exact agreement on the whole vector.** The validator asks both orders
   itself and compares. The vector decides what is paid, so two nodes that
   agree on it cannot pay different amounts.

An unusable answer is retried once inside the block and then raised as
`[LLM_ERROR]`, which a validator never agrees with, so a broken model can never
pay anyone. There is no equivalence principle and no tolerance anywhere.

## What the contract decides, not the model

For each invoice line, in the order invoiced:

| The validators said | The contract checks | Outcome | Paid |
|---|---|---|---|
| `none` | - | **unmatched** | nothing |
| order line *k* | unit price above line *k*'s agreed price | **overpriced** | nothing |
| order line *k* | quantity above what is still open on line *k* | **over_quantity** | nothing |
| order line *k* | otherwise | **accepted** | quantity x invoiced price, now |

An accepted line reduces what is still open on its order line **before the
next line is looked at**, so two lines, or two invoices, can never be paid for
the same units. When nothing is open on any line the order is **fulfilled**,
and whatever the supplier invoiced below the agreed prices goes back to the
buyer in the same transaction.

## The state machine

```
open       invoices may be filed until ends_at; one waits at a time, at most four
fulfilled  every unit ordered has been paid for; terminal
closed     released by the supplier, or closed after ends_at; the rest went back to the buyer
```

### Every way out

| Situation | Route |
|---|---|
| a line is unmatched | invoice it again, described so its order line can be recognised |
| a line is overpriced or over the open quantity | invoice it again at the agreed price, or for what is still open |
| the match is thought wrong | appeal the `match` transaction on the network |
| nobody asks for the match | `close()` after `ends_at` plus the grace window frozen at deploy; the waiting invoice lapses unpaid |
| the supplier cannot deliver | `release()` returns the rest to the buyer now |
| the same invoice again | refused: it was already matched |

## Who may write

| Method | Caller | Why |
|---|---|---|
| `open(title, supplier, descriptions, quantities, unit_prices, valid_for)` | anyone, paying the whole order in | the caller becomes the buyer |
| `invoice(id, descriptions, quantities, unit_prices)` | the supplier, before `ends_at` | the only party that bills |
| `match(id)` | the buyer or the supplier | one wants to be paid, the other wants it done |
| `release(id)` | the supplier | giving the rest back is the supplier's to offer |
| `close(id)` | anyone, deliberately, after `ends_at` | it reads no model and can only return what no invoice can claim any more; a party who vanishes must not hold the money |

`tests/test_e2e.py::TestStorageShape::test_every_gated_write_checks_the_sender`
walks the parsed source and fails on any write that does not refuse a wrong
sender, except the two above, whose reasons are written in the test.

## The API

| View | Returns |
|---|---|
| `count()` | number of orders |
| `status(id)` | `open`, `fulfilled` or `closed`: one word for another contract |
| `order(id)` | parties, status, funded, paid, refunded, still held, deadlines |
| `lines_of(id)` | every order line with its agreed price and what is still open |
| `invoices_of(id)` | every invoice, line by line: what it was matched to, what the contract decided, what it paid |
| `held_total()` | wei owed to live orders; equals the contract's balance while the accounting is right |

### Using it from another contract

```python
tally = gl.get_contract_at(Address(TALLY))
if tally.view().status(order_id) != "fulfilled":
    raise gl.vm.UserError("[EXPECTED] the order is not fulfilled yet")
```

## Running the tests

```bash
pip install pytest
pytest tests/ -q
```

<!-- measured:tests:start -->
Measured: **141 passed**, 1 skipped. The skipped tests are the opt-in StudioNet integration tests, which run with `GENLAYER_STUDIO=1`.
<!-- measured:tests:end -->

The suite runs on [`tests/glsim.py`](tests/glsim.py), a small GenVM stand-in
that executes the real contract file, gives the leader and the validator their
own mock answers, can make a leader lie, rolls back storage and value
transfers on a refusal, and refuses what GenVM refuses.

- [`tests/test_logic.py`](tests/test_logic.py) - the pure rules: parsing counts, the answer vector, the un-reversal of both lists, the fold, the structural check, the agreement, the pricing table, the fence and the prompt, and that `lib/tally_consensus.py` is the contract's own code
- [`tests/test_e2e.py`](tests/test_e2e.py) - the contract executed: payment in and out to the wei, the arithmetic the model never sees, order-dependence, a lying leader (a malformed one costs the validator zero prompts), `[LLM_ERROR]` never agreed with, the ways out, and static checks over the parsed source
- [`tests/test_runbook.py`](tests/test_runbook.py) - the demo replayed offline before a transaction is spent, and the live record replayed through this code
- [`tests/test_integration.py`](tests/test_integration.py) - opt in, `GENLAYER_STUDIO=1`: value, senders and addresses on a real runtime

### The tests have teeth

[`scripts/mutate.py`](scripts/mutate.py) removes every defence one at a time
and names the test that caught each mutant. It refuses to run on a red
baseline and exits non-zero if anything escapes.

<!-- measured:mutations:start -->
Measured: **72 mutations, 72 caught, 0 escaped.**

| Mutation | Caught by |
|---|---|
| a slot with a word is read as none | `test_an_unusable_answer_is_an_error_and_never_a_match` |
| an order row past the list is accepted | `test_a_slot_is_an_order_row_or_none_and_nothing_else` |
| an answer of the wrong length is accepted | `test_an_unusable_answer_is_an_error_and_never_a_match` |
| an unusable slot is dropped instead of failing the whole answer | `test_an_unusable_answer_is_an_error_and_never_a_match` |
| the reversed answer is not read back into the filed order | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| the un-reversal does not flip the invoice lines | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| the un-reversal does not flip the order rows | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| the reversed pass is never asked | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| only the order rows are reversed | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| a disagreement between the orders keeps the forward match | `test_a_match_that_depends_on_the_order_is_none_and_not_paid` |
| a disagreement between the orders takes the reversed match | `test_a_match_that_depends_on_the_order_is_none_and_not_paid` |
| an unusable answer is not retried | `test_an_answer_that_is_not_an_object_is_retried_not_crashed_on` |
| an unusable answer is read as every line unmatched | `test_an_unusable_answer_is_an_error_and_never_a_match` |
| an answer that is not an object crashes the block | `test_an_answer_that_is_not_an_object_is_retried_not_crashed_on` |
| the free structural layer is skipped | `test_a_malformed_proposal_is_refused_with_zero_validator_prompts` |
| a validator agrees with a leader that raised | `test_an_unusable_answer_is_an_error_and_never_a_match` |
| a validator trusts the leader | `test_nodes_that_match_differently_do_not_agree_and_nothing_is_paid` |
| a validator whose own model failed agrees | `test_a_validator_whose_model_fails_does_not_agree` |
| agreement compares the first invoice line only | `test_nodes_that_match_differently_do_not_agree_and_nothing_is_paid` |
| the structural check accepts an order row that does not exist | `test_a_malformed_proposal_is_refused_with_zero_validator_prompts` |
| the structural check accepts any length | `test_the_structural_check` |
| an unmatched line is priced against the first order row | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| the price is never checked | `test_overpriced_and_over_quantity_are_decided_by_the_contract` |
| the quantity is never checked | `test_overpriced_and_over_quantity_are_decided_by_the_contract` |
| an accepted line does not use up its units | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| a line is paid at the order's price, not the invoiced one | `test_when_every_unit_is_paid_the_order_is_fulfilled_and_the_savings_go_back` |
| what is still open is not written back | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| the supplier is not paid | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| a fully paid order is never fulfilled | `test_when_every_unit_is_paid_the_order_is_fulfilled_and_the_savings_go_back` |
| the invoice stays waiting after its match | `test_the_same_invoice_is_not_matched_twice` |
| what was paid is not added to the order | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| an order may be overpaid | `test_the_whole_order_must_be_paid_in_exactly` |
| an order may be underpaid | `test_the_whole_order_must_be_paid_in_exactly` |
| two order lines with the same wording are accepted | `test_malformed_lines_are_refused_before_anything_is_stored` |
| the buyer may be the supplier | `test_the_other_bounds` |
| the order window is unbounded | `test_the_other_bounds` |
| the grace window is unbounded | `test_the_grace_window_is_bounded_at_deploy` |
| what is held is not raised at open | `test_an_order_opens_frozen_and_holds_the_whole_payment` |
| the title is unbounded | `test_the_other_bounds` |
| a line description is unbounded | `test_malformed_lines_are_refused_before_anything_is_stored` |
| more than six lines are accepted | `test_malformed_lines_are_refused_before_anything_is_stored` |
| empty items are dropped, shifting every quantity after them | `test_split_list_keeps_empty_items_so_nothing_shifts` |
| a count of zero is accepted | `test_malformed_lines_are_refused_before_anything_is_stored` |
| anyone may invoice | `test_only_the_supplier_may_invoice` |
| an invoice after the order ends is accepted | `test_an_invoice_after_the_order_ends_is_refused_and_one_on_the_last_second_accepted` |
| two invoices may wait at once | `test_one_invoice_waits_at_a_time` |
| an order takes any number of invoices | `test_an_order_takes_at_most_four_invoices` |
| the same invoice can be matched twice | `test_the_same_invoice_is_not_matched_twice` |
| the invoice fingerprint ignores quantities | `test_the_same_invoice_is_not_matched_twice` |
| an invoice is not linked to the one before it | `test_two_invoices_are_never_paid_for_the_same_units` |
| an invoice is not marked waiting | `test_an_invoice_is_recorded_waiting_and_pays_nothing_yet` |
| anyone may ask for the match | `test_a_stranger_may_not_ask_for_the_match` |
| a match runs with nothing waiting | `test_nothing_waiting_is_refused` |
| anyone may release the order | `test_only_the_supplier_may_release` |
| the order is released while an invoice waits | `test_no_release_while_an_invoice_waits` |
| the order may be closed before it ends | `test_close_is_refused_until_the_order_ends` |
| a waiting invoice does not hold the order | `test_an_invoice_filed_in_time_holds_the_order_until_the_grace_ends` |
| a lapsed invoice keeps looking as if it were waiting | `test_after_the_grace_a_waiting_invoice_lapses_unpaid` |
| an order can be closed twice | `test_anyone_may_close_after_the_end_and_the_buyer_gets_the_rest` |
| the rest is never refunded | `test_when_every_unit_is_paid_the_order_is_fulfilled_and_the_savings_go_back` |
| a payout may exceed what is held | `test_a_payout_beyond_what_is_held_is_refused` |
| what is held is not reduced by a payout | `test_matched_lines_are_paid_and_an_unlisted_item_is_not` |
| a negative order id reads the newest order | `test_a_read_with_a_bad_id_is_a_user_error` |
| the fence is removed | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the fence leaves square brackets | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the order rows reach the prompt unfenced | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the invoice rows reach the prompt unfenced | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the title reaches the prompt unfenced | `test_every_value_interpolated_into_the_prompt_is_fenced_or_ours` |
| the prompt no longer states the counts | `test_the_prompt_states_the_counts_and_never_shows_a_number_it_does_not_own` |
| the answer example is a real answer | `test_the_prompt_states_the_counts_and_never_shows_a_number_it_does_not_own` |
| a leader's reason is stored as sent | `test_a_lying_leader_s_reason_is_sanitised_before_it_is_stored` |
| a leader's reason is stored uncapped | `test_a_lying_leader_s_reason_is_sanitised_before_it_is_stored` |
<!-- measured:mutations:end -->

## Design rules applied

- **The coarsest answer that still carries the judgment:** an index into a list the contract already holds, or none.
- **No single call reveals what only the contract should see:** quantities and prices never enter the prompt.
- **Uncertainty in the value, never in the comparison:** an order-dependent match is none, and none is not paid.
- **Both presentation orders, inside one block,** with both lists reversed together.
- **Money moves at the root of the transaction,** state first, through one guarded path.
- **Every waiting state has a clock,** so no invoice nobody matches can hold the buyer's money forever.
- **Tagging untrusted text is not a fence:** `fence()` at the prompt boundary, rows labelled by the contract.
- **The deployment is the submission:** `scripts/verify_deployment.py` reads the deployed source back and lints it.

## Further reading in this repository

- [DECISIONS.md](DECISIONS.md) - why each rule is the way it is
- [DEPLOY.md](DEPLOY.md) - the demo, step by step
- [SUBMISSION.md](SUBMISSION.md) - what to check before submitting
- [`lib/tally_consensus.py`](lib/tally_consensus.py) - the matching and pricing rules, generated from the contract

## Related work

- [Tranche](https://github.com/meitipro1/tranche) - an escrow released clause by clause; Tally pays line by line against an order
- [Mandate](https://github.com/meitipro1/mandate) - a treasury that pays only what its charter allows
- [Verbatim](https://github.com/meitipro1/verbatim) - settles what code can settle before any model is asked
