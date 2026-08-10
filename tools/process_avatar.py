"""Turn the generated avatar PNGs (green screen) into veadotube-ready art.

Each mood is its own veadotube state, so the source is one folder per mood:

    avatar_new/neutral/idle_open.png ...   ->  avatar/neutral/...
    avatar_new/smug/...                    ->  avatar/smug/...

- Chroma-keys the solid green background to transparency.
- Despills green-tinged edge pixels.
- Reports content bounding boxes. Drift matters twice over: within a mood a
  mismatch makes the avatar jump when it blinks, and across moods it makes
  her jump when her expression changes.
- Backs up whatever was there into avatar/previous_version/.

A single flat avatar_new/ (no mood folders) still works and is treated as
"neutral", which is how the first avatar was made.

Run: python tools/process_avatar.py
"""

import os
import shutil

import numpy as np
from PIL import Image

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(KIT, "avatar_new")
DST = os.path.join(KIT, "avatar")
BACKUP = os.path.join(DST, "previous_version")
NAMES = ["idle_closed.png", "idle_open.png", "blink_closed.png", "blink_open.png"]
SIZE = 512
DRIFT_OK = 12          # px, at source resolution


def key_out_green(arr):
    r = arr[..., 0].astype(int)
    g = arr[..., 1].astype(int)
    b = arr[..., 2].astype(int)
    strong = (g > 110) & (g * 2 > r * 3) & (g * 2 > b * 3)
    arr[strong, 3] = 0
    # remaining greenish fringe on kept pixels: clamp green to max(r, b)
    spill = (~strong) & (g > r) & (g > b)
    arr[spill, 1] = np.maximum(arr[spill, 0], arr[spill, 2])
    return arr


def find_moods():
    """Mood folders, or the flat layout treated as neutral."""
    moods = sorted(d for d in os.listdir(SRC)
                   if os.path.isdir(os.path.join(SRC, d))
                   and any(os.path.exists(os.path.join(SRC, d, n)) for n in NAMES))
    if moods:
        return moods
    return ["."] if any(os.path.exists(os.path.join(SRC, n)) for n in NAMES) else []


def process(mood):
    src_dir = os.path.join(SRC, mood)
    out_dir = DST if mood == "." else os.path.join(DST, mood)
    os.makedirs(out_dir, exist_ok=True)
    boxes = {}
    for name in NAMES:
        path = os.path.join(src_dir, name)
        if not os.path.exists(path):
            print("   !! missing %s" % name)
            continue
        old = os.path.join(out_dir, name)
        if os.path.exists(old):
            bdir = BACKUP if mood == "." else os.path.join(BACKUP, mood)
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(old, os.path.join(bdir, name))
        img = Image.open(path).convert("RGBA")
        keyed = Image.fromarray(key_out_green(np.array(img)))
        boxes[name] = keyed.getbbox()
        keyed.resize((SIZE, SIZE), Image.LANCZOS).save(os.path.join(out_dir, name))
    return boxes


def main():
    moods = find_moods()
    if not moods:
        print("nothing to do — put the PNGs in %s" % SRC)
        return
    print("moods found: %s\n" % ", ".join(m if m != "." else "(flat)" for m in moods))

    all_boxes = {}
    for mood in moods:
        print("[%s]" % (mood if mood != "." else "flat"))
        boxes = process(mood)
        all_boxes[mood] = boxes
        if not boxes:
            continue
        ref = boxes[sorted(boxes)[0]]
        for name in NAMES:
            if name not in boxes:
                continue
            drift = max(abs(boxes[name][i] - ref[i]) for i in range(4))
            print("   %-18s bbox %-26s drift %3dpx %s"
                  % (name, boxes[name], drift,
                     "OK" if drift <= DRIFT_OK else "<-- JUMPS WHEN BLINKING"))
        print()

    if len(all_boxes) > 1:
        print("across moods (she must not jump when her expression changes):")
        base_mood = "neutral" if "neutral" in all_boxes else sorted(all_boxes)[0]
        base = all_boxes[base_mood].get("idle_open.png")
        for mood, boxes in sorted(all_boxes.items()):
            box = boxes.get("idle_open.png")
            if not box or not base:
                continue
            drift = max(abs(box[i] - base[i]) for i in range(4))
            print("   %-10s drift vs %s: %3dpx %s"
                  % (mood, base_mood, drift,
                     "OK" if drift <= DRIFT_OK else "<-- JUMPS ON MOOD CHANGE"))


if __name__ == "__main__":
    main()
