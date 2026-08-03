#!/usr/bin/env python3
"""
prep_photo.py  <source-photo>
Prepare a photo for ASCII conversion:
  1. Remove the background (rembg) so the subject is isolated.
  2. Boost local contrast with CLAHE — flat faces gain real highlights/shadows.
  3. Composite onto pure WHITE so the background maps to the blank end of the
     ASCII ramp (white -> spaces), leaving only the subject to "print".

Output: source-prepped.png (grayscale). Run once per photo:
    python scripts/prep_photo.py source-photo.jpg
"""

import sys
import os
import numpy as np
import cv2

OUT = os.path.join(os.path.dirname(__file__), "..", "source-prepped.png")


def remove_bg(path):
    """Return an RGBA image with the background removed, or None if rembg is
    unavailable / fails (caller falls back to a luminance mask)."""
    try:
        from rembg import remove
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        cut = remove(img)  # RGBA with alpha where subject is
        return np.array(cut)
    except Exception as e:
        print(f"[prep] rembg unavailable ({e}); using luminance fallback mask.")
        return None


def luminance_mask_rgba(bgr):
    """Fallback for photos already on a dark, roughly uniform background:
    treat near-black pixels as background."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # subject = brighter than a low threshold; smooth the mask edges
    _, mask = cv2.threshold(gray, 28, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.medianBlur(mask, 7)
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    rgba[:, :, 3] = mask
    return rgba


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/prep_photo.py <source-photo>")
        sys.exit(1)
    src = sys.argv[1]
    bgr = cv2.imread(src)
    if bgr is None:
        print(f"could not read {src}")
        sys.exit(1)

    rgba = remove_bg(src)
    if rgba is None:
        rgba = luminance_mask_rgba(bgr)

    rgb = rgba[:, :, :3].astype(np.uint8)
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0

    # CLAHE on the luminance channel for punchy local contrast.
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Gamma lift (<1 brightens): opens midtones so the face shows internal
    # structure across the ramp instead of collapsing into dense glyphs.
    GAMMA = 0.80
    gray = 255.0 * np.power(np.clip(gray, 0, 255) / 255.0, GAMMA)

    # Composite onto white using the alpha mask: bg -> 255 (spaces).
    white = np.full_like(gray, 255.0)
    out = gray * alpha + white * (1.0 - alpha)
    out = np.clip(out, 0, 255).astype(np.uint8)

    cv2.imwrite(OUT, out)
    print(f"Wrote {OUT} ({out.shape[1]}x{out.shape[0]})")


if __name__ == "__main__":
    main()
