"""The demo's data, in one place.

scripts/demo.py sends exactly these values to StudioNet, and
tests/test_runbook.py replays them offline, so the demo on the explorer and the
demo the tests check cannot drift apart.

One order for office supplies, three invoices against it. Each invoice changes
one thing, so each rule of the contract shows once, on chain:

  INVOICE_1   two lines described in other words (matched, paid) and one item
              the order never listed (unmatched, not paid)
  INVOICE_2   the right items, but more paper than is still open and a stapler
              above the agreed price: matched, and refused by the contract's
              arithmetic, not by the model
  INVOICE_3   the rest, at or below the agreed prices: paid, the order is
              fulfilled, and the unspent difference goes back to the buyer

A second order is released by its supplier, and a third runs out of time and is
closed by a stranger: both return their money to the buyer.
"""

GEN = 10 ** 18
GRACE_SECONDS = 300

TITLE = "Office supplies for the Harbour branch, Q4"
ORDER = [
    ("A4 copier paper, 80 gsm, box of 5 reams", 10, 5 * GEN // 100),
    ("Black toner cartridge for HP LaserJet M404", 2, 20 * GEN // 100),
    ("Full-strip metal desk stapler", 3, 2 * GEN // 100),
]
VALID_FOR = 3600

INVOICE_1 = [
    ("Copy paper A4 80g, 5-ream box", 6, 5 * GEN // 100),
    ("HP LaserJet M404 black toner cartridge", 2, 20 * GEN // 100),
    ("LED desk lamp with USB charging port", 1, 10 * GEN // 100),
]
EXPECTED_1 = "0|1|none"

INVOICE_2 = [
    ("Copy paper A4 80 gsm, box of five reams", 5, 5 * GEN // 100),
    ("Metal stapler, full strip", 3, 25 * GEN // 1000),
]
EXPECTED_2 = "0|2"

INVOICE_3 = [
    ("Copier paper, A4, 80 gsm (5 reams per box)", 4, 5 * GEN // 100),
    ("Full strip metal stapler for desks", 3, 18 * GEN // 1000),
]
EXPECTED_3 = "0|2"

SERVICE_TITLE = "Printer service visit, Harbour branch"
SERVICE = [("On-site service visit for the office printers", 1, 10 * GEN // 100)]
SERVICE_VALID_FOR = 300

SPARE_TITLE = "Spare toner for the second office"
SPARE = [("Black toner cartridge for HP LaserJet M404", 1, 20 * GEN // 100)]


def joined(lines):
    """(descriptions, quantities, unit prices) as the three pipe joined strings open() and invoice() take."""
    return ("|".join(d for d, _, _ in lines),
            "|".join(str(q) for _, q, _ in lines),
            "|".join(str(p) for _, _, p in lines))


def total(lines):
    return sum(q * p for _, q, p in lines)


# The demo, step by step, exactly as scripts/demo.py sends it and
# tests/test_runbook.py replays it: (who, method, arguments, expected, label).
# An order is named by its lines; an invoice by (order id, lines).
# ("close", 1) marked "after_end" waits until order 1 has ended.
STEPS = [
    ("buyer", "open", (TITLE, ORDER, VALID_FOR), "ok", "order 0 opened: office supplies, three lines"),
    ("buyer", "open", (SERVICE_TITLE, SERVICE, SERVICE_VALID_FOR), "ok", "order 1 opened: runs five minutes"),
    ("stranger", "close", (1,), "refused", "order 1 closed before it ends"),
    ("buyer", "open", (SPARE_TITLE, SPARE, VALID_FOR), "ok", "order 2 opened: spare toner"),
    ("stranger", "invoice", (0, INVOICE_1), "refused", "a stranger invoices order 0"),
    ("supplier", "invoice", (0, INVOICE_1), "ok", "invoice 1: paper, toner and a desk lamp"),
    ("supplier", "invoice", (0, INVOICE_2), "refused", "a second invoice while one waits"),
    ("stranger", "match", (0,), "refused", "a stranger asks for the match"),
    ("buyer", "match", (0,), "ok", "matched: paper and toner paid, the lamp was never ordered"),
    ("supplier", "invoice", (0, INVOICE_1), "refused", "the same invoice again"),
    ("supplier", "invoice", (0, INVOICE_2), "ok", "invoice 2: too much paper, stapler above price"),
    ("supplier", "match", (0,), "ok", "matched: both lines refused by the arithmetic"),
    ("supplier", "invoice", (0, INVOICE_3), "ok", "invoice 3: the rest, stapler below price"),
    ("buyer", "match", (0,), "ok", "matched: order 0 fulfilled, the difference back"),
    ("supplier", "release", (2,), "ok", "order 2 released by the supplier"),
    ("stranger", "close", (1,), "ok", "order 1 closed after it ended", "after_end"),
]

# What each ok match is expected to agree on, in order.
EXPECTED_MATCHES = [EXPECTED_1, EXPECTED_2, EXPECTED_3]
