"""Dry-run balatro_loop against a scripted game, with the brain stubbed out.

Verifies the speed work without needing Balatro open: which screens reach the
brain, which are answered instantly, that working memory resets per screen, and
that a move the game refuses does not hang the stream. Every brain call in the
real thing costs 10-25s, so the call count IS the stream's pacing.

Run: python tools/sim_balatro_loop.py
"""

import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import balatro_link
import orchestrator as orch

# A full ante: pick the small blind, play it out, shop, then the boss.
ANTE = [
    {"state": "BLIND_SELECT", "ante": 1, "round": 1, "money": 4,
     "blinds": {"small": {"name": "Small Blind", "type": "SMALL",
                          "status": "SELECT", "score": 300},
                "boss": {"name": "The Club", "type": "BOSS",
                         "status": "UPCOMING"}}},
    {"state": "SELECTING_HAND", "ante": 1, "round": 1, "money": 4,
     "hands_left": 4, "discards_left": 3,
     "current_blind": {"name": "Small Blind", "score": 300},
     "hand": [{"rank": "K"}, {"rank": "K"}, {"rank": "7"}]},
    {"state": "SELECTING_HAND", "ante": 1, "round": 1, "money": 4,
     "hands_left": 3, "discards_left": 3,
     "current_blind": {"name": "Small Blind", "score": 300},
     "hand": [{"rank": "A"}, {"rank": "A"}, {"rank": "2"}]},
    {"state": "ROUND_EVAL", "ante": 1, "round": 1, "money": 4},
    {"state": "SHOP", "ante": 1, "round": 1, "money": 3, "reroll_cost": 5,
     "shop": {"cards": [{"name": "Cavendish", "buy": 8}]}},          # broke
    {"state": "BLIND_SELECT", "ante": 1, "round": 2, "money": 9,
     "blinds": {"big": {"name": "Big Blind", "type": "BIG",
                        "status": "SELECT", "score": 450},
                "boss": {"name": "The Club", "type": "BOSS",
                         "status": "UPCOMING"}}},
    {"state": "SELECTING_HAND", "ante": 1, "round": 2, "money": 9,
     "hands_left": 4, "discards_left": 3,
     "current_blind": {"name": "Big Blind", "score": 450},
     "hand": [{"rank": "Q"}, {"rank": "Q"}, {"rank": "9"}]},
    {"state": "ROUND_EVAL", "ante": 1, "round": 2, "money": 9},
    {"state": "SHOP", "ante": 1, "round": 2, "money": 21, "reroll_cost": 5,
     "shop": {"cards": [{"name": "Green Joker", "buy": 6}]}},        # can buy
    {"state": "BLIND_SELECT", "ante": 1, "round": 3, "money": 12,
     "blinds": {"boss": {"name": "The Club", "type": "BOSS",
                         "status": "SELECT", "score": 600,
                         "effect": "All Club cards are debuffed"}}},
    {"state": "SELECTING_HAND", "ante": 1, "round": 3, "money": 12,
     "hands_left": 4, "discards_left": 3,
     "current_blind": {"name": "The Club", "score": 600,
                       "effect": "All Club cards are debuffed"},
     "hand": [{"rank": "J"}, {"rank": "J"}, {"rank": "5"}]},
]

# One screen the game keeps refusing (a stale index, a move it will not allow).
STUCK = [
    {"state": "SELECTING_HAND", "ante": 3, "round": 7, "money": 8,
     "hands_left": 2, "discards_left": 0,
     "current_blind": {"name": "The Wall", "score": 2400},
     "hand": [{"rank": "5"}, {"rank": "6"}]},
]


def make_link(script, reject_all=False):
    from balatro_link import BalatroError

    class FakeLink:
        """Walks the script: any successful action advances one step."""

        def __init__(self, *a, **kw):
            self.i = 0

        def alive(self):
            return True

        def state(self):
            return script[min(self.i, len(script) - 1)]

        def _step(self, name):
            if reject_all:
                raise BalatroError("invalid move")
            actions.append("%s@%s" % (name, self.state()["state"]))
            self.i += 1
            if self.i >= len(script):
                o.running = False

        def play(self, c):
            self._step("play")

        def discard(self, c):
            self._step("discard")

        def select_blind(self):
            self._step("select")

        def skip_blind(self):
            self._step("skip")

        def buy(self, **kw):
            actions.append("buy")            # buying keeps you in the shop

        def sell(self, **kw):
            self._step("sell")

        def use(self, *a, **kw):
            self._step("use")

        def rearrange(self, **kw):
            actions.append("rearrange")      # free, does not advance a screen

        def reroll(self):
            self._step("reroll")

        def cash_out(self):
            self._step("cash_out")

        def next_round(self):
            self._step("next_round")

        def to_menu(self):
            self._step("menu")

        def dismiss(self):
            return {"dismissed": False}      # no popups in the sim

        def start_run(self, deck="RED", stake="WHITE", seed=None):
            actions.append("start_run(%s,%s)" % (deck, stake))
            self._step("start")

    return FakeLink


