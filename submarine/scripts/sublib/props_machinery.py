"""Dense wall machinery (set dressing): modular equipment racks that fill the walls.

A rack is a floor-standing cabinet (back on y=0, facing -Y) whose front is a stack of
randomly chosen modules: gauge rows, switch banks, LED strips, reel-to-reel recorders, small
CRTs, breaker grids, patch panels with cables, fan grilles, meters, vents, label plates.
Racks are cached per (width, seed) so the level instances a few dozen variants.
"""

import math
import random

import bmesh
from mathutils import Matrix, Vector

from .core import (Prop, R, bm_box, bm_cyl, bm_disc, bm_extrude, bm_lathe, bm_plate_with_holes, bm_sphere,
                   bm_torus, rect, rrect, sag_path)
from .props_common import louver

RACK_H = 2.05
DEPTH = 0.36
BODY_COLORS = ["PaintCream", "PaintSeafoam", "PaintGray", "PaintCream", "PaintNavy"]
SCREENS = ["screen_sonar", "screen_nav_scope", "screen_ballast", "screen_cam_fwd", "screen_fire_control",
           "screen_target_id"]
GAUGES = ["gauge_pressure", "gauge_air", "gauge_depth"]
LEDS = ["LampGreen", "LampGreen", "LampAmber", "LampRed", "LampBlue", "LampOff"]


class Face:
    """Helper that places things on the rack front (plane y = -DEPTH)."""

    def __init__(self, p, w):
        self.p, self.w = p, w
        self.y = -DEPTH

    def panel(self, z0, h, m):
        """Module plate with a recessed seam and four screws."""
        p, w = self.p, self.w
        p.box((w - 0.03, 0.012, h - 0.012), (0, self.y - 0.006, z0 + h / 2), m, bevel=0.003)
        p.bolts([(sx * (w / 2 - 0.035), self.y - 0.0125, z0 + sz) for sx in (-1, 1) for sz in (0.025, h - 0.025)],
                r=0.006, h=0.004)

    def gauge(self, x, z, r, face):
        p, y = self.p, self.y - 0.012
        p.cyl(r * 1.05, 0.03, (x, y - 0.015, z), "PaintGraphite", axis="Y", segs=24, bevel=0.004, name="gcup")
        p.add(bm_torus(r, r * 0.12, 24, 6, "Y"), "Brass" if r > 0.05 else "Chrome", (x, y - 0.031, z), smooth=180)
        p.add(bm_disc(r * 0.93, 24), face, (x, y - 0.0305, z), uv="keep", smooth=False, name="gface")
        a = random.uniform(-2.0, 2.0)
        p.box((0.004, 0.002, r * 0.75), (x + math.sin(a) * r * 0.35, y - 0.033, z + math.cos(a) * r * 0.35), "PaintRed",
              rot=(0, math.degrees(a), 0), bevel=0)

    def toggle(self, x, z, up):
        p, y = self.p, self.y - 0.012
        p.cyl(0.011, 0.01, (x, y - 0.005, z), "Chrome", axis="Y", segs=6, name="nut")
        p.cyl(0.0035, 0.04, (x, y - 0.025, z + (0.008 if up else -0.008)), "Chrome", axis="Y", segs=6,
              rot=(-25 if up else 25, 0, 0))

    def led(self, x, z, m, r=0.009):
        p, y = self.p, self.y - 0.012
        p.cyl(r * 1.5, 0.008, (x, y - 0.004, z), "Chrome", axis="Y", segs=10)
        p.add(bm_sphere(r, 10, 6, (1, 0.6, 1)), m, (x, y - 0.009, z), smooth=180)

    def knob(self, x, z, r=0.022):
        p, y = self.p, self.y - 0.012
        p.add(bm_lathe([(0, 0.0), (r, 0.0), (r * 0.9, -0.022), (0.0, -0.024)], 14, "Y"), "Bakelite", (x, y, z), smooth=40)
        p.box((0.003, 0.003, r * 0.7), (x, y - 0.024, z + r * 0.3), "PaintWhite", bevel=0)


