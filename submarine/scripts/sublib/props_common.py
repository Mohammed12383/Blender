"""Shared props and sub-assemblies used across all compartments.

Facing convention: a prop's front faces -Y (the player stands on the -Y side).
Wall props have their back on the y=0 plane. Ceiling props hang from z=0 downwards.
"""

import math

from mathutils import Euler, Vector

from .core import (Prop, R, bm_box, bm_cyl, bm_extrude, bm_lathe, bm_plate_with_holes, bm_sweep, bm_torus,
                   circle, rrect, rect, rounded_path, sag_path, bm_disc, bm_sphere)
import bmesh
from mathutils import Matrix


def _rot(v, rot):
    v = Vector(v)
    v.rotate(Euler([R(a) for a in rot]))
    return v


# ------------------------------------------------------- sub-assemblies

def handwheel(p, loc, rot=(0, 0, 0), r=0.12, parent=None, m="PaintRed", name="Wheel", spokes=4, **extras):
    """Valve/door handwheel spinning about its local Y axis."""
    piv = p.pivot(name, loc, rot, parent, interact=extras.pop("interact", "valve_wheel"), rotate_axis="Y", **extras)
    p.torus(r, r * 0.12, (0, 0, 0), m, axis="Y", segs=32, rsegs=10, parent=piv)
    p.cyl(r * 0.22, r * 0.35, (0, 0, 0), m, axis="Y", segs=16, bevel=0.004, parent=piv)
    for k in range(spokes):
        a = 2 * math.pi * k / spokes + math.pi / 4
        p.tube([(math.cos(a) * r * 0.18, 0, math.sin(a) * r * 0.18), (math.cos(a) * r * 0.95, 0, math.sin(a) * r * 0.95)],
               r * 0.06, m, segs=8, parent=piv)
    p.cyl(r * 0.1, r * 0.4, (0, -r * 0.12, 0), "Steel", axis="Y", segs=12, parent=piv)
    return piv


def gauge(p, loc, rot=(0, 0, 0), r=0.08, face="gauge_pressure", parent=None, name="Gauge", needle_deg=-30):
    """Round dial gauge with brass bezel; needle is a pivot rotating about local Y."""
    p.cyl(r * 1.02, 0.045, _v(loc, rot, (0, 0.0225, 0)), "PaintGraphite", rot=rot, axis="Y", segs=32, bevel=0.006, parent=parent, name="gaugecup")
    p.add(bm_torus(r, r * 0.12, 32, 8, "Y"), "Brass", _v(loc, rot, (0, -0.002, 0)), rot, parent, smooth=180, name="bezel")
    p.add(bm_disc(r * 0.95, 40), face, _v(loc, rot, (0, -0.001, 0)), rot, parent, uv="keep", smooth=False, name="face")
    piv = p.pivot(name + "Needle", _v(loc, rot, (0, -0.006, 0)), (rot[0], rot[1] + needle_deg, rot[2]), parent,
                  interact="gauge_needle", rotate_axis="Y", note="0 deg = straight up; dial spans -135..+135")
    p.extrude([(-r * 0.03, 0), (r * 0.03, 0), (r * 0.008, r * 0.8), (-r * 0.008, r * 0.8)], 0.003, (0, 0, 0), "PaintRed",
              rot=(90, 0, 0), parent=piv, name="needle")
    p.cyl(r * 0.09, 0.006, (0, -0.002, 0), "BlackPlastic", axis="Y", segs=12, parent=piv)
    return piv


def _v(loc, rot, off):
    return Vector(loc) + _rot(off, rot)


def indicator(p, loc, rot=(0, 0, 0), m="LampGreen", r=0.018, parent=None, name="lamp"):
    p.cyl(r * 1.4, 0.015, _v(loc, rot, (0, 0.002, 0)), "Chrome", rot=rot, axis="Y", segs=16, bevel=0.002, parent=parent, name="lampcollar")
    p.add(bm_sphere(r, 16, 8, (1, 0.7, 1)), m, _v(loc, rot, (0, -0.008, 0)), rot, parent, smooth=180, name=name)


def push_button(p, loc, rot=(0, 0, 0), m="PaintRed", r=0.025, parent=None, name="Button", **extras):
    p.cyl(r * 1.35, 0.012, _v(loc, rot, (0, 0.002, 0)), "Chrome", rot=rot, axis="Y", segs=20, bevel=0.002, parent=parent, name="btncollar")
    piv = p.pivot(name, _v(loc, rot, (0, -0.006, 0)), rot, parent, interact=extras.pop("interact", "button"),
                  translate_axis="Y", travel=0.006, **extras)
    p.add(bm_lathe([(0, -0.022), (r, -0.022), (r, -0.006), (r * 0.8, 0.0), (0, 0.002)], 24, "Y"), m, (0, 0, 0),
          (0, 0, 0), piv, smooth=50, name="cap")
    return piv


