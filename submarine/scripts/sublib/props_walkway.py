"""Walkways: open steel grating, guard railings, ship's stairs, catwalks and the pipe banks that line
the engine-room passage.
"""

import math

import bmesh
from mathutils import Matrix, Vector

from .core import Prop, R, bm_box, bm_sweep, circle, rect, rounded_path


def add_grating(p, cx, cy, z, w, l, along="X", parent=None, m="DarkSteel", pitch=0.045):
    """Open grating panel (w across, l along) with its top at height z: frame, bearing bars and cross rods."""
    ax = along == "X"
    sx, sy = (l, w) if ax else (w, l)
    for side in (-1, 1):   # frame
        if ax:
            p.box((l, 0.04, 0.05), (cx, cy + side * (w / 2 - 0.02), z - 0.025), m, bevel=0.003, parent=parent, name="gframe")
        else:
            p.box((0.04, l, 0.05), (cx + side * (w / 2 - 0.02), cy, z - 0.025), m, bevel=0.003, parent=parent, name="gframe")
    n = max(2, int((w - 0.08) / pitch))
    for k in range(n):
        o = -w / 2 + 0.04 + (w - 0.08) * (k + 0.5) / n
        if ax:
            p.box((l, 0.006, 0.035), (cx, cy + o, z - 0.0175), m, bevel=0, parent=parent, name="gbar")
        else:
            p.box((0.006, l, 0.035), (cx + o, cy, z - 0.0175), m, bevel=0, parent=parent, name="gbar")
    nc = max(2, int(l / 0.1))
    for k in range(nc):
        o = -l / 2 + l * (k + 0.5) / nc
        if ax:
            p.box((0.008, w - 0.04, 0.008), (cx + o, cy, z - 0.004), m, bevel=0, parent=parent, name="grod")
        else:
            p.box((w - 0.04, 0.008, 0.008), (cx, cy + o, z - 0.004), m, bevel=0, parent=parent, name="grod")


def add_railing(p, pts, h=1.0, m="PaintMustard", posts=1.1, parent=None, kick=True):
    """Guard rail along a polyline at floor level: posts, top rail, mid rail, kick plate."""
    pts = [Vector(q) for q in pts]
    up = Vector((0, 0, 1))
    p.tube([q + up * h for q in pts], 0.022, m, segs=10, round_r=0.08, parent=parent, name="toprail")
    p.tube([q + up * h * 0.5 for q in pts], 0.016, m, segs=8, round_r=0.08, parent=parent, name="midrail")
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        n = max(1, int(L / posts))
        for k in range(n + 1):
            q = a.lerp(b, k / n)
            p.cyl(0.02, h, q + up * h / 2, m, segs=10, parent=parent, name="post")
        if kick:
            d = (b - a).normalized()
            ang = math.degrees(math.atan2(d.y, d.x))
            p.box((L, 0.008, 0.1), (a + b) / 2 + up * 0.06, m, rot=(0, 0, ang), bevel=0, parent=parent, name="kick")


def stairs(name="Stairs", rise=2.9, run=2.7, width=1.0, rails=(True, True)):
    """Steep ship's stairs climbing along +X: bottom step at x=0 (z=0) up to the landing at x=run (z=rise).

    Grated treads, channel stringers and handrails on both sides."""
    p = Prop(name, category="stairs", interact="climb", rise=rise, run=run)
    n = max(4, round(rise / 0.22))
    hrise, hrun = rise / n, run / n
    ang = math.degrees(math.atan2(rise, run))
    Ls = math.hypot(rise, run) + 0.3
    for side in (-1, 1):
        p.box((Ls, 0.04, 0.24), (run / 2, side * (width / 2 + 0.02), rise / 2 - 0.05), "PaintMustard", rot=(0, -ang, 0), bevel=0.006)
    for k in range(n):
        z = hrise * (k + 1)
        x = hrun * (k + 0.5)
        add_grating(p, x, 0, z, width, hrun + 0.04, along="Y", m="DarkSteel", pitch=0.05)
        p.box((0.025, width, 0.04), (x - hrun / 2 - 0.01, 0, z - 0.02), "Hazard", bevel=0.003, name="nosing")
    for side, on in zip((-1, 1), rails):
        if not on:
            continue
        y = side * (width / 2 + 0.04)
        a, b = Vector((-0.1, y, 0.95)), Vector((run + 0.15, y, rise + 0.95))
        p.tube([a, b, b + Vector((0.4, 0, 0))], 0.022, "Chrome", segs=10, round_r=0.1, name="handrail")
        for t in (0.1, 0.5, 0.9):
            q = a.lerp(b, t)
            p.cyl(0.018, 0.95, q - Vector((0, 0, 0.475)), "Chrome", segs=8, name="stanchion")
    p.anchor("bottom", (-0.4, 0, 0))
    p.anchor("top", (run + 0.4, 0, rise))
    return p.finish()


