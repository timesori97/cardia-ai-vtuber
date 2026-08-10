"""Opus game decision: does lower effort make it faster without going dumb?
Runs the same combat + card-reward state at each effort level."""

import subprocess
import sys
import time
import json

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import Brain, CLAUDE_EXE, PERSONA_PATH, BRAIN_CWD, CREATE_NO_WINDOW
from test_brain import CANNED_COMBAT_STATE

b = Brain()
with open("prompts/game_decision.md", encoding="utf-8") as f:
    tmpl = f.read()

state_json = json.dumps(b and CANNED_COMBAT_STATE, ensure_ascii=False)
prompt = (tmpl.replace("{{MANUAL}}", "(short)").replace("{{LESSONS}}", "- keep it tight")
          .replace("{{PLAYBOOK}}", "(none)").replace("{{ENEMY_NOTES}}", "(none)")
          .replace("{{RECENT_ACTIONS}}", "(none)")
          .replace("{{GAME_STATE_JSON}}", state_json)
          .replace("{{RECENT_LINES}}", "(none)"))


def run(effort):
    args = [CLAUDE_EXE, "-p", "--model", "opus", "--output-format", "json",
            "--max-turns", "1", "--no-session-persistence", "--strict-mcp-config",
            "--tools", "", "--system-prompt-file", PERSONA_PATH]
    if effort:
        args += ["--effort", effort]
    env = dict(__import__("os").environ)
    env["MAX_THINKING_TOKENS"] = "0"
    t0 = time.monotonic()
    p = subprocess.run(args, input=prompt, capture_output=True, encoding="utf-8",
                       errors="replace", timeout=120, cwd=BRAIN_CWD, env=env,
                       creationflags=CREATE_NO_WINDOW)
    dt = time.monotonic() - t0
    try:
        w = json.loads(p.stdout)
        res = w.get("result", "")
        s, e = res.find("{"), res.rfind("}")
        plan = json.loads(res[s:e + 1])
        first = plan["plan"][0]
        return dt, w.get("usage", {}).get("output_tokens"), \
            "%s %s" % (first.get("action"), first.get("card", "")), plan.get("why", "")
    except Exception as ex:
        return dt, None, "PARSE FAIL: %s" % str(ex)[:60], p.stdout[:100]


for effort in ("low", "medium", "high"):
    dt, tok, move, why = run(effort)
    print("effort=%-7s %.1fs  out=%s  -> %s | %s" % (effort, dt, tok, move, why[:60]))