def toggle(p, loc, rot=(0, 0, 0), parent=None, name="Toggle", up=True):
    p.cyl(0.012, 0.01, _v(loc, rot, (0, 0, 0)), "Chrome", rot=rot, axis="Y", segs=6, parent=parent, name="nut")
    piv = p.pivot(name, _v(loc, rot, (0, -0.006, 0)), (rot[0] + (-25 if up else 25), rot[1], rot[2]), parent,
                  interact="toggle", rotate_axis="X", min_deg=-25, max_deg=25)
    p.cyl(0.004, 0.045, (0, -0.022, 0), "Chrome", axis="Y", segs=8, parent=piv)
    p.sphere(0.006, (0, -0.045, 0), "BlackPlastic", parent=piv, segs=10, rings=6)
    return piv


def knob(p, loc, rot=(0, 0, 0), r=0.03, parent=None, name="Knob", m="Bakelite", **extras):
    piv = p.pivot(name, loc, rot, parent, interact=extras.pop("interact", "knob"), rotate_axis="Y", **extras)
    p.add(bm_lathe([(0, 0.0), (r, 0.0), (r * 0.95, -0.02), (r * 0.7, -0.035), (0, -0.036)], 20, "Y"), m,
          (0, 0, 0), (0, 0, 0), piv, smooth=40, name="knob")
    p.box((0.004, 0.004, r * 0.8), (0, -0.036, r * 0.35), "PaintWhite", parent=piv, bevel=0)
    return piv


def louver(p, loc, rot=(0, 0, 0), w=0.4, h=0.25, n=6, parent=None, m="PaintGraphite"):
    """Vent with angled slats in a frame (on a -Y facing surface)."""
    p.add(bm_plate_with_holes(rect(w, h), [rect(w - 0.03, h - 0.03)], 0.012), m,
          _v(loc, rot, (0, 0, 0)), (rot[0] + 90, rot[1], rot[2]), parent, name="louverframe")
    for k in range(n):
        z = -h / 2 + 0.02 + (h - 0.04) * (k + 0.5) / n
        p.box((w - 0.03, 0.004, (h - 0.04) / n * 1.1), _v(loc, rot, (0, 0.004, z)), "DarkSteel",
              rot=(rot[0] + 40, rot[1], rot[2]), bevel=0, parent=parent, name="slat")
    p.box((w - 0.03, 0.002, h - 0.03), _v(loc, rot, (0, 0.012, 0)), "BlackPlastic", rot=rot, bevel=0, parent=parent)


def slots(p, loc, rot=(0, 0, 0), w=0.15, h=0.1, n=5, parent=None):
    """Speaker grille slots."""
    for k in range(n):
        z = -h / 2 + h * (k + 0.5) / n
        p.box((w, 0.006, h / n * 0.45), _v(loc, rot, (0, -0.001, z)), "BlackPlastic", rot=rot, bevel=0.002, parent=parent, name="slot")


def grab_rail(p, a, b, standoff=0.06, r=0.016, parent=None, m="Chrome", axis_out=(0, -1, 0)):
    """U-shaped grab handle between two mount points, standing off along axis_out."""
    a, b, o = Vector(a), Vector(b), Vector(axis_out) * standoff
    p.tube(rounded_path([a, a + o, b + o, b], standoff * 0.6, 6), r, m, segs=12, parent=parent, name="rail")
    for q in (a, b):
        p.cyl(r * 2.0, 0.012, q, m, rot=(0, 0, 0), axis="Y", segs=12, parent=parent, name="railfoot")


# ----------------------------------------------------------------- props

def bulkhead_lamp(name="CeilingLamp", glow="LightWarm", energy=130, color="#ffe7c2"):
    """Caged ceiling lamp; origin at the ceiling mount, hangs down -Z."""
    p = Prop(name, category="light")
    p.cyl(0.11, 0.035, (0, 0, -0.0175), "PaintCream", segs=32, bevel=0.008)
    p.cyl(0.09, 0.02, (0, 0, -0.045), "PaintGraphite", segs=32, bevel=0.004)
    p.sphere(0.075, (0, 0, -0.12), glow, scale=(1, 1, 1.15), segs=24, rings=12)
    for z in (-0.09, -0.15):
        rr = 0.083 if z == -0.09 else 0.08
        p.torus(rr, 0.005, (0, 0, z), "PaintGraphite", segs=32, rsegs=6)
    for k in range(6):
        a = 2 * math.pi * k / 6
        pts = [(math.cos(a) * 0.088 * math.cos(t), math.sin(a) * 0.088 * math.cos(t), -0.12 - 0.095 * math.sin(t))
               for t in [i / 8 * math.pi / 2 for i in range(9)]]
        pts = [(math.cos(a) * 0.088, math.sin(a) * 0.088, -0.05)] + pts
        p.tube(pts, 0.004, "PaintGraphite", segs=6)
    p.cyl(0.012, 0.012, (0, 0, -0.218), "PaintGraphite", segs=12)
    p.light("Light", "POINT", energy, color, (0, 0, -0.26), radius=0.05)
    return p.finish()


