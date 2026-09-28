"""Validate a contract file against the live Studionet runtime without deploying it.

    python scripts/schema_check.py contracts/tally.py

gen_getContractSchemaForCode runs the file through the runtime Studionet
executes and returns the public schema, or the error the runtime raised. It is
the cheapest way to learn that a storage type, a decorator or an import is
refused before a deploy transaction is spent on it.
"""

import json
import pathlib
import sys
import urllib.request

RPC = "https://studio.genlayer.com/api"


def schema(code):
    body = json.dumps({"jsonrpc": "2.0", "method": "gen_getContractSchemaForCode",
                       "params": [code.encode("utf-8").hex()], "id": 1}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json",
                                                          "User-Agent": "schema-check/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    out = schema(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    if "error" in out:
        print("REFUSED:", json.dumps(out["error"])[:1500])
        sys.exit(1)
    res = out.get("result", {})
    methods = res.get("methods", {}) if isinstance(res, dict) else {}
    print("OK: ctor", json.dumps(res.get("ctor", {}))[:200])
    for name, spec in sorted(methods.items()):
        kind = "view" if spec.get("readonly") else ("write payable" if spec.get("payable") else "write")
        print(f"  {kind:14} {name}({', '.join(a[0] if isinstance(a, list) else str(a) for a in spec.get('params', []))})")
