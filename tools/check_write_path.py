"""End to end: finish a run and show exactly what lands in the vault.

Answers two questions at once — WHERE it writes (the live .env path) and HOW
it writes (every rule added while fixing the learning loop). Runs against a
throwaway copy so the real vault is untouched.

Run: python tools/check_write_path.py
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vault as vault_cfg
from orchestrator import Orchestrator

LIVE = vault_cfg.vault_dir()
print("\n=== WHERE ===")
print("  .env BALATRO_VAULT : %s" % LIVE)
print("  exists             : %s" % os.path.isdir(LIVE))
print("  is an Obsidian vault: %s" % os.path.isdir(os.path.join(LIVE, ".obsidian")))
print("  contents now       : %s"
      % sorted(n for n in os.listdir(LIVE) if not n.startswith(".")))

tmp = tempfile.mkdtemp(prefix="cardia-writetest-")


def finish(blind, blind_type, ante, jokers, levels=None, won=False, rev=1):
    o = Orchestrator.__new__(Orchestrator)
    o.vault = tmp
    o.balatro = True
    o.lessons_rev = rev
    o.run_reported = False
    o.run_deck, o.run_stake = "BLUE", "WHITE"
    o.run_wins_before = None if not won else -1   # -1 => any real count is "up"
    o.run_unlocked_before = None
    o.notes, o.spoken, o.generated = [], [], []
    o.note = o.notes.append
    o.push_speech = lambda p, t, k: o.spoken.append(t)
    o.push_gen = lambda p, kind, text: o.generated.append((kind, text))
    o.run_track = {"ante": ante, "round": 6, "money": 7, "jokers": list(jokers),
                   "blind": blind, "blind_type": blind_type,
                   "blind_effect": "All Club cards are debuffed",
                   "hand_levels": dict(levels or {}),
                   "choices": ["A2 SHOP: buy (Cavendish xMult engine)"]}
    o._finish_balatro_run({"state": "GAME_OVER"})
    return o


try:
    print("\n=== HOW: a real loss to a Boss Blind ===")
    o = finish("The Club", "BOSS", ante=3, jokers=["Cavendish"],
               levels={"Flush": 3})
    for root, _, files in os.walk(tmp):
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(root, f), tmp)
            print("  wrote %s" % rel)
    print("  distilled lessons : %s" % bool(o.generated))

    print("\n=== HOW: a loss to a Small Blind with nothing on board ===")
    before = {os.path.relpath(os.path.join(r, f), tmp)
              for r, _, fs in os.walk(tmp) for f in fs}
    o2 = finish("Small Blind", "SMALL", ante=1, jokers=[])
    after = {os.path.relpath(os.path.join(r, f), tmp)
             for r, _, fs in os.walk(tmp) for f in fs}
    print("  new files         : %s" % sorted(after - before))
    print("  blind note added  : %s (must be no — not a Boss Blind)"
          % any("Boss blinds" in p for p in after - before))
    print("  distilled lessons : %s (must be no — nothing to learn)"
          % bool(o2.generated))

    print("\n=== the progress scoreboard ===")
    print("  " + open(os.path.join(tmp, "Cardia progress.md"),
                      encoding="utf-8").read().strip().replace("\n", "\n  "))

    print("\n=== a run report ===")
    runs = os.path.join(tmp, "Cardia runs")
    newest = sorted(os.listdir(runs))[-1]
    body = open(os.path.join(runs, newest), encoding="utf-8").read()
    print("  " + "\n  ".join(body.splitlines()[:12]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
