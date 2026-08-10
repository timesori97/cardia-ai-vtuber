"""Does the distiller actually prune bad notes, or just pile more on?

Feeds it the real vault notes (which contain known-bad lines, e.g. treating
the Small Blind as a deadly enemy) plus one run, and shows what comes back.
The measure is not "did it write something" but "did the wrong lines die".

Run: python tools/bench_lessons.py
"""

import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vault

from brain import Brain

LESSONS = vault.lessons()
PLAYBOOK = vault.playbook()

RUN = ("Result: LOST on the Blue Deck at White Stake. Reached Ante 3 round 8"
       " with $0. Killed by: The Wall (extra large blind). Jokers: Green"
       " Joker, Even Steven, Scary Face. Levelled hands: Flush L3, Two Pair"
       " L2. Key choices: A1 SHOP: buy (Buffoon pack for first joker) |"
       " A2 SHOP: buy (Celestial to level Two Pair) | A2 SHOP: buy (Scary"
       " Face +30 chips per face) | A3 SHOP: next_round (nothing affordable)")

BAD = ["small blind", "big blind"]


def main():
    b = Brain()
    try:
        out = b.distill_lessons(RUN, LESSONS, PLAYBOOK, game="Balatro")
    finally:
        b.close_warm()
    if not out:
        print("no result")
        return
    lessons, playbook = out

    print("\n=== new lessons (%d) ===\n" % len(lessons))
    for line in lessons:
        print("  - %s" % line)

    print("\n=== did the known-bad lines survive? ===")
    joined = (" ".join(lessons) + " " + playbook).lower()
    for phrase in BAD:
        hits = joined.count("[[%s]]" % phrase)
        print("   %-14s mentioned %d time(s)  %s"
              % (phrase, hits, "gone" if hits == 0 else "STILL THERE"))

    print("\n=== playbook: %d lines, %d chars (caps: 35 / 3500) ==="
          % (len(playbook.splitlines()), len(playbook)))
    print("\n".join("  " + ln for ln in playbook.splitlines()[:14]))


if __name__ == "__main__":
    main()