def alarm_beacon(name="AlarmBeacon"):
    """Wall-mounted rotating red beacon (bracket on wall, dome up). Reflector spins about Z."""
    p = Prop(name, category="light", note="animate Reflector spin + light for battle stations")
    p.box((0.16, 0.012, 0.12), (0, -0.006, 0), "PaintGraphite", bevel=0.004)
    p.box((0.05, 0.14, 0.02), (0, -0.07, -0.03), "PaintGraphite", bevel=0.004)
    p.cyl(0.075, 0.05, (0, -0.15, -0.015), "PaintGraphite", segs=32, bevel=0.006)
    p.add(bm_lathe([(0.068, 0.0), (0.068, 0.07), (0.055, 0.11), (0.03, 0.13), (0, 0.135)], 32), "LampRed",
          (0, -0.15, 0.01), smooth=60)
    piv = p.pivot("Reflector", (0, -0.15, 0.04), interact="spin", rotate_axis="Z")
    p.box((0.09, 0.006, 0.05), (0, 0, 0), "Chrome", parent=piv, bevel=0.002)
    p.light("Light", "POINT", 25, "#ff2a1a", (0, -0.15, 0.06), radius=0.05)
    return p.finish()


def pendant_lamp(name="PendantLamp", drop=0.55):
    """Enamel dome lamp on a cord; origin at ceiling."""
    p = Prop(name, category="light")
    p.cyl(0.06, 0.03, (0, 0, -0.015), "EnamelCream", segs=24, bevel=0.006)
    p.cyl(0.006, drop, (0, 0, -drop / 2), "BlackPlastic", segs=8)
    z = -drop
    p.cyl(0.03, 0.06, (0, 0, z - 0.02), "Brass", segs=16, bevel=0.004)
    outer = [(0.03, z), (0.06, z - 0.01), (0.14, z - 0.06), (0.22, z - 0.15), (0.25, z - 0.2), (0.255, z - 0.21)]
    inner = [(0.25, z - 0.205), (0.215, z - 0.15), (0.135, z - 0.065), (0.055, z - 0.018), (0.03, z - 0.012)]
    bm = bm_lathe(outer + inner, 48)
    p.add(bm, "PaintTeal", smooth=60, name="shade_out")
    p.add(bm_lathe([(0.248, z - 0.204), (0.214, z - 0.15), (0.134, z - 0.066), (0.054, z - 0.02), (0.0, z - 0.02)], 48),
          "EnamelCream", smooth=60, name="shade_in")
    p.sphere(0.045, (0, 0, z - 0.1), "LightWarm", scale=(1, 1, 1.2), segs=20, rings=10)
    p.light("Light", "POINT", 120, "#ffdcae", (0, 0, z - 0.19), radius=0.04)
    return p.finish()


def loudspeaker(name="Loudspeaker"):
    """Horn speaker on a wall bracket; origin on the wall, horn points -Y and down."""
    p = Prop(name, category="decor")
    p.box((0.1, 0.012, 0.14), (0, -0.006, 0), "PaintGraphite", bevel=0.004)
    p.tube([(0, -0.012, 0), (0, -0.12, 0), (0, -0.16, -0.04)], 0.012, "PaintGraphite", round_r=0.04)
    horn = bm_lathe([(0.0, -0.12), (0.045, -0.12), (0.05, -0.05), (0.06, 0.0), (0.09, 0.08), (0.14, 0.15),
                     (0.15, 0.16), (0.13, 0.155), (0.08, 0.08), (0.05, 0.0)], 36)
    p.add(horn, "PaintCream", (0, -0.2, -0.06), (110, 0, 0), smooth=60, name="horn")
    return p.finish()


