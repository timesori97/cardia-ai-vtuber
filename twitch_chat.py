"""Read-only Twitch chat via anonymous IRC. No account, no token, never sends.

Connects as justinfan<random> (Twitch's documented anonymous login), requests
tags+commands capabilities, joins one channel, and yields parsed events:

  {"type": "chat", "user": str, "message": str, "bits": int, "ts": float}
  {"type": "sub"|"resub"|"subgift"|"submysterygift"|"giftpaidupgrade",
   "user": str, "system_msg": str, "ts": float}
  {"type": "raid", "user": str, "viewers": int, "system_msg": str, "ts": float}

CLI test:  python twitch_chat.py <channel> [--seconds 30]
"""

import argparse
import os
import random
import socket
import sys
import time

HOST, PORT = "irc.chat.twitch.tv", 6667
RECONNECT_DELAYS = [2, 5, 10, 20, 30]  # then stays at 30s
KIT_DIR = os.path.dirname(os.path.abspath(__file__))

SUB_MSG_IDS = {"sub", "resub", "subgift", "submysterygift", "giftpaidupgrade"}


def load_env(path=None):
    """Tiny KEY=VALUE .env reader (no dependency)."""
    env = {}
    path = path or os.path.join(KIT_DIR, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    return env


def _unescape_tag(value):
    out, i = [], 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append({"s": " ", ":": ";", "r": "\r", "n": "\n", "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_line(line):
    """One raw IRC line -> (tags dict, prefix, command, params list, trailing)."""
    tags = {}
    if line.startswith("@"):
        raw, _, line = line[1:].partition(" ")
        for part in raw.split(";"):
            key, _, val = part.partition("=")
            tags[key] = _unescape_tag(val)
    prefix = ""
    if line.startswith(":"):
        prefix, _, line = line[1:].partition(" ")
    trailing = ""
    if " :" in line:
        line, _, trailing = line.partition(" :")
    parts = line.split()
    command = parts[0] if parts else ""
    return tags, prefix, command, parts[1:], trailing


def _username(tags, prefix):
    name = tags.get("display-name") or tags.get("login")
    if not name and "!" in prefix:
        name = prefix.split("!", 1)[0]
    return name or "someone"


class TwitchChat:
    """Iterate over events(); reconnects internally until .stop() is called."""

    def __init__(self, channel):
        self.channel = channel.lstrip("#").lower()
        self.sock = None
        self.running = True
        self._buf = b""

    def _connect(self):
        nick = "justinfan%d" % random.randint(10000, 99999)
        self.sock = socket.create_connection((HOST, PORT), timeout=15)
        self.sock.settimeout(360)  # Twitch pings roughly every 5 minutes
        self._send("CAP REQ :twitch.tv/tags twitch.tv/commands")
        self._send("NICK " + nick)
        self._send("JOIN #" + self.channel)

    def _send(self, text):
        # Outbound is handshake/PONG only. This bot never sends PRIVMSG.
        self.sock.sendall((text + "\r\n").encode("utf-8"))

    def _lines(self):
        while self.running:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                self._send("PING :keepalive")
                continue
            if not chunk:
                raise ConnectionError("server closed connection")
            self._buf += chunk
            while b"\r\n" in self._buf:
                raw, _, self._buf = self._buf.partition(b"\r\n")
                yield raw.decode("utf-8", errors="replace")

    def events(self):
        attempt = 0
        while self.running:
            try:
                self._connect()
                attempt = 0
                for raw in self._lines():
                    event = self._handle(raw)
                    if event:
                        yield event
            except (OSError, ConnectionError) as e:
                if not self.running:
                    break
                delay = RECONNECT_DELAYS[min(attempt, len(RECONNECT_DELAYS) - 1)]
                attempt += 1
                sys.stderr.write("chat reconnect in %ss (%s)\n" % (delay, e))
                time.sleep(delay)
            finally:
                try:
                    if self.sock:
                        self.sock.close()
                except OSError:
                    pass

    def _handle(self, raw):
        if os.environ.get("TWITCH_DEBUG_RAW"):
            sys.stderr.write("RAW| " + raw[:200] + "\n")
        tags, prefix, command, params, trailing = parse_line(raw)
        if command == "PING":
            self._send("PONG :" + (trailing or "tmi.twitch.tv"))
            return None
        if command == "366":  # end of NAMES: join confirmed
            sys.stderr.write("joined #%s\n" % self.channel)
            return None
        if command == "RECONNECT":
            raise ConnectionError("server requested reconnect")
        if command == "PRIVMSG":
            bits = 0
            if tags.get("bits", "").isdigit():
                bits = int(tags["bits"])
            return {"type": "chat", "user": _username(tags, prefix),
                    "message": trailing, "bits": bits, "ts": time.time()}
        if command == "USERNOTICE":
            msg_id = tags.get("msg-id", "")
            base = {"user": _username(tags, prefix),
                    "system_msg": tags.get("system-msg", ""), "ts": time.time()}
            if msg_id == "raid":
                viewers = tags.get("msg-param-viewerCount", "0")
                base.update(type="raid",
                            viewers=int(viewers) if viewers.isdigit() else 0)
                return base
            if msg_id in SUB_MSG_IDS:
                base.update(type=msg_id)
                return base
        return None

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description="read-only Twitch chat test")
    ap.add_argument("channel", nargs="?", default=load_env().get("TWITCH_CHANNEL", ""))
    ap.add_argument("--seconds", type=int, default=30)
    args = ap.parse_args()
    if not args.channel:
        print("no channel: pass one or set TWITCH_CHANNEL in .env")
        sys.exit(2)

    import threading

    chat = TwitchChat(args.channel)
    counts = {"n": 0}

    def pump():
        for ev in chat.events():
            if ev["type"] == "chat":
                extra = " [bits:%d]" % ev["bits"] if ev["bits"] else ""
                print("<%s>%s %s" % (ev["user"], extra, ev["message"][:120]))
            else:
                print("** %s: %s" % (ev["type"], ev.get("system_msg") or ev))
            counts["n"] += 1
            if counts["n"] >= 40:
                chat.stop()
                return

    print("joining #%s for %ss..." % (chat.channel, args.seconds))
    t = threading.Thread(target=pump, daemon=True)
    t.start()
    t.join(args.seconds)
    chat.stop()
    t.join(3)
    print("--- %d events captured ---" % counts["n"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
