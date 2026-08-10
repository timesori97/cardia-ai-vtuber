"""After a death, how long before Play is pressed?

Choosing the next deck is a brain call. It used to run at the main menu, so
the Play button sat there for its whole duration. Now it runs while the death
screen is still up, and the menu just uses the answer.

Run: python tools/check_restart_speed.py
"""

import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator

BRAIN_S = 6.0        # a real deck choice, measured warm


def make(slow_brain=True):
    o = Orchestrator.__new__(Orchestrator)
    o.notes = []
    o.note = o.notes.append
    o.spoken = []
    o.push_speech = lambda p, t, k: o.spoken.append(t)
    o._deck_choice = None
    o._deck_thread = None
    o.vault = ""
    o.lessons_text = o.playbook_text = ""
    o.run_wins_before = None
    o.run_unlocked_before = None

    class B:
        def balatro_run_choice(self, options, legal, **kw):
            if slow_brain:
                time.sleep(BRAIN_S)
            deck, stake = legal[-1]
            return {"deck": deck, "stake": stake,
                    "why": "test", "say": "New run, new deck."}
    o.brain = B()
    return o


print("\n[1] the old way — deck chosen when the menu appears")
o = make()
t = time.monotonic()
o._pick_deck_and_stake()
cold = time.monotonic() - t
print("    menu -> Play pressed: %.1fs" % cold)

print("\n[2] now — chosen while the death screen is still up")
o = make()
t0 = time.monotonic()
o.prefetch_deck_choice()          # fires at GAME_OVER
# the death screen, report writing and the walk back to the menu take a while
time.sleep(BRAIN_S + 1.0)
t = time.monotonic()
deck, stake = o._pick_deck_and_stake()
warm = time.monotonic() - t
print("    death screen -> menu: %.1fs (that time was already being spent)"
      % (t - t0))
print("    menu -> Play pressed: %.1fs   deck=%s/%s" % (warm, deck, stake))
print("    line spoken on start: %s" % (o.spoken or ["(none)"])[0])

print("\n[3] menu reached before the choice is ready — does it still work?")
o = make()
o.prefetch_deck_choice()
t = time.monotonic()
deck, stake = o._pick_deck_and_stake()   # no wait at all before asking
print("    menu -> Play pressed: %.1fs (waits for the answer, never guesses)"
      % (time.monotonic() - t))
print("    deck=%s/%s" % (deck, stake))

print("\n  saved at the menu: %.1fs -> %.1fs" % (cold, warm))
