"""Mutation pass: break every defence on purpose, confirm a test notices.

Passing tests prove nothing on their own. Each entry below is a small edit to
the contract that removes a defence. The suite must fail for every one of them,
and this script records WHICH test caught it, so the table in the README is
measured rather than claimed.

    python scripts/mutate.py            # run them all, print what caught what
    python scripts/mutate.py --md       # emit the markdown table for the README

An escaping mutation is a finding, not a nuisance: either a missing test, or a
later defence strict enough that an earlier test can no longer fail. The script
exits non-zero if anything escapes, and refuses to run on a red baseline.

Three rules keep the harness honest:

  * the unmutated suite must be green before anything is mutated;
  * a find string that is missing, or matches more than once, is a failure of
    the harness, never a skip, so refactoring cannot quietly turn a row off;
  * scripts/lift.py runs inside every mutated copy before the suite, so the lib
    parity test can never stand in for the behavioural test a mutation deserves.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).absolute().parent.parent
TARGET = "tally.py"

FOLD = "    return [forward[i] if forward[i] == reverse_unreversed[i] else NONE for i in range(len(forward))]"
FENCE = '    return str(raw).replace("<", "(").replace(">", ")").replace("[", "(").replace("]", ")")'
PAID_IN = "        if paid_in != total:"

MUTATIONS = [
    # -- reading the answer
    ("a slot with a word is read as none",
     '        return ""\n    k = int(s)', "        return NONE\n    k = int(s)"),
    ("an order row past the list is accepted",
     '    if k < 0 or k >= n:\n        return ""', '    if k < 0:\n        return ""'),
    ("an answer of the wrong length is accepted",
     "    if m == 0 or n == 0 or len(parts) != m:\n        return None\n    out = []",
     "    if m == 0 or n == 0:\n        return None\n    out = []"),
    ("an unusable slot is dropped instead of failing the whole answer",
     '        if c == "":\n            return None\n        out.append(c)',
     '        if c == "":\n            continue\n        out.append(c)'),

    # -- the two orders
    ("the reversed answer is not read back into the filed order",
     "            folded = fold(fwd, unreverse(rev, m, n))", "            folded = fold(fwd, rev)"),
    ("the un-reversal does not flip the invoice lines",
     "        out[m - 1 - i] = c if c == NONE else str(n - 1 - int(c))",
     "        out[i] = c if c == NONE else str(n - 1 - int(c))"),
    ("the un-reversal does not flip the order rows",
     "        out[m - 1 - i] = c if c == NONE else str(n - 1 - int(c))",
     "        out[m - 1 - i] = c if c == NONE else str(int(c))"),
    ("the reversed pass is never asked",
     "            rev, _ = read_once(title, rev_order, rev_invoice, n, m)",
     "            rev, _ = read_once(title, order_descs, invoice_descs, n, m)"),
    ("only the order rows are reversed",
     "        rev_invoice = list(reversed(invoice_descs))", "        rev_invoice = list(invoice_descs)"),
    ("a disagreement between the orders keeps the forward match", FOLD, "    return list(forward)"),
    ("a disagreement between the orders takes the reversed match", FOLD, "    return list(reverse_unreversed)"),

    # -- reading the model
    ("an unusable answer is not retried",
     "    for _ in range(2):\n        raw = gl.nondet.exec_prompt(",
     "    for _ in range(1):\n        raw = gl.nondet.exec_prompt("),
    ("an unusable answer is read as every line unmatched",
     '    raise gl.vm.UserError(f"{ERR_LLM} the model gave no usable match for the {m} invoice lines")',
     '    return [NONE] * m, ""'),
    ("an answer that is not an object crashes the block",
     "        if isinstance(raw, dict):\n            vec = parse_matches", "        if True:\n            vec = parse_matches"),

    # -- the validator
    ("the free structural layer is skipped",
     "            if not matches_sound(proposed, m, n):\n                return False\n            try:",
     "            try:"),
    ("a validator agrees with a leader that raised",
     "                # An [LLM_ERROR] is never agreed with.\n                return False",
     "                # An [LLM_ERROR] is never agreed with.\n                return True"),
    ("a validator trusts the leader",
     '            return tally_agrees(parse_proposal(mine["matches"], m), proposed, m, n)',
     "            return True"),
    ("a validator whose own model failed agrees",
     "            except gl.vm.UserError:\n                return False",
     "            except gl.vm.UserError:\n                return True"),
    ("agreement compares the first invoice line only",
     "and list(mine) == list(theirs)", "and list(mine)[0] == list(theirs)[0]"),
    ("the structural check accepts an order row that does not exist",
     "        if int(s) >= n:\n            return False\n", ""),
    ("the structural check accepts any length",
     "    if vector is None or m == 0 or n == 0 or len(vector) != m:", "    if vector is None or m == 0 or n == 0:"),

    # -- the contract's arithmetic
    ("an unmatched line is priced against the first order row",
     "        if c == NONE:\n            states.append(UNMATCHED)\n            paid.append(0)\n            continue\n        k = int(c)",
     "        k = 0 if c == NONE else int(c)"),
    ("the price is never checked", "        if int(prices[i]) > int(order_prices[k]):", "        if False:"),
    ("the quantity is never checked", "        if int(qtys[i]) > left[k]:", "        if False:"),
    ("an accepted line does not use up its units", "        left[k] -= int(qtys[i])\n", ""),
    ("a line is paid at the order's price, not the invoiced one",
     "        paid.append(int(qtys[i]) * int(prices[i]))", "        paid.append(int(qtys[i]) * int(order_prices[k]))"),
    ("what is still open is not written back",
     "            self.order_lines[ofirst + k].remaining = u256(left[k])", "            pass"),
    ("the supplier is not paid", "        self._send(o.supplier, total)", "        pass"),
    ("a fully paid order is never fulfilled",
     "        if all(r == 0 for r in left):\n            self._end(o, BY_FULFILMENT, FULFILLED)",
     "        if False:\n            self._end(o, BY_FULFILMENT, FULFILLED)"),
    ("the invoice stays waiting after its match",
     "        o.pending = False\n        o.paid = u256(int(o.paid) + total)", "        o.paid = u256(int(o.paid) + total)"),
    ("what was paid is not added to the order",
     "        o.paid = u256(int(o.paid) + total)", "        o.paid = u256(int(o.paid))"),

    # -- opening an order
    ("an order may be overpaid", PAID_IN, "        if paid_in < total:"),
    ("an order may be underpaid", PAID_IN, "        if paid_in > total:"),
    ("two order lines with the same wording are accepted",
     "        if len(set(d.lower() for d in descs)) != len(descs):", "        if False:"),
    ("the buyer may be the supplier", "        if who == gl.message.sender_address:", "        if False:"),
    ("the order window is unbounded", "        if window < MIN_WINDOW or window > MAX_WINDOW:", "        if False:"),
    ("the grace window is unbounded", "        if g < MIN_WINDOW or g > MAX_WINDOW:", "        if False:"),
    ("what is held is not raised at open", "        self.held = u256(int(self.held) + total)\n", ""),
    ("the title is unbounded", "        if len(t) < MIN_TITLE or len(t) > MAX_TITLE:", "        if False:"),
    ("a line description is unbounded", "        if len(d) < MIN_DESC or len(d) > MAX_DESC:", "        if False:"),
    ("more than six lines are accepted", "    if len(descs) > MAX_LINES:", "    if False:"),
    ("empty items are dropped, shifting every quantity after them",
     '    return [clean_text(part) for part in str(text).split("|")]',
     '    return [clean_text(part) for part in str(text).split("|") if clean_text(part) != ""]'),
    ("a count of zero is accepted", "        if v < low or v > high:", "        if v > high:"),

    # -- invoicing
    ("anyone may invoice", "        if who != o.supplier:", "        if False:"),
    ("an invoice after the order ends is accepted", "        if now > int(o.ends_at):", "        if False:"),
    ("two invoices may wait at once",
     '        if bool(o.pending):\n            return f"{ERR_EXPECTED} an invoice is waiting to be matched; either party',
     '        if False:\n            return f"{ERR_EXPECTED} an invoice is waiting to be matched; either party'),
    ("an order takes any number of invoices", "        if int(o.n_invoices) >= MAX_INVOICES:", "        if False:"),
    ("the same invoice can be matched twice", "            if str(self.invoices[i].digest) == d:", "            if False:"),
    ("the invoice fingerprint ignores quantities",
     '    rows = [f"{descs[i].lower()}#{qtys[i]}#{prices[i]}" for i in range(len(descs))]',
     '    rows = [f"{descs[i].lower()}#{prices[i]}" for i in range(len(descs))]'),
    ("an invoice is not linked to the one before it",
     "            self.invoices[int(o.last_invoice)].next = u256(iid)", "            pass"),
    ("an invoice is not marked waiting", "        o.pending = True", "        o.pending = False"),

    # -- matching
    ("anyone may ask for the match", "        if sender != o.buyer and sender != o.supplier:", "        if False:"),
    ("a match runs with nothing waiting",
     "        if str(o.status) != OPEN or not bool(o.pending):", "        if str(o.status) != OPEN:"),

    # -- the ways out
    ("anyone may release the order", "        if gl.message.sender_address != o.supplier:", "        if False:"),
    ("the order is released while an invoice waits",
     '            raise gl.vm.UserError(f"{ERR_EXPECTED} an invoice is waiting to be matched; match it first")',
     "            pass"),
    ("the order may be closed before it ends", "        if now <= int(o.ends_at):", "        if False:"),
    ("a waiting invoice does not hold the order",
     "        if bool(o.pending) and now <= int(o.ends_at) + int(self.grace_seconds):", "        if False:"),
    ("a lapsed invoice keeps looking as if it were waiting",
     "                self.invoice_lines[ifirst + i].state = LAPSED", "                pass"),
    ("an order can be closed twice",
     '        if str(o.status) != OPEN:\n            return f"{ERR_EXPECTED} this order is {o.status}; nothing more can happen on it"',
     '        if False:\n            return f"{ERR_EXPECTED} this order is {o.status}; nothing more can happen on it"'),
    ("the rest is never refunded", "        self._send(o.buyer, rest)", "        pass"),
    ("a payout may exceed what is held", "        if amount > int(self.held):", "        if False:"),
    ("what is held is not reduced by a payout", "        self.held = u256(int(self.held) - amount)\n", ""),
    ("a negative order id reads the newest order",
     "        if i < 0 or i >= len(self.orders):", "        if i >= len(self.orders):"),

    # -- the prompt
    ("the fence is removed", FENCE, "    return str(raw)"),
    ("the fence leaves square brackets", FENCE, '    return str(raw).replace("<", "(").replace(">", ")")'),
    ("the order rows reach the prompt unfenced",
     '    order_rows = "\\n".join(f"[{k}] {fence(order_descs[k])}" for k in range(n))',
     '    order_rows = "\\n".join(f"[{k}] {order_descs[k]}" for k in range(n))'),
    ("the invoice rows reach the prompt unfenced",
     '    invoice_rows = "\\n".join(f"[I{i}] {fence(invoice_descs[i])}" for i in range(m))',
     '    invoice_rows = "\\n".join(f"[I{i}] {invoice_descs[i]}" for i in range(m))'),
    ("the title reaches the prompt unfenced", "<order>\n{fence(title)}", "<order>\n{title}"),
    ("the prompt no longer states the counts",
     "Number of invoice rows: {m}. Order rows: 0 to {n - 1}.\n", ""),
    ("the answer example is a real answer",
     '    example = "|".join(f"c{i}" for i in range(m))', '    example = "|".join("none" for i in range(m))'),
    ("a leader's reason is stored as sent",
     '        inv.why = sanitise_reason(res.get("because", ""))', '        inv.why = str(res.get("because", ""))'),
    ("a leader's reason is stored uncapped",
     '    return " ".join("".join(out).split())[:limit]', '    return " ".join("".join(out).split())'),
]


PYTEST = [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]


def copy_repo(tmp):
    dst = pathlib.Path(tmp) / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".git", "artifacts", "*.pyc"))
    return dst


def run_one(label, find, replace):
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        target = dst / "contracts" / TARGET
        src = target.read_text(encoding="utf-8")
        hits = src.count(find)
        if hits == 0:
            return "PATTERN NOT FOUND", None
        if hits > 1:
            return "PATTERN NOT UNIQUE", None
        target.write_text(src.replace(find, replace, 1), encoding="utf-8", newline="\n")
        subprocess.run([sys.executable, "scripts/lift.py"], cwd=dst, capture_output=True)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True)
        if proc.returncode == 0:
            return "ESCAPED", None
        text = proc.stdout + proc.stderr
        m = re.search(r"^(?:FAILED|ERROR) (\S+?)::(\S+?)(?:\[|\s|$)", text, re.M)
        if m:
            return "caught", m.group(2).split("::")[-1]
        m = re.search(r"^E\s+(\w*(?:Error|Exception))", text, re.M)
        if m:
            return "caught", m.group(1) + " at import"
        return "caught", "unnamed failure"


def baseline_is_green():
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True)
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="emit the README table")
    args = ap.parse_args()

    green, tail = baseline_is_green()
    if not green:
        print("the unmutated suite is not green; every mutation would look caught:\n" + tail, file=sys.stderr)
        return 2

    rows, escaped = [], []
    for label, find, replace in MUTATIONS:
        status, test = run_one(label, find, replace)
        if status == "caught":
            rows.append((label, test))
            if not args.md:
                print("  caught   %-70s %s" % (label, test), flush=True)
        else:
            escaped.append((label, status))
            print("  %-8s %s" % (status, label), file=sys.stderr, flush=True)

    if args.md:
        print("| Mutation | Caught by |")
        print("|---|---|")
        for label, test in rows:
            print("| %s | `%s` |" % (label, test))
    else:
        print()
        print("  %d mutations, %d caught, %d escaped" % (len(MUTATIONS), len(rows), len(escaped)))
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
