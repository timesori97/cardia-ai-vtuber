"""A/B: does the shop's 512-token hidden thinking budget earn its seconds?

Shops are the slowest screen in a Balatro run and happen every round, so this
is the one setting worth measuring properly. Alternates the two configs so a
slow patch on the API hits both equally.

Run: python tools/bench_shop_think.py
"""

import statistics
import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import Brain
from bench_balatro import LESSONS, MANUAL, PLAYBOOK, SHOP_STATE

RUNS = 4


def main():
    b = Brain()
    results = {512: [], 0: []}
    plans = {512: [], 0: []}
    print("\n=== SHOP: thinking 512 vs 0 (Opus, %d runs each, alternating) ===\n" % RUNS)
    for i in range(RUNS):
        for think in (512, 0):
            t = time.monotonic()
            out = b.balatro_decision(SHOP_STATE, [], max_thinking=think,
                                     lessons=LESSONS, manual=MANUAL,
                                     playbook=PLAYBOOK, model_override="opus")
            secs = time.monotonic() - t
            results[think].append(secs)
            plan = " + ".join(p.get("action", "?") for p in (out or {}).get("plan", []))
            plans[think].append(plan)
            print("  think %3d  run %d: %5.1fs  %s" % (think, i + 1, secs, plan))
    print()
    for think in (512, 0):
        vals = results[think]
        print("  think %3d: median %.1fs  min %.1fs  max %.1fs"
              % (think, statistics.median(vals), min(vals), max(vals)))
    print("\n  plans produced (did it finish the screen in one call?):")
    for think in (512, 0):
        closed = sum(1 for p in plans[think] if "next_round" in p)
        print("    think %3d: %d/%d ended with next_round" % (think, closed, RUNS))


if __name__ == "__main__":
    main()
