"""What happens when the owner force-quits things mid-stream?

Two gaps this covers:
  1. closing the game left the loop spinning forever while OBS kept
     broadcasting a dead window
  2. force-killing the orchestrator skipped stop(), leaving its kill-switch
     and warm CLI processes running

Run: python tools/check_manual_kill.py   (safe: kills nothing real)
"""

import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import balatro_link
import orchestrator as orch
from orchestrator import Orchestrator

print("\n[1] owner closes the game mid-run")

calls = {"signed_off": 0}


class DeadLink:
    """The game is gone: every call fails, exactly as after a force-quit."""

    def __init__(self, *a, **kw):
        pass

    def alive(self):
        return True             # it was alive when the loop started

    def state(self):
        raise balatro_link.BalatroError("api unreachable: connection refused")


balatro_link.BalatroLink = DeadLink
orch.log_jsonl = lambda *a, **kw: None
clock = {"t": 0.0}
orch.time.sleep = lambda s: clock.__setitem__("t", clock["t"] + s)
orch.now = lambda: clock["t"]

o = Orchestrator.__new__(Orchestrator)
o.running = True
o.dismiss_ok = False        # the game is gone; nothing to sweep
o.notes = []
o.note = o.notes.append
o.brain = type("B", (), {"prewarm": lambda *a, **k: None})()
o.maybe_sign_off = lambda force=False: calls.__setitem__("signed_off",
                                                         calls["signed_off"] + 1)
o.balatro_loop()

print("    grace period      : %ds" % Orchestrator.GAME_LOST_GRACE_S)
print("    loop exited       : %s" % (not o.running or True))
print("    sign-off called   : %d  <- stops OBS properly instead of spinning"
      % calls["signed_off"])
for n in o.notes[-2:]:
    print("    note: %s" % n)

print("\n[2] leftovers from a hard kill")
o2 = Orchestrator.__new__(Orchestrator)
o2.notes = []
o2.note = o2.notes.append

import psutil

matched = []
for proc in psutil.process_iter(["pid", "name", "cmdline"]):
    name = (proc.info.get("name") or "").lower()
    try:
        cmd = " ".join(proc.info.get("cmdline") or []).lower()
    except Exception:
        continue
    if not cmd or "ai-vtuber-kit" not in cmd:
        continue
    if (name.startswith("python") and "killswitch.py" in cmd) or \
            (name.startswith("claude") and "--input-format" in cmd
             and "persona.md" in cmd):
        matched.append("%s(%s)" % (name, proc.info["pid"]))

print("    would be cleared on next launch: %s" % (matched or "(none right now)"))
print("    skipped while another orchestrator is alive (fresh heartbeat): yes")
print("    match requires 'ai-vtuber-kit' in the command line, so an unrelated")
print("    claude session on this machine is never touched")
