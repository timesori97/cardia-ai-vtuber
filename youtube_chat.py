"""Read-only YouTube Live chat + Super Chat reader.

Mirrors twitch_chat.py / tiktok_chat.py so the orchestrator treats every
platform the same:

  {"type": "chat",  "user": str, "message": str, "bits": 0, "ts": float}
  {"type": "gift",  "user": str, "gift_name": "Super Chat",
   "count": 1, "diamonds": int, "message": str, "ts": float}

Super Chats arrive as chat items carrying an amount; they are re-tagged as
"gift" so they hit the donation queue (highest priority) exactly like Twitch
bits and TikTok gifts.

Uses pytchat: no API key, no OAuth, no quota — the same "read the public
stream, never post" stance as the Twitch anonymous IRC reader. It is an
unofficial scraper, so it can break when YouTube changes; the reader retries
every 60s and never takes the stream down with it.

The live video is found from the channel's /live page, so the owner only has
to set a channel handle or ID once — no per-stream video ID.

CLI test:  python youtube_chat.py @cardiavt [--seconds 60]
"""

import argparse
import queue
import re
import sys
import threading
import time
import urllib.request

VIDEO_ID_RE = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')
LIVE_NOW_RE = re.compile(r'"isLiveNow"\s*:\s*true')
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# "US$5.00" / "₩5,000" / "£2.50" -> the numeric part, for enthusiasm scaling
AMOUNT_RE = re.compile(r"[\d][\d,.]*")


def resolve_live_video(channel, timeout=20):
    """Channel handle/ID/URL -> the video ID it is currently live on."""
    channel = (channel or "").strip()
    if not channel:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", channel):
        return channel                      # already a video id
    if channel.startswith("http"):
        url = channel.rstrip("/")
        if not url.endswith("/live"):
            url += "/live"
    elif channel.startswith("UC"):
        url = "https://www.youtube.com/channel/%s/live" % channel
    else:
        handle = channel if channel.startswith("@") else "@" + channel
        url = "https://www.youtube.com/%s/live" % handle
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception:
        return None
    # A channel that is NOT live still serves a /live page with some other
    # video's id — connecting to that would replay an old broadcast's chat as
    # if it were happening now. Only "isLiveNow": true means actually live.
    if not LIVE_NOW_RE.search(html):
        return None
    match = VIDEO_ID_RE.search(html)
    return match.group(1) if match else None


def _amount_value(text):
    """'₩5,000' -> 5000 (rough size signal; currency is not normalised)."""
    match = AMOUNT_RE.search(text or "")
    if not match:
        return 0
    try:
        return int(float(match.group(0).replace(",", "")))
    except ValueError:
        return 0


class YouTubeChat:
    def __init__(self, channel):
        self.channel = str(channel).strip()
        self.video_id = None
        self.q = queue.Queue()
        self.running = True

    def _pump(self):
        import asyncio

        import pytchat

        # pytchat spins up asyncio internally; a worker thread has no event
        # loop of its own, which surfaced as a bare ValueError on connect.
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
        except Exception:
            pass

        while self.running:
            video_id = resolve_live_video(self.channel)
            if not video_id:
                sys.stderr.write("youtube: %s is not live - retrying in 60s\n"
                                 % self.channel)
                self._sleep(60)
                continue
            self.video_id = video_id
            try:
                # interruptable=False: pytchat installs a SIGINT handler by
                # default, which only works on the main thread ("signal only
                # works in main thread of the main interpreter").
                chat = pytchat.create(video_id=video_id, interruptable=False)
                sys.stderr.write("youtube: connected to %s (video %s)\n"
                                 % (self.channel, video_id))
                while self.running and chat.is_alive():
                    for item in chat.get().sync_items():
                        self._emit(item)
                    time.sleep(1)
                try:
                    chat.terminate()
                except Exception:
                    pass
            except Exception as e:
                if not self.running:
                    break
                sys.stderr.write("youtube: chat error (%s: %s) - retrying in 60s\n"
                                 % (type(e).__name__, str(e)[:120]))
                self._sleep(60)
                continue
            if self.running:
                sys.stderr.write("youtube: chat ended - rechecking in 60s\n")
                self._sleep(60)

    def _emit(self, item):
        user = getattr(getattr(item, "author", None), "name", "") or "someone"
        message = getattr(item, "message", "") or ""
        amount = getattr(item, "amountString", "") or ""
        if amount:      # Super Chat / Super Sticker -> donation queue
            self.q.put({"type": "gift", "user": user,
                        "gift_name": "Super Chat", "count": 1,
                        "diamonds": _amount_value(amount),
                        "amount_text": amount, "message": message,
                        "ts": time.time()})
        else:
            self.q.put({"type": "chat", "user": user, "message": message,
                        "bits": 0, "ts": time.time()})

    def _sleep(self, seconds):
        for _ in range(int(seconds)):
            if not self.running:
                return
            time.sleep(1)

    def events(self):
        threading.Thread(target=self._pump, daemon=True).start()
        while self.running:
            try:
                yield self.q.get(timeout=1)
            except queue.Empty:
                continue

    def stop(self):
        self.running = False


def main():
    ap = argparse.ArgumentParser(description="read-only YouTube live chat test")
    ap.add_argument("channel", help="@handle, channel id, URL, or video id")
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()

    chat = YouTubeChat(args.channel)
    counts = {"n": 0}

    def pump():
        for ev in chat.events():
            if ev["type"] == "chat":
                print("<%s> %s" % (ev["user"], ev["message"][:120]))
            else:
                print("** SUPER CHAT %s from %s: %s"
                      % (ev.get("amount_text"), ev["user"], ev.get("message", "")[:80]))
            counts["n"] += 1

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    print("listening to %s for %ss..." % (args.channel, args.seconds))
    time.sleep(args.seconds)
    chat.stop()
    print("--- %d events (video %s) ---" % (counts["n"], chat.video_id))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
