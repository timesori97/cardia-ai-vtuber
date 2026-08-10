"""Persistent process, but with REAL prompts — does context pile up?

bench_persistent proved a warm process answers in ~3s instead of ~9s. The
open risk is that every message stays in one conversation: our prompts are
3-4k tokens each and a stream makes hundreds of decisions, so unbounded growth
would get slower and start referencing stale board states.

This sends the actual balatro_decision prompt repeatedly and watches latency
and context size, with and without a /clear between messages.

Run: python tools/bench_persistent2.py
"""

import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import BRAIN_CWD, CLAUDE_EXE, CREATE_NO_WINDOW, PERSONA_PATH, Brain
from bench_balatro import HAND_STATE, LESSONS, MANUAL, PLAYBOOK

ARGS = [
    CLAUDE_EXE, "-p",
    "--model", "sonnet",
    "--input-format", "stream-json",
    "--output-format", "stream-json",
    "--verbose",
    "--no-session-persistence",
    "--strict-mcp-config",
    "--tools", "",
    "--system-prompt-file", PERSONA_PATH,
]


def user_msg(text):
    return json.dumps({"type": "user",
                       "message": {"role": "user",
                                   "content": [{"type": "text", "text": text}]}})


def build_prompt(hands_left):
    b = Brain()
    state = dict(HAND_STATE, hands_left=hands_left)
    return b._fill("balatro_decision", {
        "MANUAL": MANUAL, "PLAYBOOK": PLAYBOOK, "LESSONS": LESSONS,
        "ENEMY_NOTES": "(none)", "RECENT_ACTIONS": "(none yet)",
        "GAME_STATE_JSON": json.dumps(state), "RECENT_LINES": "",
    })


def run(label, clear_between, rounds=5):
    proc = subprocess.Popen(
        ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
        cwd=BRAIN_CWD, env=dict(os.environ, MAX_THINKING_TOKENS="0"),
        bufsize=1,
        creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    errs = []
    threading.Thread(target=lambda: errs.extend(proc.stderr), daemon=True).start()

    def send(text):
        t = time.monotonic()
        proc.stdin.write(user_msg(text) + "\n")
        proc.stdin.flush()
        while True:
            line = proc.stdout.readline()
            if not line:
                return None, time.monotonic() - t
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "result":
                return ev, time.monotonic() - t

    print("\n=== %s ===" % label)
    prompt_chars = None
    try:
        for i in range(rounds):
            if clear_between and i:
                send("/clear")
            text = build_prompt(4 - (i % 4))
            prompt_chars = prompt_chars or len(text)
            res, secs = send(text)
            if not res:
                print("  round %d: process died" % (i + 1))
                break
            u = res.get("usage") or {}
            ctx = (u.get("input_tokens", 0)
                   + u.get("cache_read_input_tokens", 0)
                   + u.get("cache_creation_input_tokens", 0))
            body = str(res.get("result", "")).replace("\n", " ")
            print("  round %d: %5.1fs  context %6d tok  %s"
                  % (i + 1, secs, ctx, body[:46]))
    finally:
        try:
            proc.stdin.close()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    if errs:
        print("  stderr: %s" % "".join(errs)[:200])
    print("  (prompt itself is ~%d chars)" % (prompt_chars or 0))


run("persistent, conversation kept", clear_between=False)
run("persistent, /clear between decisions", clear_between=True)
