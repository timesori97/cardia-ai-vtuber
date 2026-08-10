"""Does Balatro mode ever read Slay the Spire's notes?

They are different games. StS notes describe energy, block, relics and
monsters; none of that exists in Balatro, so reading them would be worse than
reading nothing. This traces every file the vault layer opens in each mode.

Run: python tools/check_vault_isolation.py
"""

import builtins
import os
import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator
from twitch_chat import load_env

env = load_env()
STS = (env.get("OBSIDIAN_VAULT") or "").strip()
BAL = (env.get("BALATRO_VAULT") or "").strip()
print("\n  StS vault     : %s" % (STS or "(unset)"))
print("  Balatro vault : %s" % (BAL or "(unset)"))

opened = []
real_open = builtins.open


def spy(path, *a, **kw):
    if isinstance(path, str) and path.lower().endswith(".md"):
        opened.append(path)
    return real_open(path, *a, **kw)


def notes_read(vault, balatro):
    """Every .md the note layer touches for one game's setup."""
    del opened[:]
    o = Orchestrator.__new__(Orchestrator)
    o.vault = vault
    o.balatro = balatro
    o._enemy_note_cache = {}
    builtins.open = spy
    try:
        o._load_manual()
        o._load_lessons()
        o._load_playbook()
        o._recent_runs_text()
        if balatro:
            o._blind_notes_for({"current_blind": {"name": "The Club",
                                                  "type": "BOSS"}})
        else:
            o._enemy_notes_for({"game_state": {"combat_state":
                                               {"monsters": [{"name": "Cultist"}]}}})
    finally:
        builtins.open = real_open
    return list(opened)


for label, vault, is_bal in (("BALATRO mode", BAL, True),
                             ("SLAY THE SPIRE mode", STS, False)):
    print("\n=== %s ===" % label)
    paths = notes_read(vault, is_bal)
    other = STS if is_bal else BAL
    leaks = [p for p in paths
             if other and os.path.normcase(other) in os.path.normcase(p)]
    for p in paths:
        mark = "  LEAK ->" if p in leaks else "        "
        print("%s %s" % (mark, p))
    if not paths:
        print("         (no note files found — vault empty or unset)")
    print("   -> %s" % ("READS THE OTHER GAME'S NOTES" if leaks
                        else "stays inside its own vault"))

print("\n=== if BALATRO_VAULT were missing from .env ===")
paths = notes_read("", True)
print("   files read: %s" % (paths or "none"))
print("   -> %s" % ("falls back to StS (BUG)"
                    if any(STS and os.path.normcase(STS) in os.path.normcase(p)
                           for p in paths)
                    else "reads nothing, rather than the wrong game"))
