"""Measure real Balatro decision latency per screen and setting.

The stream feels slow when a screen costs a full brain round trip, so this
times the two screens that dominate a run:
  - SELECTING_HAND (~70% of all calls)  -> Sonnet, thinking 0
  - SHOP (run-shaping)                  -> Opus, thinking 512 vs 0

Run: python tools/bench_balatro.py   (best with the game NOT running)
"""

import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vault

from brain import Brain

HAND_STATE = {
    "state": "SELECTING_HAND", "ante": 2, "round": 4, "money": 12,
    "deck": "Red Deck", "stake": "White Stake",
    "hands_left": 3, "discards_left": 2, "chips_scored": 0,
    "current_blind": {"name": "Big Blind", "score": 450, "effect": ""},
    "hand": [{"rank": "K", "suit": "Hearts"}, {"rank": "9", "suit": "Spades"},
             {"rank": "K", "suit": "Clubs"}, {"rank": "3", "suit": "Hearts"},
             {"rank": "7", "suit": "Hearts"}, {"rank": "A", "suit": "Hearts"},
             {"rank": "J", "suit": "Diamonds"}, {"rank": "4", "suit": "Hearts"}],
    "jokers": [{"name": "Joker", "effect": "+4 Mult", "sell": 2}],
    "joker_slots": 5,
    "hand_levels": {"Pair": {"level": 2, "chips": 20, "mult": 3},
                    "Flush": {"level": 1, "chips": 35, "mult": 4}},
}

SHOP_STATE = {
    "state": "SHOP", "ante": 2, "round": 4, "money": 21,
    "deck": "Red Deck", "stake": "White Stake", "reroll_cost": 5,
    "jokers": [{"name": "Joker", "effect": "+4 Mult", "sell": 2}],
    "joker_slots": 5,
    "shop": {"cards": [{"name": "Cavendish", "buy": 8,
                        "effect": "X3 Mult, 1 in 1000 chance to be destroyed"},
                       {"name": "Green Joker", "buy": 6,
                        "effect": "+1 Mult per hand played, -1 per discard"}],
             "vouchers": [{"name": "Clearance Sale", "buy": 10,
                           "effect": "All cards and packs in shop are 25% off"}],
             "boosters": [{"name": "Celestial Pack", "buy": 4,
                           "effect": "Choose 1 of 3 Planet cards"}]},
    "hand_levels": {"Pair": {"level": 2, "chips": 20, "mult": 3}},
}

MANUAL = vault.manual()
PLAYBOOK = vault.playbook()
LESSONS = vault.lessons()


def bench(label, fn, runs=2):
    times = []
    for i in range(runs):
        t = time.monotonic()
        out = fn()
        ms = int((time.monotonic() - t) * 1000)
        times.append(ms)
        plan = ""
        if out and out.get("plan"):
            plan = " + ".join(p.get("action", "?") for p in out["plan"])
        print("  run %d: %5.1fs  ok=%-5s %s" % (i + 1, ms / 1000, out is not None, plan))
    avg = sum(times) / len(times) / 1000
    print("  => %s: avg %.1fs\n" % (label, avg))
    return avg


def main():
    b = Brain()
    print("\n=== BALATRO DECISION LATENCY ===\n")

    print("[1] Routine hand - Sonnet, thinking 0, no playbook (the common case):")
    hand = bench("routine hand", lambda: b.balatro_decision(
        HAND_STATE, [], max_thinking=0, lessons=LESSONS, manual=MANUAL,
        playbook="", model_override="sonnet"))

    print("[2] Shop - Opus, thinking 512 (current setting):")
    shop_512 = bench("shop opus/512", lambda: b.balatro_decision(
        SHOP_STATE, [], max_thinking=512, lessons=LESSONS, manual=MANUAL,
        playbook=PLAYBOOK, model_override="opus"))

    print("[3] Shop - Opus, thinking 0 (does hidden thinking earn its seconds?):")
    shop_0 = bench("shop opus/0", lambda: b.balatro_decision(
        SHOP_STATE, [], max_thinking=0, lessons=LESSONS, manual=MANUAL,
        playbook=PLAYBOOK, model_override="opus"))

    print("[4] Reference - routine hand WITH playbook (what we just removed):")
    hand_pb = bench("hand + playbook", lambda: b.balatro_decision(
        HAND_STATE, [], max_thinking=0, lessons=LESSONS, manual=MANUAL,
        playbook=PLAYBOOK, model_override="sonnet"))

    print("summary: hand %.1fs (was %.1fs with playbook) | shop %.1fs think512"
          " vs %.1fs think0" % (hand, hand_pb, shop_512, shop_0))


if __name__ == "__main__":
    main()
