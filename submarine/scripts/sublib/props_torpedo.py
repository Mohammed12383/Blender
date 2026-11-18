"""Torpedo room: torpedo, 2x2 tube bank with breech doors, storage racks, loading cradle, chain hoist."""

import math

import bmesh
from mathutils import Matrix, Vector

from .core import Prop, R, bm_box, bm_cyl, bm_extrude, bm_lathe, bm_plate_with_holes, bm_torus, bm_sweep, circle, rrect, rect
from .props_common import gauge, grab_rail, handwheel, indicator, push_button, toggle, _v

TORP_R = 0.24
TORP_L = 2.4
TUBE_POS = [(-0.62, 1.75), (0.62, 1.75), (-0.62, 0.75), (0.62, 0.75)]  # (x, z) of tubes 1..4 on the bulkhead


def torpedo(name="Torpedo"):
    """Carryable torpedo. Axis along local X, nose at +X, origin at the centre."""
    p = Prop(name, category="pickup", interact="carry", item="torpedo", mass_kg=80)
    h = TORP_L / 2
    body = [(0.0, -h), (0.05, -h), (0.07, -h + 0.04), (0.12, -h + 0.18), (0.19, -h + 0.38), (0.235, -h + 0.55),
            (TORP_R, -h + 0.62), (TORP_R, 0.55)]
    p.lathe(body, (0, 0, 0), "PaintGray", segs=40, axis="X", name="body")
    nose = [(TORP_R, 0.55), (TORP_R - 0.002, 0.7), (0.225, 0.85), (0.19, 0.98), (0.13, 1.09), (0.06, 1.16), (0.0, h)]
    p.lathe(nose, (0, 0, 0), "PaintMustard", segs=40, axis="X", name="warhead")
    for x, m in [(0.55, "DarkSteel"), (-0.1, "DarkSteel"), (-h + 0.62, "DarkSteel")]:
        p.add(bm_torus(TORP_R + 0.002, 0.01, 40, 6, "X"), m, (x, 0, 0), smooth=180)
    p.add(bm_cyl(TORP_R + 0.003, 0.08, 40, axis="X", caps=False), "PaintRed", (0.42, 0, 0), smooth=180, name="band")
    p.add(bm_cyl(TORP_R + 0.003, 0.05, 40, axis="X", caps=False), "Hazard", (0.3, 0, 0), smooth=180, name="hazband")
    # lifting lugs, guide stud, umbilical port
    for x in (-0.35, 0.3):
        p.box((0.06, 0.03, 0.04), (x, 0, TORP_R + 0.015), "DarkSteel", bevel=0.006)
        p.add(bm_torus(0.025, 0.007, 16, 6, "Y"), "Steel", (x, 0, TORP_R + 0.05), smooth=180)
    p.box((0.18, 0.03, 0.02), (0.05, 0, TORP_R + 0.008), "Steel", bevel=0.005)
    p.cyl(0.03, 0.02, (-0.55, -TORP_R - 0.005, 0.0), "Brass", axis="Y", segs=16)
    # cruciform fins with hazard tips
    fin = [(-h + 0.05, 0.0), (-h + 0.42, 0.0), (-h + 0.18, 0.2), (-h + 0.04, 0.2)]
    for k in range(4):
        a = k * 90 + 45
        bm = bm_extrude(fin, 0.014)
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.13))
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(R(a), 3, "X"))
        p.add(bm, "PaintGray", bevel=0.003, name="fin")
        tip = bm_box(0.12, 0.016, 0.06, (-h + 0.1, 0, 0.3))
        bmesh.ops.rotate(tip, verts=tip.verts, matrix=Matrix.Rotation(R(a), 3, "X"))
        p.add(tip, "Hazard", bevel=0.003, name="fintip")
    # contra-rotating propellers
    for k, (x, n, ang) in enumerate([(-h - 0.03, 4, 0), (-h - 0.1, 5, 20)]):
        prop = p.pivot(f"Propeller{k + 1}", (x, 0, 0), (0, 0, 0), interact="spin", rotate_axis="X")
        p.cyl(0.04, 0.05, (0, 0, 0), "Brass", axis="X", segs=16, parent=prop, bevel=0.006)
        for b in range(n):
            a = 360 / n * b + ang
            blade = bm_extrude([(-0.03, 0.03), (0.03, 0.03), (0.04, 0.13), (0.0, 0.16), (-0.035, 0.12)], 0.008)
            bmesh.ops.rotate(blade, verts=blade.verts, matrix=Matrix.Rotation(R(90 + (30 if k else -30)), 3, "Z"))
            bmesh.ops.rotate(blade, verts=blade.verts, matrix=Matrix.Rotation(R(90), 3, "Y"))
            bmesh.ops.rotate(blade, verts=blade.verts, matrix=Matrix.Rotation(R(a), 3, "X"))
            p.add(blade, "Brass", parent=prop, bevel=0.003, name="blade")
    p.cyl(0.018, 0.12, (-h - 0.06, 0, 0), "Steel", axis="X", segs=12)
    p.sphere(0.03, (-h - 0.14, 0, 0), "Brass", segs=12, rings=6)
    return p.finish()


