# Databricks notebook source
# MAGIC %md
# MAGIC # Crop player headshots to head-and-shoulders squares (serverless PIL)
# MAGIC Reads staged sources from `/Volumes/acme_sports/demo/documents/_hs_tmp/src/`,
# MAGIC crops a top-biased head-and-shoulders square, resizes to 320x320, writes to
# MAGIC `.../_hs_tmp/out/`. Read-only w.r.t. the demo tables; scratch dir is deleted after.

# COMMAND ----------

# MAGIC %pip install Pillow --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import os, io
from PIL import Image, ImageOps

SRC = "/Volumes/acme_sports/demo/documents/_hs_tmp/src"
OUT = "/Volumes/acme_sports/demo/documents/_hs_tmp/out"
os.makedirs(OUT, exist_ok=True)

results = []
for fn in sorted(os.listdir(SRC)):
    if not fn.lower().endswith(".jpg"):
        continue
    im = Image.open(os.path.join(SRC, fn))
    im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    if h <= 1.15 * w:                       # squarish / already head-and-shoulders
        side = w; top = int(0.03 * h); left = 0
    else:                                    # tall / full-body -> tighter upper head-and-shoulders square
        side = min(int(0.40 * h), w); left = (w - side) // 2; top = int(0.045 * h)
    side = min(side, h - top)
    crop = im.crop((left, top, left + side, top + side)).resize((320, 320), Image.LANCZOS)
    crop.save(os.path.join(OUT, fn), "JPEG", quality=88)
    results.append(f"{fn}: {w}x{h} -> crop {side}@({left},{top})")

dbutils.notebook.exit("\n".join(results))
