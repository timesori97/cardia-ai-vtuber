"""Balatro game link — the counterpart to Slay the Spire's Communication Mod.

balatrobot (a Steamodded mod) serves a JSON-RPC 2.0 API on localhost. Where
the StS link reads states from stdin, here we poll `gamestate` and post
actions. Everything above this file (brain, TTS, avatar, chat, safety, the
Obsidian learning loop) is reused unchanged.

Verified against balatrobot v1.5.2 / Balatro 1.0.1o on 2026-08-01.

Actions the API accepts (0-based indices):
  play/discard {cards:[i,...]}   buy {card|voucher|pack:i}   sell {joker|consumable:i}
  use {consumable:i, cards:[i]}  rearrange {hand|jokers|consumables:[order]}
  select | skip | reroll | cash_out | next_round | start {deck,stake,seed}

Game states seen: MENU, BLIND_SELECT, SELECTING_HAND, SHOP, ROUND_EVAL,
GAME_OVER (plus pack-opening states).
"""

import json
import os
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("BALATRO_API", "http://127.0.0.1:12346")


class BalatroError(Exception):
    pass


class BalatroLink:
    def __init__(self, url=API_URL, timeout=30):
        self.url = url
        self.timeout = timeout
        self._id = 0

    # ---------- transport ----------

    def rpc(self, method, params=None):
        """One JSON-RPC call. Returns the result dict, or raises BalatroError
        with the game's message (invalid moves are normal, not crashes)."""
        self._id += 1
        payload = {"jsonrpc": "2.0", "method": method, "id": self._id}
        if params:
            payload["params"] = params
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise BalatroError("api unreachable: %s" % e)
        if "error" in body:
            err = body["error"]
            raise BalatroError("%s: %s" % (err.get("code"), err.get("message")))
        return body.get("result")

    def alive(self):
        try:
            return self.rpc("health").get("status") == "ok"
        except BalatroError:
            return False

    # ---------- state ----------

    def state(self):
        return self.rpc("gamestate") or {}

    def wait_for_state(self, wanted, timeout=45.0, poll=0.6):
        """Block until the game reaches one of `wanted` states."""
        wanted = {wanted} if isinstance(wanted, str) else set(wanted)
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                last = (self.state() or {}).get("state")
            except BalatroError:
                last = None
            if last in wanted:
                return last
            time.sleep(poll)
        return last

    # ---------- actions ----------

    def start_run(self, deck="RED", stake="WHITE", seed=None):
        params = {"deck": deck, "stake": stake}
        if seed:
            params["seed"] = seed
        return self.rpc("start", params)

    def play(self, indices):
        return self.rpc("play", {"cards": list(indices)})

    def discard(self, indices):
        return self.rpc("discard", {"cards": list(indices)})

    def select_blind(self):
        return self.rpc("select")

    def skip_blind(self):
        return self.rpc("skip")

    def buy(self, card=None, voucher=None, pack=None):
        params = {}
        for key, val in (("card", card), ("voucher", voucher), ("pack", pack)):
            if val is not None:
                params[key] = val
        return self.rpc("buy", params)

    def sell(self, joker=None, consumable=None):
        params = {}
        if joker is not None:
            params["joker"] = joker
        if consumable is not None:
            params["consumable"] = consumable
        return self.rpc("sell", params)

    def use(self, consumable, cards=None):
        params = {"consumable": consumable}
        if cards:
            params["cards"] = list(cards)
        return self.rpc("use", params)

    def rearrange(self, hand=None, jokers=None, consumables=None):
        params = {}
        for key, val in (("hand", hand), ("jokers", jokers),
                         ("consumables", consumables)):
            if val is not None:
                params[key] = list(val)
        return self.rpc("rearrange", params)

    def pack_choose(self, card=None, targets=None, skip=False):
        """Pick (or skip) a card from an opened booster pack. Tarot/Spectral
        cards that act on your hand also need `targets` (0-based hand
        indices). Mega packs allow two picks: the pack simply stays open."""
        if skip:
            return self.rpc("pack", {"skip": True})
        params = {"card": card}
        if targets:
            params["targets"] = list(targets)
        return self.rpc("pack", params)

    def reroll(self):
        return self.rpc("reroll")

    def cash_out(self):
        return self.rpc("cash_out")

    def next_round(self):
        return self.rpc("next_round")

    def to_menu(self):
        return self.rpc("menu")

    def dismiss(self):
        """Close any overlay sitting on top of the game — a deck-unlock popup
        with its Continue button is the usual one, and it pauses the game
        behind it. No-op when nothing is up. Added by tools/balatro-patch, so
        an unpatched mod answers 'unknown method'; callers treat that as fine."""
        return self.rpc("dismiss")