def tube_bank(name="TorpedoTubes"):
    """Four breeches on the forward bulkhead. Local XZ = bulkhead face, tubes run along +Y into it.

    Origin on the bulkhead face at floor level. Each door is a pivot hinged on its left side.
    """
    p = Prop(name, category="station", station="torpedo_tubes")
    for i, (x, z) in enumerate(TUBE_POS):
        n = i + 1
        p.cyl(0.33, 0.95, (x, 0.0, z), "PaintTeal", axis="Y", segs=48, name="barrel")
        p.cyl(0.42, 0.1, (x, -0.42, z), "PaintTeal", axis="Y", segs=48, bevel=0.012)
        p.cyl(0.36, 0.06, (x, -0.33, z), "DarkSteel", axis="Y", segs=48, bevel=0.008)
        for k in range(12):
            a = k * math.pi / 6
            p.cyl(0.016, 0.03, (x + math.cos(a) * 0.39, -0.48, z + math.sin(a) * 0.39), "Steel", axis="Y", segs=6, name="bolt")
        for k in range(4):  # stiffening ribs along the barrel
            a = k * math.pi / 2 + math.pi / 4
            p.box((0.04, 0.4, 0.06), (x + math.cos(a) * 0.35, -0.15, z + math.sin(a) * 0.35), "PaintTeal",
                  rot=(0, -math.degrees(a), 0), bevel=0.006)
        # breech door
        hx = x - 0.42
        p.cyl(0.035, 0.22, (hx - 0.02, -0.5, z), "DarkSteel", segs=16, bevel=0.005)
        door = p.pivot(f"Door{n}", (hx - 0.02, -0.5, z), (0, 0, 0), interact="tube_door", tube=n, rotate_axis="Z",
                       min_deg=-115, max_deg=0, open_dir="towards -Y")
        p.add(bm_lathe([(0.0, 0.0), (0.4, 0.0), (0.4, -0.06), (0.37, -0.09), (0.3, -0.1), (0.0, -0.12)], 48, "Y"),
              "PaintTeal", (0.44, 0.03, 0), parent=door, smooth=40, name="door")
        for k in range(6):
            a = k * math.pi / 3
            p.box((0.3, 0.025, 0.03), (0.44 + math.cos(a) * 0.17, -0.1, math.sin(a) * 0.17), "PaintTeal",
                  rot=(0, -math.degrees(a), 0), parent=door, bevel=0.006)
        p.box((0.12, 0.08, 0.14), (0.05, -0.02, 0), "DarkSteel", parent=door, bevel=0.01)
        handwheel(p, (0.44, -0.19, 0), r=0.13, parent=door, name=f"Door{n}Wheel", interact="tube_lock", tube=n, m="PaintMustard")
        p.cyl(0.035, 0.08, (0.44, -0.14, 0), "Steel", axis="Y", segs=16, parent=door)
        lever = p.pivot(f"Door{n}Latch", (0.8, -0.06, 0), parent=door, interact="latch", rotate_axis="Y", min_deg=0, max_deg=60)
        p.box((0.05, 0.04, 0.05), (0, 0, 0), "DarkSteel", parent=lever, bevel=0.006)
        p.cyl(0.012, 0.18, (0.0, -0.03, 0.09), "Chrome", segs=10, parent=lever)
        p.sphere(0.024, (0.0, -0.03, 0.19), "PaintRed", parent=lever, segs=12, rings=6)
        # number plate, ready lamp, gauge, flood valve
        lx = x + (-0.3 if x < 0 else 0.3)
        p.plate(0.14, 0.14, (x, -0.44, z + 0.5), f"label_tube{n}", frame="PaintGraphite")
        indicator(p, (x + 0.16, -0.44, z + 0.5), m="LampGreen" if n in (1, 3) else "LampRed", r=0.022, name=f"Ready{n}")
        gauge(p, (x + (0.5 if x > 0 else -0.5), -0.44, z + 0.32), r=0.07, face="gauge_pressure", name=f"Tube{n}Gauge", needle_deg=-60)
        vx = x + (0.5 if x > 0 else -0.5)
        p.tube([(vx, 0.0, z - 0.1), (vx, -0.25, z - 0.1), (vx, -0.25, z - 0.25)], 0.022, "Copper", round_r=0.06)
        handwheel(p, (vx, -0.25, z - 0.27), rot=(90, 0, 0), r=0.06, name=f"Tube{n}Flood", interact="tube_flood", tube=n, m="PaintRed")
        p.anchor(f"tube{n}", (x, -1.3, 0), tube=n)
    # support saddles and a centre frame
    for x, _ in TUBE_POS[2:]:
        p.box((0.7, 0.5, 0.3), (x, -0.25, 0.15), "PaintGraphite", bevel=0.01)
    p.box((0.16, 0.3, 2.4), (0, -0.15, 1.2), "PaintGraphite", bevel=0.012)
    for z in (0.3, 1.25, 2.2):
        p.box((2.4, 0.12, 0.08), (0, -0.06, z), "PaintGraphite", bevel=0.01)
    # firing panel in the middle
    p.box((0.22, 0.12, 0.5), (0, -0.36, 1.25), "PaintCream", bevel=0.015)
    for k in range(4):
        toggle(p, (0, -0.42, 1.43 - k * 0.1), name=f"Interlock{k + 1}", up=k % 2 == 0)
    push_button(p, (0, -0.42, 1.07), m="PaintRed", r=0.03, name="ManualFire", interact="manual_fire")
    return p.finish()


