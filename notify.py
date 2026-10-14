#!/usr/bin/env python3
"""EDGE phone alerts (v1). Sends a push through ntfy (free app, no account) when something Zack should know happens:

  real-money trade placed, real-money trade settled, the real book hitting its stop loss or take profit,
  the switch going on or off, a strategy turning official or retired, the Kalshi key being rejected.

Needs NTFY_TOPIC (the private channel name Zack subscribed to in the ntfy app). Without it, nothing is sent.
Remembers what it has already announced in stats/alerts_state.json; the first run only records, so the phone
does not get a backlog.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "stats" / "alerts_state.json"
TRADES = ROOT / "trading" / "ledger.json"
LEDGER = ROOT / "ledger" / "ledger.json"
SITE = "https://edgesystem.netlify.app"


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def send(topic, title, body, tags="", priority="default"):
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(), "Tags": tags,
                                          "Priority": priority, "Click": SITE})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception as exc:  # noqa: BLE001
        print("ntfy", exc)
        return False


def tid(t):
    return f"{t.get('ticker')}|{t.get('side')}|{t.get('time')}"


def main():
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    trades = load(TRADES, {})
    ledger = load(LEDGER, {})
    live = trades.get("live") or {}
    status = trades.get("status") or {}
    now = {
        "placed": sorted(tid(t) for t in live.get("trades") or []),
        "settled": sorted(tid(t) for t in live.get("trades") or [] if t.get("status") == "settled"),
        "stopped": (live.get("stopped") or {}).get("at"),
        "switch": bool(status.get("liveActive")),
        "patterns": {p["id"]: p.get("status") for p in ledger.get("patterns") or [] if p.get("id")},
        "keyError": (trades.get("account") or {}).get("keys") == "error",
    }
    before = load(STATE, None)
    msgs = []
    if before is not None:
        by_id = {tid(t): t for t in live.get("trades") or []}
        for k in set(now["placed"]) - set(before.get("placed") or []):
            t = by_id[k]
            msgs.append(("Real trade placed",
                         f"{t['side'].upper()} {t['title']} ({t['sport']}): {t['count']} at {t['ask']:.2f}, "
                         f"${t['cost'] + t['fee']:.2f}. Fair {t['fair']:.0%}. {t.get('source')}.", "moneybag", "high"))
        for k in set(now["settled"]) - set(before.get("settled") or []):
            t = by_id[k]
            msgs.append(("Real trade settled", f"{'Won' if t.get('won') else 'Lost'} {t['title']}: "
                         f"{'+' if t.get('pnl', 0) >= 0 else '-'}${abs(t.get('pnl', 0)):.2f}.",
                         "white_check_mark" if t.get("won") else "x", "default"))
        if now["stopped"] and now["stopped"] != before.get("stopped"):
            why = (live.get("stopped") or {}).get("why", "a limit")
            msgs.append(("Trading stopped", f"The real-money book hit its {why}. It stays stopped until you switch "
                         "it off and on in the Trading tab.", "rotating_light", "urgent"))
        if now["switch"] != before.get("switch"):
            msgs.append(("Trading switch", "Real-money trading is now ON." if now["switch"]
                         else f"Real-money trading is now OFF ({status.get('liveWhy', '')}).", "electric_plug", "default"))
        for pid, st in now["patterns"].items():
            old = (before.get("patterns") or {}).get(pid)
            if st != old and st in ("official", "retire"):
                msgs.append((f"Strategy {'official' if st == 'official' else 'retired'}",
                             f"{pid} is now {st}." + (" Its A picks now carry a stake." if st == "official" else ""),
                             "trophy" if st == "official" else "wastebasket", "high"))
        if now["keyError"] and not before.get("keyError"):
            msgs.append(("Kalshi key rejected", "The desk could not use the Kalshi key. Check the GitHub secrets.",
                         "warning", "high"))
    if topic and not (before or {}).get("topicSeen"):
        msgs.insert(0, ("EDGE alerts connected", "You'll get a push here for real trades, settlements, stop loss or "
                        "take profit, the switch, and strategies going official.", "tada", "default"))
    now["topicSeen"] = bool(topic) or bool((before or {}).get("topicSeen"))
    sent = 0
    if topic:
        for title, body, tags, pr in msgs[:10]:
            sent += send(topic, title, body, tags, pr)
    STATE.write_text(json.dumps(now, indent=1))
    print(json.dumps({"alerts": len(msgs), "sent": sent, "topicSet": bool(topic), "firstRun": before is None,
                      "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}))


if __name__ == "__main__":
    main()
