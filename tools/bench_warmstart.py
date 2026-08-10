"""Where do the seconds actually go — the model, or booting the CLI?

Live logs say the model answers in 4-10s while the whole call takes 20-50s.
If the `claude` process does its boot work BEFORE it reads stdin, then keeping
a process already booted and only then handing it the prompt hides all of it.

Run: python tools/bench_warmstart.py   (best with the game NOT running)
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import BRAIN_CWD, CLAUDE_EXE, CREATE_NO_WINDOW, PERSONA_PATH

PROMPT = ('Reply with STRICT JSON only: {"plan":[{"action":"play",'
          '"cards":[0,1]}],"why":"pair","say":""}')

ARGS = [
    CLAUDE_EXE, "-p",
    "--model", "sonnet",
    "--output-format", "json",
    "--max-turns", "1",
    "--no-session-persistence",
    "--strict-mcp-config",
    "--tools", "",
    "--system-prompt-file", PERSONA_PATH,
]
ENV = dict(os.environ, MAX_THINKING_TOKENS="0")


def spawn():
    return subprocess.Popen(
        ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
        cwd=BRAIN_CWD, env=ENV,
        creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)


def cold():
    t = time.monotonic()
    proc = spawn()
    out, _ = proc.communicate(input=PROMPT, timeout=180)
    return time.monotonic() - t, out


def warm(prewarm_s):
    """Spawn first, wait, THEN hand it the prompt. We only count the wait
    from the moment the prompt is written — that is what the stream feels."""
    proc = spawn()
    time.sleep(prewarm_s)
    alive = proc.poll() is None
    t = time.monotonic()
    out, errtext = proc.communicate(input=PROMPT, timeout=180)
    if not alive:
        print("      (process had already exited: rc=%s, stderr=%r, stdout=%r)"
              % (proc.returncode, (errtext or "")[:200], (out or "")[:200]))
    return time.monotonic() - t, out


def api_ms(out):
    try:
        import json
        return json.loads(out).get("duration_api_ms")
    except Exception:
        return None


print("\n=== is the wait the model, or the process? ===\n")
for i in range(3):
    secs, out = cold()
    print("  cold  run %d: %5.1fs total   (model itself: %sms)"
          % (i + 1, secs, api_ms(out)))
print()
for i in range(3):
    secs, out = warm(20)
    print("  warm  run %d: %5.1fs after the prompt is handed over   "
          "(model itself: %sms)" % (i + 1, secs, api_ms(out)))
print("\n  'warm' = process spawned 20s earlier and already booted.")
print("  If warm is much lower, pre-warming a process is the whole fix.")