def catwalk(name="Catwalk", length=8.0, width=1.2, rails=(True, True), rail_m="PaintMustard", legs=0.0):
    """Grated catwalk along +X starting at x=0, deck at z=0, centred on y=0, with support beams and railings.

    legs > 0 adds support legs reaching that far down (to the floor of the pit the catwalk spans)."""
    p = Prop(name, category="walkway", walkable=True, length=length, width=width)
    seg = 1.6
    n = max(1, int(round(length / seg)))
    for k in range(n):
        add_grating(p, (k + 0.5) * length / n, 0, 0.0, width, length / n - 0.01, along="X")
    for k in range(n + 1):
        x = min(max(k * length / n, 0.04), length - 0.04)
        p.box((0.08, width + 0.1, 0.12), (x, 0, -0.11), "PaintGraphite", bevel=0.006, name="beam")
        if legs > 0.2:
            for side in (-1, 1):
                p.box((0.06, 0.06, legs - 0.17), (x, side * (width / 2 - 0.04), -0.17 - (legs - 0.17) / 2), "PaintGraphite",
                      bevel=0.005, name="leg")
                p.box((0.16, 0.16, 0.012), (x, side * (width / 2 - 0.04), -legs + 0.006), "DarkSteel", bevel=0.002, name="foot")
    for side, on in zip((-1, 1), rails):
        if on:
            add_railing(p, [(0.05, side * (width / 2 + 0.02), 0), (length - 0.05, side * (width / 2 + 0.02), 0)], m=rail_m)
    return p.finish()


def platform(name="Platform", length=2.2, width=4.9, legs=1.2):
    """Grated deck from x=0 to length, centred on y=0 (top at z=0), on beams and legs reaching `legs` down."""
    p = Prop(name, category="walkway", walkable=True, length=length, width=width)
    nx, ny = max(1, round(length / 1.1)), max(1, round(width / 1.25))
    for i in range(nx):
        for j in range(ny):
            add_grating(p, (i + 0.5) * length / nx, -width / 2 + (j + 0.5) * width / ny, 0.0, width / ny - 0.01,
                        length / nx - 0.01, along="X")
    for i in range(nx + 1):
        x = min(max(i * length / nx, 0.04), length - 0.04)
        p.box((0.08, width, 0.12), (x, 0, -0.11), "PaintGraphite", bevel=0.006, name="beam")
        for j in range(ny + 1):
            y = min(max(-width / 2 + j * width / ny, -width / 2 + 0.05), width / 2 - 0.05)
            p.box((0.07, 0.07, legs - 0.17), (x, y, -0.17 - (legs - 0.17) / 2), "PaintGraphite", bevel=0.005, name="leg")
    for j in range(ny + 1):
        y = min(max(-width / 2 + j * width / ny, -width / 2 + 0.05), width / 2 - 0.05)
        p.box((length, 0.06, 0.1), (length / 2, y, -0.1), "PaintGraphite", bevel=0.005, name="stringer")
    return p.finish()


def railing(name, pts, h=1.0, m="PaintMustard", col=None):
    """Free-standing guard rail along a polyline (world coordinates)."""
    p = Prop(name, col=col, category="railing")
    add_railing(p, pts, h=h, m=m)
    return p.finish()


def pipe_bank(name="PipeBank", length=4.0, seed=1):
    """Bundle of big horizontal pipes, flanges, valves and gauges (lines the passage below the walkway)."""
    import random
    from .props_common import handwheel, gauge
    rnd = random.Random(seed)
    p = Prop(name, category="decor")
    specs = [(0.16, 0.25, "PaintRed"), (0.12, 0.62, "PaintMustard"), (0.18, 0.95, "DarkSteel"), (0.09, 1.3, "Copper"),
             (0.11, 0.42, "PaintTeal"), (0.08, 1.1, "PaintNavy")]
    rnd.shuffle(specs)
    for k, (r, z, m) in enumerate(specs[:5]):
        y = -0.25 - (k % 3) * 0.32
        p.cyl(r, length, (length / 2, y, z), m, axis="X", segs=20, name="pipe")
        x = 0.4 + rnd.random() * 0.4
        while x < length - 0.3:
            for dx in (-0.02, 0.02):
                p.cyl(r * 1.45, 0.035, (x + dx, y, z), m, axis="X", segs=20, bevel=0.004, name="flange")
            x += 1.2 + rnd.random() * 0.8
        if rnd.random() < 0.7:
            vx = 0.6 + rnd.random() * (length - 1.2)
            p.cyl(r * 1.25, 0.25, (vx, y, z), m, axis="X", segs=16, bevel=0.01)
            p.cyl(0.02, 0.25, (vx, y, z + r + 0.12), "Steel", segs=8)
            handwheel(p, (vx, y, z + r + 0.26), rot=(90, 0, 0), r=0.09, name=f"Valve{k}", m=rnd.choice(["PaintRed", "PaintMustard", "PaintTeal"]))
    for x in (0.3, length - 0.3):
        p.box((0.08, 1.0, 0.08), (x, -0.55, 0.06), "PaintGraphite", bevel=0.006)
        p.box((0.08, 0.06, 1.4), (x, -0.06, 0.7), "PaintGraphite", bevel=0.006)
    gauge(p, (length * 0.5, -1.08, 1.45), rot=(0, 0, 0), r=0.06, face="gauge_pressure", name="Gauge", needle_deg=rnd.uniform(-60, 60))
    p.cyl(0.02, 0.4, (length * 0.5, -1.0, 1.25), "Steel", segs=8)
    return p.finish()