def torpedo_rack(name="TorpedoRack", length=2.6):
    """Wall rack with two cradle levels; back on y=0, along X. Torpedo slots are anchors."""
    p = Prop(name, category="storage")
    y = -0.42
    xs = [-length / 2 + 0.35, 0, length / 2 - 0.35]
    for x in xs:
        p.box((0.1, 0.1, 1.7), (x, -0.06, 0.85), "PaintGraphite", bevel=0.01)
        p.box((0.24, 0.02, 0.24), (x, -0.01, 1.6), "PaintGraphite", bevel=0.005)
        p.box((0.24, 0.24, 0.02), (x, -0.06, 0.01), "PaintGraphite", bevel=0.005)
        for z in (0.45, 1.25):
            arm = bm_extrude([(0.0, -0.06), (0.62, -0.06), (0.62, 0.0), (0.0, 0.06)], 0.1)
            bmesh.ops.rotate(arm, verts=arm.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
            bmesh.ops.rotate(arm, verts=arm.verts, matrix=Matrix.Rotation(R(-90), 3, "Z"))
            p.add(arm, "PaintGraphite", (x, -0.06, z - TORP_R - 0.06), bevel=0.008, name="arm")
            sad = bm_lathe([(TORP_R + 0.01, -0.05), (TORP_R + 0.07, -0.05), (TORP_R + 0.07, 0.05), (TORP_R + 0.01, 0.05)],
                           16, "X", closed=True, angle=math.pi)
            bmesh.ops.rotate(sad, verts=sad.verts, matrix=Matrix.Rotation(R(-90), 3, "X"))  # lower half
            p.add(sad, "PaintGraphite", (x, y, z), smooth=40, name="saddle")
            pad = bm_lathe([(TORP_R, -0.04), (TORP_R + 0.012, -0.04), (TORP_R + 0.012, 0.04), (TORP_R, 0.04)], 16, "X",
                           closed=True, angle=math.pi)
            bmesh.ops.rotate(pad, verts=pad.verts, matrix=Matrix.Rotation(R(-90), 3, "X"))
            p.add(pad, "Rubber", (x, y, z), smooth=40, name="pad")
            # strap over the top with buckle
            strap = bm_lathe([(TORP_R + 0.004, -0.025), (TORP_R + 0.012, -0.025), (TORP_R + 0.012, 0.025), (TORP_R + 0.004, 0.025)],
                             24, "X", closed=True, angle=math.pi)
            bmesh.ops.rotate(strap, verts=strap.verts, matrix=Matrix.Rotation(R(90), 3, "X"))  # upper half
            p.add(strap, "PaintMustard", (x + 0.12, y, z), smooth=40, name="strap")
            p.box((0.06, 0.03, 0.04), (x + 0.12, y - TORP_R - 0.02, z + 0.05), "Steel", bevel=0.005)
    for z in (0.45 - TORP_R - 0.03, 1.25 - TORP_R - 0.03):
        p.box((length - 0.5, 0.06, 0.05), (0, -0.07, z - 0.04), "PaintGraphite", bevel=0.008)
    p.anchor("slot_lower", (0, y, 0.45), slot="lower")
    p.anchor("slot_upper", (0, y, 1.25), slot="upper")
    p.anchor("use", (0, -1.2, 0))
    return p.finish()


def loading_cradle(name="LoadingCradle", rail_len=3.0):
    """Floor rails along -Y from the tubes with a rolling carriage and a lifting V-tray.

    Carriage translates along Y; LiftTray translates along Z (0.75 lower tubes, 1.75 upper tubes).
    """
    p = Prop(name, category="station", station="loader")
    for sx in (-0.28, 0.28):
        p.box((0.06, rail_len, 0.05), (sx, -rail_len / 2, 0.025), "Steel", bevel=0.005)
        for k in range(6):
            p.box((0.14, 0.08, 0.012), (sx, -0.2 - k * (rail_len - 0.4) / 5, 0.006), "DarkSteel", bevel=0.003)
            p.bolts([(sx - 0.05, -0.2 - k * (rail_len - 0.4) / 5, 0.013), (sx + 0.05, -0.2 - k * (rail_len - 0.4) / 5, 0.013)],
                    r=0.008, axis="Z")
    p.box((0.7, 0.06, 0.12), (0, -rail_len - 0.03, 0.06), "Hazard", bevel=0.006)
    car = p.pivot("Carriage", (0, -1.5, 0), interact="push", translate_axis="Y", min=-2.6, max=-0.9)
    p.box((0.7, 1.2, 0.08), (0, 0, 0.12), "PaintMustard", parent=car, bevel=0.012)
    for sx in (-0.28, 0.28):
        for sy in (-0.45, 0.45):
            p.cyl(0.05, 0.04, (sx, sy, 0.07), "DarkSteel", axis="X", segs=16, parent=car, bevel=0.006)
    for sy in (-0.3, 0.3):  # scissor columns
        p.box((0.08, 0.08, 0.5), (0, sy, 0.4), "Chrome", parent=car, bevel=0.006)
        p.box((0.14, 0.14, 0.12), (0, sy, 0.2), "PaintGraphite", parent=car, bevel=0.01)
    handwheel(p, (0.38, 0.4, 0.35), rot=(0, 0, 90), r=0.1, parent=car, name="LiftCrank", interact="lift_crank", m="PaintRed")
    tray = p.pivot("LiftTray", (0, 0, 0.75 - TORP_R - 0.05), parent=car, interact="lift", translate_axis="Z", min=0.45, max=1.45)
    vt = bm_extrude([(-0.3, 0.12), (-0.26, 0.12), (0, -0.04), (0.26, 0.12), (0.3, 0.12), (0, -0.09)], 1.3)
    bmesh.ops.rotate(vt, verts=vt.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    p.add(vt, "PaintMustard", (0, 0, 0.09), parent=tray, bevel=0.01, name="vtray")
    for k in range(6):
        yy = -0.55 + k * 0.22
        for sx in (-1, 1):
            p.cyl(0.03, 0.18, (sx * 0.1, yy, 0.12), "Rubber", axis="X", rot=(0, sx * 30, 0), segs=12, parent=tray)
    p.anchor("operate", (0.9, -1.5, 0))
    return p.finish()


def chain_hoist(name="ChainHoist", length=3.2, height=2.88):
    """Ceiling I-beam along -Y with a trolley, chain block and hook. Origin at ceiling start of the beam."""
    p = Prop(name, category="station", station="hoist")
    sec = [(-0.06, 0.0), (0.06, 0.0), (0.06, -0.015), (0.008, -0.015), (0.008, -0.145), (0.06, -0.145), (0.06, -0.16),
           (-0.06, -0.16), (-0.06, -0.145), (-0.008, -0.145), (-0.008, -0.015), (-0.06, -0.015)]
    beam = bm_extrude(sec, length)
    bmesh.ops.rotate(beam, verts=beam.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    p.add(beam, "PaintMustard", (0, -length / 2, -0.12), smooth=False, name="beam")
    for yy in (-0.3, -length + 0.3):
        p.cyl(0.015, 0.12, (0, yy, -0.06), "Steel", segs=8)
        p.box((0.15, 0.1, 0.012), (0, yy, -0.006), "DarkSteel", bevel=0.003)
    p.box((0.05, 0.06, 0.2), (0, -length - 0.02, -0.2), "PaintRed", bevel=0.006)
    tr = p.pivot("Trolley", (0, -1.2, -0.28), interact="slide", translate_axis="Y", min=-length + 0.3, max=-0.3)
    for sx in (-1, 1):
        p.box((0.02, 0.22, 0.14), (sx * 0.085, 0, 0.0), "PaintRed", parent=tr, bevel=0.006)
        for sy in (-0.07, 0.07):
            p.cyl(0.03, 0.02, (sx * 0.065, sy, 0.03), "DarkSteel", axis="X", segs=16, parent=tr)
    p.box((0.2, 0.18, 0.04), (0, 0, -0.08), "PaintRed", parent=tr, bevel=0.008)
    p.cyl(0.1, 0.18, (0, 0, -0.22), "PaintRed", parent=tr, segs=24, bevel=0.012, axis="X")
    p.cyl(0.13, 0.03, (0.1, 0, -0.22), "PaintRed", parent=tr, segs=24, axis="X", bevel=0.005)
    for k in range(14):
        z = -0.32 - k * 0.04
        p.add(bm_torus(0.016, 0.005, 10, 5, "X" if k % 2 else "Y"), "Steel", (0, 0, z), parent=tr, smooth=180, name="link")
    for k in range(18):  # hand chain loop
        t = k / 17
        p.add(bm_torus(0.012, 0.004, 8, 4, "Y" if k % 2 else "X"), "Steel", (0.14, -0.06 + 0.12 * (k % 2), -0.3 - t * 1.0),
              parent=tr, smooth=180, name="hlink")
    hook = p.pivot("Hook", (0, 0, -0.9), parent=tr, interact="hook", translate_axis="Z", min=-1.6, max=-0.4)
    p.box((0.06, 0.04, 0.1), (0, 0, 0), "DarkSteel", parent=hook, bevel=0.01)
    hk = bm_sweep(rounded_hook(), circle(0.014, 8), caps=True, up=(0, 1, 0))
    p.add(hk, "PaintMustard", (0, 0, 0), parent=hook, smooth=70, name="hook")
    return p.finish()


def rounded_hook():
    """J-shaped hook centreline: shank down, then a half circle curling back up."""
    pts = [Vector((0, 0, -0.05)), Vector((0, 0, -0.12))]
    for k in range(1, 13):
        a = math.pi * k / 12
        pts.append(Vector((0.05 - 0.05 * math.cos(a), 0, -0.12 - 0.05 * math.sin(a))))
    pts.append(Vector((0.1, 0, -0.09)))
    return pts


def workbench(name="Workbench"):
    p = Prop(name, category="decor")
    W, D, H = 1.6, 0.65, 0.9
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((0.06, 0.06, H - 0.05), (sx * (W / 2 - 0.05), -D / 2 + sy * (D / 2 - 0.05), (H - 0.05) / 2), "PaintGraphite", bevel=0.006)
    p.box((W, D, 0.05), (0, -D / 2, H - 0.025), "Wood", bevel=0.008)
    p.box((W - 0.1, D - 0.1, 0.03), (0, -D / 2, 0.15), "PaintGraphite", bevel=0.005)
    p.box((W, 0.03, 0.8), (0, -0.015, H + 0.4), "PaintGray", bevel=0.006)  # pegboard
    for k in range(10):
        for j in range(5):
            p.cyl(0.006, 0.004, (-0.7 + k * 0.155, -0.031, H + 0.15 + j * 0.14), "BlackPlastic", axis="Y", segs=6, name="peg")
    # vise
    p.box((0.18, 0.2, 0.06), (0.55, -0.45, H + 0.03), "PaintNavy", bevel=0.008)
    p.box((0.18, 0.04, 0.12), (0.55, -0.37, H + 0.12), "PaintNavy", bevel=0.008)
    jaw = p.pivot("ViseJaw", (0.55, -0.53, H + 0.12), interact="crank", translate_axis="Y", min=-0.1, max=0)
    p.box((0.18, 0.04, 0.12), (0, 0, 0), "PaintNavy", parent=jaw, bevel=0.008)
    p.cyl(0.012, 0.25, (0, -0.06, 0), "Chrome", axis="X", segs=10, parent=jaw)
    # hanging wrench + hammer silhouettes on pegboard
    p.box((0.03, 0.01, 0.3), (-0.5, -0.04, H + 0.4), "Chrome", bevel=0.004)
    p.add(bm_torus(0.035, 0.012, 16, 6, "Y"), "Chrome", (-0.5, -0.04, H + 0.57), smooth=180)
    p.box((0.025, 0.012, 0.3), (-0.2, -0.04, H + 0.4), "Wood", bevel=0.004)
    p.box((0.12, 0.03, 0.04), (-0.2, -0.04, H + 0.56), "DarkSteel", bevel=0.006)
    return p.finish()
