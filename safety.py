"""Layer 0 deterministic chat filter (see safety.md).

Runs on every incoming message BEFORE anything is buffered for the brain.
Layer 1 (the haiku ALLOW/BLOCK/DISTRESS classifier) lives in brain.classify;
the orchestrator wires the two together. Everything here fails closed and
never announces a block on stream.
"""

import os
import re
import time

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOCKLIST_PATH = os.path.join(KIT_DIR, "config", "blocklist.txt")

MAX_LEN = 200
PER_USER_COOLDOWN_S = 60
NON_ASCII_DROP_RATIO = 0.5

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a",
                      "5": "s", "7": "t", "@": "a", "$": "s"})
URL_RE = re.compile(r"(https?://|www\.|\b\w+\.(?:com|net|org|tv|gg|io|ru|xyz)\b)", re.I)
HANGUL_RE = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")  # Korean viewers are legit, not spam
CHEER_RE = re.compile(r"\b(?:cheer|bitboss|doodlecheer|uni|hype|pogchamp|kappa|streamlabs)\d+\b", re.I)
MENTION_RE = re.compile(r"@\w+")
REPEAT_RE = re.compile(r"(.)\1{7,}")
WS_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z']+")


def _fold(text):
    """lowercase + leetspeak fold + non-alnum -> space, for matching only."""
    text = text.lower().translate(LEET)
    return WS_RE.sub(" ", re.sub(r"[^a-z' ]", " ", text)).strip()


class Layer0:
    def __init__(self, blocklist_path=BLOCKLIST_PATH):
        self.words = set()
        self.phrases = []
        self.raw_phrases = []  # non-ASCII entries (e.g. Korean): raw substring match
        if os.path.exists(blocklist_path):
            with open(blocklist_path, encoding="utf-8-sig") as f:
                for line in f:
                    entry = line.strip().lower()
                    if not entry or entry.startswith("#"):
                        continue
                    if any(ord(ch) > 127 for ch in entry):
                        self.raw_phrases.append(entry)
                        continue
                    folded = _fold(entry)
                    if not folded:
                        continue
                    if " " in folded:
                        self.phrases.append(folded)
                    else:
                        self.words.add(folded)
        self.answered = {}  # user(lower) -> last reacted-to timestamp

    def mark_answered(self, users):
        now = time.time()
        for user in users:
            self.answered[str(user).lower()] = now

    def check(self, user, message):
        """-> (allowed: bool, cleaned_message: str, reason: str)."""
        msg = (message or "").strip()
        if not msg:
            return False, "", "empty"
        if len(msg) > MAX_LEN:
            return False, "", "too_long"
        if URL_RE.search(msg):
            return False, "", "url"
        if REPEAT_RE.search(msg):
            return False, "", "char_spam"
        ascii_count = sum(1 for ch in msg if ord(ch) < 128)
        if (len(msg) >= 6 and ascii_count / len(msg) < NON_ASCII_DROP_RATIO
                and not HANGUL_RE.search(msg)):
            return False, "", "non_ascii_spam"
        lowered = msg.lower()
        for phrase in self.raw_phrases:
            if phrase in lowered:
                return False, "", "blocklist_phrase"
        last = self.answered.get(str(user).lower())
        if last and time.time() - last < PER_USER_COOLDOWN_S:
            return False, "", "user_cooldown"

        folded = _fold(msg)
        tokens = set(TOKEN_RE.findall(folded))
        if tokens & self.words:
            return False, "", "blocklist_word"
        for phrase in self.phrases:
            if phrase in folded:
                return False, "", "blocklist_phrase"

        # sanitize what the brain will see: no third-party @mentions, no
        # cheermote syntax, collapsed whitespace
        cleaned = CHEER_RE.sub(" ", msg)
        cleaned = MENTION_RE.sub(" ", cleaned)
        cleaned = WS_RE.sub(" ", cleaned).strip()
        if not cleaned:
            return False, "", "empty_after_clean"
        return True, cleaned, "ok"
