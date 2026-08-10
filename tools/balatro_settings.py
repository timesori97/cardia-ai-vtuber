"""Read and edit Balatro's settings.jkr (game volume, speed, etc).

The save files looked unreadable at first, but they are just Lua source under
raw deflate — so they can be edited after all. Balatro rewrites this file when
it exits, so ONLY edit while the game is closed or the change is lost.

  python tools/balatro_settings.py                 show current settings
  python tools/balatro_settings.py --sound 100     set all three volumes
  python tools/balatro_settings.py --speed 4       game speed (1/2/4)
"""

import argparse
import os
import re
import shutil
import sys
import zlib

SETTINGS = os.path.join(os.environ.get("APPDATA", ""), "Balatro", "settings.jkr")


def read(path=SETTINGS):
    with open(path, "rb") as f:
        return zlib.decompress(f.read(), -15).decode("utf-8", "replace")


def write(text, path=SETTINGS):
    """Round-trip is verified before the file is replaced — a corrupt
    settings.jkr means the game refuses to start."""
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    blob = comp.compress(text.encode("utf-8")) + comp.flush()
    if zlib.decompress(blob, -15).decode("utf-8") != text:
        raise RuntimeError("round-trip failed - refusing to write")
    shutil.copy2(path, path + ".bak")
    with open(path, "wb") as f:
        f.write(blob)


def show(text):
    sound = re.search(r'\["SOUND"\]=\{(.*?)\}', text)
    print("  volumes    : %s" % (sound.group(1) if sound else "?"))
    speed = re.search(r'\["GAMESPEED"\]=([\d.]+)', text)
    print("  game speed : %s" % (speed.group(1) if speed else "?"))
    motion = re.search(r'\["reduced_motion"\]=(\w+)', text)
    print("  reduced motion: %s" % (motion.group(1) if motion else "?"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sound", type=int, help="0-100 for all three volumes")
    ap.add_argument("--speed", type=float, help="game speed (1, 2 or 4)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    text = read()
    print("\nbefore:")
    show(text)

    if args.sound is None and args.speed is None:
        return
    if os.system('tasklist /FI "IMAGENAME eq Balatro.exe" 2>NUL | '
                 'find /I "Balatro.exe" >NUL') == 0:
        print("\n!! Balatro is running - it would overwrite this on exit. "
              "Close the game first.")
        return

    if args.sound is not None:
        v = max(0, min(100, args.sound))
        for key in ("volume", "music_volume", "game_sounds_volume"):
            text = re.sub(r'(\["%s"\]=)[\d.]+' % key, r"\g<1>%d" % v, text)
    if args.speed is not None:
        text = re.sub(r'(\["GAMESPEED"\]=)[\d.]+', r"\g<1>%g" % args.speed, text)

    write(text)
    print("\nafter (re-read from disk):")
    show(read())
    print("\n  backup kept at settings.jkr.bak")


if __name__ == "__main__":
    main()