# ---------- state shaping for the brain ----------

# The mod's extract_card() shape (utils/gamestate.lua):
#   {id, key, set, label, value:{suit,rank,effect}, modifier:{...},
#    state:{debuff,hidden,highlight}, cost:{sell,buy}}
# Getting this wrong is expensive: reading the effect text from the top level
# (it lives in value.effect) left the brain looking at shop items that had a
# name and a price but no idea what they did, so it bought almost nothing.

EFFECT_CAP = 160        # descriptions are for judging, not for reciting


def _card_brief(card):
    """A playing card as the brain needs it: rank, suit, what is on it, and
    whether the boss blind has killed it."""
    if not isinstance(card, dict):
        return {}
    val = card.get("value") or {}
    out = {"rank": val.get("rank"), "suit": val.get("suit")}
    mod = card.get("modifier") or {}
    if isinstance(mod, dict):
        for key in ("enhancement", "edition", "seal"):
            if mod.get(key):
                out[key] = mod[key]
    if (card.get("state") or {}).get("debuff"):
        out["debuffed"] = True      # boss blinds kill suits/ranks — must see it
    return out


def _item_brief(item):
    """A joker / consumable / shop item: name, type, price and WHAT IT DOES."""
    if not isinstance(item, dict):
        return {}
    out = {"name": item.get("label") or item.get("key")}
    kind = item.get("set")
    if kind and kind not in ("DEFAULT", "ENHANCED"):
        out["type"] = kind          # JOKER / TAROT / PLANET / VOUCHER / BOOSTER
    cost = item.get("cost") or {}
    if isinstance(cost, dict):
        if cost.get("buy"):
            out["buy"] = cost["buy"]
        if cost.get("sell"):
            out["sell"] = cost["sell"]
    effect = (item.get("value") or {}).get("effect") if \
        isinstance(item.get("value"), dict) else None
    effect = effect or item.get("effect")
    if effect:
        out["effect"] = str(effect)[:EFFECT_CAP]
    mod = item.get("modifier") or {}
    if isinstance(mod, dict):
        for key in ("edition", "eternal", "perishable", "rental"):
            if mod.get(key):
                out[key] = mod[key]
    return out


def _choice_brief(card):
    """A card offered inside a booster pack. Standard packs offer playing
    cards; Buffoon/Arcana/Celestial/Spectral offer named items. Every card
    has a `value`, so tell them apart by whether it has a rank."""
    if not isinstance(card, dict):
        return {}
    if (card.get("value") or {}).get("rank"):
        return _card_brief(card)
    return _item_brief(card)


def is_pack_state(state):
    """True while a booster pack is open (Steamodded names this state
    SMODS_BOOSTER_OPENED; match loosely so a rename does not break us)."""
    return "BOOSTER" in str(state or "").upper()