def _module(face, kind, z0, h, m):
    p, w = face.p, face.w
    face.panel(z0, h, m)
    zc = z0 + h / 2
    y = face.y - 0.012
    if kind == "gauges":
        n = max(1, int((w - 0.06) / 0.17))
        r = min(0.065, (h - 0.06) / 2)
        for k in range(n):
            face.gauge(-w / 2 + (w / n) * (k + 0.5), zc + 0.01, r, random.choice(GAUGES))
    elif kind == "toggles":
        n = max(2, int((w - 0.08) / 0.06))
        for k in range(n):
            x = -w / 2 + 0.06 + (w - 0.12) * k / (n - 1)
            face.toggle(x, zc + 0.012, random.random() > 0.4)
            face.led(x, zc - 0.03, random.choice(LEDS), 0.006)
        p.box((w - 0.08, 0.002, 0.016), (0, y - 0.001, z0 + h - 0.02), "PaintWhite", bevel=0)
    elif kind == "leds":
        n = max(3, int((w - 0.06) / 0.04))
        for row in range(2 if h > 0.09 else 1):
            for k in range(n):
                face.led(-w / 2 + 0.05 + (w - 0.1) * k / (n - 1), zc + (row - 0.5) * 0.035 * (1 if h > 0.09 else 0),
                         random.choice(LEDS), 0.007)
    elif kind == "vent":
        louver(p, (0, y - 0.003, zc), w=w - 0.08, h=h - 0.06, n=max(3, int(h / 0.04)))
    elif kind == "fan":
        r = min((w - 0.1) / 2, (h - 0.06) / 2)
        for x in ([0] if w < 0.6 else [-w / 4, w / 4]):
            rr = r if w < 0.6 else min(r, w / 4 - 0.03)
            p.add(bm_plate_with_holes(rect(rr * 2 + 0.03, rr * 2 + 0.03), [[(math.cos(a) * rr, math.sin(a) * rr)
                  for a in [2 * math.pi * k / 32 for k in range(32)]]], 0.012), "PaintGraphite", (x, y, zc), (90, 0, 0),
                  name="fanframe")
            p.cyl(rr, 0.004, (x, y - 0.002, zc), "BlackPlastic", axis="Y", segs=24)
            p.cyl(rr * 0.22, 0.02, (x, y - 0.012, zc), "DarkSteel", axis="Y", segs=16)
            for b in range(5):
                bl = bm_box(0.05, 0.003, rr * 0.8, (0, 0, rr * 0.45))
                bmesh.ops.rotate(bl, verts=bl.verts, matrix=Matrix.Rotation(R(25), 3, "Z"))
                bmesh.ops.rotate(bl, verts=bl.verts, matrix=Matrix.Rotation(R(b * 72), 3, "Y"))
                p.add(bl, "DarkSteel", (x, y - 0.01, zc), name="blade")
            for k in range(1, 4):
                p.add(bm_torus(rr * k / 3.4, 0.0025, 24, 4, "Y"), "Chrome", (x, y - 0.024, zc), smooth=180)
            for a in (0, 90):
                p.box((rr * 2, 0.004, 0.005), (x, y - 0.024, zc), "Chrome", rot=(0, a, 0), bevel=0)
    elif kind == "reels":
        rr = min(0.13, (h - 0.12) / 2, (w - 0.1) / 4.4)
        p.box((w - 0.08, 0.03, h - 0.07), (0, y + 0.012, zc + 0.02), "BlackPlastic", bevel=0.004)
        for x in (-rr * 1.15, rr * 1.15):
            p.add(bm_disc(rr, 32), "PaintGraphite", (x, y - 0.006, zc + 0.03), uv="keep", smooth=False)
            p.add(bm_torus(rr, 0.006, 32, 6, "Y"), "Chrome", (x, y - 0.008, zc + 0.03), smooth=180)
            p.add(bm_torus(rr * 0.55, rr * 0.25, 32, 8, "Y"), "Rubber", (x, y - 0.006, zc + 0.03), smooth=180)
            for k in range(3):
                a = k * 2 * math.pi / 3
                p.cyl(rr * 0.17, 0.006, (x + math.cos(a) * rr * 0.62, y - 0.012, zc + 0.03 + math.sin(a) * rr * 0.62),
                      "BlackPlastic", axis="Y", segs=12)
            p.cyl(rr * 0.12, 0.03, (x, y - 0.02, zc + 0.03), "Chrome", axis="Y", segs=12)
        p.cyl(0.012, 0.03, (0, y - 0.01, zc - rr * 0.6), "Chrome", axis="Y", segs=10)
        for k in range(5):
            p.box((0.035, 0.02, 0.022), (-0.1 + k * 0.05, y - 0.008, z0 + 0.035), ["PaintCream", "PaintCream", "PaintRed", "PaintCream", "PaintTeal"][k],
                  bevel=0.003)
    elif kind == "crt":
        n = 1 if w < 0.65 else 2
        sw = min((w - 0.08) / n - 0.06, (h - 0.08) * 1.3)
        sh = sw * 0.75
        for k in range(n):
            x = -w / 2 + w / n * (k + 0.5)
            p.screen(sw, sh, (x, y - 0.0, zc + 0.01), random.choice(SCREENS), bezel=0.02, depth=0.02)
    elif kind == "breakers":
        cols = max(3, int((w - 0.08) / 0.05))
        rows = max(1, int((h - 0.06) / 0.11))
        for r_ in range(rows):
            zz = z0 + 0.06 + (h - 0.1) * (r_ + 0.5) / rows
            p.box((w - 0.08, 0.01, 0.07), (0, y - 0.004, zz), "BlackPlastic", bevel=0.002)
            for c in range(cols):
                x = -w / 2 + 0.07 + (w - 0.14) * c / (cols - 1)
                on = random.random() > 0.25
                p.box((0.02, 0.018, 0.028), (x, y - 0.015, zz + (0.008 if on else -0.008)), "PaintWhite" if on else "PaintRed",
                      bevel=0.003)
            p.box((w - 0.1, 0.002, 0.012), (0, y - 0.01, zz + 0.045), "PaintCream", bevel=0)
    elif kind == "knobs":
        n = max(2, int((w - 0.06) / 0.1))
        for k in range(n):
            face.knob(-w / 2 + (w / n) * (k + 0.5), zc, 0.022)
    elif kind == "meters":
        n = max(1, int((w - 0.05) / 0.2))
        for k in range(n):
            x = -w / 2 + (w / n) * (k + 0.5)
            mw, mh = min(0.16, w / n - 0.04), min(0.11, h - 0.06)
            p.box((mw + 0.02, 0.02, mh + 0.02), (x, y - 0.01, zc), "BlackPlastic", bevel=0.004)
            p.decal(mw, mh, (x, y - 0.0205, zc), random.choice(GAUGES))
    elif kind == "patch":
        cols = max(4, int((w - 0.08) / 0.04))
        jacks = []
        for r_ in range(2):
            for c in range(cols):
                x = -w / 2 + 0.06 + (w - 0.12) * c / (cols - 1)
                zz = zc + (r_ - 0.5) * 0.06
                p.cyl(0.008, 0.01, (x, y - 0.005, zz), "DarkSteel", axis="Y", segs=8)
                jacks.append(Vector((x, y - 0.012, zz)))
        for k in range(random.randint(2, 4)):
            a, b = random.sample(jacks, 2)
            p.tube(sag_path(a, b, 0.05 + random.random() * 0.06, 10), 0.004,
                   random.choice(["PaintRed", "PaintMustard", "BlackPlastic", "PaintTeal"]), segs=6)
    elif kind == "plate":
        p.box((w * 0.6, 0.004, 0.035), (0, y - 0.002, zc), "PaintWhite", bevel=0)
        for k in range(3):
            face.led(w * 0.35 + 0.0 - 0.06 * k, zc, random.choice(LEDS), 0.006)
    # "blank" panels just get the plate


