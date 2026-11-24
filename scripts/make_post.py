#!/usr/bin/env python3
"""post_photo.png — 1200x1200 photo for the "make your own bounty" post.

Drawn entirely with Pillow from the press kit; no image model, no photo.
Deterministic: same input, same bytes.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                 # repo/
PRESS = ROOT.parent / "press"      # px01/press/

W = H = 1200
MARGIN = 48

MAGENTA = (196, 28, 131)           # #c41c83
INK = (25, 20, 25)                 # #191419
WHITE = (255, 255, 255)

CARD_W, CARD_H = 940, 700
CARD_L = (W - CARD_W) // 2         # 130
CARD_T = (H - CARD_H) // 2         # 250
CARD_R = CARD_L + CARD_W           # 1070
CARD_B = CARD_T + CARD_H           # 950
RADIUS = 28
INSET = 40
BAR_H = 76
BAR_T = CARD_B - BAR_H             # 874

FONT = Path.home() / ".local/share/fonts/Inter-var.ttf"

GHOST_SRC = PRESS / "ghost-clipboard-check.png"
WORDMARK_SRC = PRESS / "wordmark-on-dark.svg"

def say(msg: str) -> None:
    print(msg)


def font(size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_name(weight)
    return f


def tracked_width(text: str, f: ImageFont.FreeTypeFont, tracking: float = 0) -> float:
    return sum(f.getlength(ch) for ch in text) + tracking * max(len(text) - 1, 0)


def draw_tracked(draw, x, baseline, text, f, fill, tracking=0.0):
    """Left-baseline text with per-character tracking. Returns width."""
    cx = float(x)
    for ch in text:
        draw.text((cx, baseline), ch, font=f, fill=fill, anchor="ls")
        cx += f.getlength(ch) + tracking
    return cx - x - tracking if text else 0.0


def ink_at_55(over=WHITE):
    a = 0.55
    return tuple(round(over[i] * (1 - a) + INK[i] * a) for i in range(3))


# ---------------------------------------------------------------- ground
def ground() -> Image.Image:
    y, x = np.mgrid[0:H, 0:W].astype(np.float64)
    d = np.sqrt((x - (W - 1) / 2) ** 2 + (y - (H - 1) / 2) ** 2)
    d /= np.sqrt(2) * (W / 2)                       # 0 centre .. 1 corner
    f = 1.0 - 0.08 * np.clip(d, 0.0, 1.0) ** 1.8    # max 8% darkening
    arr = np.empty((H, W, 3), np.uint8)
    for i, c in enumerate(MAGENTA):
        arr[..., i] = np.clip(np.rint(c * f), 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


# ------------------------------------------------------------ the card
def base_card(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    off = 10
    d.rounded_rectangle(
        (CARD_L + off, CARD_T + off, CARD_R + off, CARD_B + off),
        radius=RADIUS, fill=INK, outline=INK, width=4,
    )
    d.rounded_rectangle(
        (CARD_L, CARD_T, CARD_R, CARD_B),
        radius=RADIUS, fill=WHITE, outline=INK, width=4,
    )

    bar = Image.new("RGB", img.size, WHITE)
    bd = ImageDraw.Draw(bar)
    bd.rectangle((CARD_L, BAR_T, CARD_R, CARD_B), fill=INK)

    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (CARD_L, CARD_T, CARD_R, CARD_B), radius=RADIUS, fill=255
    )
    img.paste(bar, (0, 0), mask)

    d.rounded_rectangle(
        (CARD_L, CARD_T, CARD_R, CARD_B),
        radius=RADIUS, outline=INK, width=4,
    )


# ------------------------------------------------------------- ghost
def flood_cut(im: Image.Image) -> Image.Image:
    """If the artwork still carries an opaque background, flood-fill it out
    from the four corners. Already-transparent corners are left alone."""
    im = im.convert("RGBA")
    a = im.getchannel("A")
    if a.getpixel((0, 0)) == 0 and a.getpixel((im.width - 1, im.height - 1)) == 0:
        return im
    rgba = np.array(im)
    bg = rgba[0, 0].copy()
    close = (np.abs(rgba[..., :3].astype(int) - bg[:3].astype(int)).sum(axis=2) < 24)
    from collections import deque
    h, w = close.shape
    seen = np.zeros((h, w), bool)
    q = deque([(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)])
    while q:
        cy, cx = q.popleft()
        if cy < 0 or cx < 0 or cy >= h or cx >= w or seen[cy, cx] or not close[cy, cx]:
            continue
        seen[cy, cx] = True
        q.extend(((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)))
    rgba[..., 3] = np.where(seen, 0, rgba[..., 3])
    return Image.fromarray(rgba, "RGBA")


def ghost_art() -> Image.Image:
    im = flood_cut(Image.open(GHOST_SRC))
    box = im.getchannel("A").getbbox()
    return im.crop(box) if box else im


def place_ghost(img: Image.Image, art: Image.Image, height: int, box) -> int:
    x0, y0, x1, y1 = box
    w = round(height * art.width / art.height)
    g = art.resize((w, height), Image.LANCZOS)
    off = 10
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sil = Image.new("RGBA", g.size, INK + (255,))
    sh.paste(sil, (x0 + off, y0 + off), g)
    img.paste(sh, (0, 0), sh)
    img.paste(g, (x0, y0), g)
    return w


# ---------------------------------------------------------- wordmark
def wordmark(width: int) -> Image.Image:
    """Rasterise the press SVG with its own geometry, fills set to white."""
    import cairosvg
    import re

    svg = WORDMARK_SRC.read_text()
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1).split()
    ratio = float(vb[3]) / float(vb[2])
    scale = 4
    svg = re.sub(r'fill="#[0-9a-fA-F]{3,8}"', 'fill="#ffffff"', svg)
    svg = re.sub(r'\swidth="[^"]*"', f' width="{width * scale}"', svg, count=1)
    svg = re.sub(r'\sheight="[^"]*"', f' height="{width * scale * ratio:.2f}"', svg, count=1)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=width * scale)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    return im.resize((width, round(width * ratio)), Image.LANCZOS)


# -------------------------------------------------------------- text
def main() -> None:
    headline_f = font(62, "Bold")
    label_f = font(22, "Bold")
    row_label_f = font(26, "SemiBold")
    value_f = font(44, "Bold")
    bar_f = font(32, "Bold")

    HEAD = "MAKE YOUR OWN BOUNTY"
    LABEL = "BOUNTY"
    ROWS = [
        ("TASK", "WHATEVER YOU WANT BUILT"),
        ("REWARD", "$200"),
        ("ENTRY FEE", "$2"),
    ]
    BAR = "YOU KEEP A SHARE OF EVERY FEE"

    # headline: 62 px, one line, else 54
    head_track = 1.0
    hw = tracked_width(HEAD, headline_f, head_track)
    if hw > W - 2 * MARGIN:
        headline_f = font(54, "Bold")
        hw = tracked_width(HEAD, headline_f, head_track)

    # rows laid out from the measured bar text so nothing collides
    bar_w = tracked_width(BAR, bar_f, 0)
    bar_left = W / 2 - bar_w / 2

    rows_top = 354
    row_h = 160
    blocks = []                        # (name, x, baseline, width, limit_right)
    ha, hd = headline_f.getmetrics()
    head_base = MARGIN + (CARD_T - MARGIN - (ha + hd)) / 2 + ha   # optically centred
    blocks.append(("headline", W / 2 - hw / 2, head_base, hw, W - MARGIN))
    blocks.append(("BOUNTY", CARD_L + INSET, CARD_T + INSET + label_f.getmetrics()[0],
                   tracked_width(LABEL, label_f, 3), CARD_R - INSET))
    for i, (lab, val) in enumerate(ROWS):
        rule_y = rows_top + row_h * (i + 1)
        blocks.append((lab, CARD_L + INSET, rule_y - 44 - 54,
                       tracked_width(lab, row_label_f, 0), CARD_R - INSET))
        blocks.append((val, CARD_L + INSET, rule_y - 44,
                       tracked_width(val, value_f, 0), CARD_R - INSET))
    blocks.append((BAR, bar_left, BAR_T + BAR_H / 2, bar_w, CARD_R))

    # ---- margins + card containment
    for name, x, base, w, limit in blocks:
        right = x + w
        if right > limit + 0.01:
            raise SystemExit(f"{name!r} width {w:.1f} at x {x:.1f} -> right edge "
                             f"{right:.1f} crosses limit {limit:.1f}")
        if x < MARGIN or right > W - MARGIN:
            raise SystemExit(f"{name!r} right edge {right:.1f} breaks the "
                             f"{MARGIN}px canvas margin")

    # ---- ghost: biggest that is seated on the card's left edge and touches no type
    art = ghost_art()
    ratio = art.width / art.height
    type_boxes = [(x, base - value_f.getmetrics()[0], x + w, base + 12)
                  for name, x, base, w, limit in blocks if name != "headline"]
    bar_box = (bar_left - 6, BAR_T, bar_left + bar_w + 6, CARD_B)

    def collides(box, w):
        x0, y0, x1, y1 = box
        x1 = x0 + w
        for bx in type_boxes + [bar_box]:
            if x1 > bx[0] and x0 < bx[2] and y1 > bx[1] and y0 < bx[3]:
                return True
        return False

    ghost_h, ghost_why = None, ""
    for h in range(380, 120, -2):
        w = round(h * ratio)
        if MARGIN + w > bar_box[0]:
            ghost_why = f"width would reach the bar's white type at x={bar_box[0]:.0f}"
            continue
        top = (CARD_B + 154) - h          # feet on the magenta below the card
        if top < MARGIN or top + h > H - MARGIN:
            continue
        if not collides((MARGIN, top, MARGIN + w, top + h), w):
            ghost_h = h
            break
    if ghost_h is None:
        raise SystemExit("no ghost size fits between the type and the margins")
    ghost_w = round(ghost_h * ratio)
    ghost_top = (CARD_B + 154) - ghost_h
    ghost_box = (MARGIN, ghost_top, MARGIN + ghost_w, ghost_top + ghost_h)

    # ---- draw
    img = ground()
    base_card(img)
    d = ImageDraw.Draw(img)

    draw_tracked(d, W / 2 - hw / 2, blocks[0][2], HEAD, headline_f, WHITE, head_track)

    draw_tracked(d, CARD_L + INSET, blocks[1][2], LABEL, label_f, INK, 3)

    for i in range(3):
        lab, val = ROWS[i]
        lab_b = rows_top + row_h * (i + 1) - 44 - 54
        val_b = rows_top + row_h * (i + 1) - 44
        rule_y = rows_top + row_h * (i + 1)
        draw_tracked(d, CARD_L + INSET, lab_b, lab, row_label_f, ink_at_55())
        draw_tracked(d, CARD_L + INSET, val_b, val, value_f, INK)
        d.rectangle((CARD_L + INSET, rule_y, CARD_R - INSET, rule_y + 2), fill=INK)

    d.text((W / 2, BAR_T + BAR_H / 2), BAR, font=bar_f, fill=WHITE, anchor="mm")

    before_ghost = img.copy()
    place_ghost(img, art, ghost_h, ghost_box)

    wm = wordmark(300)
    wm_x = W - 60 - wm.width
    wm_y = H - 60 - wm.height
    before_wm = img.copy()
    img.paste(wm, (wm_x, wm_y), wm)

    # ---- verify
    say("text blocks (width / right edge):")
    for name, x, base, w, limit in blocks:
        say(f"  {name:<24} w={w:7.1f}  right={x + w:8.1f}  limit={limit:6.0f}")

    def placed_ink(asset, box, snapshot, label):
        x0, y0, x1, y1 = box
        alpha = asset.getchannel("A").point(lambda v: 255 if v else 0)
        ink = sum(1 for v in alpha.getdata() if v)
        changed = sum(1 for a, b in zip(img.crop(box).getdata(), snapshot.crop(box).getdata()) if a != b)
        if ink == 0 or changed == 0:
            raise SystemExit(f"{label} did not land on the canvas")
        say(f"{label} box {x1 - x0}x{y1 - y0} at ({x0},{y0}) "
            f"ink px = {ink}  changed px = {changed}")

    say(f"ghost: {ghost_h}px tall (380 asked; limited by {ghost_why})")
    placed_ink(art.resize((ghost_w, ghost_h), Image.LANCZOS), ghost_box, before_ghost, "ghost")
    placed_ink(wm, (wm_x, wm_y, wm_x + wm.width, wm_y + wm.height), before_wm, "wordmark")

    # nothing but ground may sit inside the 48 px margin ring
    gnd = ground()
    ring = np.ones((H, W), bool)
    ring[MARGIN:H - MARGIN, MARGIN:W - MARGIN] = False
    diff = np.any(np.asarray(img) != np.asarray(gnd), axis=2) & ring
    if diff.any():
        y, x = np.argwhere(diff)[0]
        raise SystemExit(f"ink inside the {MARGIN}px margin at ({int(x)},{int(y)})")
    say(f"margin ring clean: {int(ring.sum())} px checked, all ground")

    out = ROOT / "post_photo.png"
    img.save(out, "PNG", optimize=True)
    img.resize((600, 600), Image.LANCZOS).save(ROOT / "preview_600.png", "PNG", optimize=True)

    say(f"post_photo.png {out.stat().st_size} bytes  "
        f"sha/md5 {hashlib.md5(out.read_bytes()).hexdigest()}")
    say(f"preview_600.png {(ROOT / 'preview_600.png').stat().st_size} bytes")
    if out.stat().st_size > 2 * 1024 * 1024:
        raise SystemExit("post_photo.png over 2 MiB")


if __name__ == "__main__":
    main()