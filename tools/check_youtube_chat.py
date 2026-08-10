"""Verify the YouTube chat reader: live detection, amount parsing, routing."""

import sys

sys.path.insert(0, "D:/ai-vtuber-kit")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from youtube_chat import resolve_live_video, _amount_value
from twitch_chat import load_env

env = load_env()
mine = env.get("YOUTUBE_CHANNEL", "").strip()

print("=== live detection ===")
print("  @SkyNews (live now)      ->", resolve_live_video("@SkyNews"))
print("  %-24s ->" % mine, resolve_live_video(mine), "(None = not live, correct)")
print("  video id passthrough     ->", resolve_live_video("rSh-jjUIhLA"))

print("\n=== super chat amount parsing ===")
for text in ("US$5.00", "\u20a95,000", "\u00a32.50", "\u00a51,000", ""):
    print("  %-10s -> %s" % (text or "(none)", _amount_value(text)))

print("\n=== routing ===")
from orchestrator import Orchestrator

o = Orchestrator(game_link=False, use_twitch=False, use_tts=False)
o.ingest_chat_event({"type": "gift", "user": "Supporter", "gift_name": "Super Chat",
                     "count": 1, "diamonds": 5000, "amount_text": "\u20a95,000",
                     "message": "good luck", "ts": 0})
with o.gen_cv:
    prio, _, kind, payload = o.gen_q[0]
print("  super chat -> queue %s, priority %d (0 = donation, highest)" % (kind, prio))
o.ingest_chat_event({"type": "chat", "user": "viewer", "message": "hello cardia",
                     "bits": 0, "ts": 0})
print("  plain chat -> buffered:", len(o.chat_buffer))
o.ingest_chat_event({"type": "chat", "user": "spammer",
                     "message": "free viewers at cheapviews.com", "bits": 0, "ts": 0})
print("  spam chat  -> buffered:", len(o.chat_buffer), "(unchanged = filtered)")
