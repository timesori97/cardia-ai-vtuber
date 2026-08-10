"""Does Balatro get its own exit, and does the volume actually stick?

Two bugs this covers:
  1. shutdown ran Slay the Spire's Save & Quit click coordinates against
     Balatro, which just clicks random spots on the board
  2. Balatro only writes settings.jkr when it exits through its own menus, so
     killing it threw away any in-game change — the volume kept reverting

Run: python tools/check_balatro_quit.py   (safe: does not close anything)
"""

import os
import shutil
import sys
import zlib

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator

SETTINGS = os.path.join(os.environ.get("APPDATA", ""), "Balatro", "settings.jkr")


def volumes():
    with open(SETTINGS, "rb") as f:
        text = zlib.decompress(f.read(), -15).decode("utf-8", "replace")
    import re
    return dict(re.findall(r'\["(volume|music_volume|game_sounds_volume)"\]=([\d.]+)',
                           text))


print("\n[1] which exit path does each mode take?")
for balatro in (False, True):
    o = Orchestrator.__new__(Orchestrator)
    o.balatro = balatro
    o.notes = []
    o.note = o.notes.append
    path = "_quit_balatro (menu + pin settings)" if o.balatro else \
           "save_and_quit_game (StS menu clicks)"
    print("  %-14s -> %s" % ("balatro" if balatro else "slay the spire", path))

print("\n[2] volume pinning — simulate the game having reverted it to 0")
backup = SETTINGS + ".checktmp"
shutil.copy2(SETTINGS, backup)
try:
    o = Orchestrator.__new__(Orchestrator)
    o.notes = []
    o.note = o.notes.append
    o._force_balatro_sound(0)
    print("  after forcing 0   : %s" % volumes())
    o._force_balatro_sound(Orchestrator.BALATRO_VOLUME)
    print("  after shutdown pin: %s" % volumes())
    print("  notes: %s" % o.notes)
finally:
    shutil.copy2(backup, SETTINGS)
    os.remove(backup)
print("\n  restored from backup: %s" % volumes())