def junction_box(name="JunctionBox", w=0.28, h=0.22, d=0.1):
    p = Prop(name, category="decor")
    p.box((w, d, h), (0, -d / 2, 0), "PaintGray", bevel=0.01, segs=2)
    p.box((w - 0.02, 0.012, h - 0.02), (0, -d - 0.006, 0), "PaintGray", bevel=0.004)
    p.bolts([(sx * (w / 2 - 0.025), -d - 0.013, sz * (h / 2 - 0.025)) for sx in (-1, 1) for sz in (-1, 1)])
    for x in (-w / 4, w / 4):
        p.cyl(0.018, 0.08, (x, -d / 2, h / 2 + 0.03), "DarkSteel", segs=12)
        p.cyl(0.024, 0.02, (x, -d / 2, h / 2 + 0.01), "Brass", segs=6)
    p.decal(0.09, 0.112, (0, -d - 0.0135, 0), "sign_voltage")
    return p.finish()


def fire_extinguisher(name="FireExtinguisher"):
    """Wall-mounted extinguisher; origin on the wall at the bottom of the cylinder."""
    p = Prop(name, category="pickup", interact="pickup")
    body = bm_lathe([(0, 0), (0.07, 0.0), (0.078, 0.015), (0.078, 0.43), (0.065, 0.48), (0.03, 0.5), (0, 0.5)], 32)
    p.add(body, "EnamelRed", (0, -0.1, 0.02), smooth=60)
    p.box((0.06, 0.003, 0.12), (0, -0.181, 0.28), "PaintWhite", bevel=0)
    p.cyl(0.02, 0.05, (0, -0.1, 0.545), "BlackPlastic", segs=16)
    p.box((0.03, 0.12, 0.02), (0, -0.12, 0.58), "Chrome", bevel=0.005)
    p.box((0.025, 0.1, 0.012), (0, -0.13, 0.6), "PaintRed", rot=(12, 0, 0), bevel=0.004)
    p.tube(rounded_path([(0.0, -0.08, 0.56), (0.06, -0.07, 0.5), (0.085, -0.06, 0.3), (0.06, -0.08, 0.15)], 0.05), 0.009, "Rubber", segs=8)
    p.cyl(0.013, 0.06, (0.06, -0.085, 0.12), "BlackPlastic", segs=12)
    p.box((0.12, 0.01, 0.3), (0, -0.005, 0.25), "PaintGraphite", bevel=0.003)
    p.add(bm_torus(0.083, 0.006, 32, 6), "PaintGraphite", (0, -0.1, 0.32), smooth=180)
    return p.finish()


def ship_clock(name="ShipClock", r=0.15):
    p = Prop(name, category="decor", note="Hour/Minute/Second hands rotate about Y")
    p.cyl(r, 0.06, (0, -0.03, 0), "Brass", axis="Y", segs=48, bevel=0.01)
    p.add(bm_torus(r, 0.014, 48, 10, "Y"), "Brass", (0, -0.065, 0), smooth=180)
    p.add(bm_disc(r * 0.92, 48), "gauge_clock", (0, -0.0605, 0), uv="keep", smooth=False)
    for nm, L, wdt, ang, m in [("HourHand", 0.07, 0.012, 300, "PaintGraphite"), ("MinuteHand", 0.11, 0.008, 60, "PaintGraphite"),
                               ("SecondHand", 0.12, 0.003, 150, "PaintRed")]:
        piv = p.pivot(nm, (0, -0.064 - 0.002 * len(nm) / 10, 0), (0, ang, 0), interact="clock_hand", rotate_axis="Y")
        p.extrude([(-wdt, -0.015), (wdt, -0.015), (wdt * 0.5, L), (-wdt * 0.5, L)], 0.002, (0, 0, 0), m, rot=(90, 0, 0), parent=piv)
    p.cyl(0.008, 0.012, (0, -0.07, 0), "Brass", axis="Y", segs=12)
    return p.finish()


def intercom(name="Intercom"):
    p = Prop(name, category="station", interact="intercom")
    p.box((0.2, 0.07, 0.28), (0, -0.035, 0), "PaintCream", bevel=0.012, segs=3)
    slots(p, (0, -0.071, 0.05), w=0.14, h=0.12, n=7)
    push_button(p, (-0.04, -0.07, -0.08), m="PaintRed", r=0.02, name="TalkButton", interact="intercom_talk")
    indicator(p, (0.05, -0.07, -0.08), m="LampGreen", r=0.012)
    p.add(bm_extrude(rrect(0.05, 0.11, 0.02), 0.03), "BlackPlastic", (0.12, -0.04, -0.02), (90, 0, 0), bevel=0.008)
    p.tube(sag_path((0.12, -0.04, -0.075), (0.06, -0.06, -0.14), 0.05, 10), 0.004, "BlackPlastic", segs=6)
    return p.finish()


