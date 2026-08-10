"""Read Balatro's own save files to learn what Cardia is allowed to play.

The balatrobot `start` endpoint happily accepts any of the 15 decks and any of
the 8 stakes — it force-sets the deck without checking unlocks. That would be
cheating on stream, so we read the real unlock state instead and only ever
offer choices the profile has actually earned.

Save files are Lua tables compressed with raw deflate:
  <APPDATA>/Balatro/settings.jkr     -> which profile slot is active
  <APPDATA>/Balatro/<n>/meta.jkr     -> ["unlocked"] = {["b_red"]=true, ...}
  <APPDATA>/Balatro/<n>/profile.jkr  -> deck_usage[deck].wins keyed by stake

Unlock rules read out of the game's own data (lovely dump of game.lua, 1.0.1o).
Stake N+1 becomes available for a deck once that deck has a win at stake N;
the win_stake deck unlocks use the best stake across ALL decks.
"""

import os
import re
import zlib

STAKES = ["WHITE", "RED", "GREEN", "BLACK", "BLUE", "PURPLE", "ORANGE", "GOLD"]

# key -> (enum, display name, what it does, how it unlocks)
DECKS = [
    ("b_red", "RED", "Red Deck", "+1 discard every round", None),
    ("b_blue", "BLUE", "Blue Deck", "+1 hand every round",
     ("discover", 20)),
    ("b_yellow", "YELLOW", "Yellow Deck", "start with $10 extra",
     ("discover", 50)),
    ("b_green", "GREEN", "Green Deck",
     "more cash per unused hand/discard, but no interest", ("discover", 75)),
    ("b_black", "BLACK", "Black Deck", "+1 joker slot, -1 hand",
     ("discover", 100)),
    ("b_magic", "MAGIC", "Magic Deck", "free Crystal Ball voucher + 2 Fools",
     ("win_deck", "b_red")),
    ("b_nebula", "NEBULA", "Nebula Deck",
     "free Telescope voucher, -1 consumable slot", ("win_deck", "b_blue")),
    ("b_ghost", "GHOST", "Ghost Deck",
     "Spectral cards appear in shops, start with Hex", ("win_deck", "b_yellow")),
    ("b_abandoned", "ABANDONED", "Abandoned Deck", "no face cards in the deck",
     ("win_deck", "b_green")),
    ("b_checkered", "CHECKERED", "Checkered Deck", "26 Spades and 26 Hearts only",
     ("win_deck", "b_black")),
    ("b_zodiac", "ZODIAC", "Zodiac Deck",
     "free Tarot Merchant, Planet Merchant and Overstock", ("win_stake", 2)),
    ("b_painted", "PAINTED", "Painted Deck", "+2 hand size, -1 joker slot",
     ("win_stake", 3)),
    ("b_anaglyph", "ANAGLYPH", "Anaglyph Deck", "a Double Tag after every boss",
     ("win_stake", 4)),
    ("b_plasma", "PLASMA", "Plasma Deck",
     "balances chips and mult, but blinds are twice as big", ("win_stake", 5)),
    ("b_erratic", "ERRATIC", "Erratic Deck", "every card's rank and suit is random",
     ("win_stake", 7)),
]

DECK_BY_KEY = {key: (enum, name, effect) for key, enum, name, effect, _ in DECKS}


def _load(path):
    """Balatro saves are raw-deflate Lua source. Returns '' if unreadable."""
    try:
        with open(path, "rb") as f:
            return zlib.decompress(f.read(), -15).decode("utf-8", "replace")
    except (OSError, zlib.error):
        return ""


def _table(text, name):
    """Body of the lua table ["name"]={...}, brace-balanced."""
    m = re.search(r'\["%s"\]=\{' % re.escape(name), text)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[m.end():i - 1]


def _deck_blocks(deck_usage):
    """Split deck_usage into {deck_key: body} without a real lua parser."""
    out = {}
    for m in re.finditer(r'\["(b_\w+)"\]=\{', deck_usage):
        depth, i = 1, m.end()
        while i < len(deck_usage) and depth:
            if deck_usage[i] == "{":
                depth += 1
            elif deck_usage[i] == "}":
                depth -= 1
            i += 1
        out[m.group(1)] = deck_usage[m.end():i - 1]
    return out


