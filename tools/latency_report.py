"""How fast are decisions actually coming back, warm vs cold?

Reads logs/brain.jsonl and splits game decisions by whether a live (warm) CLI
process served them. The gap between total time and model time is pure process
overhead — the thing the warm path exists to delete.

Run: python tools/latency_report.py [minutes_back]
"""

import json
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG = "D:/ai-vtuber-kit/logs/brain.jsonl"
GAME_ROUTES = ("balatro_decision", "game_decision")


def load(minutes):
    cutoff = time.time() - minutes * 60
    rows = []
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("route") not in GAME_ROUTES or not e.get("ok"):
                continue
            try:
                ts = time.mktime(time.strptime(e["ts"], "%Y-%m-%d %H:%M:%S"))
            except (KeyError, ValueError):
                continue
            if ts < cutoff:
                continue
            total = (e.get("latency_ms") or 0) / 1000.0
            api = (e.get("api_ms") or 0) / 1000.0
            rows.append((bool(e.get("warm")), total, api, e.get("model")))
    return rows


def show(label, rows):
    if not rows:
        print("  %-22s (none)" % label)
        return
    totals = [r[1] for r in rows]
    overhead = [max(0.0, r[1] - r[2]) for r in rows]
    print("  %-22s n=%-3d  median %5.1fs  min %5.1fs  max %5.1fs   "
          "process overhead median %5.1fs"
          % (label, len(rows), statistics.median(totals), min(totals),
             max(totals), statistics.median(overhead)))


def main():
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    rows = load(minutes)
    print("\n=== game decisions in the last %d minutes (n=%d) ===\n"
          % (minutes, len(rows)))
    show("warm (live process)", [r for r in rows if r[0]])
    show("cold (new process)", [r for r in rows if not r[0]])
    print()
    for model in sorted({r[3] for r in rows if r[3]}):
        show("  warm/" + str(model),
             [r for r in rows if r[0] and r[3] == model])


if __name__ == "__main__":
    main()
