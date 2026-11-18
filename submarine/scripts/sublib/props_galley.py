"""Galley (kitchen) and crew mess props, including food items."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

from .core import (Prop, R, bm_box, bm_cyl, bm_extrude, bm_lathe, bm_plate_with_holes, bm_sphere, bm_sweep, bm_torus,
                   circle, rect, rrect, rounded_path, sag_path)
from .props_common import gauge, grab_rail, handwheel, indicator, knob, louver, push_button, slots, toggle


# ----------------------------------------------------------------- galley

def griddle(name="Griddle"):
    """Flat-top grill station: ridged half + flat half, knobs, power button, cupboard doors.

    Cook slots (where food snaps) are anchors on the plate."""
    p = Prop(name, category="station", station="cooking")
    W, D, H = 1.25, 0.75, 0.9
    p.box((W - 0.08, D - 0.08, 0.1), (0, -D / 2, 0.05), "PaintGraphite", bevel=0.008)
    p.box((W, D, H - 0.2), (0, -D / 2, 0.1 + (H - 0.2) / 2), "Stainless", bevel=0.015)
    # sloped control strip
    strip = bm_extrude([(0, 0), (0.12, 0), (0.12, 0.12), (0.0, 0.08)], W)
    mtx = Matrix(((0, 0, 1), (-1, 0, 0), (0, 1, 0)))
    for v in strip.verts:
        v.co = mtx @ v.co
    p.add(strip, "Stainless", (0, -D, H - 0.12), bevel=0.006, name="strip")
    for k, nm in enumerate(["LeftHeat", "RightHeat", "Timer"]):
        knob(p, (-0.4 + k * 0.22, -D - 0.085, H - 0.065), rot=(-18, 0, 0), r=0.032, name=nm + "Knob", interact="dial")
    pb = push_button(p, (0.32, -D - 0.085, H - 0.065), rot=(-18, 0, 0), m="PaintRed", r=0.035, name="PowerButton", interact="power")
    indicator(p, (0.48, -D - 0.085, H - 0.065), rot=(-18, 0, 0), m="LampGreen", r=0.016, name="ReadyLamp")
    # cooking plate
    p.box((W - 0.06, D - 0.12, 0.04), (0, -D / 2 - 0.02, H - 0.02), "DarkSteel", bevel=0.006)
    p.box((W / 2 - 0.08, D - 0.2, 0.01), (-W / 4, -D / 2 - 0.02, H + 0.0), "GrillGlow", bevel=0)
    for k in range(13):
        x = -W / 2 + 0.07 + k * (W / 2 - 0.12) / 12
        p.box((0.018, D - 0.2, 0.025), (x, -D / 2 - 0.02, H + 0.012), "DarkSteel", bevel=0.004, name="bar")
    p.box((W / 2 - 0.06, D - 0.2, 0.012), (W / 4 - 0.01, -D / 2 - 0.02, H + 0.006), "Steel", bevel=0.003)
    p.box((W - 0.1, 0.06, 0.03), (0, -D + 0.06, H - 0.01), "DarkSteel", bevel=0.004)  # grease trough
    # splash guards
    p.box((W, 0.02, 0.3), (0, -0.01, H + 0.15), "Stainless", bevel=0.005)
    for sx in (-1, 1):
        sg = bm_extrude([(0, 0), (D, 0), (D, 0.06), (0.0, 0.3)], 0.02)
        mtx = Matrix(((0, 0, 1), (-1, 0, 0), (0, 1, 0)))
        for v in sg.verts:
            v.co = mtx @ v.co
        p.add(sg, "Stainless", (sx * (W / 2 - 0.01), 0, H), bevel=0.004, name="side")
    # cupboard doors
    for k, sx in enumerate((-1, 1)):
        hinge_x = sx * (W / 2 - 0.03)
        door = p.pivot(f"Door{k + 1}", (hinge_x, -D - 0.005, 0.15), interact="door", rotate_axis="Z",
                       min_deg=0 if sx > 0 else -100, max_deg=100 if sx > 0 else 0)
        dw = W / 2 - 0.05
        p.box((dw, 0.02, 0.55), (-sx * dw / 2, 0, 0.275), "Stainless", parent=door, bevel=0.006)
        p.tube([(-sx * (dw - 0.06), -0.01, 0.2), (-sx * (dw - 0.06), -0.05, 0.2), (-sx * (dw - 0.06), -0.05, 0.4),
                (-sx * (dw - 0.06), -0.01, 0.4)], 0.01, "Chrome", round_r=0.02, parent=door)
    for k in range(4):
        x = -W / 2 + 0.16 + (k % 2) * 0.3 + (0 if k < 2 else W / 2)
        p.anchor(f"cook_slot{k + 1}", (x - (0.0 if k < 2 else 0.04), -D / 2 - 0.02, H + 0.03), slot=k + 1)
    p.anchor("operate", (0, -D - 0.5, 0))
    return p.finish()


def exhaust_hood(name="ExhaustHood", W=1.35, D=0.85, z=1.75, ceiling=2.9):
    """Wall hood over the griddle, ducted to the ceiling, with baffle filters and a work light."""
    p = Prop(name, category="decor")
    lip = 0.22
    p.add(bm_plate_with_holes(rect(W, D), [rect(W - 0.06, D - 0.06)], lip), "Stainless", (0, -D / 2, z), bevel=0.006,
          name="lip")
    # tapered canopy: loft from W x D at z+lip to duct size
    bm = bmesh.new()
    lo = [(-W / 2, -D), (W / 2, -D), (W / 2, 0), (-W / 2, 0)]
    hi = [(-0.22, -0.55), (0.22, -0.55), (0.22, -0.1), (-0.22, -0.1)]
    v_lo = [bm.verts.new((x, y, z + lip)) for x, y in lo]
    v_hi = [bm.verts.new((x, y, z + lip + 0.35)) for x, y in hi]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((v_lo[i], v_lo[j], v_hi[j], v_hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    p.add(bm, "Stainless", smooth=False, name="canopy")
    p.box((0.44, 0.45, ceiling - (z + lip + 0.35)), (0, -0.325, (ceiling + z + lip + 0.35) / 2), "Stainless", bevel=0.005)
    # baffle filters inside, angled
    for k in range(5):
        x = -W / 2 + 0.17 + k * (W - 0.34) / 4
        p.box((0.24, D - 0.12, 0.02), (x, -D / 2, z + 0.25), "Steel", rot=(0, 35, 0), bevel=0.003)
    p.box((0.6, 0.06, 0.02), (0, -D + 0.12, z + 0.01), "LightCool", bevel=0.002)
    p.light("WorkLight", "SPOT", 120, "#eef4ff", (0, -D / 2, z), (0, 0, 0), spot=110, radius=0.05)
    return p.finish()


def wire_shelf(name="WireShelf", W=1.0, D=0.45, H=1.8, levels=(0.15, 0.6, 1.1, 1.6)):
    p = Prop(name, category="storage")
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 - 0.015), -D / 2 + sy * (D / 2 - 0.015)
            p.cyl(0.013, H, (x, y, H / 2), "Chrome", segs=12)
            p.cyl(0.02, 0.025, (x, y, 0.0125), "BlackPlastic", segs=12)
            for z in levels:
                p.cyl(0.02, 0.05, (x, y, z), "Chrome", segs=12, r2=0.016)
    for z in levels:
        frame = [Vector((x, y, z)) for x, y in rect(W - 0.03, D - 0.03)]
        p.add(bm_sweep([f + Vector((0, -D / 2, 0)) for f in frame], circle(0.006, 6), caps=False, closed_path=True),
              "Chrome", smooth=60, name="frame")
        n = int((D - 0.03) / 0.035)
        for k in range(1, n):
            y = -D + 0.015 + k * (D - 0.03) / n
            p.cyl(0.0035, W - 0.03, (0, y, z), "Chrome", axis="X", segs=6, name="wire")
        for k in range(1, 5):
            x = -W / 2 + k * W / 5
            p.cyl(0.004, D - 0.03, (x, -D / 2, z - 0.008), "Chrome", axis="Y", segs=6, name="wire")
    for i, z in enumerate(levels):
        p.anchor(f"shelf{i + 1}", (0, -D / 2, z + 0.01), shelf=i + 1)
    return p.finish()


def tray(name="Tray", m="TrayGreen", W=0.5, D=0.35):
    p = Prop(name, category="pickup", interact="pickup", item="tray")
    bm = bm_plate_with_holes(rrect(W, D, 0.04, 4), [rrect(W - 0.03, D - 0.03, 0.03, 4)], 0.035)
    p.add(bm, m, bevel=0.004, name="rim")
    p.box((W - 0.02, D - 0.02, 0.006), (0, 0, 0.003), m, bevel=0)
    return p.finish()


def fridge(name="Fridge", W=0.8, D=0.72, H=1.95):
    p = Prop(name, category="storage", interact="open")
    p.box((W, D - 0.04, H), (0, -(D - 0.04) / 2, H / 2), "Stainless", bevel=0.02, segs=3)
    louver(p, (0, -D + 0.035, 0.08), w=W - 0.15, h=0.1, n=4)
    for k, (z0, h, nm) in enumerate([(0.16, 1.15, "FridgeDoor"), (1.33, H - 1.35, "FreezerDoor")]):
        door = p.pivot(nm, (W / 2 - 0.02, -D + 0.04, z0), interact="door", rotate_axis="Z", min_deg=0, max_deg=110)
        p.box((W - 0.02, 0.05, h), (-(W - 0.02) / 2, -0.025, h / 2), "Stainless", parent=door, bevel=0.012, segs=2)
        p.box((W - 0.06, 0.012, h - 0.04), (-(W - 0.02) / 2, 0.006, h / 2), "Rubber", parent=door, bevel=0.003)
        hz = 0.25 if k == 0 else 0.05
        hl = 0.5 if k == 0 else 0.35
        p.tube([(-W + 0.12, -0.05, hz), (-W + 0.12, -0.1, hz + 0.04), (-W + 0.12, -0.1, hz + hl - 0.04),
                (-W + 0.12, -0.05, hz + hl)], 0.014, "Chrome", round_r=0.03, parent=door)
    # magnets and notes on the door
    door = [o for o in p.groups if o.name.endswith("FridgeDoor")][0]
    for k, (x, z, rot, m) in enumerate([(-0.3, 0.85, 4, "PaintCream"), (-0.5, 0.72, -6, "PaintWhite"), (-0.25, 0.55, -2, "PaintMustard")]):
        p.decal(0.14, 0.18, (x, -0.051, z), m, rot=(0, rot, 0), parent=door)
        p.cyl(0.012, 0.008, (x, -0.055, z + 0.08), ["PaintRed", "PaintTeal", "PaintNavy"][k], axis="Y", segs=12, parent=door)
    p.box((0.16, 0.02, 0.05), (0, -D + 0.035, H - 0.05), "BlackPlastic", bevel=0.005)
    p.box((0.06, 0.004, 0.025), (0, -D + 0.023, H - 0.05), "LampGreen", bevel=0)
    p.anchor("use", (0, -D - 0.5, 0))
    return p.finish()


def prep_counter(name="PrepCounter", W=1.4, D=0.7, H=0.9):
    """Counter with a sink, faucet, cutting board and knife; backsplash against the wall."""
    p = Prop(name, category="station", station="prep")
    p.box((W - 0.08, D - 0.08, 0.1), (0, -D / 2, 0.05), "PaintGraphite", bevel=0.008)
    p.box((W, D - 0.02, H - 0.14), (0, -(D - 0.02) / 2, 0.1 + (H - 0.14) / 2), "PaintTeal", bevel=0.015)
    for k in range(3):
        x = -W / 2 + W / 6 + k * W / 3
        p.box((W / 3 - 0.03, 0.02, H - 0.3), (x, -D + 0.01, 0.15 + (H - 0.3) / 2), "PaintTeal", bevel=0.006)
        p.add(bm_extrude(rrect(0.12, 0.025, 0.01), 0.02), "Chrome", (x, -D, H - 0.2), (90, 0, 0), bevel=0.003)
    sink_x, sw, sd = W / 2 - 0.35, 0.45, 0.38
    top = bm_plate_with_holes(rect(W + 0.02, D + 0.02), [[(x + sink_x, y - 0.02) for x, y in rrect(sw, sd, 0.04, 4)]], 0.04)
    p.add(top, "Stainless", (0, -D / 2, H - 0.04), bevel=0.006, name="top")
    bm = bm_plate_with_holes(rrect(sw + 0.01, sd + 0.01, 0.045, 4), [rrect(sw - 0.01, sd - 0.01, 0.035, 4)], 0.22)
    p.add(bm, "Stainless", (sink_x, -D / 2 - 0.02, H - 0.25), name="basin")
    p.box((sw, sd, 0.01), (sink_x, -D / 2 - 0.02, H - 0.245), "Stainless", bevel=0)
    p.cyl(0.025, 0.012, (sink_x, -D / 2 - 0.02, H - 0.238), "Chrome", segs=16)
    # backsplash and faucet
    p.box((W, 0.02, 0.45), (0, -0.01, H + 0.225), "Stainless", bevel=0.004)
    p.cyl(0.025, 0.08, (sink_x, -0.06, H + 0.04), "Chrome", segs=16)
    p.tube(rounded_path([(sink_x, -0.06, H + 0.07), (sink_x, -0.06, H + 0.38), (sink_x, -0.24, H + 0.38), (sink_x, -0.24, H + 0.28)], 0.08),
           0.012, "Chrome", segs=12)
    for sx in (-1, 1):
        knob(p, (sink_x + sx * 0.1, -0.06, H + 0.06), rot=(-90, 0, 0), r=0.025,
             name="HotTap" if sx < 0 else "ColdTap", interact="tap", m="EnamelRed" if sx < 0 else "EnamelBlue")
    # cutting board and knife
    p.box((0.42, 0.28, 0.025), (-0.3, -0.38, H + 0.0125), "CuttingBoard", bevel=0.006)
    knife = p.pivot("Knife", (-0.25, -0.3, H + 0.03), (0, 0, 15), interact="pickup", item="knife")
    p.extrude([(0, -0.012), (0.18, -0.012), (0.2, 0.0), (0.18, 0.016), (0, 0.016)], 0.002, (0, 0, 0.001), "Chrome", parent=knife)
    p.box((0.11, 0.024, 0.018), (-0.055, 0.002, 0.004), "Bakelite", parent=knife, bevel=0.005)
    for k, (x, y) in enumerate([(-0.42, -0.42), (-0.36, -0.46), (-0.4, -0.33)]):
        p.sphere(0.03, (x, y, H + 0.055), "EnamelRed", segs=14, rings=8, scale=(1, 1, 0.85), name="tomato")
    p.anchor("operate", (0, -D - 0.5, 0))
    return p.finish()


def pot_rail(name="PotRail", W=1.3):
    """Wall rail with S-hooks: two pans, a pot, a ladle and a whisk."""
    p = Prop(name, category="decor")
    p.cyl(0.014, W, (0, -0.07, 0), "Chrome", axis="X", segs=12)
    for sx in (-1, 1):
        p.tube([(sx * W / 2, -0.07, 0), (sx * W / 2, 0, 0)], 0.012, "Chrome", segs=10)
        p.cyl(0.03, 0.01, (sx * W / 2, -0.005, 0), "Chrome", axis="Y", segs=16)
    items = [(-0.5, "pan", 0.13), (-0.2, "pot", 0.12), (0.12, "pan", 0.1), (0.35, "ladle", 0), (0.52, "whisk", 0)]
    for x, kind, r in items:
        p.add(bm_torus(0.02, 0.003, 12, 4, "X", angle=math.pi * 1.5), "Chrome", (x, -0.07, 0.0), smooth=180)
        pv = p.pivot(kind.title() + f"_{int(x * 100)}", (x, -0.07, -0.04), interact="pickup", item=kind)
        if kind == "pan":
            p.add(bm_lathe([(0, -0.03), (r - 0.01, -0.03), (r, -0.025), (r + 0.015, 0.0), (r + 0.012, 0.003), (r - 0.005, -0.022), (0, -0.024)], 32, "Y"),
                  "DarkSteel", (0, -0.04, -0.03 - r - 0.04), (0, 0, 0), parent=pv, smooth=50)
            p.box((0.03, 0.02, 0.2), (0, -0.03, -0.1), "Bakelite", parent=pv, bevel=0.008)
            p.add(bm_torus(0.012, 0.003, 10, 4, "Y"), "Chrome", (0, -0.03, -0.0), parent=pv, smooth=180)
        elif kind == "pot":
            p.add(bm_lathe([(0, 0), (r, 0), (r, 0.18), (r + 0.006, 0.185), (r - 0.004, 0.18), (r - 0.004, 0.006), (0, 0.006)], 32),
                  "Copper", (0, -0.13, -0.3), parent=pv, smooth=50)
            p.tube([(0, -0.13 + 0.0, -0.1), (0, -0.07, -0.02), (0, -0.0, -0.0)], 0.006, "Chrome", parent=pv)
        elif kind == "ladle":
            p.cyl(0.006, 0.3, (0, -0.0, -0.17), "Chrome", segs=8, parent=pv)
            p.add(bm_lathe([(0, 0), (0.05, 0.02), (0.055, 0.045), (0.05, 0.047), (0, 0.006)], 24), "Chrome", (0, -0.0, -0.37), parent=pv, smooth=60)
        else:
            p.cyl(0.012, 0.12, (0, 0, -0.06), "Bakelite", segs=10, parent=pv)
            for k in range(6):
                a = k * math.pi / 6
                pts = [(math.cos(a) * 0.035 * math.sin(t * math.pi), math.sin(a) * 0.035 * math.sin(t * math.pi), -0.12 - t * 0.16) for t in [i / 10 for i in range(11)]]
                p.tube(pts, 0.0015, "Chrome", segs=4, parent=pv)
    return p.finish()


def _blob(rx, ry, h, seed, n=28, rough=0.08):
    rnd = random.Random(seed)
    offs = [1 + rnd.uniform(-rough, rough) for _ in range(6)]
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        f = 1 + sum(o * 0.0 for o in offs) + rough * math.sin(3 * a + seed) * 0.6 + rough * math.cos(5 * a + seed * 2) * 0.4
        pts.append((rx * f * math.cos(a), ry * f * math.sin(a)))
    return pts


def steak(name="Steak", cooked=False, seed=3):
    """Food pickup: steak with fat cap. Top/bottom use the meat texture, sides the fat."""
    p = Prop(name, category="pickup", interact="pickup", item="steak_cooked" if cooked else "steak_raw",
             cook_state="cooked" if cooked else "raw")
    poly = _blob(0.11, 0.075, 0.03, seed)
    bm = bm_extrude(poly, 0.03, center_z=False)
    for f in bm.faces:
        f.material_index = 0 if abs(f.normal.z) > 0.5 else 1
    me_mats = ["MeatCooked" if cooked else "MeatRaw", "MeatCooked" if cooked else "MeatFat"]
    p.add(bm, me_mats, bevel=0.008, segs=3, name="steak")
    return p.finish()


def drumstick(name="Drumstick", cooked=True):
    p = Prop(name, category="pickup", interact="pickup", item="drumstick_cooked" if cooked else "drumstick_raw",
             cook_state="cooked" if cooked else "raw")
    prof = [(0.0, 0.0), (0.035, 0.005), (0.05, 0.03), (0.055, 0.06), (0.05, 0.09), (0.035, 0.12), (0.018, 0.15), (0.013, 0.17), (0.013, 0.17)]
    p.add(bm_lathe(prof[:-1], 24, "X"), "ChickenSkin" if cooked else "MeatFat", (0, 0, 0.05), (0, 0, 0), smooth=180, scale=(1, 1, 0.85))
    p.cyl(0.011, 0.06, (0.19, 0, 0.05), "Bone", axis="X", segs=12)
    for dy in (-0.008, 0.008):
        p.sphere(0.013, (0.225, dy, 0.05), "Bone", segs=12, rings=6)
    return p.finish()


def patty(name="Patty", cooked=False):
    p = Prop(name, category="pickup", interact="pickup", item="patty_cooked" if cooked else "patty_raw")
    p.add(bm_lathe([(0, 0), (0.055, 0.0), (0.062, 0.008), (0.06, 0.018), (0.05, 0.022), (0, 0.023)], 32),
          "MeatCooked" if cooked else "MeatRaw", smooth=60)
    return p.finish()


# ------------------------------------------------------------------- mess

def mess_table(name="MessTable", L=2.0, W=0.9, H=0.76):
    """Bolted-down wooden table with a metal edge band and pedestal legs."""
    p = Prop(name, category="furniture")
    p.box((L, W, 0.05), (0, 0, H - 0.025), "Wood", bevel=0.01)
    p.add(bm_plate_with_holes(rrect(L + 0.02, W + 0.02, 0.03, 4), [rect(L - 0.005, W - 0.005)], 0.04), "Steel",
          (0, 0, H - 0.055), bevel=0.004, name="band")
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.3)
        p.box((0.08, W - 0.2, 0.06), (x, 0, H - 0.09), "PaintNavy", bevel=0.008)
        p.box((0.08, 0.08, H - 0.12), (x, 0, (H - 0.12) / 2 + 0.03), "PaintNavy", bevel=0.01)
        p.box((0.1, W - 0.25, 0.05), (x, 0, 0.025), "PaintNavy", bevel=0.01)
        p.bolts([(x, sy * (W / 2 - 0.16), 0.052) for sy in (-1, 1)], axis="Z", r=0.014)
    p.box((L - 0.6, 0.05, 0.05), (0, 0, 0.25), "PaintNavy", bevel=0.008)
    # fiddle rails (stop plates sliding when the boat rolls)
    for sy in (-1, 1):
        p.box((L - 0.1, 0.012, 0.02), (0, sy * (W / 2 - 0.006), H + 0.01), "Brass", bevel=0.003)
    return p.finish()


def mug(name="Mug", m="EnamelBlue", full=True):
    p = Prop(name, category="pickup", interact="pickup", item="mug")
    p.add(bm_lathe([(0, 0), (0.04, 0.0), (0.042, 0.004), (0.042, 0.095), (0.045, 0.1), (0.039, 0.1), (0.038, 0.006), (0, 0.006)], 32),
          m, smooth=50)
    p.add(bm_torus(0.0425, 0.003, 32, 6), "EnamelCream", (0, 0, 0.099), smooth=180)
    p.add(bm_torus(0.026, 0.006, 16, 6, "Y", angle=math.pi), m, (0.042, 0, 0.052), (0, -90, 0), smooth=180)
    if full:
        p.cyl(0.037, 0.004, (0, 0, 0.085), "Coffee", segs=24)
    return p.finish()


def plate(name="Plate"):
    p = Prop(name, category="pickup", interact="pickup", item="plate")
    p.add(bm_lathe([(0, 0.0), (0.06, 0.0), (0.065, 0.006), (0.12, 0.018), (0.125, 0.022), (0.118, 0.022), (0.065, 0.011), (0, 0.009)], 40),
          "Ceramic", smooth=50)
    p.add(bm_torus(0.115, 0.002, 40, 4), "PaintTeal", (0, 0, 0.0205), smooth=180)
    return p.finish()


def bunk_bed(name="BunkBed", L=2.0, W=0.8, H=1.85):
    """Two berths with mattresses, pillows, folded blankets, curtains and reading lamps (against a wall, along X)."""
    p = Prop(name, category="furniture", interact="sleep")
    y0 = -W / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((0.05, 0.05, H), (sx * (L / 2 - 0.025), y0 + sy * (W / 2 - 0.025), H / 2), "PaintGraphite", bevel=0.008)
    for zb, nm in ((0.35, "lower"), (1.2, "upper")):
        p.add(bm_plate_with_holes(rect(L, W), [rect(L - 0.1, W - 0.1)], 0.06), "PaintGraphite", (0, y0, zb - 0.06), bevel=0.006, name="frame")
        p.box((L - 0.1, W - 0.1, 0.02), (0, y0, zb - 0.04), "PaintGray", bevel=0.003)
        p.box((L - 0.12, W - 0.12, 0.14), (0, y0, zb + 0.04), "Ticking", bevel=0.04, segs=3)
        p.add(bm_box(0.36, W - 0.22, 0.1), "Pillow", (L / 2 - 0.3, y0, zb + 0.15), bevel=0.04, segs=3, name="pillow")
        p.box((0.5, W - 0.14, 0.08), (-L / 2 + 0.4, y0, zb + 0.14), "Blanket", bevel=0.03, segs=2)
        p.box((L - 0.8, W - 0.1, 0.025), (-0.1, y0, zb + 0.12), "Blanket", bevel=0.01)
        p.anchor(f"berth_{nm}", (0, y0, zb + 0.12), berth=nm)
        # privacy curtain on a rail
        p.cyl(0.008, L - 0.1, (0, -W + 0.03, zb + 0.72), "Chrome", axis="X", segs=8)
        cur = p.pivot(f"Curtain_{nm}", (L / 2 - 0.05, -W + 0.03, zb + 0.72), interact="curtain", scale_axis="X")
        pts = [(-(k / 16) * 0.55, 0.012 * math.sin(k * 1.6), 0) for k in range(17)]
        bm = bmesh.new()
        top = [bm.verts.new((x, y, -0.02)) for x, y, _ in pts]
        bot = [bm.verts.new((x, y, -0.62)) for x, y, _ in pts]
        for i in range(16):
            bm.faces.new((top[i], top[i + 1], bot[i + 1], bot[i]))
        p.add(bm, "Curtain", parent=cur, smooth=180, name="curtain")
        # reading lamp
        p.box((0.06, 0.04, 0.1), (L / 2 - 0.15, -0.02, zb + 0.5), "PaintGraphite", bevel=0.008)
        p.add(bm_lathe([(0.0, 0.0), (0.03, 0.0), (0.045, -0.06), (0.04, -0.062), (0.0, -0.05)], 20), "PaintMustard",
              (L / 2 - 0.15, -0.08, zb + 0.5), (-60, 0, 0), smooth=60)
        p.light(f"ReadingLight_{nm}", "SPOT", 8, "#ffe0b0", (L / 2 - 0.15, -0.1, zb + 0.48), (60, 0, 0), spot=70, radius=0.02)
    # ladder to the upper berth
    for sx in (-1, 1):
        p.box((0.03, 0.03, 1.3), (-L / 2 + 0.15 + sx * 0.15, -W - 0.02, 0.65), "Chrome", bevel=0.004)
    for k in range(3):
        p.cyl(0.012, 0.3, (-L / 2 + 0.15, -W - 0.02, 0.45 + k * 0.32), "Chrome", axis="X", segs=10)
    return p.finish()


def lockers(name="Lockers", n=3, w=0.42, D=0.5, H=1.9):
    p = Prop(name, category="storage")
    colors = ["PaintTeal", "PaintMustard", "PaintTeal", "PaintRed"]
    p.box((n * w + 0.02, D - 0.02, H), (0, -(D - 0.02) / 2, H / 2), "PaintGraphite", bevel=0.01)
    for k in range(n):
        x = -n * w / 2 + w / 2 + k * w
        door = p.pivot(f"Door{k + 1}", (x - w / 2 + 0.015, -D + 0.005, 0.08), interact="door", rotate_axis="Z", min_deg=-110, max_deg=0,
                       locker=k + 1)
        dw = w - 0.03
        p.box((dw, 0.02, H - 0.12), (dw / 2, -0.01, (H - 0.12) / 2), colors[k % 4], parent=door, bevel=0.006)
        for j in range(5):
            p.box((dw * 0.6, 0.004, 0.012), (dw / 2, -0.021, H - 0.35 - j * 0.03), "BlackPlastic", parent=door, bevel=0)
            p.box((dw * 0.6, 0.004, 0.012), (dw / 2, -0.021, 0.15 + j * 0.03), "BlackPlastic", parent=door, bevel=0)
        p.box((0.03, 0.03, 0.12), (dw - 0.05, -0.03, (H - 0.12) / 2), "Chrome", parent=door, bevel=0.006)
        p.box((0.1, 0.004, 0.04), (dw / 2, -0.0215, H - 0.25), "PaintCream", parent=door, bevel=0)
    return p.finish()


def coffee_station(name="CoffeeStation", W=1.1, D=0.6, H=0.9):
    """Counter with a big coffee urn (tap is a pivot), mug tree and sugar jar."""
    p = Prop(name, category="station", station="coffee")
    p.box((W, D, H - 0.04), (0, -D / 2, (H - 0.04) / 2), "PaintNavy", bevel=0.012)
    p.box((W + 0.03, D + 0.02, 0.04), (0, -D / 2, H - 0.02), "Wood", bevel=0.008)
    for k in range(2):
        x = -W / 4 + k * W / 2
        p.box((W / 2 - 0.04, 0.02, H - 0.2), (x, -D - 0.005, 0.1 + (H - 0.2) / 2), "PaintNavy", bevel=0.006)
        p.add(bm_extrude(rrect(0.1, 0.02, 0.008), 0.02), "Brass", (x, -D - 0.02, H - 0.15), (90, 0, 0), bevel=0.003)
    ux = -0.2
    urn = bm_lathe([(0, 0), (0.17, 0), (0.18, 0.02), (0.18, 0.5), (0.16, 0.55), (0.1, 0.58), (0.04, 0.6), (0.0, 0.6)], 40)
    p.add(urn, "Stainless", (ux, -0.28, H), smooth=50, name="urn")
    p.add(bm_torus(0.181, 0.008, 40, 6), "Brass", (ux, -0.28, H + 0.25), smooth=180)
    p.sphere(0.03, (ux, -0.28, H + 0.62), "Bakelite", segs=12, rings=6)
    for sx in (-1, 1):
        p.tube([(ux + sx * 0.18, -0.28, H + 0.4), (ux + sx * 0.24, -0.28, H + 0.4), (ux + sx * 0.24, -0.28, H + 0.2), (ux + sx * 0.18, -0.28, H + 0.2)],
               0.01, "Bakelite", round_r=0.03)
    p.box((0.03, 0.03, 0.3), (ux + 0.13, -0.42, H + 0.25), "Glass", bevel=0.008)  # sight glass
    p.box((0.012, 0.035, 0.2), (ux + 0.13, -0.42, H + 0.2), "Coffee", bevel=0)
    p.cyl(0.018, 0.1, (ux, -0.48, H + 0.12), "Chrome", axis="Y", segs=12)
    tap = p.pivot("Tap", (ux, -0.53, H + 0.12), interact="pour", rotate_axis="Y", min_deg=0, max_deg=90)
    p.cyl(0.02, 0.05, (0, 0, -0.02), "Chrome", segs=12, parent=tap)
    p.box((0.016, 0.02, 0.08), (0, 0, 0.04), "Bakelite", parent=tap, bevel=0.006)
    p.cyl(0.08, 0.008, (ux, -0.5, H + 0.004), "Steel", segs=24)  # drip tray
    # mug tree
    mx = 0.3
    p.cyl(0.07, 0.015, (mx, -0.3, H + 0.008), "Wood", segs=20)
    p.cyl(0.012, 0.36, (mx, -0.3, H + 0.18), "Wood", segs=10)
    for k in range(4):
        a = k * math.pi / 2
        p.tube([(mx, -0.3, H + 0.2 + k * 0.04), (mx + math.cos(a) * 0.09, -0.3 + math.sin(a) * 0.09, H + 0.25 + k * 0.04)], 0.006, "Wood")
    p.add(bm_lathe([(0, 0), (0.05, 0), (0.05, 0.11), (0.035, 0.13), (0, 0.13)], 24), "Glass", (0.45, -0.45, H), smooth=50)
    p.add(bm_lathe([(0, 0.11), (0.04, 0.11), (0.04, 0.13), (0, 0.13)], 24), "Brass", (0.45, -0.45, H), smooth=50)
    p.anchor("use", (ux, -D - 0.5, 0))
    return p.finish()


def wall_monitor(name="WallMonitor", image="screen_cam_fwd"):
    """CRT monitor on a wall bracket showing an exterior camera feed."""
    p = Prop(name, category="screen", feed=image)
    p.box((0.12, 0.03, 0.18), (0, -0.015, 0), "PaintGraphite", bevel=0.005)
    p.box((0.05, 0.22, 0.05), (0, -0.13, 0), "PaintGraphite", bevel=0.008)
    body = bm_extrude(rrect(0.5, 0.4, 0.05, 4), 0.32)
    bmesh.ops.rotate(body, verts=body.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    p.add(body, "PaintCream", (0, -0.42, 0.02), bevel=0.02, segs=2, name="tv")
    back = bm_extrude(rrect(0.34, 0.26, 0.04, 4), 0.1)
    bmesh.ops.rotate(back, verts=back.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    p.add(back, "PaintCream", (0, -0.23, 0.02), bevel=0.015, name="tvback")
    p.screen(0.38, 0.29, (0, -0.58, 0.04), image, bezel=0.02, depth=0.02)
    for k in range(2):
        knob(p, (0.21, -0.581, -0.04 - k * 0.06 + 0.06), r=0.012, name=f"Knob{k + 1}")
    return p.finish()


def notice_board(name="NoticeBoard", W=0.8, H=0.55):
    p = Prop(name, category="decor")
    p.box((W, 0.02, H), (0, -0.01, 0), "Wood", bevel=0.006)
    p.box((W - 0.06, 0.012, H - 0.06), (0, -0.022, 0), "Leather", bevel=0)
    rnd = random.Random(7)
    for k in range(7):
        x, z = rnd.uniform(-W / 2 + 0.1, W / 2 - 0.1), rnd.uniform(-H / 2 + 0.1, H / 2 - 0.1)
        w, h = rnd.uniform(0.1, 0.16), rnd.uniform(0.12, 0.2)
        p.decal(w, h, (x, -0.029 - k * 0.0004, z), rnd.choice(["PaintCream", "PaintWhite", "PaintMustard", "PaintSeafoam"]),
                rot=(0, rnd.uniform(-8, 8), 0))
        p.sphere(0.008, (x, -0.034, z + h / 2 - 0.02), rnd.choice(["PaintRed", "PaintNavy", "PaintTeal"]), segs=8, rings=4)
    return p.finish()


def checkers_board(name="CheckersBoard"):
    p = Prop(name, category="pickup", interact="game")
    p.box((0.34, 0.34, 0.02), (0, 0, 0.01), "Wood", bevel=0.004)
    for i in range(8):
        for j in range(8):
            p.box((0.0375, 0.0375, 0.003), (-0.13125 + i * 0.0375, -0.13125 + j * 0.0375, 0.0215),
                  "EnamelCream" if (i + j) % 2 else "PaintTeal", bevel=0, name="sq")
    rnd = random.Random(4)
    for k in range(14):
        i, j = rnd.randrange(8), rnd.randrange(8)
        if (i + j) % 2:
            continue
        p.cyl(0.015, 0.008, (-0.13125 + i * 0.0375, -0.13125 + j * 0.0375, 0.027), "PaintRed" if k % 2 else "BlackPlastic",
              segs=16, bevel=0.002)
    return p.finish()
