"""Measure real game-decision latency at the current settings.

Runs the actual Brain.game_decision on canned states, timing wall-clock:
  - Sonnet, thinking 0  -> routine turns, card rewards, shop, rest, map, events
  - Sonnet, thinking 512 -> boss/elite/deadly combat turns
  - Haiku, thinking 0    -> reference (the old routine speed)

Run: python tools/bench_game.py   (best with the game NOT running)
"""

import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import Brain
from test_brain import CANNED_COMBAT_STATE

CARD_REWARD_STATE = {
    "available_commands": ["choose", "skip", "state"],
    "ready_for_command": True, "in_game": True,
    "game_state": {
        "screen_type": "CARD_REWARD", "room_phase": "COMPLETE",
        "floor": 5, "act": 1, "current_hp": 58, "max_hp": 80, "gold": 120,
        "class": "IRONCLAD",
        "deck": [{"name": n} for n in
                 ["Strike", "Strike", "Strike", "Strike", "Defend", "Defend",
                  "Defend", "Bash", "Shrug It Off", "Anger", "Cleave"]],
        "relics": [{"name": "Burning Blood"}],
        "screen_state": {"cards": [
            {"name": "Inflame", "type": "POWER", "rarity": "UNCOMMON"},
            {"name": "Twin Strike", "type": "ATTACK", "rarity": "COMMON"},
            {"name": "Flex", "type": "SKILL", "rarity": "COMMON"}]},
    },
}

LESSONS = ("- Thin decks under fourteen cards win: skip mediocre commons\n"
           "- Take scaling powers (Inflame, Demon Form) over vanilla attacks\n"
           "- Gremlin Nob: block early, his scaling punishes slow turns")


def bench(label, fn, runs=2):
    times = []
    for i in range(runs):
        t = time.monotonic()
        out = fn()
        ms = int((time.monotonic() - t) * 1000)
        times.append(ms)
        ok = out is not None
        first = ""
        if ok and out.get("plan"):
            p = out["plan"][0]
            first = p.get("action", "") + " " + (p.get("card") or p.get("choice") or "")
        print("  run %d: %5.1fs  ok=%s  %s" % (i + 1, ms / 1000, ok, first.strip()))
    avg = sum(times) / len(times) / 1000
    print("  => %s: avg %.1fs\n" % (label, avg))
    return avg


def main():
    b = Brain()
    print("\n=== GAME DECISION LATENCY (background: veadotube + TikTok Studio idle) ===\n")

    print("[1] Card reward — Sonnet, thinking 0 (deckbuilding / shop / rewards):")
    bench("card reward", lambda: b.game_decision(
        CARD_REWARD_STATE, [], max_thinking=0, lessons=LESSONS))

    print("[2] Routine combat turn — Sonnet, thinking 0:")
    bench("routine combat", lambda: b.game_decision(
        CANNED_COMBAT_STATE, [], max_thinking=0, lessons=LESSONS))

    print("[3] Boss/deadly combat — Sonnet, thinking 512:")
    bench("boss/deadly", lambda: b.game_decision(
        CANNED_COMBAT_STATE, [], max_thinking=512, lessons=LESSONS))

    print("[4] Reference — Haiku, thinking 0 (the old routine speed):")
    bench("haiku ref", lambda: b.game_decision(
        CANNED_COMBAT_STATE, [], max_thinking=0, lessons=LESSONS,
        model_override="haiku"))

    print("Note: a live stream adds the running game + active encoding, so real")
    print("numbers will be somewhat higher than these background-load figures.")


if __name__ == "__main__":
    main()