MODULES = [("gauges", 0.18, 0.22), ("toggles", 0.12, 0.14), ("leds", 0.07, 0.1), ("vent", 0.16, 0.3),
           ("fan", 0.28, 0.4), ("reels", 0.36, 0.42), ("crt", 0.26, 0.34), ("breakers", 0.24, 0.36),
           ("knobs", 0.1, 0.12), ("meters", 0.16, 0.2), ("patch", 0.14, 0.18), ("plate", 0.07, 0.09),
           ("blank", 0.08, 0.2)]


def equipment_rack(w=0.7, seed=0, name=None):
    """Full-height equipment cabinet with a randomised stack of modules."""
    rnd = random.Random(seed * 97 + int(w * 100))
    random.seed(seed * 131 + int(w * 1000))
    name = name or f"Rack_{int(w * 100)}_{seed}"
    p = Prop(name, category="decor", note="set dressing")
    body = rnd.choice(BODY_COLORS)
    p.box((w - 0.04, DEPTH - 0.04, 0.1), (0, -DEPTH / 2, 0.05), "PaintGraphite", bevel=0.008)
    p.box((w, DEPTH, RACK_H - 0.1), (0, -DEPTH / 2, 0.1 + (RACK_H - 0.1) / 2), body, bevel=0.012)
    p.box((w + 0.01, DEPTH + 0.01, 0.04), (0, -DEPTH / 2, RACK_H - 0.02), "PaintGraphite", bevel=0.006)
    for sx in (-1, 1):  # side rails
        p.box((0.02, 0.02, RACK_H - 0.16), (sx * (w / 2 - 0.01), -DEPTH - 0.004, 0.12 + (RACK_H - 0.16) / 2), "PaintGraphite",
              bevel=0.004)
    z = 0.14
    top = RACK_H - 0.06
    face = Face(p, w - 0.02)
    used_tall = set()
    while z < top - 0.06:
        choices = [mm for mm in MODULES if mm[1] <= top - z and not (mm[0] in used_tall)]
        if not choices:
            break
        kind, hmin, hmax = rnd.choice(choices)
        if kind in ("reels", "crt", "fan"):
            used_tall.add(kind)
        h = min(rnd.uniform(hmin, hmax), top - z)
        _module(face, kind, z, h, body if rnd.random() > 0.35 else rnd.choice(BODY_COLORS))
        z += h + 0.006
    # conduits and cable glands on top
    for k in range(rnd.randint(2, 4)):
        x = -w / 2 + 0.08 + rnd.random() * (w - 0.16)
        p.cyl(0.018, 0.05, (x, -DEPTH / 2 + 0.05, RACK_H + 0.02), "DarkSteel", segs=10)
    p.anchor("cable_in", (0, -DEPTH / 2 + 0.05, RACK_H + 0.04))
    return p.finish()


