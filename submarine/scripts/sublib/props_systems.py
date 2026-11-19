"""Ship systems: bilge hand pump, smoke-extract panel, ceiling exhaust fans, battery banks,
main switchboard, and the medical bay (cabinet, bed, first-aid kit).

Wall props have their back on y=0 and face -Y.
"""

import math
import random

import bmesh
from mathutils import Matrix, Vector

from .core import Prop, R, bm_box, bm_cyl, bm_disc, bm_extrude, bm_lathe, bm_plate_with_holes, bm_sphere, bm_torus, rect, rrect, sag_path
from .props_common import gauge, indicator, louver, push_button, toggle


def bilge_pump(name="BilgePump"):
    """Wall-mounted hand bilge pump. Pump the lever up and down to lift flood water out of the room."""
    p = Prop(name, category="station", station="bilge")
    y = -0.22
    p.box((0.3, 0.02, 1.1), (0, -0.01, 0.75), "PaintGraphite", bevel=0.004)
    for z in (0.35, 0.85):
        p.box((0.06, 0.2, 0.06), (0, -0.11, z), "DarkSteel", bevel=0.008)
    body = bm_lathe([(0.0, 0.0), (0.08, 0.0), (0.09, 0.03), (0.09, 0.62), (0.07, 0.66), (0.0, 0.68)], 32)
    p.add(body, "PaintRed", (0, y, 0.25), smooth=50, name="barrel")
    for z in (0.3, 0.6, 0.86):
        p.add(bm_torus(0.092, 0.01, 32, 6), "DarkSteel", (0, y, z), smooth=180)
    p.cyl(0.11, 0.05, (0, y, 0.23), "DarkSteel", segs=24, bevel=0.006)
    p.tube([(0, y, 0.23), (0, y, 0.05), (0, y - 0.05, -0.02)], 0.035, "DarkSteel", segs=12, round_r=0.05)
    p.box((0.22, 0.22, 0.04), (0, y - 0.05, -0.01), "DarkSteel", bevel=0.006)        # strainer on the bilge well
    p.tube([(0.07, y, 0.75), (0.2, y + 0.04, 0.78), (0.2, -0.05, 1.0), (0.2, -0.05, 2.2)], 0.03, "PaintRed", segs=12, round_r=0.08)
    p.box((0.12, 0.08, 0.12), (0, y, 0.98), "DarkSteel", bevel=0.01)                  # pivot block
    lever = p.pivot("Lever", (0, y, 1.02), interact="pump_lever", rotate_axis="X", min_deg=-25, max_deg=25,
                    note="each full up-down stroke pumps water out of this room")
    p.box((0.05, 0.1, 0.06), (0, 0, 0), "DarkSteel", parent=lever, bevel=0.008)
    p.cyl(0.02, 0.62, (0, -0.33, 0.02), "Chrome", axis="Y", segs=12, parent=lever)
    p.add(bm_lathe([(0, 0), (0.032, 0.0), (0.036, 0.03), (0.036, 0.2), (0.032, 0.23), (0, 0.23)], 16, "X"), "PaintRed",
          (-0.115, -0.66, 0.02), parent=lever, smooth=50, name="tgrip")
    p.cyl(0.012, 0.12, (0, -0.25, -0.08), "Chrome", parent=lever, segs=8)          # plunger rod
    p.plate(0.36, 0.07, (0, -0.012, 1.55), "label_bilge")
    gauge(p, (0.12, -0.02, 1.3), r=0.045, face="gauge_pressure", name="Gauge", needle_deg=-60)
    p.use_camera((0.25, -1.2, 1.6), (0, -0.3, 0.95), lens=30)
    p.hand("R", (0.05, -0.7, 1.05), "grip", control="Lever")
    p.hand("L", (-0.08, -0.7, 1.05), "grip", control="Lever")
    p.anchor("operate", (0, -1.0, 0))
    return p.finish()