def slim_state(raw):
    """Drop everything the brain does not need for THIS screen.

    Balatro's full state carries all 52 deck cards, every poker-hand entry and
    UI scaffolding — several thousand tokens per call on a 2-core CPU. Only
    the current screen's decision surface is kept, with hand levels reduced to
    the ones that matter."""
    if not isinstance(raw, dict):
        return {}
    state = raw.get("state")
    out = {
        "state": state,
        "ante": raw.get("ante_num"),
        "round": raw.get("round_num"),
        "money": raw.get("money"),
        "deck": raw.get("deck"),
        "stake": raw.get("stake"),
    }
    rnd = raw.get("round") or {}
    if isinstance(rnd, dict):
        out["hands_left"] = rnd.get("hands_left")
        out["discards_left"] = rnd.get("discards_left")
        out["chips_scored"] = rnd.get("chips")
        out["reroll_cost"] = rnd.get("reroll_cost")

    blinds = raw.get("blinds") or {}
    if state == "BLIND_SELECT" and isinstance(blinds, dict):
        out["blinds"] = {k: {"name": v.get("name"), "score": v.get("score"),
                             "effect": v.get("effect"),
                             "tag": v.get("tag_name"),
                             "tag_effect": v.get("tag_effect"),
                             "type": v.get("type"),      # SMALL/BIG/BOSS
                             "status": v.get("status")}
                         for k, v in blinds.items() if isinstance(v, dict)}
    elif isinstance(blinds, dict):
        # mid-round: only the blind we are actually fighting matters
        current = next((v for v in blinds.values()
                        if isinstance(v, dict) and v.get("status") == "CURRENT"), None)
        if current:
            out["current_blind"] = {"name": current.get("name"),
                                    "score": current.get("score"),
                                    "effect": current.get("effect"),
                                    # SMALL/BIG/BOSS — without this, dying to
                                    # a Small Blind got filed as a boss defeat
                                    # and taught the brain to fear it
                                    "type": current.get("type")}

    hand = raw.get("hand") or {}
    if isinstance(hand, dict) and hand.get("cards"):
        out["hand"] = [_card_brief(c) for c in hand["cards"]]

    jokers = raw.get("jokers") or {}
    if isinstance(jokers, dict) and jokers.get("cards"):
        out["jokers"] = [_item_brief(j) for j in jokers["cards"]]
        out["joker_slots"] = jokers.get("limit")

    cons = raw.get("consumables") or {}
    if isinstance(cons, dict) and cons.get("cards"):
        out["consumables"] = [_item_brief(c) for c in cons["cards"]]

    # Each shop row is its OWN top-level key in the API's state, not a field
    # inside "shop": shop=jokers/cards, vouchers=voucher row, packs=booster
    # row. Reading them from inside "shop" hid vouchers and booster packs from
    # the brain completely, so it could never buy either.
    shop_out = {}
    for out_key, raw_key in (("cards", "shop"), ("vouchers", "vouchers"),
                             ("packs", "packs")):
        area = raw.get(raw_key)
        items = area.get("cards") if isinstance(area, dict) else area
        if items:
            shop_out[out_key] = [_item_brief(i) for i in items]
    if shop_out:
        out["shop"] = shop_out

    # A booster pack that is open right now: these are the cards on screen.
    pack = raw.get("pack")
    if isinstance(pack, dict) and pack.get("cards"):
        out["pack_choices"] = [_choice_brief(c) for c in pack["cards"]]

    hands = raw.get("hands") or {}
    if isinstance(hands, dict):
        # only levelled or commonly used hands — not all twelve every call
        levels = {name: {"level": h.get("level"), "chips": h.get("chips"),
                         "mult": h.get("mult")}
                  for name, h in hands.items()
                  if isinstance(h, dict)
                  and (h.get("level", 1) > 1 or name in
                       ("High Card", "Pair", "Two Pair", "Three of a Kind",
                        "Straight", "Flush", "Full House"))}
        if levels:
            out["hand_levels"] = levels

    if raw.get("used_vouchers"):
        out["used_vouchers"] = raw["used_vouchers"]
    return out


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    link = BalatroLink()
    print("api alive:", link.alive())
    raw = link.state()
    slim = slim_state(raw)
    print("state:", slim.get("state"))
    print("slim keys:", sorted(slim))
    print("size: raw %d chars -> slim %d chars"
          % (len(json.dumps(raw)), len(json.dumps(slim))))
    print(json.dumps(slim, ensure_ascii=False, indent=1)[:1200])


if __name__ == "__main__":
    main()
