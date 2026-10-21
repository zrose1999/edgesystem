#!/usr/bin/env python3
"""Kalshi order-path self-test on the DEMO exchange (mock funds). Added 2026-10-21.

Checks that the order code kalshi.py uses for real money works against Kalshi's current API, without risking a cent:
  1. a post-only good-till-canceled bid for 1 YES contract at 1 cent on an open demo market (cannot fill), with an
     expiration 10 minutes out: the maker path
  2. read it back (fills, status, fee fields)
  3. cancel it
  4. an immediate-or-cancel bid at 1 cent (should fill 0): the taker path and its read-back
Prints one JSON line and writes trading/selftest.json. Needs KALSHI_DEMO_KEY_ID and KALSHI_DEMO_PRIVATE_KEY.
Never touches production: the base URL is fixed to DEMO.

  python3 kalshi_selftest.py
"""

import json
import os
import time
from pathlib import Path

import kalshi as K

OUT = Path(__file__).resolve().parent / "trading" / "selftest.json"


def main():
    out = {"at": K.iso(K.now_utc()), "base": K.DEMO, "steps": []}

    def step(name, ok, **info):
        out["steps"].append({"step": name, "ok": bool(ok), **info})
        return ok

    try:
        signer = K.Signer(os.environ["KALSHI_DEMO_KEY_ID"], os.environ["KALSHI_DEMO_PRIVATE_KEY"])
        step("keys", True)
    except Exception as exc:  # noqa: BLE001
        step("keys", False, error=f"{type(exc).__name__}: {exc}"[:200])
        return finish(out)

    try:
        mk = K.api_get(K.DEMO, "/markets", {"status": "open", "limit": 200}).get("markets") or []
    except Exception as exc:  # noqa: BLE001
        step("markets", False, error=str(exc)[:200])
        return finish(out)
    pick = next((m for m in mk if (K.f(m.get("yes_ask_dollars")) or 0) >= 0.05), None)
    if not step("markets", pick is not None, open=len(mk), ticker=(pick or {}).get("ticker")):
        return finish(out)

    c = {"ticker": pick["ticker"], "side": "yes", "ask": 0.01,
         "commence": K.iso(K.now_utc().replace(microsecond=0)) }
    # maker path: post-only resting bid at 1 cent, expiring in 10 minutes
    exp = time.time() + 600
    oid, how = K.create_order(signer, K.DEMO, c, 1, 0.01, "good_till_canceled", post_only=True, expiration=exp)
    if step("maker create", oid, path=how, orderId=oid):
        try:
            o = K.get_order(signer, K.DEMO, oid)
            filled, cost, fees = K.order_numbers(o, 0.01)
            step("maker read-back", True, status=o.get("status"), filled=filled,
                 fields=sorted(k for k in o if "fill" in k or "fee" in k or "side" in k))
        except Exception as exc:  # noqa: BLE001
            step("maker read-back", False, error=str(exc)[:200])
        try:
            r = signer.call(K.DEMO, "DELETE", f"/portfolio/orders/{oid}")
            step("cancel", True, reduced=r.get("reduced_by_fp") or r.get("reduced_by"),
                 status=(r.get("order") or {}).get("status"))
        except Exception as exc:  # noqa: BLE001
            step("cancel", False, error=str(exc)[:200])
    # taker path: IOC at 1 cent, should fill nothing
    try:
        res = K.place(signer, K.DEMO, c, 1)
        step("taker IOC", True, result=res)
    except Exception as exc:  # noqa: BLE001
        step("taker IOC", False, error=str(exc)[:200])
    return finish(out)


def finish(out):
    out["allOk"] = all(s["ok"] for s in out["steps"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