def vent_panel(name="VentPanel"):
    """SMOKE EXTRACT switch box: turns this room's exhaust fans on (needs power)."""
    p = Prop(name, category="station", station="vent")
    p.box((0.42, 0.14, 0.56), (0, -0.07, 0), "PaintCream", bevel=0.015, segs=3)
    p.plate(0.34, 0.06, (0, -0.145, 0.2), "label_smoke", frame="PaintGraphite", depth=0.008)
    p.cyl(0.11, 0.02, (0, -0.15, -0.02), "PaintMustard", axis="Y", segs=32, bevel=0.004)
    sw = p.pivot("FanSwitch", (0, -0.16, -0.02), interact="vent_switch", rotate_axis="Y", min_deg=-45, max_deg=45)
    p.box((0.05, 0.05, 0.16), (0, -0.02, 0), "BlackPlastic", parent=sw, bevel=0.012)
    p.cyl(0.035, 0.03, (0, -0.02, 0), "BlackPlastic", axis="Y", segs=16, parent=sw)
    indicator(p, (-0.13, -0.142, -0.2), m="LampGreen", r=0.014, name="run")
    indicator(p, (0.13, -0.142, -0.2), m="LampAmber", r=0.014, name="smoke")
    p.tube([(0.1, -0.07, 0.28), (0.1, -0.07, 0.6), (0.1, 0.0, 0.65)], 0.015, "DarkSteel", segs=8, round_r=0.04)
    p.hand("R", (0.0, -0.25, -0.02), "pinch", control="FanSwitch")
    return p.finish()


def duct_fan(name="DuctFan"):
    """Exhaust fan hanging under the ventilation duct (origin at the duct underside). Blades spin about Z."""
    p = Prop(name, category="machine")
    p.cyl(0.24, 0.26, (0, 0, -0.13), "PaintGray", segs=32, bevel=0.01, caps=False)
    p.add(bm_torus(0.24, 0.014, 32, 6), "PaintGray", (0, 0, -0.26), smooth=180)
    p.cyl(0.08, 0.12, (0, 0, -0.07), "PaintGraphite", segs=20, bevel=0.01)
    for k in range(4):
        a = k * math.pi / 2
        p.box((0.24, 0.015, 0.015), (math.cos(a) * 0.12, math.sin(a) * 0.12, -0.08), "DarkSteel", rot=(0, 0, math.degrees(a)), bevel=0)
    fan = p.pivot("Fan", (0, 0, -0.17), interact="spin", rotate_axis="Z")
    p.cyl(0.04, 0.05, (0, 0, 0), "DarkSteel", segs=16, parent=fan)
    for k in range(5):
        bl = bm_box(0.19, 0.06, 0.006, (0.12, 0, 0))
        bmesh.ops.rotate(bl, verts=bl.verts, matrix=Matrix.Rotation(R(25), 3, "X"))
        bmesh.ops.rotate(bl, verts=bl.verts, matrix=Matrix.Rotation(R(k * 72), 3, "Z"))
        p.add(bl, "Steel", parent=fan, smooth=False, name="blade")
    for k in range(1, 4):
        p.add(bm_torus(0.24 * k / 3.5, 0.004, 32, 4), "Chrome", (0, 0, -0.25), smooth=180)
    for a in (0, 90):
        p.box((0.48, 0.006, 0.006), (0, 0, -0.25), "Chrome", rot=(0, 0, a), bevel=0)
    return p.finish()


