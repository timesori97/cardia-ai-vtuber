"""Does the AI actually compare all three shop rows, or fixate on one?

The shop has a top card row, a voucher beside the packs, and the packs. Each
has its own buy parameter. This builds three shops where a DIFFERENT row is
clearly the right buy, and checks it picks the right one each time — a model
that always reaches for the same row fails here even though every answer is
"legal".

Run: python tools/check_shop_rows.py
"""

import json
import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vault

from balatro_link import slim_state
from brain import Brain

MANUAL = vault.manual()
PLAYBOOK = vault.playbook()


def item(label, kind, buy=None, sell=None, effect=""):
    """One card shaped the way the mod's extract_card() reports it."""
    return {"id": 1, "key": label.lower().replace(" ", "_"), "set": kind,
            "label": label, "value": {"effect": effect}, "modifier": {},
            "state": {}, "cost": {"buy": buy or 0, "sell": sell or 0}}


def shop(money, cards, vouchers, packs, jokers=(), reroll=5):
    return {
        "state": "SHOP", "ante_num": 3, "round_num": 7, "money": money,
        "round": {"reroll_cost": reroll},
        "shop": {"count": len(cards), "limit": 2, "cards": list(cards)},
        "vouchers": {"count": len(vouchers), "limit": 1, "cards": list(vouchers)},
        "packs": {"count": len(packs), "limit": 2, "cards": list(packs)},
        "jokers": {"count": len(jokers), "limit": 5, "cards": list(jokers)},
    }


HELD = [item("Joker", "JOKER", sell=2, effect="+4 Mult")]

CASES = [
    # the top-row joker is a run-winning engine and everything else is filler
    ("top card row", "card", shop(
        money=12,
        cards=[item("Baron", "JOKER", buy=8,
                    effect="Each King held in hand gives X1.5 Mult"),
               item("Chaos the Clown", "JOKER", buy=4,
                    effect="1 free Reroll per shop")],
        vouchers=[item("Seed Money", "VOUCHER", buy=10,
                       effect="Raise the cap on interest earned per round to $10")],
        packs=[item("Standard Pack", "BOOSTER", buy=4,
                    effect="Choose 1 of 3 playing cards to add to your deck")],
        jokers=HELD)),

    # the voucher is clearly the best thing here and affordable without
    # going broke — nothing else on the screen is worth the money
    ("voucher (beside the packs)", "voucher", shop(
        money=22,
        cards=[item("8 of Clubs", "DEFAULT", buy=4,
                    effect="Add this card to your deck"),
               item("Chaos the Clown", "JOKER", buy=4,
                    effect="1 free Reroll per shop")],
        vouchers=[item("Grabber", "VOUCHER", buy=10,
                       effect="Permanently gain +1 hand per round")],
        packs=[item("Standard Pack", "BOOSTER", buy=4,
                    effect="Choose 1 of 3 playing cards to add to your deck")],
        jokers=HELD)),

    # nothing on the shelves fits; the pack is the only real value
    ("booster pack", "pack", shop(
        money=8,
        cards=[item("Golden Ticket", "JOKER", buy=6,
                    effect="Played Gold cards earn $4 when scored"),
               item("2 of Diamonds", "DEFAULT", buy=4,
                    effect="Add this card to your deck")],
        vouchers=[item("Hone", "VOUCHER", buy=10,
                       effect="Foil, Holographic and Polychrome cards appear 2X more often")],
        packs=[item("Celestial Pack", "BOOSTER", buy=4,
                    effect="Choose 1 of 3 Planet cards to be used immediately")],
        jokers=HELD)),
]


def main():
    b = Brain()
    print("\n=== which row does it buy from? ===\n")
    right = 0
    try:
        for label, want, raw in CASES:
            slim = slim_state(raw)
            out = b.balatro_decision(slim, [], max_thinking=0, manual=MANUAL,
                                     playbook=PLAYBOOK, model_override="opus")
            plan = (out or {}).get("plan") or []
            bought = [k for p in plan if p.get("action") == "buy"
                      for k in ("card", "voucher", "pack") if k in p]
            ok = want in bought
            right += ok
            print("  expected %-26s got %-22s %s"
                  % (label, ", ".join(bought) or "(bought nothing)",
                     "OK" if ok else "MISS"))
            print("      plan: %s" % json.dumps(plan))
            print("      why : %s\n" % (out or {}).get("why"))
    finally:
        b.close_warm()
    print("  %d of %d picked the right row" % (right, len(CASES)))


if __name__ == "__main__":
    main()
