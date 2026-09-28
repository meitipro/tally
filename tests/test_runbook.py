"""
The demo, replayed offline.

scripts/demo.py puts the demo on StudioNet from scripts/demo_data.py (STEPS).
This file replays the same steps against the real contract in the simulator,
so a demo that could not succeed is caught before a single transaction is
spent on it.

When deployments/studionet.json exists, the replay goes further: it feeds the
simulator the matches the validators actually agreed on, and checks that the
contract in this repository pays exactly what the deployed one paid, refunds
exactly what it refunded, and refuses exactly where it refused.

    pytest tests/test_runbook.py -v
"""

import hashlib
import importlib.util
import json
import pathlib

import pytest

import glsim as S

CONTRACT_PATH = "contracts/tally.py"
M = S.load_contract(CONTRACT_PATH)
RECORD = pathlib.Path("deployments/studionet.json")

_spec = importlib.util.spec_from_file_location("demo_data", "scripts/demo_data.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

WHO = {"buyer": "0x" + "a1" * 20, "supplier": "0x" + "b2" * 20, "stranger": "0x" + "c3" * 20}
T0 = 1_790_000_000


def honest(order_descs, invoice_descs, forward):
    """Both prompts of one match, answered consistently with `forward`."""
    n, m = len(order_descs), len(invoice_descs)
    fwd = forward.split("|")
    rev = "|".join(fwd[m - 1 - j] if fwd[m - 1 - j] == "none" else str(n - 1 - int(fwd[m - 1 - j]))
                   for j in range(m))
    if m > 1:
        return {"[I0] " + invoice_descs[0]: {"matches": forward, "because": "replayed"},
                "[I0] " + invoice_descs[-1]: {"matches": rev, "because": "replayed"}}
    return {"[0] " + order_descs[0]: {"matches": forward, "because": "replayed"},
            "[0] " + order_descs[-1]: {"matches": rev, "because": "replayed"}}


def replay(agreed):
    """Run STEPS. `agreed` are the vectors the ok match steps come back with, in order."""
    c = S.deploy(CONTRACT_PATH, D.GRACE_SECONDS)
    S.reset_transfers()
    queue = list(agreed)
    outcomes = []
    clock = T0
    for step in D.STEPS:
        actor, method, spec, expect, label = step[:5]
        clock += 30
        if "after_end" in step[5:]:
            clock = max(clock, T0 + 60 + D.SERVICE_VALID_FOR + 1000)
        S.set_time(M.iso(clock))
        S.set_mocks()
        value = 0
        if method == "open":
            title, lines, valid_for = spec
            args = [title, WHO["supplier"], *D.joined(lines), valid_for]
            value = D.total(lines)
        elif method == "invoice":
            args = [spec[0], *D.joined(spec[1])]
        else:
            args = list(spec)
        if method == "match" and expect == "ok":
            o = c.orders[spec[0]]
            order_descs = [c.order_lines[o.first_line + k].text for k in range(o.n_lines)]
            inv = c.invoices[o.last_invoice]
            invoice_descs = [c.invoice_lines[inv.first_line + i].text for i in range(inv.n_lines)]
            S.set_mocks(leader_prompts=honest(order_descs, invoice_descs, queue.pop(0)))
        S.set_sender(WHO[actor])
        try:
            S.call(c, method, *args, value=value)
            outcomes.append(("ok", ""))
        except S.UserError as e:
            outcomes.append(("refused", e.message))
    return c, outcomes


class TestDemoData:
    def test_every_value_the_demo_sends_passes_the_bounds(self):
        for lines in (D.ORDER, D.SERVICE, D.SPARE, D.INVOICE_1, D.INVOICE_2, D.INVOICE_3):
            descs, qtys, prices = D.joined(lines)
            assert M.lines_refusal(M.split_list(descs), M.parse_counts(qtys, 1, M.MAX_QTY),
                                   M.parse_counts(prices, 1, M.MAX_PRICE), "x") == ""

    def test_each_invoice_changes_one_thing(self):
        """INVOICE_2 names the same items as INVOICE_1's first line and the
        order's stapler, and differs only by quantity and price; INVOICE_3
        brings both within the order."""
        order_price = {d: p for d, _, p in D.ORDER}
        assert D.INVOICE_2[0][2] == order_price[D.ORDER[0][0]]              # paper at the agreed price...
        assert D.INVOICE_2[0][1] > D.ORDER[0][1] - D.INVOICE_1[0][1]        # ...but more than is open
        assert D.INVOICE_2[1][2] > order_price[D.ORDER[2][0]]              # stapler above the price
        assert D.INVOICE_3[0][1] == D.ORDER[0][1] - D.INVOICE_1[0][1]       # exactly what is open
        assert D.INVOICE_3[1][2] < order_price[D.ORDER[2][0]]              # below the price

    def test_the_short_order_outlasts_the_step_meant_to_find_it_open(self):
        """The early close is the third transaction; at the 40 s per
        transaction measured on StudioNet it lands well inside five minutes."""
        assert D.SERVICE_VALID_FOR >= 3 * 40 * 2


class TestReplay:
    def test_the_demo_succeeds_and_refuses_exactly_where_it_says(self):
        _, outcomes = replay(D.EXPECTED_MATCHES)
        assert [o for o, _ in outcomes] == [s[3] for s in D.STEPS]

    def test_the_refusals_say_why(self):
        _, outcomes = replay(D.EXPECTED_MATCHES)
        msgs = [m for o, m in outcomes if o == "refused"]
        for msg, want in zip(msgs, ["the order runs until", "only the supplier may invoice",
                                    "waiting to be matched", "only the buyer or the supplier",
                                    "already matched as invoice 1"]):
            assert want in msg, (want, msg)

    def test_the_expected_matches_pay_and_refund_what_the_readme_says(self):
        c, _ = replay(D.EXPECTED_MATCHES)
        G = D.GEN
        o0 = c.order(0)
        assert o0["status"] == "fulfilled"
        assert int(o0["paid"]) == 6 * G // 20 + 2 * G // 5 + 4 * G // 20 + 3 * 18 * G // 1000
        assert int(o0["refunded"]) == D.total(D.ORDER) - int(o0["paid"])
        assert c.order(1)["closed_how"] == "closed" and int(c.order(1)["refunded"]) == D.total(D.SERVICE)
        assert c.order(2)["closed_how"] == "released" and int(c.order(2)["refunded"]) == D.total(D.SPARE)
        assert c.held_total() == 0
        states = [[ln["state"] for ln in inv["lines"]] for inv in c.invoices_of(0)["invoices"]]
        assert states == [["accepted", "accepted", "unmatched"], ["over_quantity", "overpriced"],
                          ["accepted", "accepted"]]


@pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded yet: python scripts/demo.py")
class TestTheRecord:
    """The live run, checked against this repository."""

    def _record(self):
        return json.loads(RECORD.read_text(encoding="utf-8"))

    def _agreed(self, rec):
        out = []
        for inv in rec["orders"][0]["invoices"]:
            if inv["matched"]:
                out.append("|".join(ln["match"] for ln in inv["lines"]))
        return out

    def test_the_record_is_of_this_source(self):
        here = hashlib.sha256(pathlib.Path(CONTRACT_PATH).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert self._record()["source_sha256"] == here, "the deployed contract is not this file; redeploy"

    def test_every_step_on_chain_did_what_the_demo_expected(self):
        steps = [s for s in self._record()["steps"] if s["step"] != "deploy"]
        assert [("ok" if s["ok"] else "refused") for s in steps] == [s[3] for s in D.STEPS]

    def test_this_contract_pays_what_the_deployed_one_paid(self):
        rec = self._record()
        c, outcomes = replay(self._agreed(rec))
        assert [o for o, _ in outcomes] == [s[3] for s in D.STEPS]
        for k, o in enumerate(rec["orders"]):
            mine = c.order(k)
            for field in ("status", "paid", "refunded", "closed_how"):
                assert str(mine[field]) == str(o["order"][field]), (k, field)
            mine_lines = [[ln["state"] for ln in inv["lines"]] for inv in c.invoices_of(k)["invoices"]]
            theirs = [[ln["state"] for ln in inv["lines"]] for inv in o["invoices"]]
            assert mine_lines == theirs, k
        assert str(rec["held_after"]) == "0"
