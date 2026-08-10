"""Does the vault only accumulate things that make the brain better?

The notes are injected into every decision, so junk compounds. This checks the
three ways junk used to get in:

  1. losing to a Small/Big Blind filed as a boss defeat (it taught the brain
     that the easiest blind in the game was its deadliest enemy)
  2. run reports growing without limit
  3. the distiller being told the wrong game, and not being told to delete

Run: python tools/check_learning_loop.py   (uses a throwaway vault)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator


def finish(vault, blind, blind_type, ante=2, jokers=("Joker",), wins_before=None):
    o = Orchestrator.__new__(Orchestrator)
    o.vault = vault
    o.balatro = True
    o.run_reported = False
    o.run_deck, o.run_stake = "RED", "WHITE"
    o.run_wins_before = wins_before
    o.run_unlocked_before = None
    o.lessons_rev = 1
    o.notes, o.spoken, o.generated = [], [], []
    o.note = o.notes.append
    o.push_speech = lambda p, t, k: o.spoken.append(t)
    o.push_gen = lambda p, kind, text: o.generated.append((kind, text))
    o.run_track = {"ante": ante, "round": 5, "money": 4, "jokers": list(jokers),
                   "blind": blind, "blind_type": blind_type,
                   "blind_effect": "-", "hand_levels": {}}
    o._finish_balatro_run({"state": "GAME_OVER"})
    return o


tmp = tempfile.mkdtemp(prefix="cardia-vault-")
try:
    print("\n[1] who gets a dossier?")
    finish(tmp, "Small Blind", "SMALL")
    finish(tmp, "Big Blind", "BIG")
    finish(tmp, "The Club", "BOSS")
    dossiers = sorted(os.listdir(os.path.join(tmp, "Boss blinds"))) \
        if os.path.isdir(os.path.join(tmp, "Boss blinds")) else []
    print("    lost to Small Blind, Big Blind and The Club")
    print("    dossiers written: %s" % (dossiers or ["(none)"]))
    print("    -> %s" % ("only the real boss (correct)"
                         if dossiers == ["The Club.md"] else "WRONG"))

    print("\n[1b] a WIN must not be filed as a defeat")
    import balatro_profile as bp
    live_wins = bp.read_profile()["wins"]
    won = finish(tmp, "The Wall", "BOSS", ante=8, wins_before=live_wins - 1)
    wall = os.path.join(tmp, "Boss blinds", "The Wall.md")
    print("    won the run against The Wall")
    print("    'The Wall' note written: %s  -> %s"
          % (os.path.exists(wall),
             "correct — it did not end the run" if not os.path.exists(wall)
             else "WRONG, logged as a loss"))
    print("    report says: %s" % won.generated[0][1][:34])

    print("\n[1c] a run with nothing on board must not churn the lessons")
    barren = finish(tmp, "Small Blind", "SMALL", ante=1, jokers=())
    rich = finish(tmp, "The Needle", "BOSS", ante=3, jokers=("Baron",))
    print("    ante 1, no jokers  -> distilled: %s" % bool(barren.generated))
    print("    ante 3, has jokers -> distilled: %s" % bool(rich.generated))
    print("    note: %s" % ([n for n in barren.notes if "lessons" in n]
                            or ["(none)"])[0])

    print("\n[2] do run reports stay bounded?")
    cap = Orchestrator.KEEP_RUN_REPORTS
    runs = os.path.join(tmp, "Cardia runs")
    for i in range(cap + 12):        # fake older reports
        open(os.path.join(runs, "2026-07-%02d 0000.md" % (i % 28 + 1)), "w",
             encoding="utf-8").write("---\nresult: lost\n---\n")
    before = len(os.listdir(runs))
    finish(tmp, "The Needle", "BOSS")
    after = len(os.listdir(runs))
    print("    %d reports -> %d (cap %d)  %s"
          % (before, after, cap, "OK" if after <= cap else "UNBOUNDED"))

    print("\n[3] is the distiller told the right game, and told to prune?")
    import brain as brain_mod

    seen = {}

    class Probe(brain_mod.Brain):
        def __init__(self):
            self.routes = {"lessons": {"model": "opus"}}

        def _call(self, route, task, **kw):
            seen["task"] = task
            return {"lessons": ["x"], "playbook": "y"}

    Probe().distill_lessons("a Balatro run", "old lessons", "old playbook",
                            game="Balatro")
    task = seen["task"]
    for label, needle in (("names the game", "Balatro study notes"),
                          ("says notes hit every decision", "EVERY decision"),
                          ("orders deleting bad lines", "DELETE any existing"),
                          ("rejects one-run rules", "ONE loss is not"),
                          ("rejects narration", "not a description of what")):
        print("    %-30s %s" % (label, "yes" if needle in task else "NO"))
    print("    mentions Slay the Spire wrongly: %s"
          % ("YES - BUG" if "Slay the Spire" in task else "no"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