class FakeBrain:
    routes = {"balatro_decision": {"fast_model": "sonnet"}}

    def prewarm(self, route, models, thinking=0):
        pass                                 # no real processes in the sim

    def balatro_run_choice(self, options, legal, **kw):
        brain_calls.append({"state": "RUN_START", "model": "opus", "think": 0,
                            "playbook": bool(kw.get("playbook")), "memory": []})
        deck, stake = legal[0]
        return {"deck": deck, "stake": stake, "why": "test", "say": ""}

    def balatro_decision(self, st, recent, max_thinking=None, lessons="",
                         manual="", playbook="", blind_notes="",
                         recent_actions=(), model_override=None):
        brain_calls.append({
            "state": st.get("state"),
            "model": model_override or "opus",
            "think": max_thinking,
            "playbook": bool(playbook),
            "memory": list(recent_actions),
        })
        if len(brain_calls) > 30:            # sim-only runaway guard
            o.running = False
        plan = {"SELECTING_HAND": [{"action": "play", "cards": [0, 1]}],
                "BLIND_SELECT": [{"action": "select"}],
                "SHOP": [{"action": "buy", "card": 0},
                         {"action": "next_round"}]}.get(st.get("state"), [])
        return {"plan": plan, "why": "test", "say": "a line"}


balatro_link.slim_state = lambda raw: raw    # script states are already slim
orch.log_jsonl = lambda *a, **kw: None
orch.time.sleep = lambda s: None             # no real waiting in the sim


def run(script, reject_all=False):
    global o, actions, brain_calls
    actions, brain_calls = [], []
    balatro_link.BalatroLink = make_link(script, reject_all)
    o = orch.Orchestrator.__new__(orch.Orchestrator)
    o.running = True
    o.signing_off = False
    o.run_reported = False
    o.run_track = {}
    o.turn_actions = []
    o.recent = []
    o.stats = {"cmd_sent": 0}
    o.brain = FakeBrain()
    o.game_model = None
    o.game_decision_fails = 0
    o.game_context = ""
    o.game_deciding = False
    o.lessons_text = "lesson"
    o.manual_text = "manual"
    o.playbook_text = "playbook"
    o.vault = ""                             # no notes read in the sim
    o.dismiss_ok = True
    o._deck_choice = None
    o._deck_thread = None
    o.spoken = []
    o.notes = []
    o.note = o.notes.append
    o._track_balatro = lambda st: None
    o._blind_notes_for = lambda st: ""
    o._finish_balatro_run = lambda st: None
    o._reset_run_track = lambda: None
    o.maybe_sign_off = lambda force=False: None
    o.push_speech = lambda prio, text, kind: o.spoken.append(text)
    o.balatro_loop()
    return o


print("\n=== scenario 1: a full ante (%d screens) ===\n" % len(ANTE))
o = run(ANTE)
for i, s in enumerate(ANTE):
    print("  %2d. %s" % (i + 1, s["state"]))
print("\n  actions taken : %s" % ", ".join(actions))
print("  brain calls   : %d of %d screens" % (len(brain_calls), len(ANTE)))
for c in brain_calls:
    print("     - %-14s model=%-6s think=%s playbook=%-5s mem=%d"
          % (c["state"], c["model"], c["think"], c["playbook"], len(c["memory"])))
instant = len(ANTE) - len(brain_calls)
print("\n  instant screens: %d  (~%ds of dead air removed per ante at 15s/call)"
      % (instant, instant * 15))
print("  commentary     : %d lines (boss intro included)" % len(o.spoken))

print("\n=== scenario 3: starting at the menu (deck + stake choice) ===\n")
MENU_FIRST = [{"state": "MENU"}] + ANTE[:2]
o = run(MENU_FIRST)
start = [a for a in actions if a.startswith("start_run")]
print("  start call    : %s" % (start[0] if start else "NONE (bug)"))
print("  brain calls   : %d (deck choice only happens once more than one"
      " deck/stake is unlocked)" % len(brain_calls))
print("  recorded      : deck=%s stake=%s wins_before=%s"
      % (o.run_deck, o.run_stake, o.run_wins_before))

print("\n=== scenario 2: the game refuses every move (freeze check) ===\n")
o = run(STUCK, reject_all=True)
print("  brain calls   : %d (re-asked instead of hanging on a dead screen)"
      % len(brain_calls))
mem = [len(c["memory"]) for c in brain_calls]
print("  memory grew   : %s  <- the brain is told WHY it was refused" % mem[:6])
esc = [n for n in o.notes if "escape" in n]
print("  escape hatch  : fired %d time(s) -> %s" % (len(esc), esc[:1]))
print("  loop exited   : %s" % (not o.running))
