#!/usr/bin/env python3
"""Grade EDGE ledger. The model does not recompute n.

n counts only rows with a numeric openLine and a numeric closeLine.
A cover board is not a sample. Backfill with one print stays pass.
Official only if the open beat the close and n is at least 5.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "ledger.json"
SCORE = ROOT / "score.json"

LINE = re.compile(r"([A-Za-z0-9]{1,12})\s*([+-]\d+(?:\.\d+)?)")
TOTAL = re.compile(r"^[Uu](\d+(?:\.\d+)?)\s*([+-]\d+)$")
AMERICAN = re.compile(r"([+-]\d{3,4})")


def missing(value):
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower().startswith("missing")


def num(value):
    if missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def row_id(row):
    return "|".join(str(row.get(k) or "") for k in ("sport", "date", "event", "market"))


def extract_open(row):
    side = row.get("side") or ""
    open_line = row.get("openLine")
    open_price = row.get("openPrice")
    if num(open_line) is not None or (open_line not in (None, "") and not missing(open_line)):
        return side or "missing", open_line, open_price if open_price not in (None, "") else "missing"
    source = str(row.get("open") or "")
    market = str(row.get("market") or "")
    total = TOTAL.match(source.strip()) or TOTAL.match(market.strip())
    if total:
        return "under", float(total.group(1)), int(total.group(2))
    for text in (source, market):
        hit = LINE.search(text)
        if hit and " / " not in text:
            return hit.group(1), float(hit.group(2)), "missing"
    price = AMERICAN.search(source)
    if price and " / " not in source and not LINE.search(source):
        return "missing", "missing", int(price.group(1))
    return "missing", "missing", "missing"


def normalize(row):
    side, open_line, open_price = extract_open(row)
    close = row.get("close")
    close_line = row.get("closeLine")
    close_price = row.get("closePrice")
    if missing(close):
        close_line = "missing"
        close_price = "missing"
    elif num(close_line) is None:
        close_line = "missing"
        close_price = "missing" if missing(close_price) else close_price
    row["id"] = row_id(row)
    row["side"] = side
    row["openLine"] = open_line
    row["openPrice"] = open_price
    row["closeLine"] = close_line
    row["closePrice"] = close_price
    for key in ("openTime", "closeTime", "injury", "weather"):
        if missing(row.get(key)):
            row[key] = "missing"
    if num(open_line) is None or num(close_line) is None:
        row["clv"] = "missing"
        row["clvPoints"] = "missing"
        row["clvCents"] = "missing"
        row["bucket"] = "pass"
    return row


def grade(rows):
    groups = defaultdict(list)
    priced = 0
    for row in rows:
        if num(row.get("openLine")) is None or num(row.get("closeLine")) is None:
            continue
        priced += 1
        points = num(row["openLine"]) - num(row["closeLine"])
        cents = None
        if num(row.get("openPrice")) is not None and num(row.get("closePrice")) is not None:
            cents = num(row["openPrice"]) - num(row["closePrice"])
        row["clvPoints"] = round(points, 3)
        row["clvCents"] = "missing" if cents is None else round(cents, 1)
        row["clv"] = str(row["clvPoints"]) + " pt"
        beat = points > 0 or (points == 0 and cents is not None and cents > 0)
        row["openBeatClose"] = beat
        groups[(row.get("sport"), row.get("market"), row.get("side"))].append(row)
    patterns = []
    for key, group in sorted(groups.items(), key=lambda item: -len(item[1])):
        n = len(group)
        beats = sum(1 for row in group if row.get("openBeatClose"))
        official = n >= 5 and beats == n
        for row in group:
            if official and row.get("openBeatClose"):
                row["bucket"] = "official"
            elif row.get("bucket") != "pass":
                row["bucket"] = "shadow"
        patterns.append({
            "id": "|".join(str(part) for part in key),
            "n": n,
            "beat": beats,
            "official": official,
            "note": "Priced sample only. n under 5 stays shadow.",
        })
    if not patterns:
        patterns.append({
            "id": "priced",
            "n": 0,
            "beat": 0,
            "official": False,
            "note": "No row has a numeric openLine and closeLine. Backfill stays pass. A cover board is not a sample.",
        })
    official_n = sum(1 for row in rows if row.get("bucket") == "official")
    return {
        "pricedN": priced,
        "officialN": official_n,
        "official": "0-0" if official_n == 0 else str(official_n),
        "patterns": patterns,
    }


def main():
    ledger = json.loads(LEDGER.read_text())
    rows = [normalize(row) for row in ledger.get("rows") or []]
    seen = {}
    for row in rows:
        seen[row["id"]] = row
    rows = list(seen.values())
    scored = grade(rows)
    ledger["rows"] = rows
    ledger["patterns"] = scored["patterns"]
    ledger["law"] = (
        "Row id is sport|date|event|market. First print writes open and is never overwritten. "
        "Close is the last number before start. A candidate is not a close. A result board is not a close. "
        "grade.py computes n. The model does not. Official only if the open beat the close and n is at least 5."
    )
    ledger["gap"] = (
        "Backfill has no numeric close. pricedN is the only sample. Cover notes are not n. Official stays 0-0 until a row has both prices."
    )
    ledger["score"] = {
        "official": "0-0",
        "pricedN": scored["pricedN"],
        "rows": len(rows),
        "passN": sum(1 for row in rows if row.get("bucket") == "pass"),
    }
    LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")
    SCORE.write_text(json.dumps(ledger["score"], indent=2) + "\n")
    print(json.dumps(ledger["score"]))


if __name__ == "__main__":
    main()
