"""Procedural texture generation (numpy + Pillow).

Every texture is generated from code so it can be regenerated or restyled.
Tileable textures wrap seamlessly; screens, signs and posters map 0..1 onto a quad.
All images are written as PNG into submarine/textures/.
"""

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "textures")
FORCE = False  # set by build.py --retex

FONT_DIRS = ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/dejavu"]


def font(name, size):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    for fallback in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if os.path.exists(fallback):
            return ImageFont.truetype(fallback, size)
    return ImageFont.load_default(size)


def BLACK(s): return font("Inter-Black.otf", s)
def BOLD(s): return font("Inter-Bold.otf", s)
def SEMI(s): return font("Inter-SemiBold.otf", s)
def MONO(s): return font("DejaVuSansMono-Bold.ttf", s)


# ----------------------------------------------------------------- basics

def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def path(name):
    return os.path.join(TEX_DIR, name + ".png")


def needed(*names):
    os.makedirs(TEX_DIR, exist_ok=True)
    return FORCE or not all(os.path.exists(path(n)) for n in names)


def save_rgb(name, arr):
    arr = np.clip(arr, 0, 1)
    Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB").save(path(name))


def save_img(name, img):
    img.convert("RGB").save(path(name))


def noise(size, cells, seed, octaves=4, persistence=0.5, aspect=(1, 1)):
    """Tileable fractal value noise in 0..1. aspect stretches cells (x, y)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cx = max(1, int(cells * aspect[0] * 2 ** o))
        cy = max(1, int(cells * aspect[1] * 2 ** o))
        if cx > size or cy > size:
            break
        g = rng.random((cy, cx)).astype(np.float32)
        big = np.tile(g, (3, 3))
        img = Image.fromarray(big, "F").resize((size * 3, size * 3), Image.BICUBIC)
        out += np.asarray(img)[size:2 * size, size:2 * size] * amp
        total += amp
        amp *= persistence
    out /= total
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / (hi - lo + 1e-6), 0, 1)


def blur(a, r):
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), "F").filter(ImageFilter.GaussianBlur(r)))
    return np.stack([blur(a[..., i], r) for i in range(a.shape[2])], -1)


def normal_from_height(h, strength=4.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.stack([-dx * strength, dy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def grid(size):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    return x, y


def scratches(size, count, seed, length=(20, 90)):
    """Thin random scratch lines, 0..1 mask (tileable enough at this scale)."""
    rng = np.random.default_rng(seed)
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.random(2) * size
        a = rng.random() * math.pi
        l = rng.uniform(*length)
        d.line([(x, y), (x + math.cos(a) * l, y + math.sin(a) * l)], fill=int(rng.uniform(90, 255)), width=1)
    return np.asarray(img, np.float32) / 255.0


# ------------------------------------------------------- tileable surfaces

def paint_panel(name, color, seed=1, size=1024, panel_px=512, rivet_step=40, wear=1.0):
    """Painted steel wall: panel seams, rivet rows, grime, streaks. 1 tile = 2 m."""
    if not needed(name, name + "_n"):
        return
    x, y = grid(size)
    px, py = x % panel_px, y % panel_px
    dseam = np.minimum(np.minimum(px, panel_px - px), np.minimum(py, panel_px - py))
    seam = 1 - smoothstep(0.5, 2.5, dseam)

    # rivets: rows 14 px either side of each seam
    rivet = np.zeros_like(x)
    r = 4.5
    for off in (14, panel_px - 14):
        # horizontal rows
        cy = (np.floor(y / panel_px) * panel_px + off)
        cx = (np.floor(x / rivet_step) * rivet_step + rivet_step / 2)
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        rivet = np.maximum(rivet, np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1)))
        # vertical rows
        cx2 = (np.floor(x / panel_px) * panel_px + off)
        cy2 = (np.floor(y / rivet_step) * rivet_step + rivet_step / 2)
        d2 = np.sqrt((x - cx2) ** 2 + (y - cy2) ** 2)
        rivet = np.maximum(rivet, np.sqrt(np.clip(1 - (d2 / r) ** 2, 0, 1)))

    big = noise(size, 3, seed)
    mid = noise(size, 12, seed + 1)
    fine = noise(size, 96, seed + 2, octaves=2)
    dents = noise(size, 6, seed + 3)

    h = -seam * 1.0 + rivet * 0.9 + (fine - 0.5) * 0.04 + (dents - 0.5) * 0.25
    save_rgb(name + "_n", normal_from_height(h, 3.0))

    base = hex_rgb(color)
    col = np.ones((size, size, 3), np.float32) * base
    col *= (1 + (big - 0.5) * 0.10)[..., None]
    col *= (1 + (mid - 0.5) * 0.05)[..., None]
    # grime gathers at the bottom of each panel and in seams
    grime = smoothstep(panel_px * 0.55, panel_px, py) * 0.10 * wear
    grime += seam * 0.35
    # streaks running down from rivets
    streak_n = noise(size, 4, seed + 4, octaves=2, aspect=(8, 0.5))
    streaks = smoothstep(0.72, 0.95, streak_n) * smoothstep(0, panel_px * 0.8, py) * 0.12 * wear
    dirt = np.array([0.20, 0.17, 0.13])
    k = np.clip(grime + streaks, 0, 0.8)[..., None]
    col = col * (1 - k) + dirt * k
    # worn paint on rivet heads + scratches reveal lighter metal
    metal = np.array([0.62, 0.62, 0.60])
    scr = scratches(size, int(60 * wear), seed + 5) * 0.6 * wear
    km = np.clip(rivet * 0.25 + scr, 0, 1)[..., None]
    col = col * (1 - km) + metal * km
    save_rgb(name, col)


def paint_smooth(name, color, seed=1, size=512, wear=1.0):
    """Smooth painted metal for props: subtle variation, scratches, edge dirt. 1 tile = 1 m."""
    if not needed(name):
        return
    big = noise(size, 3, seed)
    mid = noise(size, 16, seed + 1)
    col = np.ones((size, size, 3), np.float32) * hex_rgb(color)
    col *= (1 + (big - 0.5) * 0.08 + (mid - 0.5) * 0.05)[..., None]
    dirt = smoothstep(0.68, 0.95, noise(size, 6, seed + 2)) * 0.10 * wear
    col = col * (1 - dirt[..., None]) + np.array([0.18, 0.15, 0.12]) * dirt[..., None]
    scr = scratches(size, int(35 * wear), seed + 3, (8, 40)) * 0.45 * wear
    col = col * (1 - scr[..., None]) + np.array([0.70, 0.70, 0.68]) * scr[..., None]
    save_rgb(name, col)


def orange_peel_normal(name="paint_peel_n", size=512):
    if not needed(name):
        return
    h = noise(size, 64, 99, octaves=2) * 0.6 + noise(size, 8, 98) * 0.4
    save_rgb(name, normal_from_height(h, 1.2))


def diamond_plate(name="floor_diamond", size=1024, cell=64, color="#6d7378"):
    """Tread plate: alternating ±45° raised bars. 1 tile = 1 m."""
    if not needed(name, name + "_n"):
        return
    x, y = grid(size)
    i, j = np.floor(x / cell), np.floor(y / cell)
    u = (x % cell) / cell - 0.5
    v = (y % cell) / cell - 0.5
    ang = np.where((i + j) % 2 == 0, math.pi / 4, -math.pi / 4)
    ru = u * np.cos(ang) - v * np.sin(ang)
    rv = u * np.sin(ang) + v * np.cos(ang)
    d = (ru / 0.36) ** 2 + (rv / 0.085) ** 2
    bar = smoothstep(1.0, 0.55, d)
    wear_n = noise(size, 5, 11)
    fine = noise(size, 128, 12, octaves=2)
    h = bar + (fine - 0.5) * 0.05 + (noise(size, 8, 13) - 0.5) * 0.15
    save_rgb(name + "_n", normal_from_height(h, 5.0))
    col = np.ones((size, size, 3), np.float32) * hex_rgb(color)
    col *= (1 + (wear_n - 0.5) * 0.18)[..., None]
    # tops are polished by boots, recesses hold dirt
    col += (bar * 0.16 * (0.5 + wear_n))[..., None]
    dirt = (1 - bar) * smoothstep(0.4, 0.9, noise(size, 10, 14)) * 0.25
    col = col * (1 - dirt[..., None]) + np.array([0.16, 0.14, 0.12]) * dirt[..., None]
    save_rgb(name, col)


def checker_tiles(name="floor_tiles", size=1024, tiles=8, c1="#e9dfc6", c2="#2f6f73"):
    """Linoleum checker tiles for galley/mess. 1 tile = 2 m (25 cm squares)."""
    if not needed(name, name + "_n"):
        return
    x, y = grid(size)
    t = size / tiles
    i, j = np.floor(x / t), np.floor(y / t)
    a, b = hex_rgb(c1), hex_rgb(c2)
    parity = ((i + j) % 2)[..., None]
    col = a * (1 - parity) + b * parity
    rng = np.random.default_rng(5)
    var = rng.uniform(-0.04, 0.04, (tiles, tiles)).astype(np.float32)
    col *= (1 + var[j.astype(int) % tiles, i.astype(int) % tiles])[..., None]
    gx, gy = x % t, y % t
    dg = np.minimum(np.minimum(gx, t - gx), np.minimum(gy, t - gy))
    grout = 1 - smoothstep(1.0, 3.0, dg)
    col = col * (1 - grout[..., None]) + np.array([0.25, 0.23, 0.2]) * grout[..., None]
    scuff = smoothstep(0.6, 0.95, noise(size, 10, 6)) * 0.12
    col = col * (1 - scuff[..., None]) + np.array([0.2, 0.18, 0.16]) * scuff[..., None]
    scr = scratches(size, 80, 7, (10, 50)) * 0.15
    col = col * (1 - scr[..., None]) + 0.9 * scr[..., None]
    save_rgb(name, col)
    h = -grout + (noise(size, 64, 8, octaves=2) - 0.5) * 0.03
    save_rgb(name + "_n", normal_from_height(h, 3.0))


def wood_planks(name="wood_planks", size=1024, planks=8, seed=21):
    """Varnished plank tabletop, grain along X. 1 tile = 1 m."""
    if not needed(name, name + "_n"):
        return
    x, y = grid(size)
    pw = size / planks
    k = np.floor(y / pw)
    rng = np.random.default_rng(seed)
    offs = rng.uniform(0, size, planks)
    tone = rng.uniform(-0.08, 0.08, planks)
    warp = noise(size, 4, seed, aspect=(1, 4)) * 30
    grain_n = noise(size, 6, seed + 1, octaves=5, aspect=(0.25, 4))
    rings = np.sin((y + warp + grain_n * 40) * 0.35 + k * 7.0) * 0.5 + 0.5
    rings = rings ** 3
    light, dark = hex_rgb("#c08a52"), hex_rgb("#7d4f2a")
    t = np.clip(rings * 0.55 + grain_n * 0.45, 0, 1)[..., None]
    col = light * (1 - t) + dark * t
    col *= (1 + tone[k.astype(int) % planks])[..., None]
    # plank seams and butt joints
    dy = np.minimum(y % pw, pw - (y % pw))
    seam = 1 - smoothstep(0.5, 2.0, dy)
    jx = (x + offs[k.astype(int) % planks]) % size
    joint = 1 - smoothstep(0.5, 2.0, np.minimum(jx, size - jx))
    gap = np.maximum(seam, joint)
    col = col * (1 - 0.7 * gap[..., None])
    ring_marks = smoothstep(0.8, 0.95, noise(size, 3, seed + 3)) * 0.12  # cup rings, wear
    col *= (1 - ring_marks[..., None])
    save_rgb(name, col)
    h = -gap + rings * 0.05 + (noise(size, 64, seed + 4, octaves=2) - 0.5) * 0.02
    save_rgb(name + "_n", normal_from_height(h, 3.0))


def brushed_steel(name="steel_brushed", size=512):
    if not needed(name):
        return
    s = noise(size, 2, 31, octaves=6, aspect=(0.05, 40))
    col = np.ones((size, size, 3), np.float32) * hex_rgb("#b3b9be")
    col *= (1 + (s - 0.5) * 0.12)[..., None]
    col *= (1 + (noise(size, 3, 32) - 0.5) * 0.08)[..., None]
    scr = scratches(size, 50, 33, (6, 30)) * 0.15
    col = col * (1 - scr[..., None]) + 0.85 * scr[..., None]
    save_rgb(name, col)


def hazard(name="hazard_stripes", size=512, stripes=8):
    if not needed(name):
        return
    x, y = grid(size)
    s = ((x + y) / size * stripes) % 1.0
    m = smoothstep(0.48, 0.52, s) * (1 - smoothstep(0.98, 1.0, s))
    yel, blk = hex_rgb("#efb81d"), hex_rgb("#1d1d1f")
    col = yel * (1 - m[..., None]) + blk * m[..., None]
    wear = smoothstep(0.7, 0.9, noise(size, 8, 41)) * 0.5
    col = col * (1 - wear[..., None]) + np.array([0.45, 0.45, 0.43]) * wear[..., None]
    save_rgb(name, col)


def fabric(name, c1, c2, stripe_px=40, size=512, seed=51, ticking=False):
    """Woven fabric with optional stripes (mattress ticking / wool blanket)."""
    if not needed(name):
        return
    x, y = grid(size)
    weave = (np.sin(x * 1.6) * np.sin(y * 1.6)) * 0.5 + 0.5
    a, b = hex_rgb(c1), hex_rgb(c2)
    if ticking:
        s = ((x // stripe_px) % 2)[..., None]
    else:
        s = (np.abs(((y + stripe_px) % (size // 2)) - stripe_px) < stripe_px * 0.35)[..., None].astype(np.float32)
    col = a * (1 - s) + b * s
    col *= (0.9 + 0.1 * weave)[..., None]
    col *= (1 + (noise(size, 6, seed) - 0.5) * 0.1)[..., None]
    save_rgb(name, col)


def leather(name="leather_brown", color="#7a3b22", size=512):
    if not needed(name):
        return
    cells = noise(size, 48, 61, octaves=3)
    col = np.ones((size, size, 3), np.float32) * hex_rgb(color)
    col *= (0.85 + 0.25 * cells)[..., None]
    col *= (1 + (noise(size, 4, 62) - 0.5) * 0.2)[..., None]
    save_rgb(name, col)


# ------------------------------------------------------------------ food

def meat_raw(name="meat_raw", size=512):
    if not needed(name):
        return
    n1 = noise(size, 6, 71, octaves=5)
    n2 = noise(size, 14, 72, octaves=4)
    veins = smoothstep(0.035, 0.0, np.abs(n1 - 0.5)) * 0.8 + smoothstep(0.03, 0.0, np.abs(n2 - 0.45)) * 0.6
    red, deep, fat = hex_rgb("#b3263a"), hex_rgb("#6f1121"), hex_rgb("#f0d2c8")
    t = noise(size, 8, 73)[..., None]
    col = red * (1 - t) + deep * t
    v = np.clip(veins, 0, 1)[..., None]
    col = col * (1 - v) + fat * v
    col *= (0.92 + 0.12 * noise(size, 90, 74, octaves=2))[..., None]
    save_rgb(name, col)


def meat_cooked(name="meat_cooked", size=512):
    if not needed(name):
        return
    x, y = grid(size)
    base = hex_rgb("#7a4024") * (0.85 + 0.3 * noise(size, 10, 81))[..., None]
    crust = smoothstep(0.55, 0.85, noise(size, 20, 82)) * 0.35
    col = base * (1 - crust[..., None]) + hex_rgb("#3a1a0c") * crust[..., None]
    s = ((x + y) / 64.0) % 1.0
    marks = smoothstep(0.12, 0.0, np.abs(s - 0.5))
    col = col * (1 - 0.7 * marks[..., None]) + hex_rgb("#1c0d06") * 0.7 * marks[..., None]
    save_rgb(name, col)


def chicken_skin(name="chicken_skin", size=512):
    if not needed(name, name + "_n"):
        return
    n = noise(size, 24, 91, octaves=4)
    spots = smoothstep(0.62, 0.9, noise(size, 12, 92))
    col = hex_rgb("#d79a48") * (0.8 + 0.35 * n)[..., None]
    col = col * (1 - spots[..., None] * 0.6) + hex_rgb("#7b3d17") * spots[..., None] * 0.6
    save_rgb(name, col)
    save_rgb(name + "_n", normal_from_height(noise(size, 40, 93, octaves=3), 4.0))


# --------------------------------------------------- screens (emissive)

def _scanlines(img, strength=0.18):
    a = np.asarray(img, np.float32) / 255.0
    rows = (np.arange(a.shape[0]) % 3 == 0).astype(np.float32)[:, None, None]
    a = a * (1 - rows * strength)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = 1 - 0.35 * (((xx / w - 0.5) * 2) ** 2 + ((yy / h - 0.5) * 2) ** 2) ** 1.5
    a *= np.clip(vig, 0.4, 1)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def sea_chart(name="screen_chart", w=1536, h=1024, seed=3):
    """Backlit paper sea chart for the navigation table."""
    if not needed(name):
        return
    hgt = noise(1024, 3, seed, octaves=6)[:h, :w] if w <= 1024 else \
        np.asarray(Image.fromarray(noise(1024, 3, seed, octaves=6), "F").resize((w, h), Image.BICUBIC))
    paper = np.ones((h, w, 3), np.float32) * hex_rgb("#efe6cf")
    shallow, deep = hex_rgb("#a9cfd6"), hex_rgb("#6fa3b8")
    land, land2 = hex_rgb("#d9c08e"), hex_rgb("#b89a63")
    lvl = 0.66
    t = np.clip((lvl - hgt) / 0.35, 0, 1)[..., None]
    water = shallow * (1 - t) + deep * t
    is_land = (hgt > lvl)[..., None]
    lt = np.clip((hgt - lvl) / 0.3, 0, 1)[..., None]
    col = np.where(is_land, land * (1 - lt) + land2 * lt, water)
    col = col * 0.85 + paper * 0.15
    # depth contours
    for c in np.arange(0.2, lvl, 0.07):
        line = smoothstep(0.004, 0.0, np.abs(hgt - c))
        col = col * (1 - line[..., None] * 0.35) + hex_rgb("#2d5f78") * line[..., None] * 0.35
    coast = smoothstep(0.006, 0.0, np.abs(hgt - lvl))
    col = col * (1 - coast[..., None]) + hex_rgb("#4a3a22") * coast[..., None]
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for gx in range(0, w, 128):
        d.line([(gx, 0), (gx, h)], fill=(70, 90, 100), width=1)
    for gy in range(0, h, 128):
        d.line([(0, gy), (w, gy)], fill=(70, 90, 100), width=1)
    f = SEMI(18)
    for i, gx in enumerate(range(0, w, 128)):
        d.text((gx + 4, 4), chr(65 + i), fill=(60, 70, 80), font=f)
    for i, gy in enumerate(range(0, h, 128)):
        d.text((4, gy + 4), str(i + 1), fill=(60, 70, 80), font=f)
    # compass rose
    cx, cy, R = w - 170, h - 170, 120
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(120, 60, 40), width=3)
    d.ellipse([cx - R + 14, cy - R + 14, cx + R - 14, cy + R - 14], outline=(120, 60, 40), width=1)
    for a in range(0, 360, 10):
        r1 = R - (14 if a % 30 else 26)
        ar = math.radians(a)
        d.line([(cx + math.sin(ar) * r1, cy - math.cos(ar) * r1), (cx + math.sin(ar) * R, cy - math.cos(ar) * R)],
               fill=(120, 60, 40), width=2)
    for k in range(8):
        a = math.radians(k * 45)
        L = R - 20 if k % 2 == 0 else R * 0.55
        p = [(cx + math.sin(a) * L, cy - math.cos(a) * L),
             (cx + math.sin(a + 0.25) * 18, cy - math.cos(a + 0.25) * 18),
             (cx, cy), (cx + math.sin(a - 0.25) * 18, cy - math.cos(a - 0.25) * 18)]
        d.polygon(p, fill=(150, 55, 40) if k == 0 else (90, 70, 55))
    d.text((cx - 9, cy - R - 34), "N", fill=(150, 55, 40), font=BOLD(28))
    # plotted course, waypoints and contacts
    pts = [(160, 820), (420, 700), (610, 760), (840, 560), (1020, 470), (1250, 300)]
    for a, b in zip(pts, pts[1:]):
        steps = int(math.dist(a, b) / 18)
        for s in range(0, steps, 2):
            p0 = (a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps)
            p1 = (a[0] + (b[0] - a[0]) * (s + 1) / steps, a[1] + (b[1] - a[1]) * (s + 1) / steps)
            d.line([p0, p1], fill=(40, 40, 50), width=4)
    for p in pts[1:-1]:
        d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], outline=(40, 40, 50), width=3)
    for p in [(980, 260), (1100, 380), (700, 300)]:
        d.polygon([(p[0], p[1] - 16), (p[0] + 14, p[1] + 10), (p[0] - 14, p[1] + 10)], fill=(200, 40, 40))
    for p in [(520, 380), (1300, 720)]:  # engagement zones
        d.ellipse([p[0] - 60, p[1] - 60, p[0] + 60, p[1] + 60], outline=(200, 40, 40), width=4)
        d.line([(p[0] - 18, p[1] - 18), (p[0] + 18, p[1] + 18)], fill=(200, 40, 40), width=5)
        d.line([(p[0] - 18, p[1] + 18), (p[0] + 18, p[1] - 18)], fill=(200, 40, 40), width=5)
    d.text((40, h - 60), "SOUNDINGS IN FATHOMS  ·  CHART 7-B  ·  KELPWATER STRAIT", fill=(60, 60, 60), font=SEMI(22))
    img.save(path(name))


def scope_screen(name, color, kind, seed=0, size=768):
    """Round CRT scopes: 'radar' (terrain contours), 'sonar' (sweep + blips)."""
    if not needed(name):
        return
    c = hex_rgb(color)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    u, v = (xx / size - 0.5) * 2, (yy / size - 0.5) * 2
    r = np.sqrt(u * u + v * v)
    a = np.arctan2(u, -v)
    inten = np.zeros((size, size), np.float32) + 0.06
    if kind == "radar":
        hgt = np.asarray(Image.fromarray(noise(512, 4, seed + 7, octaves=5), "F").resize((size, size), Image.BICUBIC))
        for lv in np.arange(0.3, 1.0, 0.08):
            inten += smoothstep(0.012, 0.0, np.abs(hgt - lv)) * 0.6
        inten += (hgt > 0.72) * 0.25
    else:
        sweep = ((a - 0.6) % (2 * math.pi)) / (2 * math.pi)
        inten += (1 - sweep) ** 6 * 0.7
        rng = np.random.default_rng(seed + 9)
        for _ in range(7):
            br, ba = rng.uniform(0.2, 0.85), rng.uniform(0, 2 * math.pi)
            bx, by = math.sin(ba) * br, -math.cos(ba) * br
            inten += np.exp(-(((u - bx) ** 2 + (v - by) ** 2) / 0.0006)) * 1.2
        inten += noise(size, 64, seed + 3, octaves=2) * 0.08
    for rr in (0.25, 0.5, 0.75):
        inten += smoothstep(0.006, 0.0, np.abs(r - rr)) * 0.5
    inten += smoothstep(0.004, 0.0, np.abs(u)) * (r < 0.95) * 0.45
    inten += smoothstep(0.004, 0.0, np.abs(v)) * (r < 0.95) * 0.45
    for k in range(72):
        ang = k * 5 / 180 * math.pi
        tick = smoothstep(0.006, 0, np.abs(a - (ang if ang <= math.pi else ang - 2 * math.pi)) * r)
        inten += tick * ((r > (0.88 if k % 6 else 0.84)) & (r < 0.94)) * 0.6
    inten *= (r < 0.95)
    inten += smoothstep(0.012, 0.0, np.abs(r - 0.95)) * 0.8
    col = np.clip(inten[..., None] * c * 1.3, 0, 1)
    col += np.clip(inten - 0.8, 0, 1)[..., None] * 0.5  # hot core
    img = _scanlines(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)))
    img.save(path(name))


def text_screen(name, lines, color="#ffb52e", w=1024, h=768, title=None, boxes=None):
    """Monospace CRT text display (fire control etc.)."""
    if not needed(name):
        return
    c = tuple(int(v * 255) for v in hex_rgb(color))
    dim = tuple(int(v * 0.35) for v in c)
    img = Image.new("RGB", (w, h), (8, 10, 8))
    d = ImageDraw.Draw(img)
    y = 40
    if title:
        d.rectangle([30, 28, w - 30, 100], fill=c)
        d.text((50, 38), title, fill=(10, 10, 10), font=MONO(48))
        y = 130
    for ln in lines:
        d.text((50, y), ln, fill=c, font=MONO(40))
        y += 58
    for (bx, by, bw, bh, label, on) in (boxes or []):
        d.rectangle([bx, by, bx + bw, by + bh], outline=c, width=4, fill=c if on else None)
        d.text((bx + 18, by + bh / 2 - 22), label, fill=(10, 10, 10) if on else c, font=MONO(40))
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    glow = img.filter(ImageFilter.GaussianBlur(8))
    img = Image.blend(img, glow, 0.25)
    a = np.maximum(np.asarray(img, np.float32), np.asarray(glow, np.float32) * 1.4)
    img = _scanlines(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    img.save(path(name))


def camera_feed(name, label, seed=0, w=1024, h=768, tint="#b8d8e8"):
    """Exterior camera monitor: sky, sea, horizon, overlay text."""
    if not needed(name):
        return
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    hor = h * (0.48 + 0.04 * math.sin(seed))
    sky_t = np.clip(yy / hor, 0, 1)[..., None]
    sky = hex_rgb("#6aa6d6") * (1 - sky_t) + hex_rgb("#cfe6f2") * sky_t
    cloud = smoothstep(0.55, 0.85, np.asarray(Image.fromarray(noise(512, 3, seed + 1, octaves=5, aspect=(1, 2.5)), "F").resize((w, h))))
    sky = sky * (1 - cloud[..., None] * 0.8) + 0.97 * cloud[..., None] * 0.8
    sea_t = np.clip((yy - hor) / (h - hor), 0, 1)[..., None]
    sea = hex_rgb("#3d7fa3") * (1 - sea_t) + hex_rgb("#164a6a") * sea_t
    waves = np.asarray(Image.fromarray(noise(512, 8, seed + 2, octaves=4, aspect=(0.3, 3)), "F").resize((w, h)))
    sea *= (0.85 + 0.3 * waves)[..., None]
    col = np.where((yy < hor)[..., None], sky, sea)
    col = col * hex_rgb(tint) * 1.1
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.text((30, 24), label, fill=(240, 240, 240), font=MONO(44))
    d.text((w - 260, 24), "● REC", fill=(230, 60, 50), font=MONO(44))
    for k in (-1, 1):
        d.line([(w / 2 + k * 30, h / 2), (w / 2 + k * 90, h / 2)], fill=(240, 240, 240), width=3)
        d.line([(w / 2, h / 2 + k * 30), (w / 2, h / 2 + k * 90)], fill=(240, 240, 240), width=3)
    _scanlines(img, 0.25).save(path(name))


def periscope_display(name="screen_target_id", w=1024, h=512):
    if not needed(name):
        return
    img = Image.new("RGB", (w, h), (10, 24, 16))
    d = ImageDraw.Draw(img)
    g = (120, 255, 150)
    d.text((30, 20), "TARGET IDENT", fill=g, font=MONO(46))
    d.text((30, 420), "BRG 047   RNG 2.4NM", fill=g, font=MONO(40))
    # generic cargo ship silhouette
    base_y = 300
    hull = [(160, base_y), (860, base_y), (820, base_y + 60), (210, base_y + 60)]
    d.polygon(hull, fill=g)
    d.rectangle([600, base_y - 90, 720, base_y], fill=g)
    d.rectangle([630, base_y - 140, 670, base_y - 90], fill=g)
    for k in range(4):
        d.rectangle([260 + k * 80, base_y - 50, 320 + k * 80, base_y], outline=g, width=4)
    d.line([(400, base_y - 50), (400, base_y - 160)], fill=g, width=5)
    _scanlines(img, 0.25).save(path(name))


# --------------------------------------------------------- dials, signs

def gauge_face(name, label, maxv, step, red_from=None, size=512, unit=""):
    if not needed(name):
        return
    img = Image.new("RGB", (size, size), (238, 233, 218))
    d = ImageDraw.Draw(img)
    c = size / 2
    R = size * 0.42
    a0, a1 = math.radians(225), math.radians(-45)
    n = int(maxv / step)
    if red_from is not None:
        fr = a0 + (a1 - a0) * red_from / maxv
        for k in range(60):
            t = fr + (a1 - fr) * k / 59
            x, y = c + math.cos(t) * R * 0.88, c - math.sin(t) * R * 0.88
            d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(200, 50, 40))
    for k in range(n * 5 + 1):
        t = a0 + (a1 - a0) * k / (n * 5)
        major = k % 5 == 0
        r1 = R * (0.78 if major else 0.86)
        d.line([(c + math.cos(t) * r1, c - math.sin(t) * r1), (c + math.cos(t) * R, c - math.sin(t) * R)],
               fill=(25, 25, 25), width=6 if major else 2)
        if major:
            val = str(int(k / 5 * step))
            f = BOLD(int(size * 0.07))
            tw = d.textlength(val, font=f)
            d.text((c + math.cos(t) * R * 0.62 - tw / 2, c - math.sin(t) * R * 0.62 - size * 0.04), val, fill=(25, 25, 25), font=f)
    f = BOLD(int(size * 0.06))
    tw = d.textlength(label, font=f)
    d.text((c - tw / 2, c - size * 0.2), label, fill=(25, 25, 25), font=f)
    if unit:
        f2 = SEMI(int(size * 0.045))
        tw = d.textlength(unit, font=f2)
        d.text((c - tw / 2, c + size * 0.07), unit, fill=(80, 80, 80), font=f2)
    img.save(path(name))


def clock_face(name="gauge_clock", size=512):
    if not needed(name):
        return
    img = Image.new("RGB", (size, size), (245, 242, 232))
    d = ImageDraw.Draw(img)
    c, R = size / 2, size * 0.44
    for k in range(60):
        t = math.radians(90 - k * 6)
        major = k % 5 == 0
        r1 = R * (0.82 if major else 0.9)
        d.line([(c + math.cos(t) * r1, c - math.sin(t) * r1), (c + math.cos(t) * R, c - math.sin(t) * R)],
               fill=(20, 20, 20), width=8 if major else 3)
    for h in range(1, 13):
        t = math.radians(90 - h * 30)
        s = str(h)
        f = BLACK(int(size * 0.09))
        tw = d.textlength(s, font=f)
        d.text((c + math.cos(t) * R * 0.66 - tw / 2, c - math.sin(t) * R * 0.66 - size * 0.055), s, fill=(20, 20, 20), font=f)
    f = SEMI(int(size * 0.045))
    s = "SHIP'S TIME"
    d.text((c - d.textlength(s, font=f) / 2, c - size * 0.17), s, fill=(120, 40, 30), font=f)
    img.save(path(name))


def label_plate(name, text, fg="#f3ead2", bg="#1f3a3d", w=1024, h=192, border=True, font_fn=BLACK):
    if not needed(name):
        return
    bgc = tuple(int(v * 255) for v in hex_rgb(bg))
    fgc = tuple(int(v * 255) for v in hex_rgb(fg))
    img = Image.new("RGB", (w, h), bgc)
    d = ImageDraw.Draw(img)
    if border:
        d.rounded_rectangle([10, 10, w - 10, h - 10], radius=16, outline=fgc, width=6)
    size = int(h * 0.55)
    f = font_fn(size)
    while d.textlength(text, font=f) > w * 0.86 and size > 10:
        size -= 2
        f = font_fn(size)
    tw = d.textlength(text, font=f)
    bbox = d.textbbox((0, 0), text, font=f)
    d.text(((w - tw) / 2, (h - (bbox[3] - bbox[1])) / 2 - bbox[1]), text, fill=fgc, font=f)
    for sx in (34, w - 34):  # screw heads
        for sy in (h // 2,):
            d.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], fill=(150, 150, 140))
            d.line([(sx - 7, sy), (sx + 7, sy)], fill=(70, 70, 70), width=3)
    img.save(path(name))


def warning_sign(name, title, body, kind, w=512, h=640, color="#f2c230"):
    """ISO-style warning sign: triangle pictogram + caption."""
    if not needed(name):
        return
    yel = tuple(int(v * 255) for v in hex_rgb(color))
    img = Image.new("RGB", (w, h), (250, 248, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=(30, 30, 30), width=8)
    cx, top, bot = w / 2, 50, 400
    tri = [(cx, top), (w - 50, bot), (50, bot)]
    d.polygon(tri, fill=(25, 25, 25))
    inner = [(cx, top + 42), (w - 84, bot - 22), (84, bot - 22)]
    d.polygon(inner, fill=yel)
    if kind == "heat":
        for k in (-50, 0, 50):
            pts = [(cx + k + 14 * math.sin(t / 6), 330 - t * 1.2) for t in range(0, 110, 4)]
            d.line(pts, fill=(25, 25, 25), width=10)
        d.line([(cx - 90, 352), (cx + 90, 352)], fill=(25, 25, 25), width=10)
    elif kind == "bolt":
        d.polygon([(cx + 20, 160), (cx - 40, 280), (cx, 280), (cx - 25, 370), (cx + 50, 240), (cx + 8, 240), (cx + 40, 160)], fill=(25, 25, 25))
    elif kind == "blast":
        for k in range(12):
            a = k * math.pi / 6
            d.line([(cx, 285), (cx + math.cos(a) * 70, 285 + math.sin(a) * 70)], fill=(25, 25, 25), width=12)
        d.ellipse([cx - 32, 253, cx + 32, 317], fill=(25, 25, 25))
    elif kind == "pressure":
        d.ellipse([cx - 60, 220, cx + 60, 340], outline=(25, 25, 25), width=12)
        d.line([(cx, 280), (cx + 40, 245)], fill=(25, 25, 25), width=10)
    d.rectangle([20, 420, w - 20, h - 20], fill=yel)
    f = BLACK(64)
    tw = d.textlength(title, font=f)
    d.text(((w - tw) / 2, 440), title, fill=(25, 25, 25), font=f)
    f2 = BOLD(44)
    tw = d.textlength(body, font=f2)
    d.text(((w - tw) / 2, 530), body, fill=(25, 25, 25), font=f2)
    img.save(path(name))


# --------------------------------------------------------------- posters

def _poster_base(w, h, top, bottom):
    yy = np.linspace(0, 1, h)[:, None, None]
    col = hex_rgb(top) * (1 - yy) + hex_rgb(bottom) * yy
    col = np.broadcast_to(col, (h, w, 3)).copy()
    grain = noise(512, 64, 5, octaves=2)
    grain = np.asarray(Image.fromarray(grain, "F").resize((w, h)))
    col *= (0.94 + 0.08 * grain)[..., None]
    return Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8))


def _center(d, y, text, f, fill, w):
    tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, y), text, fill=fill, font=f)


def _age(img, seed):
    a = np.asarray(img, np.float32) / 255
    h, w = a.shape[:2]
    n = np.asarray(Image.fromarray(noise(256, 4, seed), "F").resize((w, h)))
    stain = smoothstep(0.7, 0.95, n) * 0.18
    a = a * (1 - stain[..., None]) + np.array([0.55, 0.45, 0.3]) * stain[..., None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy))
    a *= (0.85 + 0.15 * smoothstep(0, 40, edge))[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def posters():
    w, h = 768, 1024
    cream, ink = (244, 232, 200), (30, 36, 48)
    if needed("poster_dive"):
        img = _poster_base(w, h, "#f0b54a", "#1f5f73")
        d = ImageDraw.Draw(img)
        d.ellipse([w / 2 - 180, 150, w / 2 + 180, 510], fill=(250, 214, 120))  # sun
        d.rectangle([0, 420, w, h], fill=(31, 95, 115))
        for k in range(8):
            y = 440 + k * 28
            d.line([(0, y), (w, y)], fill=(60, 130, 145), width=4)
        # diving sub silhouette
        sub = [(150, 640), (520, 560), (600, 575), (640, 610), (600, 650), (210, 700)]
        d.polygon(sub, fill=ink)
        d.polygon([(380, 590), (400, 520), (470, 505), (480, 570)], fill=ink)
        d.line([(440, 505), (450, 455)], fill=ink, width=8)
        for k in range(5):
            r = 10 + k * 5
            d.ellipse([620 + k * 22 - r / 2, 560 - k * 40 - r / 2, 620 + k * 22 + r / 2, 560 - k * 40 + r / 2], outline=cream, width=3)
        _center(d, 40, "DIVE! DIVE!", BLACK(104), ink, w)
        _center(d, 770, "SERVE BENEATH", BLACK(72), cream, w)
        _center(d, 850, "THE WAVES", BLACK(72), (250, 200, 90), w)
        _center(d, 950, "ENLIST AT YOUR NEAREST HARBOUR", BOLD(26), cream, w)
        _age(img, 1).save(path("poster_dive"))
    if needed("poster_quiet"):
        img = _poster_base(w, h, "#1d2b3a", "#0e1620")
        d = ImageDraw.Draw(img)
        cx, cy = w / 2, 450
        for k in range(6, 0, -1):
            r = 60 + k * 45
            d.arc([cx - r, cy - r, cx + r, cy + r], 200, 340, fill=(90, 200, 190), width=10)
        d.ellipse([cx - 70, cy - 20, cx + 70, cy + 180], fill=(240, 200, 170))
        d.ellipse([cx - 35, cy + 30, cx + 35, cy + 130], fill=(200, 150, 130))
        _center(d, 60, "SHHH...", BLACK(130), (240, 230, 200), w)
        _center(d, 720, "THE OCEAN", BLACK(84), (90, 200, 190), w)
        _center(d, 810, "IS LISTENING", BLACK(84), (90, 200, 190), w)
        _center(d, 930, "RIG FOR SILENT RUNNING", BOLD(32), (240, 230, 200), w)
        _age(img, 2).save(path("poster_quiet"))
    if needed("poster_galley"):
        img = _poster_base(w, h, "#f3e7c9", "#e9d6a8")
        d = ImageDraw.Draw(img)
        d.rectangle([30, 30, w - 30, h - 30], outline=(200, 60, 45), width=12)
        # cartoon fish chef
        d.ellipse([170, 330, 560, 600], fill=(240, 150, 60))
        d.polygon([(540, 465), (680, 360), (680, 570)], fill=(240, 150, 60))
        d.ellipse([240, 400, 300, 460], fill=(255, 255, 255))
        d.ellipse([258, 418, 286, 446], fill=ink)
        d.arc([210, 470, 330, 560], 20, 120, fill=ink, width=8)
        d.rectangle([230, 250, 380, 340], fill=(255, 255, 255))
        d.ellipse([200, 190, 300, 280], fill=(255, 255, 255))
        d.ellipse([270, 170, 380, 270], fill=(255, 255, 255))
        d.ellipse([340, 195, 430, 285], fill=(255, 255, 255))
        _center(d, 70, "WASH", BLACK(110), (200, 60, 45), w)
        _center(d, 640, "YOUR HANDS", BLACK(96), ink, w)
        _center(d, 760, "BEFORE YOU", BOLD(56), ink, w)
        _center(d, 830, "TOUCH THE FOOD", BOLD(56), ink, w)
        _center(d, 930, "— BY ORDER OF THE COOK —", BOLD(28), (200, 60, 45), w)
        _age(img, 3).save(path("poster_galley"))
    if needed("poster_crew"):
        img = _poster_base(w, h, "#2c5d63", "#2c5d63")
        d = ImageDraw.Draw(img)
        _center(d, 60, "CREW", BLACK(120), (245, 215, 110), w)
        _center(d, 190, "OF THE MONTH", BLACK(70), (245, 235, 210), w)
        d.rectangle([164, 320, w - 164, 800], fill=(245, 235, 210))
        d.rectangle([190, 346, w - 190, 774], fill=(150, 170, 170))
        d.ellipse([w / 2 - 90, 420, w / 2 + 90, 600], fill=(80, 90, 95))
        d.pieslice([w / 2 - 170, 600, w / 2 + 170, 900], 180, 360, fill=(80, 90, 95))
        d.text((w / 2 - 70, 470), "?", fill=(245, 235, 210), font=BLACK(110))
        _center(d, 840, "COULD BE YOU!", BLACK(64), (245, 215, 110), w)
        _center(d, 930, "SINK 10 TARGETS · KEEP THE COFFEE HOT", BOLD(24), (245, 235, 210), w)
        _age(img, 4).save(path("poster_crew"))


def iris(name, color, size=512):
    """Eyeball texture viewed from the front: sclera, iris with radial fibres, pupil, limbal ring."""
    if not needed(name):
        return
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    u, v = (xx / size - 0.5) * 2, (yy / size - 0.5) * 2
    r = np.sqrt(u * u + v * v)
    a = np.arctan2(v, u)
    sclera = np.array([0.93, 0.91, 0.88]) * (1 - 0.06 * smoothstep(0.5, 1.0, r))[..., None]
    veins = smoothstep(0.85, 0.97, noise(size, 24, 3, octaves=3)) * smoothstep(0.5, 0.95, r) * 0.25
    sclera = sclera * (1 - veins[..., None]) + np.array([0.8, 0.3, 0.3]) * veins[..., None]
    c = hex_rgb(color)
    fib = 0.75 + 0.25 * np.sin(a * 60 + noise(size, 8, 4) * 6) * noise(size, 32, 5)
    ir = c * fib[..., None] * (0.7 + 0.5 * smoothstep(0.42, 0.12, r))[..., None]
    ir = ir * (1 - 0.6 * smoothstep(0.36, 0.42, r))[..., None]
    col = np.where((r < 0.42)[..., None], ir, sclera)
    col = np.where((r < 0.15)[..., None], np.array([0.02, 0.02, 0.025]), col)
    save_rgb(name, col)


# ------------------------------------------------------------- generate

def generate_all():
    os.makedirs(TEX_DIR, exist_ok=True)
    orange_peel_normal()
    paint_panel("wall_cream", "#e6dcc3", seed=1)
    paint_panel("wall_teal", "#2e6e72", seed=2, wear=1.4)
    paint_panel("wall_navy", "#2a3c52", seed=3, wear=1.2)
    for nm, c, s in [
        ("paint_teal", "#2f7a7f", 10), ("paint_seafoam", "#8fbcaa", 11), ("paint_cream", "#e7dcc0", 12),
        ("paint_mustard", "#dc9f34", 13), ("paint_red", "#c9412d", 14), ("paint_navy", "#26394f", 15),
        ("paint_graphite", "#3c4146", 16), ("paint_olive", "#5f6b45", 17), ("paint_white", "#eeeae0", 18),
        ("paint_gray", "#8a9095", 19),
    ]:
        paint_smooth(nm, c, seed=s)
    diamond_plate()
    checker_tiles()
    wood_planks()
    brushed_steel()
    hazard()
    fabric("fabric_ticking", "#e9e4d6", "#3b5a7a", stripe_px=18, ticking=True)
    fabric("fabric_blanket", "#5c2e2a", "#e0c98c", stripe_px=30)
    fabric("fabric_curtain", "#2f6d6f", "#2a6164", stripe_px=10, ticking=True)
    leather()
    meat_raw()
    meat_cooked()
    chicken_skin()
    sea_chart()
    scope_screen("screen_nav_scope", "#ffae2e", "radar", seed=1)
    scope_screen("screen_sonar", "#53ff8a", "sonar", seed=2)
    text_screen("screen_fire_control",
                ["TGT  BRG 047  RNG 2.4", "SPD  12KT  DEPTH 0", "", "", "", "SOLUTION: LOCKED"],
                title="FIRE CONTROL",
                boxes=[(50 + k * 238, 330, 210, 120, f"TUBE{k + 1}", k in (0, 2)) for k in range(4)])
    text_screen("screen_ballast", ["DEPTH   042 M", "TRIM    +0.4°", "BALLAST  62 %", "O2      21 %", "HULL    OK"],
                color="#7dffb0", title="DIVE STATUS")
    camera_feed("screen_cam_fwd", "CAM 1  FWD", seed=1)
    camera_feed("screen_cam_aft", "CAM 2  AFT", seed=4, tint="#c8e0d8")
    periscope_display()
    gauge_face("gauge_pressure", "PRESSURE", 10, 1, red_from=8, unit="BAR")
    gauge_face("gauge_depth", "DEPTH", 300, 50, red_from=250, unit="METRES")
    gauge_face("gauge_air", "AIR", 200, 25, red_from=None, unit="PSI x10")
    clock_face()
    for nm, txt in [("navigation", "NAVIGATION"), ("fire_control", "FIRE CONTROL"), ("sonar", "SONAR"),
                    ("periscope", "PERISCOPE"), ("ballast", "BALLAST & TRIM"), ("control_room", "CONTROL ROOM"),
                    ("torpedo_room", "TORPEDO ROOM"), ("crew_mess", "CREW MESS"), ("galley", "GALLEY"),
                    ("engine_room", "ENGINE ROOM · NO ENTRY")]:
        label_plate("label_" + nm, txt)
    for k in range(1, 5):
        label_plate(f"label_tube{k}", str(k), fg="#1d1d1f", bg="#efb81d", w=256, h=256, font_fn=BLACK)
    for nm, txt in [("view", "VIEW"), ("zoom", "ZOOM"), ("fire", "FIRE"), ("arm", "ARM"), ("flood", "FLOOD"),
                    ("vent", "VENT"), ("blow", "BLOW")]:
        label_plate("label_" + nm, txt, fg="#f3ead2", bg="#222426", w=512, h=160, border=False, font_fn=BOLD)
    label_plate("hull_number", "27", fg="#f3ead2", bg="#244f55", w=512, h=384, border=False, font_fn=BLACK)
    label_plate("frigate_number", "F 41", fg="#f4f4f0", bg="#7d858c", w=768, h=256, border=False, font_fn=BLACK)
    label_plate("freighter_name", "KESTREL BAY", fg="#f4f4f0", bg="#2b3a52", w=1024, h=160, border=False, font_fn=BOLD)
    warning_sign("sign_hot", "CAUTION", "HOT SURFACE", "heat")
    warning_sign("sign_voltage", "DANGER", "HIGH VOLTAGE", "bolt")
    warning_sign("sign_explosive", "DANGER", "LIVE WARHEADS", "blast", color="#f08a24")
    warning_sign("sign_pressure", "WARNING", "HIGH PRESSURE", "pressure")
    posters()
    iris("eye_brown", "#6b3d1f")
    iris("eye_blue", "#3f6f9e")
    iris("eye_green", "#4f7a4a")
    iris("eye_hazel", "#8a6a33")


if __name__ == "__main__":
    import sys
    FORCE = "--retex" in sys.argv
    generate_all()
    print("textures in", TEX_DIR)
