"""A thin, measured layer over genlayer-py 0.18 for StudioNet.

Used by scripts/demo.py. Everything here was checked against the installed SDK
rather than a docs page, and the receipt reading follows what Recourse measured
on the same network:

  * the genlayer CLI's `write` has no way to attach value to a call, so a
    payable method is called through genlayer-py, whose write_contract takes
    `value`;
  * genlayer-py 0.18's fund_account() refuses every chain but localnet, so the
    StudioNet faucet is called as the RPC method it is, sim_fundAccount, and
    the balance is read before and after, because the faucet's answer is not
    evidence of anything;
  * ACCEPTED and FINALIZED say the committee agreed, not that the contract
    returned. A refusal is agreed on too. Success is a leader result whose
    status is "return", and a refusal is the payload of a "rollback".

Accounts are made in memory for one run and never written anywhere. They hold
StudioNet test GEN from StudioNet's own faucet and nothing else.
"""

import json
import time

from genlayer_py import create_account, create_client, studionet
from genlayer_py.types import TransactionStatus

GEN = 10 ** 18
EXPLORER = "https://explorer-studio.genlayer.com"
RPC = "https://studio.genlayer.com/api"


def _find(node, names):
    """The first non-empty value under any of `names`. A deploy receipt keeps
    the new address at data.contract_address (measured on StudioNet)."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in names and v:
                return v
        for v in node.values():
            hit = _find(v, names)
            if hit:
                return hit
    elif isinstance(node, list):
        for v in node:
            hit = _find(v, names)
            if hit:
                return hit
    return None


def outcome(receipt):
    """What happened, read from the leader's receipt.

    {"status", "ok", "refusal", "result"}: ok only when the committee settled
    AND the leader returned; refusal is the sentence the contract raised.
    """
    if not isinstance(receipt, dict):
        return {"status": "?", "ok": False, "refusal": "", "result": None}
    status = str(receipt.get("status_name") or receipt.get("status") or "")
    if status.isdigit():
        status = {"5": "ACCEPTED", "6": "UNDETERMINED", "7": "FINALIZED"}.get(status, status)
    leader = (receipt.get("consensus_data") or {}).get("leader_receipt") or [{}]
    first = leader[0] if isinstance(leader, list) and leader else (leader if isinstance(leader, dict) else {})
    result = first.get("result") or {}
    kind = str(result.get("status", "")).lower() if isinstance(result, dict) else ""
    payload = result.get("payload") if isinstance(result, dict) else None
    refusal = ""
    if kind in ("rollback", "user_error"):
        refusal = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    settled = status.upper() in ("ACCEPTED", "FINALIZED")
    return {"status": status.upper(), "ok": settled and kind == "return",
            "refusal": refusal, "result": payload}


class Studio:
    def __init__(self):
        # genlayer-py 0.18 refuses a read with no account ("No account provided
        # and no account is connected"), so reads carry an account of their
        # own that never signs anything.
        self.reader = create_client(chain=studionet, account=create_account())
        self.log = []

    # -- accounts ------------------------------------------------------------

    def account(self, label, gen=0):
        acct = create_account()
        if gen:
            self.fund(acct.address, gen * GEN)
        print(f"  {label:<9} {acct.address}  {self.balance(acct.address) / GEN:.2f} GEN")
        return acct

    def balance(self, address):
        try:
            return int(self.reader.get_balance(address))
        except Exception:                                   # noqa: BLE001
            return 0

    def fund(self, address, wei):
        # The faucet has been measured crediting an account and THEN answering
        # an error, so its answer is not evidence and a blind retry can credit
        # twice. The balance is: ask again only while it is still short.
        for attempt in range(4):
            if self.balance(address) >= int(wei):
                return
            try:
                self.reader.provider.make_request(method="sim_fundAccount", params=[address, int(wei)])
            except Exception as e:                          # noqa: BLE001
                print(f"  faucet answered {str(e)[:80]}; reading the balance instead")
            time.sleep(5 * (attempt + 1))
        if self.balance(address) < int(wei):
            raise SystemExit(f"the StudioNet faucet did not fund {address}; try again in a minute")

    # -- transactions --------------------------------------------------------

    def _client(self, acct):
        return create_client(chain=studionet, account=acct)

    def _nonce(self, address):
        for attempt in range(6):
            try:
                return int(self.reader.get_current_nonce(address))
            except Exception:                               # noqa: BLE001
                if attempt == 5:
                    raise
                time.sleep(10)

    def _submit(self, acct, send):
        """Send once, and again only when the nonce proves nothing arrived.

        The SDK reads the nonce and signs inside every call, and StudioNet has
        answered that read with an HTML error page mid-run. A plain retry would
        be wrong the other way: a response lost AFTER the node accepted the
        transaction would send it twice. So the nonce is read before and after
        a failure. Unchanged means nothing reached the node and a retry is
        safe; advanced means the transaction exists, and it is never resent.
        """
        for attempt in range(5):
            before = self._nonce(acct.address)
            try:
                tx = send()
                return tx if isinstance(tx, str) else tx.hex()
            except Exception as e:                          # noqa: BLE001
                reason = str(e).splitlines()[0][:80]
                time.sleep(15)
                if self._nonce(acct.address) != before:
                    raise SystemExit(f"the node accepted a transaction from {acct.address} but the answer "
                                     f"was lost ({reason}); not sending it twice")
                print(f"      send did not reach the node ({reason}); retrying")
        raise SystemExit("could not submit the transaction after 5 attempts")

    def _wait(self, client, tx, status=TransactionStatus.ACCEPTED):
        # LLM rounds on StudioNet take tens of seconds; poll every 5 s for up
        # to 15 minutes, which stays far under the 60 requests a minute limit.
        #
        # Polling is a read, so it is retried through transport failures: a
        # live run was lost when StudioNet answered one poll with an HTML
        # error page instead of JSON. Sending is never retried here, because a
        # resend after the node accepted the first is a second transaction.
        deadline = time.time() + 900
        while True:
            try:
                return client.wait_for_transaction_receipt(
                    transaction_hash=tx, status=status, interval=5000, retries=12, full_transaction=True)
            except Exception as e:                          # noqa: BLE001
                if time.time() > deadline:
                    raise
                print(f"      still waiting on {tx[:12]}... ({str(e).splitlines()[0][:70]})")
                time.sleep(10)

    def deploy(self, acct, code, args):
        client = self._client(acct)
        tx = self._submit(acct, lambda: client.deploy_contract(code=code, account=acct, args=args))
        print(f"  deploy tx {tx}")
        receipt = self._wait(client, tx, TransactionStatus.FINALIZED)
        out = outcome(receipt)
        address = _find(receipt, ("contract_address", "contractAddress"))
        if not out["ok"] or not address:
            lead = ((receipt.get("consensus_data") or {}).get("leader_receipt") or [{}])[0]
            raise SystemExit(
                f"deploy did not succeed: status={out['status']} result_name={receipt.get('result_name')} "
                f"address={address}\n  leader result: {json.dumps(lead.get('result'), default=str)[:400]}\n"
                f"  genvm: {json.dumps(lead.get('genvm_result'), default=str)[:400]}")
        self.log.append({"step": "deploy", "tx": tx, "status": out["status"], "ok": True,
                         "address": address})
        print(f"  deploy -> {address}  tx {tx}")
        time.sleep(3)
        return address

    def write(self, acct, address, method, args, value=0, step="", expect="ok"):
        """Send one write and record what happened. `expect` is "ok" or
        "refused"; a result that contradicts it stops the run, because the
        demo claims whatever it records."""
        client = self._client(acct)
        tx = self._submit(acct, lambda: client.write_contract(address=address, function_name=method,
                                                             account=acct, args=args, value=int(value)))
        receipt = self._wait(client, tx)
        out = outcome(receipt)
        row = {"step": step or method, "method": method, "tx": tx, "status": out["status"],
               "ok": out["ok"], "refusal": out["refusal"]}
        self.log.append(row)
        mark = "ok" if out["ok"] else ("refused: " + out["refusal"][:90] if out["refusal"] else out["status"])
        print(f"  {row['step']:<44} {mark}\n      tx {tx}")
        if expect == "ok" and not out["ok"]:
            lead = ((receipt.get("consensus_data") or {}).get("leader_receipt") or [{}])[0]
            raise SystemExit(f"{method} was expected to succeed and did not: {mark} "
                             f"(result_name={receipt.get('result_name')})\n  leader result: "
                             f"{json.dumps(lead.get('result'), default=str)[:400]}")
        if expect == "refused" and out["ok"]:
            raise SystemExit(f"{method} was expected to be refused and succeeded")
        time.sleep(3)
        return row

    def read(self, address, method, args=None):
        """A view call, retried through transport failures: reads change nothing."""
        for attempt in range(6):
            try:
                return self.reader.read_contract(address=address, function_name=method, args=args or [])
            except Exception as e:                          # noqa: BLE001
                if attempt == 5:
                    raise
                print(f"      read {method} failed ({str(e).splitlines()[0][:60]}); retrying")
                time.sleep(10)
