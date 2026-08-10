"""Latency isolation bench: one chat_react-shaped haiku call per flag variant.

Run: python tools/bench_brain.py
Prints wall / api / output-token numbers so we can see where time goes.
"""

import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(KIT, "tools", "claude-cli", "node_modules",
                   "@anthropic-ai", "claude-code", "bin", "claude.exe")
PERSONA = os.path.join(KIT, "persona.md")
CWD = os.path.join(KIT, "tools", "brain-cwd")

with open(os.path.join(KIT, "prompts", "chat_react.md"), encoding="utf-8") as f:
    TEMPLATE = f.read()

PROMPT = (TEMPLATE
          .replace("{{GAME_CONTEXT}}", "Act one floor three, fighting a Jaw Worm.")
          .replace("{{CHAT_MESSAGES_JSON}}", json.dumps([
              {"user": "CardFan99", "message": "cardia what is your actual win rate be honest"},
              {"user": "lurker_toad", "message": "first time here, this AI plays by itself??"}]))
          .replace("{{RECENT_LINES}}", "- The RNG owes me three apologies already."))

BASE = [EXE, "-p", "--model", "haiku", "--output-format", "json", "--max-turns", "1",
        "--no-session-persistence", "--strict-mcp-config",
        "--system-prompt-file", PERSONA]

VARIANTS = {
    "A effort=low + tools ''": BASE + ["--effort", "low", "--tools", ""],
    "B effort=low, no tools flag": BASE + ["--effort", "low"],
    "C default effort + tools ''": BASE + ["--tools", ""],
}

for name, args in VARIANTS.items():
    t0 = time.monotonic()
    proc = subprocess.run(args, input=PROMPT, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=90, cwd=CWD,
                          creationflags=0x08000000)
    wall = int((time.monotonic() - t0) * 1000)
    try:
        w = json.loads(proc.stdout)
        print(f"{name}: wall={wall}ms api={w.get('duration_api_ms')}ms "
              f"out_tokens={w.get('usage', {}).get('output_tokens')} "
              f"is_error={w.get('is_error')}")
        print("   result: " + str(w.get("result"))[:150].replace("\n", " "))
    except json.JSONDecodeError:
        print(f"{name}: wall={wall}ms exit={proc.returncode} "
              f"stdout={proc.stdout[:200]} stderr={proc.stderr[:200]}")
