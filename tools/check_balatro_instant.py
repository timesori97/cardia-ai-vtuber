"""Which Balatro screens skip the brain entirely? (speed sanity check)"""

import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator

o = Orchestrator.__new__(Orchestrator)

cases = [
    ("round payout", {"state": "ROUND_EVAL"}),
    ("boss blind (cannot skip)", {"state": "BLIND_SELECT", "blinds": {
        "boss": {"name": "The Club", "type": "BOSS", "status": "SELECT"}}}),
    ("run opening (ante 1, no jokers)", {
        "state": "BLIND_SELECT", "ante": 1, "money": 4, "blinds": {
            "small": {"name": "Small Blind", "type": "SMALL", "status": "SELECT",
                      "tag": "Voucher Tag"},
            "boss": {"name": "The Club", "type": "BOSS", "status": "UPCOMING"}}}),
    ("small blind, mid-run", {"state": "BLIND_SELECT", "ante": 2,
                              "jokers": [{"name": "Joker"}], "blinds": {
        "small": {"name": "Small Blind", "type": "SMALL", "status": "SELECT"},
        "boss": {"name": "The Club", "type": "BOSS", "status": "UPCOMING"}}}),
    ("shop, broke", {"state": "SHOP", "money": 1, "reroll_cost": 5,
                     "shop": {"cards": [{"name": "Joker", "buy": 6}]}}),
    ("shop, can afford", {"state": "SHOP", "money": 10, "reroll_cost": 5,
                          "shop": {"cards": [{"name": "Joker", "buy": 6}]}}),
    ("shop, broke but can reroll", {"state": "SHOP", "money": 5, "reroll_cost": 5,
                                    "shop": {"cards": [{"name": "Joker", "buy": 6}]}}),
    ("playing a hand", {"state": "SELECTING_HAND", "hand": [{"rank": "A"}]}),
]

for label, st in cases:
    got = o._balatro_instant(st)
    print("  %-28s -> %s" % (label,
                             ("INSTANT: " + got["action"]) if got else "brain decides"))
