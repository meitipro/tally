"""Integration tests, run against StudioNet.

    pip install genlayer-py==0.18.0
    GENLAYER_STUDIO=1 pytest tests/test_integration.py -v

They are opt in. Without GENLAYER_STUDIO set they skip, so `pytest tests/ -q`
stays clean and offline on a reviewer's machine whatever is installed there,
and an unreachable network can never be mistaken for a broken contract.

They exercise the deterministic half on a real runtime, where the simulator is
weakest: the sender is derived from a signature rather than set by a test,
value really arrives with a payable call, and an address is 20 bytes rather
than a string. The match itself costs inference on every validator and is on
the record from scripts/demo.py.
"""

import os
import pathlib
import sys

import pytest

if not os.environ.get("GENLAYER_STUDIO"):
    pytest.skip("integration tests run against StudioNet and are opt in: set GENLAYER_STUDIO=1. "
                "Everything else runs offline with pytest tests/ -q", allow_module_level=True)

pytest.importorskip("genlayer_py", reason="pip install genlayer-py==0.18.0")

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent.parent / "scripts"))
from studio import GEN, Studio                               # noqa: E402

CODE = (pathlib.Path(__file__).absolute().parent.parent / "contracts" / "tally.py").read_text(encoding="utf-8")
TITLE = "Office supplies, integration run"
DESCS = "A4 copier paper, 80 gsm, box of 5 reams|Full-strip metal desk stapler"
QTYS = "2|1"
PRICES = f"{GEN // 10}|{GEN // 20}"
TOTAL = 2 * (GEN // 10) + GEN // 20


@pytest.fixture(scope="module")
def world():
    s = Studio()
    buyer = s.account("buyer", gen=2)
    supplier = s.account("supplier")
    stranger = s.account("stranger")
    address = s.deploy(buyer, CODE, [300])
    s.write(buyer, address, "open", [TITLE, supplier.address, DESCS, QTYS, PRICES, 3600], value=TOTAL,
            step="open an order")
    return s, address, buyer, supplier, stranger


def test_value_arrives_with_a_payable_call(world):
    s, address, buyer, supplier, _ = world
    o = s.read(address, "order", [0])
    assert o["status"] == "open" and o["funded"] == str(TOTAL) and o["held"] == str(TOTAL)
    assert o["buyer"].lower() == buyer.address.lower() and o["supplier"].lower() == supplier.address.lower()
    assert int(s.read(address, "held_total")) == TOTAL


def test_an_order_must_be_paid_in_exactly(world):
    s, address, buyer, supplier, _ = world
    row = s.write(buyer, address, "open", [TITLE, supplier.address, DESCS, QTYS, PRICES, 3600], value=TOTAL - 1,
                  step="underpay an order", expect="refused")
    assert "pay the whole order in" in row["refusal"]


def test_only_the_supplier_may_invoice(world):
    s, address, buyer, _, stranger = world
    for who in (buyer, stranger):
        row = s.write(who, address, "invoice", [0, "Copy paper A4", "1", str(GEN // 10)],
                      step="invoice from the wrong account", expect="refused")
        assert "only the supplier" in row["refusal"]


def test_a_stranger_may_not_ask_for_the_match_and_nothing_releases_under_a_waiting_invoice(world):
    s, address, _, supplier, stranger = world
    s.write(supplier, address, "invoice", [0, "Copy paper A4 80g", "1", str(GEN // 10)], step="the supplier invoices")
    row = s.write(stranger, address, "match", [0], step="a stranger asks for the match", expect="refused")
    assert "only the buyer or the supplier" in row["refusal"]
    row = s.write(supplier, address, "release", [0], step="release under a waiting invoice", expect="refused")
    assert "match it first" in row["refusal"]


def test_close_is_refused_before_the_end(world):
    s, address, _, _, stranger = world
    row = s.write(stranger, address, "close", [0], step="close too early", expect="refused")
    assert "the order runs until" in row["refusal"]


def test_a_release_returns_the_whole_order_to_the_buyer(world):
    s, address, buyer, supplier, _ = world
    s.write(buyer, address, "open", ["Second order", supplier.address, DESCS, QTYS, PRICES, 3600], value=TOTAL,
            step="open a second order")
    s.write(supplier, address, "release", [1], step="the supplier releases it")
    o = s.read(address, "order", [1])
    assert o["status"] == "closed" and o["closed_how"] == "released" and o["refunded"] == str(TOTAL)


def test_an_unknown_order_is_a_refusal_not_the_newest_row(world):
    s, address, _, _, stranger = world
    row = s.write(stranger, address, "close", [99], step="close an order that does not exist", expect="refused")
    assert "no such order" in row["refusal"]
