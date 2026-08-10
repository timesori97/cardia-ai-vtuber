"""Read-only TikTok LIVE chat/gift reader.

Uses the unofficial TikTokLive library (the same webcast interface every
TikTok chat bot uses). Read-only: we never post, never authenticate.
Events mirror twitch_chat.py so the orchestrator treats both sources alike:

  {"type": "chat", "user": str, "message": str, "bits": 0, "ts": float}
  {"type": "gift", "user": str, "gift_name": str, "count": int,
   "diamonds": int, "ts": float}   # diamonds ~ gift value, drives enthusiasm

When the account is not live, the client fails and we retry every 60s, so the
orchestrator can keep this thread running for the whole session.

CLI test:  python tiktok_chat.py <username> [--seconds 60]
"""

import argparse
import queue
import sys
import threading
import time


class TikTokChat:
    def __init__(self, username):
        self.username = str(username).lstrip("@").strip()
        self.q = queue.Queue()
        self.running = True

    def _pump(self):
        import asyncio
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import CommentEvent, ConnectEvent, GiftEvent

        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
        except Exception:
            pass

        while self.running:
            try:
                client = TikTokLiveClient(unique_id="@" + self.username)

                @client.on(ConnectEvent)
                async def _on_connect(event):
                    sys.stderr.write("tiktok: connected to @%s\n" % self.username)

                @client.on(CommentEvent)
                async def _on_comment(event):
                    user = (getattr(event.user, "nickname", "")
                            or getattr(event.user, "unique_id", "") or "someone")
                    self.q.put({"type": "chat", "user": user,
                                "message": event.comment or "", "bits": 0,
                                "ts": time.time()})

                @client.on(GiftEvent)
                async def _on_gift(event):
                    gift = getattr(event, "gift", None)
                    streakable = bool(getattr(gift, "streakable", False))
                    if streakable and getattr(event, "streaking", False):
                        return  # thank once when the combo finishes, not per tick
                    count = getattr(event, "repeat_count", 1) or 1
                    diamonds = (getattr(gift, "diamond_count", 0) or 0) * count
                    user = (getattr(event.user, "nickname", "")
                            or getattr(event.user, "unique_id", "") or "someone")
                    self.q.put({"type": "gift", "user": user,
                                "gift_name": getattr(gift, "name", "a gift"),
                                "count": count, "diamonds": diamonds,
                                "ts": time.time()})

                client.run()  # blocks until the live ends or errors
            except Exception as e:
                if not self.running:
                    break
                sys.stderr.write("tiktok: not live or disconnected (%s) - "
                                 "retrying in 60s\n" % type(e).__name__)
                for _ in range(60):
                    if not self.running:
                        break
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
    ap = argparse.ArgumentParser(description="read-only TikTok LIVE chat test")
    ap.add_argument("username")
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()

    chat = TikTokChat(args.username)
    counts = {"n": 0}

    def pump():
        for ev in chat.events():
            if ev["type"] == "chat":
                print("<%s> %s" % (ev["user"], ev["message"][:120]))
            else:
                print("** GIFT %s x%d (%d diamonds) from %s"
                      % (ev["gift_name"], ev["count"], ev["diamonds"], ev["user"]))
            counts["n"] += 1

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    print("listening to @%s for %ss..." % (chat.username, args.seconds))
    time.sleep(args.seconds)
    chat.stop()
    print("--- %d events ---" % counts["n"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
