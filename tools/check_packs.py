"""Does the brain now SEE vouchers and booster packs, and can it open one?

The API puts each shop row at the top level of the state (shop / vouchers /
packs), but slim_state used to look for them inside "shop" — so the brain
only ever saw the joker row and could never buy a voucher or a pack.

Run: python tools/check_packs.py
"""

import json
import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vault

from balatro_link import is_pack_state, slim_state

# Shaped exactly like the mod's extract_card(): effect lives in value.effect,
# modifiers in modifier{}, price in cost{}. Getting this wrong is the whole
# reason the brain used to see nameless prices and buy nothing.
def item(label, kind, buy=None, sell=None, effect="", **mod):
    return {"id": 1, "key": label.lower().replace(" ", "_"), "set": kind,
            "label": label, "value": {"effect": effect},
            "modifier": mod, "state": {},
            "cost": {"buy": buy or 0, "sell": sell or 0}}


def playing(rank, suit, **mod):
    return {"id": 1, "key": "c_%s" % rank, "set": "DEFAULT", "label": "Base Card",
            "value": {"rank": rank, "suit": suit, "effect": ""},
            "modifier": mod, "state": {}, "cost": {"buy": 0, "sell": 0}}


RAW_SHOP = {
    "state": "SHOP", "ante_num": 2, "round_num": 4, "money": 21,
    "round": {"reroll_cost": 5},
    "shop": {"count": 2, "limit": 2, "cards": [
        item("Cavendish", "JOKER", buy=8,
             effect="X3 Mult, 1 in 1000 chance this card is destroyed"),
        item("Green Joker", "JOKER", buy=6,
             effect="+1 Mult per hand played, -1 Mult per discard")]},
    "vouchers": {"count": 1, "limit": 1, "cards": [
        item("Clearance Sale", "VOUCHER", buy=10,
             effect="All cards and packs in shop are 25% off")]},
    "packs": {"count": 2, "limit": 2, "cards": [
        item("Celestial Pack", "BOOSTER", buy=4,
             effect="Choose 1 of 3 Planet cards to be used immediately"),
        item("Buffoon Pack", "BOOSTER", buy=6,
             effect="Choose 1 of 2 Joker cards to be used immediately")]},
    "jokers": {"count": 1, "limit": 5, "cards": [
        item("Joker", "JOKER", sell=2, effect="+4 Mult")]},
}

RAW_PACK_OPEN = {
    "state": "SMODS_BOOSTER_OPENED", "ante_num": 2, "money": 15,
    "pack": {"count": 3, "limit": 3, "cards": [
        item("The Magician", "TAROT",
             effect="Enhances 2 selected cards into Lucky Cards"),
        item("The Hermit", "TAROT", effect="Doubles money (Max of $20)"),
        item("Strength", "TAROT",
             effect="Increases rank of up to 2 selected cards by 1")]},
    "hand": {"count": 3, "limit": 8, "cards": [
        playing("K", "HEARTS"), playing("K", "CLUBS"),
        playing("3", "SPADES", enhancement="STEEL")]},
}

print("\n[1] SHOP — what the brain can see")
slim = slim_state(RAW_SHOP)
shop = slim.get("shop") or {}
for row in ("cards", "vouchers", "packs"):
    items = shop.get(row) or []
    print("  %-8s %s" % (row, "OK" if items else "MISSING"))
    for c in items:
        print("      %-16s %-8s $%-3s %s"
              % (c.get("name"), c.get("type", "?"), c.get("buy", "-"),
                 (c.get("effect") or "!! NO EFFECT TEXT")[:56]))

print("\n[2] pack open — is it recognised, and are the choices visible?")
print("  is_pack_state: %s" % is_pack_state(RAW_PACK_OPEN["state"]))
slim2 = slim_state(RAW_PACK_OPEN)
print("  pack_choices : %s"
      % ", ".join(c.get("name") for c in slim2.get("pack_choices") or []))
print("  hand visible : %s   <- needed for Tarot targets"
      % ", ".join("%s%s" % (c.get("rank"), (c.get("suit") or "")[:1])
                  for c in slim2.get("hand") or []))

print("\n[3] size check (the brain pays for every character)")
for label, raw, s in (("shop", RAW_SHOP, slim), ("pack", RAW_PACK_OPEN, slim2)):
    print("  %-5s raw %5d chars -> slim %4d chars"
          % (label, len(json.dumps(raw)), len(json.dumps(s))))

print("\n[4] real brain calls — does it actually use them?")
from brain import Brain

MANUAL = vault.manual()
PLAYBOOK = vault.playbook()
b = Brain()
try:
    for label, state in (("shop with packs", slim), ("pack open", slim2)):
        out = b.balatro_decision(state, [], max_thinking=0, manual=MANUAL,
                                 playbook=PLAYBOOK, model_override="opus")
        if not out:
            print("  %-16s -> no decision" % label)
            continue
        plan = out["plan"]
        print("  %-16s -> %s" % (label, json.dumps(plan)))
        print("  %-16s    why: %s" % ("", out.get("why")))
        if label == "pack open":
            item = plan[0]
            ok = item.get("action") == "pack" and (
                item.get("skip") or isinstance(item.get("card"), int))
            print("  %-16s    valid pack action: %s" % ("", ok))
finally:
    b.close_warm()
