"""Ctrl+F12 kill switch, isolated in its own process.

The `keyboard` library installs a low-level Windows hook and has crashed the
whole orchestrator with a native access violation (logs/hardcrash.log,
2026-07-26). A native crash cannot be caught by Python, so the hook now lives
here: if this process dies, the stream keeps running untouched.

Protocol: toggling writes/removes logs/mute.flag; the orchestrator polls it.
"""

import os
import sys
import time

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG = os.path.join(KIT, "logs", "mute.flag")


def toggle():
    try:
        if os.path.exists(FLAG):
            os.remove(FLAG)
            sys.stderr.write("killswitch: UNMUTED\n")
        else:
            with open(FLAG, "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            sys.stderr.write("killswitch: MUTED\n")
        sys.stderr.flush()
    except OSError:
        pass


def main():
    os.makedirs(os.path.dirname(FLAG), exist_ok=True)
    if os.path.exists(FLAG):
        os.remove(FLAG)  # always start unmuted
    import keyboard
    keyboard.add_hotkey("ctrl+f12", toggle)
    sys.stderr.write("killswitch: armed (Ctrl+F12)\n")
    sys.stderr.flush()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