def electrical_cabinet(name="ElectricalCabinet", w=0.8, h=1.95, d=0.45, variant="gauges", m="PaintSeafoam"):
    """Floor-standing equipment cabinet against a wall; front door hinged on the left."""
    p = Prop(name, category="decor")
    p.box((w, d - 0.02, h), (0, -(d - 0.02) / 2, h / 2), m, bevel=0.015, segs=2)
    p.box((w + 0.02, d, 0.08), (0, -d / 2, 0.04), "PaintGraphite", bevel=0.008)
    p.box((w + 0.02, d + 0.01, 0.04), (0, -d / 2, h - 0.02), "PaintGraphite", bevel=0.008)
    louver(p, (0, -d - 0.002, h - 0.2), w=w * 0.75, h=0.2, n=6)
    louver(p, (0, -d - 0.002, 0.25), w=w * 0.75, h=0.16, n=5)
    door = p.pivot("Door", (-w / 2 + 0.03, -d, 0.5), interact="door", rotate_axis="Z", min_deg=-110, max_deg=0)
    dw, dh = w - 0.08, h - 0.95
    p.box((dw, 0.025, dh), (dw / 2 + 0.01, -0.0125, dh / 2), m, parent=door, bevel=0.008)
    for zz in (0.12, dh - 0.12):
        p.cyl(0.012, 0.08, (0, -0.005, zz), "Chrome", parent=door, segs=12)
    p.add(bm_extrude(rrect(0.03, 0.14, 0.012), 0.025), "Chrome", (dw - 0.04, -0.04, dh / 2), (90, 0, 0), parent=door, bevel=0.004)
    if variant == "gauges":
        gauge(p, (dw * 0.3, -0.026, dh - 0.2), r=0.075, face="gauge_pressure", parent=door, name="GaugeA", needle_deg=-40)
        gauge(p, (dw * 0.72, -0.026, dh - 0.2), r=0.075, face="gauge_air", parent=door, name="GaugeB", needle_deg=20)
        for k in range(5):
            toggle(p, (0.1 + k * (dw - 0.2) / 4, -0.026, dh - 0.42), parent=door, name=f"Switch{k + 1}", up=k % 2 == 0)
        for k, lm in enumerate(["LampGreen", "LampGreen", "LampAmber", "LampOff", "LampRed"]):
            indicator(p, (0.1 + k * (dw - 0.2) / 4, -0.026, dh - 0.52), m=lm, r=0.013, parent=door)
        p.decal(0.16, 0.2, (dw / 2, -0.0265, 0.25), "sign_voltage", parent=door)
    else:
        for k in range(4):
            p.box((dw - 0.1, 0.015, 0.012), (dw / 2, -0.03, 0.15 + k * 0.17), "PaintGraphite", parent=door, bevel=0.003)
        for k in range(8):
            indicator(p, (0.08 + (k % 4) * (dw - 0.16) / 3, -0.026, dh - 0.12 - (k // 4) * 0.1),
                      m=["LampGreen", "LampAmber", "LampGreen", "LampRed"][k % 4], r=0.012, parent=door)
    p.tube([(w / 2 - 0.08, -0.1, h), (w / 2 - 0.08, -0.1, h + 0.6)], 0.025, "DarkSteel", segs=12)
    return p.finish()


def watertight_door(name="WatertightDoor", w=0.9, h=1.8, sill=0.12, corner=0.4, depth=0.42, frame_m="PaintTeal"):
    """Oval watertight door: frame (fits a bulkhead hole of (w+0.1)x(h+0.1)) + hinged leaf.

    Local frame: the bulkhead plane is XZ (y=0); the leaf sits on the -Y side, hinged at -X.
    Origin at floor level in the middle of the opening.
    """
    p = Prop(name, category="door", interact="door")
    cz = sill + h / 2
    outer = rrect(w + 0.26, h + 0.26, corner + 0.13, 8)
    inner = rrect(w, h, corner, 8)
    fr = bm_plate_with_holes(outer, [inner], depth)
    bmesh.ops.rotate(fr, verts=fr.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    bmesh.ops.translate(fr, verts=fr.verts, vec=(0, depth / 2, cz))
    p.add(fr, frame_m, bevel=0.01, segs=2, name="frame")
    # dogs (locking wedges) on both faces
    for side in (-1, 1):
        for a in (30, 90, 150, 210, 270, 330):
            ar = R(a)
            x, z = math.cos(ar) * (w / 2 + 0.07), cz + math.sin(ar) * (h / 2 + 0.07) * 0.98
            p.box((0.05, 0.03, 0.05), (x, side * (depth / 2 + 0.012), z), "DarkSteel", bevel=0.006)
    # hazard sill
    p.box((w * 0.8, depth - 0.02, 0.006), (0, 0, sill + 0.003), "Hazard", bevel=0)
    # hinge knuckles
    hx = -w / 2 - 0.1
    for zz in (cz - h * 0.3, cz + h * 0.3):
        p.cyl(0.03, 0.14, (hx, -depth / 2 - 0.05, zz), "DarkSteel", segs=16, bevel=0.004)
        p.box((0.1, 0.06, 0.1), (hx + 0.02, -depth / 2 - 0.02, zz), "DarkSteel", bevel=0.006)
    # leaf (pivot on hinge axis)
    leaf = p.pivot("Leaf", (hx, -depth / 2 - 0.05, 0), interact="door", rotate_axis="Z", min_deg=-105, max_deg=0,
                   open_dir="towards -Y")
    lw, lh = w + 0.16, h + 0.16
    shape = rrect(lw, lh, corner + 0.08, 8)
    lb = bm_extrude(shape, 0.06)
    bmesh.ops.rotate(lb, verts=lb.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    p.add(lb, frame_m, (-hx, -0.015, cz), bevel=0.012, segs=2, parent=leaf, name="leaf")
    gs = bm_sweep([Vector((x, 0, z)) for x, z in rrect(lw - 0.03, lh - 0.03, corner + 0.07, 8)] , circle(0.012, 6),
                  caps=False, closed_path=True)
    p.add(gs, "Rubber", (-hx, 0.018, cz), parent=leaf, smooth=70, name="gasket")
    for zz in (-0.45, 0, 0.45):
        p.box((lw - 0.3, 0.03, 0.05), (-hx, -0.06, cz + zz), frame_m, parent=leaf, bevel=0.01)
    p.box((0.05, 0.03, lh - 0.4), (-hx, -0.06, cz), frame_m, parent=leaf, bevel=0.01)
    handwheel(p, (-hx, -0.12, cz), r=0.16, parent=leaf, name="WheelFront", interact="door_lock")
    handwheel(p, (-hx, 0.09, cz), rot=(0, 0, 180), r=0.16, parent=leaf, name="WheelBack", interact="door_lock")
    p.cyl(0.03, 0.1, (-hx, 0.04, cz), "Steel", axis="Y", segs=16, parent=leaf)
    p.cyl(0.03, 0.12, (-hx, -0.05, cz), "Steel", axis="Y", segs=16, parent=leaf)
    p.hand("L", (-hx - 0.12, -0.13, cz), "grip", parent=leaf, control="WheelFront")
    p.hand("R", (-hx + 0.12, -0.13, cz), "grip", parent=leaf, control="WheelFront")
    p.anchor("open_front", (0, -0.9, 0), (0, 0, 0))
    p.anchor("open_back", (0, 0.9, 0), (0, 0, 180))
    return p.finish()


def ladder(name="Ladder", height=2.9, width=0.5, standoff=0.18):
    p = Prop(name, category="ladder", interact="climb")
    for x in (-width / 2, width / 2):
        p.box((0.05, 0.03, height), (x, -standoff, height / 2), "PaintMustard", bevel=0.008)
        for z in (0.4, height - 0.3):
            p.box((0.04, standoff, 0.04), (x, -standoff / 2, z), "PaintGraphite", bevel=0.006)
            p.box((0.1, 0.01, 0.1), (x, -0.005, z), "PaintGraphite", bevel=0.003)
    n = int((height - 0.2) / 0.3)
    for k in range(n):
        p.cyl(0.016, width, (0, -standoff, 0.3 + k * 0.3), "Steel", axis="X", segs=12)
    p.anchor("climb", (0, -standoff - 0.45, 0))
    return p.finish()


def stool(name="Stool", height=0.62, m="Leather"):
    p = Prop(name, category="seat", interact="sit")
    p.cyl(0.16, 0.012, (0, 0, 0.006), "PaintGraphite", segs=32, bevel=0.004)
    p.bolts([(math.cos(a) * 0.12, math.sin(a) * 0.12, 0.014) for a in [k * math.pi / 2 + 0.6 for k in range(4)]], axis="Z", r=0.01)
    p.cyl(0.03, height - 0.08, (0, 0, (height - 0.08) / 2), "Chrome", segs=16)
    p.add(bm_torus(0.15, 0.011, 32, 8), "Chrome", (0, 0, 0.28), smooth=180)
    for a in range(4):
        ar = a * math.pi / 2
        p.tube([(0, 0, 0.24), (math.cos(ar) * 0.15, math.sin(ar) * 0.15, 0.28)], 0.008, "Chrome", segs=8)
    p.cyl(0.13, 0.03, (0, 0, height - 0.085), "PaintGraphite", segs=32, bevel=0.006)
    cushion = bm_lathe([(0, height - 0.07), (0.17, height - 0.07), (0.185, height - 0.05), (0.185, height - 0.01),
                        (0.17, height + 0.005), (0.09, height + 0.012), (0.0, height + 0.006)], 40)
    p.add(cushion, m, smooth=60, name="cushion")
    for k in range(6):
        a = k * math.pi / 3
        p.sphere(0.008, (math.cos(a) * 0.09, math.sin(a) * 0.09, height + 0.008), "Brass", segs=8, rings=4)
    p.sphere(0.008, (0, 0, height + 0.006), "Brass", segs=8, rings=4)
    return p.finish()


def poster(image, name=None, w=0.45, h=0.6):
    """Paper poster with tape corners; origin at its centre on the wall."""
    p = Prop(name or ("Poster_" + image.replace("poster_", "").title()), category="decor")
    p.decal(w, h, (0, -0.002, 0), image)
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.decal(0.07, 0.025, (sx * (w / 2 - 0.01), -0.003, sz * (h / 2 - 0.01)), "PaintCream",
                    rot=(0, sx * sz * 40, 0))
    return p.finish()


def sign(image, name=None, w=0.25, h=0.31):
    p = Prop(name or ("Sign_" + image.replace("sign_", "").title()), category="decor")
    p.box((w + 0.012, 0.006, h + 0.012), (0, -0.003, 0), "PaintWhite", bevel=0.002)
    p.decal(w, h, (0, -0.0065, 0), image)
    p.bolts([(sx * (w / 2 - 0.012), -0.008, sz * (h / 2 - 0.012)) for sx in (-1, 1) for sz in (-1, 1)], r=0.005, h=0.004)
    return p.finish()


def room_sign(image, name=None, w=0.7, h=0.13):
    p = Prop(name or ("RoomSign_" + image.replace("label_", "").title()), category="decor")
    p.plate(w, h, (0, -0.008, 0), image, frame="PaintGraphite", depth=0.014)
    return p.finish()


def toolbox(name="Toolbox"):
    p = Prop(name, category="pickup", interact="pickup")
    p.box((0.5, 0.22, 0.2), (0, 0, 0.1), "PaintRed", bevel=0.01)
    lid = p.pivot("Lid", (0, 0.11, 0.2), interact="lid", rotate_axis="X", min_deg=0, max_deg=110)
    p.box((0.5, 0.22, 0.04), (0, -0.11, 0.02), "PaintRed", parent=lid, bevel=0.01)
    p.tube([(-0.15, -0.11, 0.04), (-0.15, -0.11, 0.1), (0.15, -0.11, 0.1), (0.15, -0.11, 0.04)], 0.01, "Chrome",
           round_r=0.03, parent=lid)
    for x in (-0.2, 0.2):
        p.box((0.04, 0.01, 0.05), (x, -0.112, 0.19), "Chrome", bevel=0.003)
    return p.finish()


def crate(name="SupplyCrate", w=0.7, d=0.5, h=0.45, m="PaintOlive", label="FOOD"):
    p = Prop(name, category="decor")
    p.box((w, d, h), (0, 0, h / 2), m, bevel=0.012)
    for x in (-w / 2 + 0.03, w / 2 - 0.03):
        p.box((0.04, d + 0.012, h + 0.012), (x, 0, h / 2), "PaintGraphite", bevel=0.006)
    for side in (-1, 1):
        p.box((0.16, 0.02, 0.04), (0, side * (d / 2 + 0.01), h * 0.75), "DarkSteel", bevel=0.006)
    return p.finish()


def air_tanks(name="AirTanks", n=3):
    """Vertical compressed-air bottles in a wall rack with a manifold."""
    p = Prop(name, category="decor")
    for k in range(n):
        x = (k - (n - 1) / 2) * 0.28
        body = bm_lathe([(0, 0.05), (0.1, 0.05), (0.12, 0.09), (0.12, 1.25), (0.09, 1.36), (0.035, 1.4), (0.0, 1.4)], 32)
        p.add(body, "PaintMustard", (x, -0.16, 0), smooth=60)
        p.cyl(0.03, 0.08, (x, -0.16, 1.43), "Brass", segs=12)
        handwheel(p, (x, -0.16, 1.5), rot=(90, 0, 0), r=0.04, name=f"Valve{k + 1}", m="PaintGraphite")
        p.tube([(x, -0.16, 1.47), (x, -0.16, 1.62), (x, -0.06, 1.62)], 0.012, "Copper", round_r=0.04)
        for z in (0.35, 1.05):
            p.add(bm_torus(0.125, 0.012, 32, 6), "PaintGraphite", (x, -0.16, z), smooth=180)
    p.tube([(-0.5, -0.06, 1.62), (0.5, -0.06, 1.62)], 0.02, "Copper")
    for z in (0.35, 1.05):
        p.box((n * 0.28 + 0.1, 0.04, 0.05), (0, -0.02, z), "PaintGraphite", bevel=0.006)
    gauge(p, (0.55, -0.08, 1.62), r=0.06, face="gauge_air", name="Gauge", needle_deg=30)
    return p.finish()


def pipe_riser(name="PipeRiser", height=2.9, r=0.05, m="PaintRed"):
    """Vertical pipe in a corner with a gate valve, a tee + gauge and wall clamps (back on y=0)."""
    p = Prop(name, category="station", station="valve")
    y = -0.12
    p.cyl(r, height, (0, y, height / 2), m, segs=16)
    for z in (0.05, height - 0.05):
        p.cyl(r * 1.8, 0.04, (0, y, z), m, segs=20, bevel=0.005)
    for z in (0.5, 1.9, 2.55):
        p.add(bm_torus(r + 0.008, 0.008, 20, 6), "DarkSteel", (0, y, z), smooth=180)
        p.box((0.03, abs(y) - r, 0.02), (0, y / 2 - r / 2 + 0.0, z), "DarkSteel", bevel=0.004)
        p.box((0.1, 0.012, 0.06), (0, -0.006, z), "DarkSteel", bevel=0.003)
    # gate valve body
    p.cyl(r * 1.9, 0.04, (0, y, 1.08), m, segs=20, bevel=0.005)
    p.cyl(r * 1.9, 0.04, (0, y, 1.32), m, segs=20, bevel=0.005)
    p.add(bm_sphere(r * 1.7, 20, 10, (1, 1, 1.3)), m, (0, y, 1.2), smooth=180)
    p.cyl(0.02, 0.2, (0, y - 0.15, 1.2), "Steel", axis="Y", segs=10)
    handwheel(p, (0, y - 0.26, 1.2), r=0.1, name="Valve", interact="valve_wheel", m="PaintMustard")
    p.cyl(r * 0.7, 0.12, (0.09, y, 1.65), m, axis="X", segs=12)
    gauge(p, (0.17, y, 1.65), rot=(0, 0, 0), r=0.055, face="gauge_pressure", name="Gauge", needle_deg=25)
    p.box((0.18, 0.003, 0.04), (0, y - r - 0.002, 0.8), "PaintWhite", bevel=0)
    p.anchor("operate", (0, -0.75, 0))
    return p.finish()


def floor_hatch(name="FloorHatch", w=0.7):
    """Bilge access plate flush with the deck: bevelled lid (pivot on one edge) with lift rings."""
    p = Prop(name, category="door", interact="hatch")
    p.add(bm_plate_with_holes(rect(w + 0.08, w + 0.08), [rect(w + 0.005, w + 0.005)], 0.006), "PaintGraphite",
          (0, 0, 0.0), bevel=0.002, name="frame")
    lid = p.pivot("Lid", (-w / 2, 0, 0.006), interact="hatch", rotate_axis="Y", min_deg=-100, max_deg=0)
    p.box((w, w, 0.008), (w / 2, 0, -0.002), "FloorPlate", parent=lid, bevel=0.002)
    for dy in (-w / 4, w / 4):
        p.box((0.1, 0.04, 0.003), (w - 0.1, dy, 0.003), "DarkSteel", parent=lid, bevel=0)
        p.add(bm_torus(0.03, 0.005, 16, 6, "Y", angle=math.pi), "Steel", (w - 0.1, dy, 0.0035), (0, 0, 0), parent=lid,
              smooth=180)
    p.bolts([(sx * (w / 2 + 0.02), sy * (w / 2 + 0.02), 0.007) for sx in (-1, 1) for sy in (-1, 1)], axis="Z", r=0.01, h=0.004)
    p.box((w * 0.6, 0.004, 0.0015), (w / 2, w / 2 - 0.06, 0.003), "Hazard", parent=lid, bevel=0)
    return p.finish()


def cable_bundle(name="CableBundle", span=1.6, sag=0.35, n=5):
    """A loom of cables slung between two deckhead hangers, sagging in the middle (along X, hangers at z=0)."""
    p = Prop(name, category="decor")
    for sx in (-1, 1):
        p.box((0.06, 0.16, 0.08), (sx * span / 2, 0, -0.04), "DarkSteel", bevel=0.01)
    mats = ["BlackPlastic", "PaintNavy", "BlackPlastic", "PaintRed", "BlackPlastic", "PaintMustard", "BlackPlastic"]
    for k in range(n):
        dy = (k - (n - 1) / 2) * 0.026
        sg = sag * (0.75 + 0.5 * ((k * 37) % 10) / 10)
        pts = [(sx * span / 2 * t, dy, -0.08 - sg * (1 - t * t)) for t in [i / 8 for i in range(-8, 9)] for sx in (1,)]
        p.tube(pts, 0.011, mats[k % len(mats)], segs=8)
    return p.finish()
