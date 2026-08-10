"""Cardia TTS — Piper synthesis played onto the VB-Cable input device.

Pipeline: sanitize text -> piper.exe (WAV file) -> sounddevice playback on the
output device whose name contains "CABLE Input". veadotube listens on CABLE
Output for lip sync; OBS captures CABLE Output as the stream's voice audio.

CLI usage:
  python tts.py --list-devices
  python tts.py "text to speak"            # play on CABLE Input
  python tts.py "text" --default-device    # play on system default (pre-VB-Cable test)
"""

import argparse
import os
import re
import subprocess
import sys
import time
import wave

import numpy as np
import sounddevice as sd

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPER_DIR = os.path.join(KIT_DIR, "tools", "piper")
PIPER_EXE = os.path.join(PIPER_DIR, "piper.exe")
VOICE_ONNX = os.path.join(PIPER_DIR, "voices", "en_US-amy-medium.onnx")
TTS_OUT_DIR = os.path.join(KIT_DIR, "tools", "tts-out")
DEVICE_SUBSTR = "CABLE Input"
CREATE_NO_WINDOW = 0x08000000

# Spoken text should be plain words and light punctuation. Everything else
# (emoji, markdown, cheermote syntax, urls, non-ascii) either mangles the
# en_US voice or wastes air, so it is stripped before synthesis.
_URL_RE = re.compile(r"https?://\S+")
_KEEP_RE = re.compile(r"[^A-Za-z0-9 .,!?;:'\"()-]")
_WS_RE = re.compile(r"\s+")


def sanitize(text):
    text = _URL_RE.sub(" ", text or "")
    for ch in "*#_~`^|<>[]{}\\/":
        text = text.replace(ch, " ")
    text = text.replace("—", ", ").replace("–", ", ")  # dashes -> pause
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = _KEEP_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()


def synth(text, out_path=None):
    """Sanitized text -> WAV file path, or None when nothing speakable/failed."""
    clean = sanitize(text)
    if not clean:
        return None
    os.makedirs(TTS_OUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(TTS_OUT_DIR, "utt_%d.wav" % int(time.time() * 1000))
    proc = subprocess.run(
        [PIPER_EXE, "--model", VOICE_ONNX, "--output_file", out_path],
        input=clean, capture_output=True, encoding="utf-8", errors="replace",
        timeout=60, cwd=PIPER_DIR,
        creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    if proc.returncode != 0 or not os.path.exists(out_path):
        sys.stderr.write("piper failed: " + (proc.stderr or "")[:300] + "\n")
        return None
    return out_path


def find_device(substr=DEVICE_SUBSTR):
    for idx, dev in enumerate(sd.query_devices()):
        if substr.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
            return idx
    return None


def play_wav(path, device=None):
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels())
    if data.ndim == 1:
        # Piper is mono; mirror it onto channels 1+2 so multichannel devices
        # (CABLE Input is 16ch) don't end up with left-only stream audio.
        try:
            sd.play(data, rate, device=device, mapping=[1, 2], blocking=True)
            return
        except Exception:
            pass  # mono-only device: fall through to plain playback
    sd.play(data, rate, device=device, blocking=True)


def speak(text, device_substr=DEVICE_SUBSTR, use_default=False, keep_wav=False):
    """Full pipeline. Returns True if audio was played to completion."""
    path = synth(text)
    if path is None:
        return False
    device = None
    if not use_default:
        device = find_device(device_substr)
        if device is None:
            sys.stderr.write("output device not found: " + device_substr + "\n")
            return False
    try:
        play_wav(path, device)
    finally:
        if not keep_wav:
            try:
                os.remove(path)
            except OSError:
                pass
    return True


def main():
    ap = argparse.ArgumentParser(description="Cardia TTS")
    ap.add_argument("text", nargs="*", help="text to speak")
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--default-device", action="store_true",
                    help="play on system default instead of CABLE Input")
    args = ap.parse_args()

    if args.list_devices:
        for idx, dev in enumerate(sd.query_devices()):
            if dev["max_output_channels"] > 0:
                print("%3d  %s  (out ch: %d)" % (idx, dev["name"], dev["max_output_channels"]))
        return

    text = " ".join(args.text) or (
        "Cardia voice check. All systems nominal, "
        "probability of success ninety-nine point nine percent.")
    ok = speak(text, use_default=args.default_device)
    print("spoken" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
