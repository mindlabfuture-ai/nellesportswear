#!/usr/bin/env python3
"""Cut product photos out of their background -> transparent PNG + black-background JPG.

usage: python tools/cutout.py images/photos/original/<name>.webp [...]
"""
import os
import sys

from PIL import Image
from rembg import new_session, remove

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
session = new_session(os.environ.get("REMBG_MODEL", "birefnet-general"))

for path in sys.argv[1:]:
    name = os.path.splitext(os.path.basename(path))[0]
    src = Image.open(path).convert("RGB")
    cut = remove(src, session=session, alpha_matting=os.environ.get("MATTING") == "1",
                 alpha_matting_foreground_threshold=240,
                 alpha_matting_background_threshold=20,
                 alpha_matting_erode_size=8)
    cut.save(os.path.join(ROOT, "images/photos/transparent", f"{name}.png"))
    black = Image.new("RGBA", cut.size, (5, 5, 5, 255))
    black.alpha_composite(cut)
    black.convert("RGB").save(os.path.join(ROOT, "images/photos/black", f"{name}.jpg"), quality=92)
    print("cut", name)
