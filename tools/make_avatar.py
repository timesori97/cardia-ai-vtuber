"""Generate the 4 placeholder avatar PNGs for veadotube mini.

Flat vector-style card-dealer girl, 512x512 transparent, palette:
deep red #C1121F / navy #003049 / cream #FDF0D5 (+ white, soft blush).
States: idle_closed, idle_open (mouth open), blink_closed, blink_open.
Placeholder until commissioned art — veadotube only needs the PNGs swapped.

Run: python tools/make_avatar.py
"""

import os

from PIL import Image, ImageDraw

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(KIT, "avatar")

RED = (193, 18, 31, 255)      # C1121F
NAVY = (0, 48, 73, 255)       # 003049
CREAM = (253, 240, 213, 255)  # FDF0D5
WHITE = (255, 255, 255, 255)
BLUSH = (231, 111, 111, 170)


def make_card():
    """Small playing card (ace of diamonds) used as a hair ornament."""
    card = Image.new("RGBA", (64, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((2, 2, 62, 86), radius=8, fill=WHITE, outline=RED, width=4)
    d.polygon([(32, 22), (48, 44), (32, 66), (16, 44)], fill=RED)
    return card.rotate(18, expand=True, resample=Image.BICUBIC)


def build(eyes_open, mouth_open, path):
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # back hair + side locks
    d.ellipse((110, 70, 402, 330), fill=NAVY)
    d.rounded_rectangle((112, 190, 196, 430), radius=42, fill=NAVY)
    d.rounded_rectangle((316, 190, 400, 430), radius=42, fill=NAVY)

    # neck, then dealer vest torso
    d.rectangle((234, 310, 278, 372), fill=CREAM)
    d.polygon([(176, 356), (336, 356), (394, 512), (118, 512)], fill=NAVY)
    d.polygon([(224, 356), (288, 356), (256, 424)], fill=WHITE)          # shirt
    d.polygon([(233, 366), (256, 380), (233, 394)], fill=RED)            # bowtie L
    d.polygon([(279, 366), (256, 380), (279, 394)], fill=RED)            # bowtie R
    d.ellipse((249, 373, 263, 387), fill=RED)                            # bowtie knot
    d.polygon([(256, 442), (272, 466), (256, 490), (240, 466)], fill=RED)  # vest diamond

    # face
    d.ellipse((146, 108, 366, 332), fill=CREAM)

    # bangs: top dome + three scallop points
    d.pieslice((140, 96, 372, 252), 180, 360, fill=NAVY)
    d.polygon([(156, 172), (204, 172), (180, 212)], fill=NAVY)
    d.polygon([(232, 172), (280, 172), (256, 222)], fill=NAVY)
    d.polygon([(308, 172), (356, 172), (332, 212)], fill=NAVY)
    # red headband accent along the hairline
    d.arc((140, 100, 372, 268), 205, 335, fill=RED, width=10)

    # blush
    d.ellipse((176, 270, 212, 292), fill=BLUSH)
    d.ellipse((300, 270, 336, 292), fill=BLUSH)

    # eyes
    if eyes_open:
        d.ellipse((196, 232, 232, 272), fill=NAVY)
        d.ellipse((300, 232, 336, 272), fill=NAVY)
        d.ellipse((206, 240, 217, 251), fill=WHITE)
        d.ellipse((310, 240, 321, 251), fill=WHITE)
    else:
        d.arc((196, 238, 232, 268), 0, 180, fill=NAVY, width=6)
        d.arc((300, 238, 336, 268), 0, 180, fill=NAVY, width=6)
    # brows
    d.arc((192, 210, 236, 234), 200, 340, fill=NAVY, width=5)
    d.arc((296, 210, 340, 234), 200, 340, fill=NAVY, width=5)

    # mouth
    if mouth_open:
        d.ellipse((232, 274, 280, 320), fill=RED, outline=NAVY, width=5)
        d.pieslice((238, 276, 274, 298), 180, 360, fill=WHITE)  # teeth
    else:
        d.arc((236, 276, 276, 304), 10, 170, fill=NAVY, width=6)

    # card ornament on the hair, drawn last so it sits on top
    card = make_card()
    img.alpha_composite(card, (306, 44))

    img.save(path)
    return path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    states = {
        "idle_closed.png": (True, False),
        "idle_open.png": (True, True),
        "blink_closed.png": (False, False),
        "blink_open.png": (False, True),
    }
    for name, (eyes, mouth) in states.items():
        print("wrote", build(eyes, mouth, os.path.join(OUT_DIR, name)))


if __name__ == "__main__":
    main()
