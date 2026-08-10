"""End-to-end: is a real balatro_decision faster now, and still correct?

Runs the actual Brain.balatro_decision several times and reports each call's
wall clock plus whether the warm (live process) path served it. The first call
pays the process boot; everything after it should be much faster.

Run: python tools/bench_warm_route.py
"""

import json
import statistics
import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import Brain
from bench_balatro import HAND_STATE, LESSONS, MANUAL, PLAYBOOK, SHOP_STATE

ROUNDS = 6


def warm_flag(b):
    """Did the last logged call use the live process?"""
    try:
        with open("D:/ai-vtuber-kit/logs/brain.jsonl", encoding="utf-8") as f:
            last = f.readlines()[-1]
        return json.loads(last).get("warm")
    except Exception:
        return None


def main():
    b = Brain()
    print("\n=== balatro_decision, %d calls through the real brain ===\n" % ROUNDS)
    times = []
    try:
        for i in range(ROUNDS):
            # alternate hand/shop so both models get exercised
            shop = i % 3 == 2
            state = SHOP_STATE if shop else dict(HAND_STATE, hands_left=4 - (i % 3))
            t = time.monotonic()
            out = b.balatro_decision(
                state, [], max_thinking=0, lessons=LESSONS, manual=MANUAL,
                playbook=PLAYBOOK if shop else "",
                model_override="opus" if shop else "sonnet")
            secs = time.monotonic() - t
            times.append(secs)
            plan = " + ".join(p.get("action", "?") for p in (out or {}).get("plan", []))
            print("  %d. %-5s %5.1fs  warm=%-5s  %s"
                  % (i + 1, "SHOP" if shop else "hand", secs, warm_flag(b),
                     plan or "FAILED"))
    finally:
        b.close_warm()

    after_first = times[1:]
    print("\n  first call (pays the boot): %.1fs" % times[0])
    print("  after that: median %.1fs   min %.1fs   max %.1fs"
          % (statistics.median(after_first), min(after_first), max(after_first)))
    print("  cold baseline measured earlier: 9-11s idle, 20-50s under stream load")


if __name__ == "__main__":
    main()
