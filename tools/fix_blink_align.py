"""Realign blink_closed to idle_closed's content box (Gemini drew it ~1% larger).

Crops each source to its content bbox, then fits blink_closed's content into
idle_closed's bbox position/size so all four states overlap exactly.
"""

import os

import numpy as np
from PIL import Image

from process_avatar import KIT, SRC, DST, SIZE, key_out_green


def keyed(name):
    img = Image.open(os.path.join(SRC, name)).convert("RGBA")
    return Image.fromarray(key_out_green(np.array(img)))


def main():
    ref = keyed("idle_closed.png")
    ref_box = ref.getbbox()
    target = keyed("blink_closed.png")
    t_box = target.getbbox()

    content = target.crop(t_box)
    ref_w, ref_h = ref_box[2] - ref_box[0], ref_box[3] - ref_box[1]
    content = content.resize((ref_w, ref_h), Image.LANCZOS)

    canvas = Image.new("RGBA", ref.size, (0, 0, 0, 0))
    canvas.paste(content, (ref_box[0], ref_box[1]), content)
    canvas = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    out = os.path.join(DST, "blink_closed.png")
    canvas.save(out)
    print("realigned blink_closed: bbox", t_box, "->", ref_box)


if __name__ == "__main__":
    main()
