"""Can ONE claude process answer many decisions, instead of one process each?

Live logs: the model answers in 4-10s but each call costs 20-50s, because a
fresh `claude` process is booted and torn down every single time on a 2-core
CPU. --input-format stream-json keeps one process alive and feeds it messages,
which would delete that overhead entirely.

Two things must hold for this to be usable:
  1. the 2nd and later answers must be much faster than a cold call
  2. context must NOT pile up (our prompts are independent and large)

Run: python tools/bench_persistent.py   (best with the game NOT running)
"""

import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from brain import BRAIN_CWD, CLAUDE_EXE, CREATE_NO_WINDOW, PERSONA_PATH

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

PROMPTS = [
    'Reply with STRICT JSON only, no prose: {"plan":[{"action":"play","cards":[0,1]}],"why":"pair of kings","say":""}',
    'Reply with STRICT JSON only, no prose: {"plan":[{"action":"discard","cards":[2,3]}],"why":"chase the flush","say":""}',
    'Reply with STRICT JSON only, no prose: {"plan":[{"action":"buy","card":0}],"why":"xmult joker","say":""}',
    'Reply with STRICT JSON only, no prose: {"plan":[{"action":"next_round"}],"why":"nothing worth buying","say":""}',
]


def user_msg(text):
    return json.dumps({"type": "user",
                       "message": {"role": "user",
                                   "content": [{"type": "text", "text": text}]}})


def main():
    proc = subprocess.Popen(
        ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
        cwd=BRAIN_CWD, env=dict(os.environ, MAX_THINKING_TOKENS="0"),
        bufsize=1,
        creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)

    errs = []
    threading.Thread(target=lambda: errs.extend(proc.stderr),
                     daemon=True).start()

    print("\n=== one process, %d decisions ===\n" % len(PROMPTS))
    ok = True
    for i, text in enumerate(PROMPTS):
        t = time.monotonic()
        try:
            proc.stdin.write(user_msg(text) + "\n")
            proc.stdin.flush()
        except OSError as e:
            print("  msg %d: could not write (%s) - process dead" % (i + 1, e))
            ok = False
            break
        result = None
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "result":
                result = ev
                break
        secs = time.monotonic() - t
        if not result:
            print("  msg %d: no result after %.1fs - process died" % (i + 1, secs))
            ok = False
            break
        print("  msg %d: %5.1fs   model %sms   in_tokens %s   %s"
              % (i + 1, secs, result.get("duration_api_ms"),
                 (result.get("usage") or {}).get("input_tokens"),
                 str(result.get("result", ""))[:52].replace("\n", " ")))

    try:
        proc.stdin.close()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    if errs:
        print("\n  stderr: %s" % "".join(errs)[:300])
    if ok:
        print("\n  Watch input_tokens: if it climbs every message, context is")
        print("  piling up and each call gets slower and more confused.")


if __name__ == "__main__":
    main()
