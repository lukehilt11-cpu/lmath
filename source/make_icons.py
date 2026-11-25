#!/usr/bin/env python3
"""
make_icons.py — draws the lmath app icon at every size and writes:

    icons/lmath.png  icons/lmath.ico  icons/lmath.icns   (the app)
    docs/assets/logo.png  docs/assets/favicon.png          (the website)

The icon is a graph-paper tile with y = x² − 4x + 3: the curve, its two x-intercepts
(white rings) and its vertex (orange dot) — the same picture the app draws for students.
Needs Pillow (pip install pillow). build.bat / build.sh run this automatically.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SS = 4                                   # supersampling for smooth edges

TOP, BOTTOM = (24, 36, 112), (20, 94, 190)
ORANGE, WHITE = (255, 138, 61), (255, 255, 255)


def _gradient(n):
    img = Image.new("RGB", (n, n))
    px = img.load()
    for y in range(n):
        t = y / (n - 1)
        row = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(n):
            px[x, y] = row
    return img


def draw_icon(size: int) -> Image.Image:
    n = size * SS
    base = _gradient(n).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    detailed = size >= 64
    if detailed:                                           # graph-paper grid
        step = n / 8
        for i in range(1, 8):
            d.line([(i * step, 0), (i * step, n)], fill=(255, 255, 255, 26), width=max(1, n // 400))
            d.line([(0, i * step), (n, i * step)], fill=(255, 255, 255, 26), width=max(1, n // 400))
    axis_y, axis_x = 0.56 * n, 0.5 * n
    aw = max(2, int(n * (0.016 if detailed else 0.03)))
    d.line([(0.07 * n, axis_y), (0.93 * n, axis_y)], fill=(255, 255, 255, 150), width=aw)
    d.line([(axis_x, 0.07 * n), (axis_x, 0.93 * n)], fill=(255, 255, 255, 110), width=aw)
    # the parabola, as a smooth polyline
    lw = n * (0.058 if detailed else 0.09)
    steps = 1500                                           # a round brush stamped along the curve
    for i in range(steps + 1):
        u = 0.1 + 0.8 * i / steps
        cx, cy = u * n, (0.76 - 2.6 * (u - 0.5) ** 2) * n
        d.ellipse([cx - lw / 2, cy - lw / 2, cx + lw / 2, cy + lw / 2], fill=ORANGE + (255,))
    # x-intercepts (rings) and vertex (dot)
    r = n * (0.048 if detailed else 0.075)
    for ux in (0.5 - 0.277, 0.5 + 0.277):
        cx, cy = ux * n, axis_y
        d.ellipse([cx - r * 1.35, cy - r * 1.35, cx + r * 1.35, cy + r * 1.35], fill=TOP + (255,))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE + (255,))
    vx, vy = 0.5 * n, 0.76 * n
    d.ellipse([vx - r * 1.45, vy - r * 1.45, vx + r * 1.45, vy + r * 1.45], fill=TOP + (255,))
    d.ellipse([vx - r * 1.1, vy - r * 1.1, vx + r * 1.1, vy + r * 1.1], fill=(255, 214, 102, 255))
    # rounded-square mask
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, n - 1, n - 1], radius=int(n * 0.22), fill=255)
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    if detailed:                                           # a soft inner highlight along the top edge
        hi = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        ImageDraw.Draw(hi).rounded_rectangle([n * 0.02, n * 0.02, n * 0.98, n * 0.5], radius=int(n * 0.2), fill=(255, 255, 255, 22))
        out = Image.alpha_composite(out, hi.filter(ImageFilter.GaussianBlur(n * 0.01)))
        out.putalpha(mask)
    return out.resize((size, size), Image.LANCZOS)


def main():
    icons = os.path.join(ROOT, "icons")
    assets = os.path.join(ROOT, "docs", "assets")
    os.makedirs(icons, exist_ok=True)
    os.makedirs(assets, exist_ok=True)
    big = draw_icon(1024)
    big.save(os.path.join(icons, "lmath.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = {s: draw_icon(s) for s in sizes}                 # each size drawn natively, not shrunk
    frames[256].save(os.path.join(icons, "lmath.ico"), format="ICO", sizes=[(s, s) for s in sizes], append_images=[frames[s] for s in sizes if s != 256])
    try:
        big.save(os.path.join(icons, "lmath.icns"), format="ICNS")
    except Exception as e:                                    # ICNS is only needed on macOS builds
        print(f"(skipped .icns: {e})")
    draw_icon(128).save(os.path.join(assets, "logo.png"))
    draw_icon(64).save(os.path.join(assets, "favicon.png"))
    print("icons ready")


if __name__ == "__main__":
    sys.exit(main())