def battery_bank(name="BatteryBank", n=8):
    """Two tiers of big lead-acid cells on a rack along X (back on y=0)."""
    p = Prop(name, category="machine")
    cw, depth = 0.3, 0.42
    L = n * cw + 0.1
    for sx in (-1, 1):
        for sy in (-0.04, -depth + 0.04):
            p.box((0.05, 0.05, 1.5), (sx * L / 2, sy, 0.75), "PaintGraphite", bevel=0.005)
    rnd = random.Random(3)
    for tier, z in enumerate((0.05, 0.78)):
        p.box((L, depth, 0.05), (0, -depth / 2, z), "PaintGraphite", bevel=0.006)
        for k in range(n):
            x = -L / 2 + 0.05 + cw * (k + 0.5)
            p.box((cw - 0.03, depth - 0.08, 0.5), (x, -depth / 2, z + 0.3), "PaintBattery", bevel=0.012)
            p.box((cw - 0.02, depth - 0.07, 0.04), (x, -depth / 2, z + 0.57), "PaintRed" if k % 2 else "BlackPlastic", bevel=0.01)
            for sy in (-0.1, 0.1):
                p.cyl(0.022, 0.06, (x - 0.07, -depth / 2 + sy, z + 0.61), "Lead", segs=10)
                p.cyl(0.022, 0.06, (x + 0.07, -depth / 2 + sy, z + 0.61), "Lead", segs=10)
            p.cyl(0.018, 0.04, (x, -depth / 2, z + 0.61), "PaintMustard", segs=10)
            if k < n - 1:
                p.box((0.12, 0.05, 0.012), (x + cw / 2, -depth / 2 - 0.1, z + 0.635), "Copper", bevel=0.002)
                p.box((0.12, 0.05, 0.012), (x + cw / 2, -depth / 2 + 0.1, z + 0.635), "Copper", bevel=0.002)
            p.box((0.1, 0.004, 0.05), (x, -depth + 0.038, z + 0.4), "PaintWhite", bevel=0)
    for k in range(3):
        p.tube([(-L / 2, -0.06 - k * 0.04, 1.42 + k * 0.03), (L / 2, -0.06 - k * 0.04, 1.42 + k * 0.03)], 0.025,
               ["BlackPlastic", "PaintRed", "BlackPlastic"][k], segs=10)
    p.decal(0.22, 0.27, (L / 2 - 0.25, -0.002, 1.62), "sign_voltage")
    return p.finish()


def main_switchboard(name="MainSwitchboard"):
    """Main DC switchboard: knife-switch breakers, meters, mimic bus diagram and the big MAIN BREAKER lever."""
    p = Prop(name, category="station", station="switchboard")
    W, D, H = 2.6, 0.55, 2.05
    p.box((W, D, H), (0, -D / 2, H / 2), "PaintGray", bevel=0.015, segs=2)
    p.box((W + 0.04, D + 0.02, 0.08), (0, -D / 2, 0.04), "PaintGraphite", bevel=0.008)
    for x in (-0.43, 0.43):
        p.box((0.015, 0.02, H - 0.1), (x, -D - 0.005, H / 2), "PaintGraphite", bevel=0)
    f = -D - 0.003
    p.decal(0.9, 0.45, (0, f, 1.6), "mimic_bus")
    p.plate(0.9, 0.12, (0, f - 0.006, 1.93), "label_switchboard")
    for sx in (-1, 1):
        cx = sx * 0.85
        for k in range(3):
            gauge(p, (cx - 0.22 + k * 0.22, f, 1.62), r=0.075, face=["gauge_pressure", "gauge_air", "gauge_depth"][k],
                  name=f"Meter{'LR'[sx > 0]}{k + 1}", needle_deg=-40 + k * 30)
        for k in range(4):
            bx = cx - 0.3 + k * 0.2
            p.box((0.12, 0.05, 0.22), (bx, f - 0.025, 1.12), "Bakelite", bevel=0.01)
            for dz in (-0.07, 0.07):
                p.box((0.03, 0.03, 0.03), (bx, f - 0.06, 1.12 + dz), "Copper", bevel=0.004)
            br = p.pivot(f"Breaker{'LR'[sx > 0]}{k + 1}", (bx, f - 0.06, 1.05), interact="breaker", rotate_axis="X",
                         min_deg=0, max_deg=150)
            p.box((0.02, 0.02, 0.15), (0, 0, 0.075), "Copper", parent=br, bevel=0.004)
            p.box((0.1, 0.03, 0.03), (0, -0.01, 0.15), "Bakelite", parent=br, bevel=0.008)
            indicator(p, (bx, f, 0.9), m="LampGreen" if (k + sx) % 3 else "LampAmber", r=0.012)
    # MAIN BREAKER lever (pull down = off, push up = on)
    p.box((0.32, 0.08, 0.48), (0, f - 0.04, 1.0), "PaintGraphite", bevel=0.015)
    p.plate(0.3, 0.06, (0, f - 0.085, 1.3), "label_main_breaker")
    mb = p.pivot("MainBreaker", (0, f - 0.09, 0.95), interact="main_breaker", rotate_axis="X", min_deg=-60, max_deg=60,
                 note="+60 = ON (up), -60 = tripped (down)")
    p.box((0.06, 0.06, 0.08), (0, 0, 0), "DarkSteel", parent=mb, bevel=0.01)
    p.cyl(0.018, 0.3, (0, -0.0, 0.15), "Chrome", segs=12, parent=mb)
    p.add(bm_lathe([(0, 0), (0.03, 0.0), (0.035, 0.03), (0.035, 0.22), (0.03, 0.25), (0, 0.25)], 16, "X"), "PaintRed",
          (-0.125, 0, 0.32), parent=mb, smooth=50, name="grip")
    louver(p, (0, f, 0.4), w=1.4, h=0.2, n=5)
    p.box((W, 0.9, 0.012), (0, -D - 0.45, 0.006), "Rubber", bevel=0)               # insulating mat
    p.decal(0.2, 0.25, (W / 2 - 0.2, f, 0.62), "sign_voltage")
    p.use_camera((0.1, -1.45, 1.6), (0, -0.4, 1.05), lens=28)
    p.hand("R", (0.0, f - 0.25, 1.27), "grip", control="MainBreaker")
    p.anchor("operate", (0, -D - 0.7, 0))
    return p.finish()


