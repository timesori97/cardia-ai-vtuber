"""Verify the stream cap and the shutdown ordering."""

import inspect
import sys
import time

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import Orchestrator

o = Orchestrator(game_link=False, use_twitch=False, use_tts=False)
if o.stream_deadline:
    print("stream cap: %.2f hours" % ((o.stream_deadline - time.time()) / 3600))
else:
    print("stream cap: disabled")

src = inspect.getsource(Orchestrator.maybe_sign_off)
print("\nshutdown steps in code order:")
for line in src.splitlines():
    if "shutdown " in line and "note(" in line:
        print("  " + line.strip())

print("\nsafety checks:")
print("  farewell before kills   :", src.index("FAREWELL_LINE") < src.index("shutdown 1/4"))
print("  stream before game      :", src.index("shutdown 1/4") < src.index("shutdown 2/4"))
print("  game before avatar      :", src.index("shutdown 2/4") < src.index("shutdown 3/4"))
print("  avatar before self exit :", src.index("shutdown 3/4") < src.index("os._exit(0)"))
print("  game kill has no /T     :", '"/T"' not in src)
print("  self-exit present       :", "os._exit(0)" in src)