def valve_manifold(name="ValveManifold", w=1.4, seed=1):
    """Wall-hung pipe manifold with branch valves going up to the ceiling."""
    rnd = random.Random(seed)
    p = Prop(name, category="decor", note="set dressing")
    m = rnd.choice(["PaintRed", "PaintMustard", "Copper", "PaintTeal"])
    z = 1.55
    p.cyl(0.05, w, (0, -0.16, z), m, axis="X", segs=16)
    for sx in (-1, 1):
        p.cyl(0.07, 0.03, (sx * w / 2, -0.16, z), m, axis="X", segs=20, bevel=0.004)
    n = max(2, int(w / 0.32))
    from .props_common import handwheel, gauge
    for k in range(n):
        x = -w / 2 + w * (k + 0.5) / n
        p.cyl(0.028, 1.2, (x, -0.16, z + 0.6), m, segs=12)
        p.add(bm_sphere(0.05, 16, 8, (1, 1, 1.3)), m, (x, -0.16, z + 0.22), smooth=180)
        p.cyl(0.012, 0.12, (x, -0.24, z + 0.22), "Steel", axis="Y", segs=8)
        handwheel(p, (x, -0.3, z + 0.22), r=0.06, name=f"Valve{k + 1}", m=rnd.choice(["PaintRed", "PaintMustard", "PaintTeal"]))
        if k % 2 == 0:
            p.cyl(0.015, 0.08, (x + 0.06, -0.16, z + 0.45), m, axis="X", segs=8)
            gauge(p, (x + 0.12, -0.16, z + 0.45), r=0.045, face=rnd.choice(GAUGES), name=f"Gauge{k + 1}", needle_deg=rnd.uniform(-60, 60))
        p.box((0.05, 0.16, 0.03), (x, -0.08, z + 0.9), "DarkSteel", bevel=0.004)
    for sx in (-1, 1):
        p.box((0.06, 0.16, 0.06), (sx * (w / 2 - 0.15), -0.08, z), "DarkSteel", bevel=0.006)
    return p.finish()


def wall_box(w=0.75, seed=0, name=None):
    """Shallow wall-hung instrument box for the band above consoles (z 1.86..2.1, back on y=0)."""
    rnd = random.Random(seed * 53 + int(w * 100))
    random.seed(seed * 71 + int(w * 1000))
    name = name or f"WallBox_{int(w * 100)}_{seed}"
    p = Prop(name, category="decor", note="set dressing; origin at its bottom-back edge")
    d, h = 0.22, 0.23
    body = rnd.choice(BODY_COLORS)
    p.box((w, d, h), (0, -d / 2, h / 2), body, bevel=0.01)
    for sx in (-1, 1):
        p.box((0.05, 0.03, h + 0.04), (sx * (w / 2 - 0.08), -0.015, h / 2), "DarkSteel", bevel=0.004)
    global DEPTH
    old = DEPTH
    DEPTH = d
    try:
        face = Face(p, w - 0.02)
        kind = rnd.choice(["gauges", "leds", "vent", "meters", "toggles", "breakers", "knobs", "patch"])
        _module(face, kind, 0.01, h - 0.02, body)
    finally:
        DEPTH = old
    p.cyl(0.018, 0.12, (w / 2 - 0.12, -d / 2, h + 0.06), "DarkSteel", segs=10)
    return p.finish()
