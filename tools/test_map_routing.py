"""Does the brain route toward a shop when it is carrying gold?"""

import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import Brain
from orchestrator import Orchestrator

o = Orchestrator(game_link=False, use_twitch=False, use_tts=False)
print("manual: %d chars" % len(o.manual_text))
for key in ("SHOP", "Elite", "treasure chest", "card REMOVAL"):
    print("  contains %-16s %s" % (key, key in o.manual_text))

state = {
    "available_commands": ["choose", "state"],
    "ready_for_command": True, "in_game": True,
    "game_state": {
        "screen_type": "MAP", "floor": 8, "act": 1,
        "current_hp": 62, "max_hp": 80, "gold": 210,
        "deck": [{"name": "Strike"}] * 5 + [{"name": "Defend"}] * 4
                + [{"name": "Bash"}, {"name": "Inflame"}],
        "choice_list": ["M", "$", "R"],
        "map": [{"symbol": "M", "x": 1, "y": 9, "children": []},
                {"symbol": "$", "x": 3, "y": 9, "children": []},
                {"symbol": "R", "x": 5, "y": 9, "children": []}],
    },
}

b = Brain()
t0 = time.monotonic()
out = b.game_decision(state, [], max_thinking=0, manual=o.manual_text,
                      lessons=o.lessons_text, playbook=o.playbook_text)
print("\nopus map decision: %.1fs" % (time.monotonic() - t0))
if out:
    print("plan:", [(i.get("action"), i.get("choice", "")) for i in out["plan"]])
    print("why :", out["why"])
    picked = str(out["plan"][0].get("choice", "")).lower() if out["plan"] else ""
    print(">>> routed to SHOP:", picked in ("$", "1", "shop"))
else:
    print("decision failed")
