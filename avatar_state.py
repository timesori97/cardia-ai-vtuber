"""Switch veadotube mini's avatar state from the stream brain.

veadotube already does the mouth flapping from the TTS audio, but the face
never changes. It exposes a websocket where each "state" is a whole avatar
look (its own open/closed mouth and eye images), so giving Cardia a face for
winning, panicking and dying costs nothing at runtime — one tiny local
message, no extra rendering.

Protocol, confirmed against veadotube mini 2.2 by probing it:
  - the port changes every launch and is published in
    ~/.veadotube/instances/<id>  as {"server": "127.0.0.1:PORT", ...}
  - connect to  ws://<server>?n=<client name>
  - every message is the channel name, a colon, then JSON:
        nodes:{"event":"payload","type":"stateEvents","id":"mini",
               "payload":{"event":"list"}}
  - "list" returns the states, "set" switches (no reply), "peek" reports
    the current one

Nothing here may raise: a missing avatar must never disturb the stream.
"""

import glob
import json
import os
import threading
import time

INSTANCE_DIR = os.path.join(os.path.expanduser("~"), ".veadotube", "instances")

# What each mood is called in veadotube. The owner names the states when they
# add the artwork; matching is loose so "smug", "Smug", "smug face" all count.
MOOD_WORDS = {
    "neutral": ("neutral", "idle", "default", "base", "aaaaa"),
    "smug": ("smug", "win", "confident", "proud"),
    "nervous": ("nervous", "boss", "sweat", "worried", "tense"),
    "shocked": ("shocked", "surprise", "panic"),
    "sad": ("sad", "lose", "lost", "defeat", "dead"),
    "excited": ("excited", "happy", "unlock", "star"),
}


class AvatarStates:
    """Best-effort control of the avatar's face. Every call is safe."""

    RECONNECT_AFTER_S = 20      # do not hammer a closed app

    def __init__(self, note=None):
        self.note = note or (lambda _m: None)
        self._ws = None
        self._states = []
        self._lock = threading.Lock()
        self._last_try = 0.0
        self._revert_timer = None

    # ---------- connection ----------

    def _instance(self):
        try:
            files = glob.glob(os.path.join(INSTANCE_DIR, "*"))
            if not files:
                return None
            with open(max(files, key=os.path.getmtime), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _connect(self):
        if self._ws is not None:
            return True
        if time.time() - self._last_try < self.RECONNECT_AFTER_S:
            return False
        self._last_try = time.time()
        info = self._instance()
        if not info or not info.get("server"):
            return False
        try:
            import websocket
            self._ws = websocket.create_connection(
                "ws://%s?n=cardia" % info["server"], timeout=4)
            self._states = self._list_states()
            if self._states:
                self.note("avatar states: %s"
                          % ", ".join(s["name"] for s in self._states))
            return True
        except Exception:
            self._ws = None
            return False

    def _drop(self):
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None

    def _send(self, payload):
        msg = "nodes:" + json.dumps({"event": "payload", "type": "stateEvents",
                                     "id": "mini", "payload": payload})
        self._ws.send(msg)

    def _read_state_event(self, tries=5):
        """Skip the greeting and any chatter until a stateEvents reply."""
        for _ in range(tries):
            raw = str(self._ws.recv())
            if raw.startswith("nodes:"):
                try:
                    return json.loads(raw[len("nodes:"):])
                except ValueError:
                    return None
        return None

    def _list_states(self):
        self._send({"event": "list"})
        msg = self._read_state_event()
        return ((msg or {}).get("payload") or {}).get("states") or []

    # ---------- public ----------

    def available(self):
        with self._lock:
            return [s["name"] for s in self._states] if self._connect() else []

    def set_mood(self, mood, hold_s=0):
        """Show this mood if the avatar has a face for it, else do nothing.
        With hold_s, drop back to neutral afterwards."""
        with self._lock:
            if not self._connect():
                return False
            state = self._match(mood)
            if not state:
                return False
            try:
                self._send({"event": "set", "state": state["id"]})
            except Exception:
                self._drop()
                return False
        if hold_s:
            self._schedule_revert(hold_s)
        return True

    def _match(self, mood):
        words = MOOD_WORDS.get(mood, (mood,))
        for state in self._states:
            name = str(state.get("name", "")).lower()
            if any(w in name for w in words):
                return state
        return None

    def _schedule_revert(self, delay):
        if self._revert_timer:
            self._revert_timer.cancel()
        self._revert_timer = threading.Timer(delay, self.set_mood, ("neutral",))
        self._revert_timer.daemon = True
        self._revert_timer.start()

    def current(self):
        with self._lock:
            if not self._connect():
                return None
            try:
                self._send({"event": "peek"})
                msg = self._read_state_event(tries=3)
                return ((msg or {}).get("payload") or {}).get("state")
            except Exception:
                self._drop()
                return None

    def close(self):
        if self._revert_timer:
            self._revert_timer.cancel()
        with self._lock:
            self._drop()


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    av = AvatarStates(note=print)
    names = av.available()
    print("states available: %s" % (names or "(none — is veadotube running?)"))
    print("currently showing: %s" % av.current())
    if len(sys.argv) > 1:
        mood = sys.argv[1]
        print("set_mood(%r) -> %s" % (mood, av.set_mood(mood)))
        time.sleep(0.5)
        print("now showing: %s" % av.current())
    av.close()


if __name__ == "__main__":
    main()
