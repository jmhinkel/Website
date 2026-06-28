#!/usr/bin/env python3
"""
Fetches market data for the Gold Signal Dashboard and writes data.json.

Runs inside GitHub Actions (on GitHub's servers), so there is NO browser and
NO CORS problem — it can read these free feeds directly. The dashboard then
reads the resulting data.json from your own site (same origin, no CORS).

Output shape (data.json):
{
  "asOf": "2026-06-28T13:00:00Z",
  "prices": { "gold": {"ok":true,"close":...,"open":...,"pct":...,"date":...}, ... },
  "fred":   { "realRate": {"ok":true,"value":...,"date":...}, ... }
}

If a symbol shows "ok": false in data.json, its ticker below is wrong —
fix it and the next run self-corrects.
"""

import json, datetime, urllib.request

# Stooq tickers (correct any that show ok:false in data.json)
STOOQ = {
    "gold":   "xauusd",
    "silver": "xagusd",
    "dxy":    "usdindx",   # if ok:false, try: usd_i, dx.f
    "gdx":    "gdx.us",
    "wti":    "cl.f",
    "copper": "hg.f",
    "gvz":    "^gvz",
}

# FRED series (free CSV, no API key)
FRED = {
    "realRate":  "DFII10",   # 10yr TIPS real yield
    "breakeven": "T5YIFR",   # 5yr-5yr forward inflation expectation
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def stooq(sym):
    txt = get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlc&h&e=csv")
    lines = txt.strip().splitlines()
    if len(lines) < 2:
        raise ValueError("empty response")
    cols = lines[1].split(",")  # Symbol,Date,Time,Open,High,Low,Close,Volume
    open_ = float(cols[3])
    close = float(cols[6])
    if close <= 0:
        raise ValueError("no quote (bad ticker?)")
    pct = ((close - open_) / open_ * 100) if open_ else 0.0
    return {"ok": True, "close": close, "open": open_, "pct": pct,
            "date": cols[1], "symbol": sym}


def fred(series):
    txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
    rows = txt.strip().splitlines()[1:]
    for row in reversed(rows):
        parts = row.split(",")
        try:
            return {"ok": True, "value": float(parts[-1]),
                    "date": parts[0], "series": series}
        except ValueError:
            continue  # FRED uses "." for missing values
    raise ValueError("no numeric observation")


def main():
    out = {
        "asOf": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prices": {},
        "fred": {},
    }
    for key, sym in STOOQ.items():
        try:
            out["prices"][key] = stooq(sym)
        except Exception as e:
            out["prices"][key] = {"ok": False, "error": str(e), "symbol": sym}
    for key, series in FRED.items():
        try:
            out["fred"][key] = fred(series)
        except Exception as e:
            out["fred"][key] = {"ok": False, "error": str(e), "series": series}

    with open("data.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
