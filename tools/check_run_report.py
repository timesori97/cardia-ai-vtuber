"""Does a finished run get recorded with its deck, stake and real outcome?

The game's GAME_OVER state does not say whether you won, so the outcome is
read back out of the save (career wins). This checks both branches and that
the next run's deck choice can read the result back.

Run: python tools/check_run_report.py
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import balatro_profile as bp
from orchestrator import Orchestrator

live = bp.read_profile()
print("live profile: %d career wins\n" % live["wins"])


def fake_run(vault, deck, stake, wins_before, unlocked_before):
    o = Orchestrator.__new__(Orchestrator)
    o.vault = vault
    o.run_reported = False
    o.run_deck, o.run_stake = deck, stake
    o.run_wins_before = wins_before
    o.run_unlocked_before = unlocked_before
    o.notes, o.spoken, o.generated = [], [], []
    o.note = o.notes.append
    o.push_speech = lambda p, t, k: o.spoken.append(t)
    o.push_gen = lambda p, kind, text: o.generated.append((kind, text))
    o.run_track = {"ante": 4, "round": 11, "money": 17,
                   "jokers": ["Green Joker", "Cavendish"],
                   "blind": "The Wall", "blind_effect": "Extra large blind",
                   "hand_levels": {"Flush": 3},
                   "choices": ["A2 SHOP: buy (xMult beats everything)"]}
    o._finish_balatro_run({"state": "GAME_OVER"})
    return o


tmp = tempfile.mkdtemp(prefix="cardia-vault-")
try:
    print("[1] a loss (career wins unchanged)")
    o = fake_run(tmp, "RED", "WHITE", live["wins"], live["unlocked"])
    print("    summary: %s" % o.generated[0][1][:110])

    print("\n[2] a win that unlocked a deck (career wins went up)")
    # empty "before" list, so whatever is unlocked now reads as newly earned
    o = fake_run(tmp, "BLUE", "RED", live["wins"] - 1, [])
    print("    summary: %s" % o.generated[0][1][:110])
    print("    spoken : %s" % (o.spoken or ["(nothing)"])[0])

    files = sorted(os.listdir(os.path.join(tmp, "Cardia runs")))
    print("\n[3] the report file")
    body = open(os.path.join(tmp, "Cardia runs", files[-1]), encoding="utf-8").read()
    print("    " + "\n    ".join(body.splitlines()[:9]))

    print("\n[4] can the next deck choice read it back?")
    o2 = Orchestrator.__new__(Orchestrator)
    o2.vault = tmp
    o2._read_capped = Orchestrator._read_capped.__get__(o2)
    print("    " + (o2._recent_runs_text() or "(nothing readable - BUG)"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