def medical_cabinet(name="MedicalCabinet"):
    """Wall cabinet with a red cross, glass doors and shelves of supplies (restock first-aid kits here)."""
    p = Prop(name, category="station", station="medical")
    W, D, H = 0.8, 0.28, 0.9
    p.box((W, D, H), (0, -D / 2, H / 2), "PaintWhite", bevel=0.012)
    p.box((W - 0.06, 0.01, H - 0.06), (0, -D + 0.04, H / 2), "PaintCream", bevel=0)
    rnd = random.Random(5)
    for z in (0.08, 0.38, 0.66):
        p.box((W - 0.06, D - 0.06, 0.012), (0, -D / 2, z), "PaintWhite", bevel=0)
        for k in range(7):
            x = -W / 2 + 0.08 + k * 0.1
            h = rnd.uniform(0.08, 0.18)
            m = rnd.choice(["EnamelBlue", "PaintWhite", "PaintMustard", "EnamelRed", "Glass"])
            p.add(bm_lathe([(0, 0), (0.03, 0), (0.03, h * 0.8), (0.012, h), (0, h)], 12), m, (x, -D / 2, z + 0.006), smooth=40)
    for sx in (-1, 1):
        hx = sx * (W / 2 - 0.02)
        door = p.pivot(f"Door{'LR'[sx > 0]}", (hx, -D - 0.005, 0.03), interact="door", rotate_axis="Z",
                       min_deg=0 if sx > 0 else -110, max_deg=110 if sx > 0 else 0)
        dw = W / 2 - 0.03
        frame = bm_plate_with_holes(rect(dw, H - 0.08), [rect(dw - 0.08, H - 0.16)], 0.02)
        bmesh.ops.rotate(frame, verts=frame.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
        p.add(frame, "PaintWhite", (-sx * dw / 2, 0.01, (H - 0.08) / 2), parent=door, smooth=False, name="frame")
        p.box((dw - 0.08, 0.004, H - 0.16), (-sx * dw / 2, 0.0, (H - 0.08) / 2), "Glass", parent=door, bevel=0)
        p.box((0.02, 0.025, 0.1), (-sx * (dw - 0.05), -0.02, (H - 0.08) / 2), "Chrome", parent=door, bevel=0.004)
    p.decal(0.24, 0.24, (0, -0.0115, H + 0.18), "label_red_cross")
    p.box((0.28, 0.01, 0.28), (0, -0.005, H + 0.18), "PaintWhite", bevel=0.003)
    p.anchor("restock", (0, -0.9, 0))
    return p.finish()


def med_bed(name="MedBed"):
    """Sick-bay bed with rails and an IV stand. Lie down to heal."""
    p = Prop(name, category="station", station="medical", interact="heal")
    L, W, H = 1.95, 0.85, 0.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl(0.022, H, (sx * (L / 2 - 0.05), sy * (W / 2 - 0.05), H / 2), "Chrome", segs=10)
            p.sphere(0.04, (sx * (L / 2 - 0.05), sy * (W / 2 - 0.05), 0.04), "BlackPlastic", segs=10, rings=5)
    p.box((L, W, 0.06), (0, 0, H), "PaintGray", bevel=0.01)
    p.box((L - 0.06, W - 0.06, 0.14), (0, 0, H + 0.1), "MattressWhite", bevel=0.05, segs=3)
    p.box((0.4, W - 0.25, 0.1), (-L / 2 + 0.3, 0, H + 0.21), "Pillow", bevel=0.04, segs=3)
    p.box((L * 0.55, W - 0.04, 0.03), (0.3, 0, H + 0.185), "EnamelBlue", bevel=0.012)
    for sy in (-1, 1):
        p.tube([(-0.5, sy * (W / 2 + 0.01), H + 0.05), (-0.5, sy * (W / 2 + 0.01), H + 0.35), (0.5, sy * (W / 2 + 0.01), H + 0.35),
                (0.5, sy * (W / 2 + 0.01), H + 0.05)], 0.014, "Chrome", segs=8, round_r=0.05)
    for sx in (-1, 1):
        p.tube([(sx * L / 2, -W / 2 + 0.05, H), (sx * L / 2, -W / 2 + 0.05, H + 0.45 - (0.1 if sx > 0 else 0)),
                (sx * L / 2, W / 2 - 0.05, H + 0.45 - (0.1 if sx > 0 else 0)), (sx * L / 2, W / 2 - 0.05, H)], 0.018, "Chrome",
               segs=8, round_r=0.06)
    # IV stand
    ix, iy = -L / 2 + 0.2, -W / 2 - 0.25
    for k in range(4):
        a = k * math.pi / 2
        p.tube([(ix, iy, 0.06), (ix + math.cos(a) * 0.22, iy + math.sin(a) * 0.22, 0.03)], 0.012, "Chrome", segs=6)
    p.cyl(0.012, 1.75, (ix, iy, 0.9), "Chrome", segs=8)
    p.tube([(ix - 0.12, iy, 1.75), (ix + 0.12, iy, 1.75)], 0.008, "Chrome", segs=6)
    p.box((0.1, 0.04, 0.18), (ix + 0.1, iy, 1.62), "IVBag", bevel=0.02)
    p.tube(sag_path((ix + 0.1, iy, 1.52), (-L / 2 + 0.5, -W / 2 + 0.1, H + 0.25), 0.3, 12), 0.004, "IVBag", segs=6)
    p.anchor("lie", (0, 0, H + 0.25), note="lie here to heal")
    p.anchor("use", (0, -W / 2 - 0.6, 0))
    return p.finish()


def first_aid_kit(name="FirstAidKit"):
    p = Prop(name, category="pickup", interact="carry", item="first_aid")
    p.box((0.32, 0.12, 0.22), (0, 0, 0.11), "EnamelRed", bevel=0.02, segs=2)
    p.decal(0.12, 0.12, (0, -0.0605, 0.11), "label_red_cross")
    p.tube([(-0.07, 0, 0.22), (-0.07, 0, 0.26), (0.07, 0, 0.26), (0.07, 0, 0.22)], 0.01, "BlackPlastic", segs=8, round_r=0.02)
    p.box((0.33, 0.125, 0.012), (0, 0, 0.17), "EnamelCream", bevel=0.003)
    return p.finish()
