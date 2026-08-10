"""Which moods will the avatar actually be able to show?

Cardia asks for a face by mood name; veadotube only has the states the owner
added artwork for. This reports what is wired up, what is still missing, and
proves a missing one is a harmless no-op rather than an error.

Run: python tools/check_moods.py          report
     python tools/check_moods.py demo     cycle through what exists
"""

import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from avatar_state import MOOD_WORDS, AvatarStates
from orchestrator import Orchestrator

TRIGGERS = {
    "neutral": "between events (everything else)",
    "smug": "cleared a blind / won a run",
    "nervous": "a Boss Blind is about to start",
    "shocked": "(spare — not wired yet)",
    "sad": "the run just ended in a loss",
    "excited": "new deck unlocked / a donation arrived",
}

av = AvatarStates(note=lambda m: None)
have = av.available()
print("\nveadotube states found: %s"
      % (", ".join(have) if have else "(none — is veadotube mini running?)"))
print("currently showing     : %s\n" % av.current())

print("%-9s %-8s %-42s %s" % ("MOOD", "READY", "SHOWN WHEN", "NAME THE STATE"))
for mood, when in TRIGGERS.items():
    ready = av._match(mood) is not None
    print("%-9s %-8s %-42s %s"
          % (mood, "yes" if ready else "-", when,
             "/".join(MOOD_WORDS.get(mood, ()))[:34]))

print("\nA mood with no artwork is skipped, not an error:")
o = Orchestrator.__new__(Orchestrator)
o.avatar = av
o.notes = []
o.note = o.notes.append
o.set_mood("definitely-not-a-real-mood")
print("   set_mood('definitely-not-a-real-mood') -> no exception, nothing changed")
print("   still showing: %s" % av.current())

if "demo" in sys.argv:
    print("\ncycling through the ones that exist...")
    for mood in TRIGGERS:
        if av._match(mood):
            av.set_mood(mood)
            time.sleep(1.5)
            print("   %-9s -> %s" % (mood, av.current()))
    av.set_mood("neutral")
av.close()
