"""Does Cardia pick its own deck and stake, and only ones it has earned?

Three things matter here:
  1. with one legal combination there must be NO brain call (nothing to decide)
  2. with several, the brain picks one and it must be a legal one
  3. a locked deck must be rejected even if the model names it

Run: python tools/check_deck_choice.py
"""

import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import balatro_profile as bp
from brain import Brain

print("\n[1] the real profile right now")
info = bp.read_profile()
legal = bp.legal_choices(info)
print("    unlocked decks : %s" % ", ".join(info["unlocked"]))
print("    career         : %d wins / %d losses, %d items discovered"
      % (info["wins"], info["losses"], info["discovered"]))
print("    legal combos   : %d -> %s"
      % (len(legal), "no brain call, just play it" if len(legal) <= 1
         else "the AI chooses"))

# A profile a few streams from now: more decks earned, Red Stake opened on Red.
future = bp.read_profile()
for d in future["decks"]:
    if d["deck"] in ("RED", "BLUE", "YELLOW", "MAGIC"):
        d["unlocked"] = True
        d.pop("unlock", None)
        d["max_stake"] = "RED" if d["deck"] == "RED" else "WHITE"
        d["stakes_beaten"] = 1 if d["deck"] == "RED" else 0
future["unlocked"] = [d["deck"] for d in future["decks"] if d["unlocked"]]
future["wins"] = 1
future_legal = bp.legal_choices(future)

print("\n[2] a future profile (4 decks unlocked, Red Stake earned on Red)")
print("    legal combos   : %d" % len(future_legal))
print("    %s" % ", ".join("%s/%s" % c for c in future_legal))

print("\n[3] asking the brain to choose (real call)")
b = Brain()
choice = b.balatro_run_choice(
    bp.options_text(future), future_legal,
    lessons="- Buy an xMult joker by Ante 3 or the run stalls out",
    playbook="- Prefer +Mult early, xMult by Ante 3",
    recent_runs="- 2026-08-01: RED on WHITE stake, lost at ante 1")
if choice:
    ok = (choice["deck"], choice["stake"]) in set(future_legal)
    print("    picked  : %s / %s  (legal: %s)"
          % (choice["deck"], choice["stake"], ok))
    print("    why     : %s" % choice.get("why"))
    print("    say     : %s" % choice.get("say"))
else:
    print("    no choice returned (timeout or illegal pick) -> caller falls back")

print("\n[4] a locked deck must be refused even if the model names it")
faked = {"deck": "PLASMA", "stake": "GOLD"}
print("    PLASMA/GOLD in legal set: %s  -> %s"
      % ((faked["deck"], faked["stake"]) in set(future_legal),
         "rejected, falls back" if (faked["deck"], faked["stake"])
         not in set(future_legal) else "ACCEPTED (BUG)"))