def read_profile(appdata=None):
    """What this profile has earned. Never raises — a missing or unreadable
    save just means 'Red Deck on White Stake', which is always legal."""
    base = os.path.join(appdata or os.environ.get("APPDATA", ""), "Balatro")
    settings = _load(os.path.join(base, "settings.jkr"))
    m = re.search(r'\["profile"\]=(\d+)', settings)
    slot = m.group(1) if m else "1"

    meta = _load(os.path.join(base, slot, "meta.jkr"))
    prof = _load(os.path.join(base, slot, "profile.jkr"))

    unlocked_keys = set(re.findall(r'\["(b_\w+)"\]',
                                   _table(meta, "unlocked")))
    unlocked_keys.add("b_red")          # always legal, even on a fresh profile
    unlocked_keys.discard("b_challenge")  # challenge mode, not a deck

    # deck_usage[deck].wins is keyed by the stake number that was beaten
    usage = _deck_blocks(_table(prof, "deck_usage"))
    best_stake = {}
    for key, body in usage.items():
        wins = _table(body, "wins") or ""
        levels = [int(n) for n in re.findall(r'\[(\d+)\]=', wins)]
        if levels:
            best_stake[key] = max(levels)
    global_best = max(best_stake.values()) if best_stake else 0

    discovered = 0
    dm = re.search(r'\["discovered"\]=\{\["of"\]=\d+,\["tally"\]=(\d+)',
                   _table(prof, "progress"))
    if not dm:
        dm = re.search(r'\["tally"\]=(\d+)',
                       _table(_table(prof, "progress"), "discovered"))
    if dm:
        discovered = int(dm.group(1))

    decks = []
    for key, enum, name, effect, cond in DECKS:
        entry = {"deck": enum, "name": name, "effect": effect,
                 "unlocked": key in unlocked_keys}
        if entry["unlocked"]:
            # a deck can be played at one stake above its best win
            entry["max_stake"] = STAKES[min(best_stake.get(key, 0), len(STAKES) - 1)]
            entry["stakes_beaten"] = best_stake.get(key, 0)
        else:
            entry["unlock"] = _describe(cond, discovered, unlocked_keys, global_best)
        decks.append(entry)

    career = _table(prof, "career_stats")

    def stat(name):
        m2 = re.search(r'\["%s"\]=(-?\d+)' % name, career)
        return int(m2.group(1)) if m2 else 0

    return {
        "decks": decks,
        "unlocked": [d["deck"] for d in decks if d["unlocked"]],
        "discovered": discovered,
        "best_stake_anywhere": STAKES[min(global_best, len(STAKES) - 1)],
        "profile_slot": slot,
        # career wins is how we tell a win from a loss after the fact: the
        # game state at GAME_OVER does not say which it was
        "wins": stat("c_wins"),
        "losses": stat("c_losses"),
    }


def _describe(cond, discovered, unlocked_keys, global_best):
    """Human/AI readable unlock requirement, with current progress."""
    if not cond:
        return "already available"
    kind, arg = cond
    if kind == "discover":
        return "discover %d different items (at %d now)" % (arg, discovered)
    if kind == "win_deck":
        _, name, _ = DECK_BY_KEY.get(arg, ("", arg, ""))
        state = "available" if arg in unlocked_keys else "still locked"
        return "win a run with the %s (%s)" % (name, state)
    if kind == "win_stake":
        return "win a run on %s Stake or higher (best so far: %s)" % (
            STAKES[min(arg - 1, len(STAKES) - 1)],
            STAKES[min(global_best, len(STAKES) - 1)] if global_best else "none")
    return str(cond)


def options_text(info):
    """The unlock picture as the brain should see it — short, no JSON noise."""
    lines = ["PLAYABLE NOW:"]
    for d in info["decks"]:
        if d["unlocked"]:
            stakes = STAKES[:STAKES.index(d["max_stake"]) + 1]
            lines.append("- %s (%s) - %s | stakes allowed: %s"
                         % (d["deck"], d["name"], d["effect"], ", ".join(stakes)))
    locked = [d for d in info["decks"] if not d["unlocked"]]
    if locked:
        lines.append("")
        lines.append("LOCKED (what it would take):")
        for d in locked:
            lines.append("- %s (%s) - %s | needs: %s"
                         % (d["deck"], d["name"], d["effect"], d["unlock"]))
    return "\n".join(lines)


def legal_choices(info):
    """Every (deck, stake) pair the profile may legally start."""
    out = []
    for d in info["decks"]:
        if not d["unlocked"]:
            continue
        for stake in STAKES[:STAKES.index(d["max_stake"]) + 1]:
            out.append((d["deck"], stake))
    return out


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    info = read_profile()
    print("profile slot %s - discovered %d items, best stake %s"
          % (info["profile_slot"], info["discovered"], info["best_stake_anywhere"]))
    print()
    print(options_text(info))
    print()
    choices = legal_choices(info)
    print("legal (deck, stake) combinations: %d" % len(choices))
    if len(choices) == 1:
        print("  -> only one option, so no decision to make: %s / %s" % choices[0])


if __name__ == "__main__":
    main()
