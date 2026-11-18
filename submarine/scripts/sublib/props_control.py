"""Control room stations: navigation table + console, fire control, periscope, sonar, ballast panel."""

import math

import bmesh
from mathutils import Matrix, Vector

from .core import Prop, R, bm_box, bm_cyl, bm_extrude, bm_lathe, bm_plate_with_holes, bm_torus, bm_disc, rrect, rect
from .props_common import (gauge, grab_rail, handwheel, indicator, knob, louver, push_button, slots, toggle, _v)


def _tilted_box(p, w, d, h_front, h_back, z0, m, parent=None, bevel=0.012, y0=0.0, name="console"):
    """Console body whose top slopes from h_front (at -Y) to h_back (at +Y). Footprint centred on x, from y0-d/2..y0+d/2."""
    poly = [(-d / 2, 0), (d / 2, 0), (d / 2, h_back), (-d / 2, h_front)]
    bm = bm_extrude(poly, w)
    # extruded along Z -> rotate so profile is in YZ and width along X
    mtx = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))
    for v in bm.verts:
        v.co = mtx @ v.co
    return p.add(bm, m, (0, y0, z0), parent=parent, bevel=bevel, segs=2, name=name)


def nav_table(name="NavTable"):
    """Backlit chart table (centre of the control room). Long axis X, usable from both long sides."""
    p = Prop(name, category="station", station="navigation")
    L, W, H = 1.9, 1.15, 0.95
    p.box((L - 0.16, W - 0.16, 0.1), (0, 0, 0.05), "PaintGraphite", bevel=0.01)
    p.box((L, W, H - 0.2), (0, 0, 0.1 + (H - 0.2) / 2), "PaintSeafoam", bevel=0.02, segs=3)
    # top frame with chart glass
    top = bm_plate_with_holes(rrect(L + 0.04, W + 0.04, 0.05, 4), [rect(1.56, 1.04)], 0.1)
    p.add(top, "PaintTeal", (0, 0, H - 0.1), bevel=0.012, segs=2, name="topframe")
    p.decal(1.56, 1.04, (0, 0, H - 0.03), "screen_chart", rot=(-90, 0, 0))
    p.box((1.6, 1.08, 0.04), (0, 0, H - 0.07), "BlackPlastic", bevel=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.add(bm_extrude(rrect(0.1, 0.1, 0.03), 0.105), "Brass", (sx * (L / 2 - 0.03), sy * (W / 2 - 0.03), H - 0.05), bevel=0.006)
    # chart drawers on both long sides
    for side in (-1, 1):
        for k in range(3):
            x = (k - 1) * 0.58
            p.box((0.52, 0.02, 0.2), (x, side * (W / 2 + 0.005), 0.55), "PaintSeafoam", bevel=0.006)
            p.add(bm_extrude(rrect(0.16, 0.03, 0.012), 0.02), "Brass", (x, side * (W / 2 + 0.025), 0.6), (90, 0, 0), bevel=0.003)
            p.box((0.08, 0.004, 0.03), (x, side * (W / 2 + 0.017), 0.5), "PaintCream", bevel=0)
        louver(p, (0, side * (W / 2 + 0.01), 0.27), rot=(0, 0, 0 if side < 0 else 180), w=1.2, h=0.14, n=4)
        grab_rail(p, (-0.8, side * (W / 2 + 0.02), H - 0.17), (0.8, side * (W / 2 + 0.02), H - 0.17), standoff=0.07,
                  axis_out=(0, side, 0), r=0.016)
    # instruments lying on the chart
    ruler = p.pivot("ParallelRuler", (0.15, -0.2, H - 0.025), (0, 0, 18), interact="pickup")
    for dy in (-0.035, 0.035):
        p.box((0.6, 0.05, 0.008), (0, dy, 0.004), "Brass", parent=ruler, bevel=0.002)
    for dx in (-0.2, 0.2):
        p.box((0.02, 0.08, 0.006), (dx, 0, 0.011), "Brass", parent=ruler, bevel=0.002)
    div = p.pivot("Dividers", (-0.45, 0.25, H - 0.025), (0, 0, -30), interact="pickup")
    for a in (-8, 8):
        p.add(bm_cyl(0.004, 0.22, 8, 0.001, "X"), "Steel", (0.1, a * 0.004, 0.006), (0, 0, a), parent=div)
    p.cyl(0.012, 0.012, (0, 0, 0.008), "Brass", segs=12, parent=div)
    for k, (x, y, mm) in enumerate([(0.32, 0.1, "PaintRed"), (0.48, 0.3, "PaintRed"), (-0.1, 0.18, "PaintNavy"), (0.6, -0.35, "PaintMustard")]):
        mk = p.pivot(f"Marker{k + 1}", (x, y, H - 0.03), interact="map_marker")
        p.add(bm_lathe([(0, 0), (0.025, 0), (0.025, 0.01), (0.008, 0.02), (0.008, 0.05), (0.014, 0.06), (0, 0.065)], 16), mm, parent=mk)
    # end stand with NAVIGATION plate
    p.box((0.05, 0.4, 0.3), (L / 2 + 0.04, 0, H + 0.08), "PaintGraphite", rot=(0, -12, 0), bevel=0.008)
    p.plate(0.36, 0.068, (L / 2 + 0.07, 0, H + 0.14), "label_navigation", rot=(0, 0, 90))
    p.anchor("use_front", (0, -W / 2 - 0.5, 0))
    p.anchor("use_back", (0, W / 2 + 0.5, 0), (0, 0, 180))
    return p.finish()


def nav_console(name="NavConsole"):
    """Standing navigation console with amber terrain scope, joystick and zoom dial."""
    p = Prop(name, category="station", station="navigation")
    W, D = 0.95, 0.62
    p.box((W - 0.1, D - 0.1, 0.1), (0, 0, 0.05), "PaintGraphite", bevel=0.01)
    _tilted_box(p, W, D, 0.95, 1.3, 0.1, "PaintSeafoam")
    p.box((W, 0.25, 0.45), (0, D / 2 - 0.125, 1.4 + 0.1 - 0.05), "PaintSeafoam", bevel=0.02)
    tilt = math.degrees(math.atan2(0.35, D))  # slope of the console top
    # scope on the sloped face
    rx = tilt - 90  # tilt a -Y facing quad back so it lies on the sloped top
    sc = Vector((0, 0.06, 0.1 + 0.95 + (1.3 - 0.95) * (0.5 + 0.06 / D) + 0.005))
    p.screen(0.36, 0.36, sc, "screen_nav_scope", rot=(rx, 0, 0), bezel=0.05, depth=0.03)
    # controls on the lower front panel
    stick = p.pivot("Joystick", (0.22, -0.2, 0.1 + 0.95 + (0.35 * (D / 2 - 0.2) / D) - 0.02), (rx + 90, 0, 0),
                    interact="joystick", rotate_axes="XY", max_deg=25)
    p.add(bm_lathe([(0.0, 0.0), (0.05, 0.0), (0.045, 0.02), (0.02, 0.05), (0.014, 0.06), (0.0, 0.06)], 20), "Rubber", parent=stick)
    p.cyl(0.009, 0.14, (0, 0, 0.12), "Chrome", segs=12, parent=stick)
    p.add(bm_lathe([(0, 0.17), (0.022, 0.18), (0.026, 0.23), (0.022, 0.27), (0.0, 0.28)], 20), "BlackPlastic", parent=stick)
    push_button(p, (0, 0, 0.285), rot=(-90, 0, 0), m="PaintRed", r=0.01, parent=stick, name="StickTrigger")
    zoom = knob(p, (-0.24, -0.2, 0.1 + 0.95 + (0.35 * (D / 2 - 0.2) / D)), rot=(rx + 180, 0, 0), r=0.045, name="ZoomDial",
                interact="dial", m="Bakelite")
    for k, mm in enumerate(["PaintRed", "PaintMustard", "PaintTeal", "PaintWhite"]):
        push_button(p, (-0.3 + k * 0.2, -D / 2 - 0.002, 0.88), m=mm, r=0.022, name=f"Button{k + 1}")
    p.decal(0.11, 0.035, (-0.24, -0.29, 1.07), "label_zoom", rot=(rx, 0, 0))
    p.decal(0.11, 0.035, (0.22, -0.29, 1.07), "label_view", rot=(rx, 0, 0))
    louver(p, (0, -D / 2 - 0.001, 0.42), w=0.6, h=0.22, n=5)
    for side in (-1, 1):
        grab_rail(p, (side * (W / 2 + 0.01), -0.2, 0.98), (side * (W / 2 + 0.01), 0.15, 1.2), standoff=0.06,
                  axis_out=(side, 0, 0))
        louver(p, (side * (W / 2 + 0.002), 0, 0.5), rot=(0, 0, side * -90), w=0.35, h=0.25, n=5)
    p.plate(0.6, 0.11, (0, D / 2 - 0.25 - 0.004, 1.58), "label_navigation")
    for k in range(4):
        indicator(p, (-0.3 + k * 0.2, D / 2 - 0.252, 1.38), m=["LampGreen", "LampGreen", "LampAmber", "LampGreen"][k], r=0.014)
    p.anchor("operate", (0, -D / 2 - 0.45, 0))
    return p.finish()


def fire_control(name="FireControl"):
    """Weapons console: target solution screen, tube selectors, ARM key, guarded FIRE button, phone."""
    p = Prop(name, category="station", station="weapons")
    W, D = 1.15, 0.6
    p.box((W - 0.1, D - 0.1, 0.1), (0, 0, 0.05), "PaintGraphite", bevel=0.01)
    p.box((W, D, 0.85), (0, 0, 0.1 + 0.425), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.04, D + 0.06, 0.05), (0, -0.02, 0.975), "PaintGraphite", bevel=0.01)  # desk edge
    # upper tilted cabinet
    _tilted_box(p, W, 0.42, 0.62, 0.8, 1.0, "PaintCream", y0=0.09)
    p.screen(0.56, 0.42, (0, 0.09 - 0.21 - 0.004, 1.32), "screen_fire_control", bezel=0.04, depth=0.04)
    p.plate(0.62, 0.11, (0, 0.09 - 0.21 - 0.006, 1.72), "label_fire_control")
    for k in range(4):
        x = -0.42 + k * 0.28
        p.decal(0.07, 0.07, (x, -D / 2 - 0.004, 0.86), f"label_tube{k + 1}")
        toggle(p, (x, -D / 2 - 0.002, 0.76), name=f"TubeSelect{k + 1}", up=k == 0)
        indicator(p, (x, -D / 2 - 0.002, 0.66), m="LampGreen" if k in (0, 2) else "LampRed", r=0.016)
    # desk surface controls
    desk_z = 1.0
    key = knob(p, (-0.38, -0.12, desk_z), rot=(-90, 0, 0), r=0.035, name="ArmKey", interact="key_switch", m="PaintGraphite")
    p.decal(0.12, 0.04, (-0.38, -0.21, desk_z + 0.001), "label_arm", rot=(-90, 0, 0))
    # guarded fire button
    p.box((0.2, 0.2, 0.02), (0.2, -0.12, desk_z + 0.01), "Hazard", bevel=0.004)
    push_button(p, (0.2, -0.12, desk_z + 0.02), rot=(-90, 0, 0), m="PaintRed", r=0.045, name="FireButton", interact="fire")
    guard = p.pivot("FireGuard", (0.2, -0.02, desk_z + 0.03), interact="guard", rotate_axis="X", min_deg=0, max_deg=110)
    p.box((0.16, 0.16, 0.006), (0, -0.1, 0.05), "LampRed", parent=guard, bevel=0.002)
    for sx in (-1, 1):
        p.box((0.006, 0.16, 0.05), (sx * 0.077, -0.1, 0.025), "LampRed", parent=guard, bevel=0.002)
    p.box((0.16, 0.006, 0.05), (0, -0.177, 0.025), "LampRed", parent=guard, bevel=0.002)
    p.decal(0.12, 0.04, (0.2, -0.24, desk_z + 0.001), "label_fire", rot=(-90, 0, 0))
    # telephone handset on a hook
    p.box((0.12, 0.06, 0.2), (W / 2 + 0.03, 0.05, 1.25), "Bakelite", bevel=0.015)
    phone = p.pivot("Handset", (W / 2 + 0.075, 0.05, 1.25), interact="pickup")
    p.add(bm_extrude(rrect(0.05, 0.22, 0.02), 0.03), "Bakelite", (0, 0, 0), (0, 90, 0), parent=phone, bevel=0.01)
    for zz in (-0.1, 0.1):
        p.cyl(0.035, 0.03, (0.01, 0, zz), "Bakelite", axis="X", segs=16, parent=phone, bevel=0.006)
    p.tube([(W / 2 + 0.08, 0.05, 1.13)] + [(W / 2 + 0.08 + 0.02 * math.cos(t), 0.05 + 0.02 * math.sin(t), 1.12 - t * 0.012) for t in [i * 0.6 for i in range(40)]],
           0.004, "Bakelite", segs=6)
    louver(p, (0, -D / 2 - 0.002, 0.32), w=0.8, h=0.2, n=5)
    for side in (-1, 1):
        grab_rail(p, (side * (W / 2 + 0.01), -0.25, 0.85), (side * (W / 2 + 0.01), 0.2, 0.85), standoff=0.05, axis_out=(side, 0, 0))
    p.anchor("operate", (0, -D / 2 - 0.45, 0))
    return p.finish()


def periscope(name="Periscope", ceiling=2.9):
    """Periscope column; the Head pivot (eyepiece, handles) trains 360° about Z."""
    p = Prop(name, category="station", station="periscope")
    p.cyl(0.32, 0.04, (0, 0, 0.02), "PaintGraphite", segs=40, bevel=0.01)
    p.add(bm_torus(0.26, 0.02, 40, 8), "Hazard", (0, 0, 0.045), smooth=180)
    p.cyl(0.14, ceiling + 0.4, (0, 0, (ceiling + 0.4) / 2), "Steel", segs=32)
    for z in (0.5, 0.9, 2.25, 2.6):
        p.cyl(0.15, 0.03, (0, 0, z), "DarkSteel", segs=32, bevel=0.005)
    p.cyl(0.3, 0.08, (0, 0, ceiling - 0.04), "PaintGraphite", segs=40, bevel=0.01)
    p.bolts([(math.cos(a) * 0.25, math.sin(a) * 0.25, ceiling - 0.085) for a in [k * math.pi / 4 for k in range(8)]], axis="Z", r=0.012)
    # bearing ring (fixed)
    p.add(bm_torus(0.2, 0.025, 48, 8), "Brass", (0, 0, 1.18), smooth=180)
    for k in range(36):
        a = k * math.pi / 18
        p.box((0.012, 0.03, 0.025 if k % 3 else 0.04), (math.cos(a) * 0.235, math.sin(a) * 0.235, 1.18), "PaintGraphite",
              rot=(0, 0, math.degrees(a) + 90), bevel=0)
    # rotating head
    head = p.pivot("Head", (0, 0, 0), interact="periscope_train", rotate_axis="Z")
    p.cyl(0.19, 0.1, (0, 0, 1.25), "PaintGraphite", segs=40, bevel=0.01, parent=head)
    housing = bm_extrude(rrect(0.42, 0.42, 0.1, 6), 0.34)  # XY footprint, Z height
    p.add(housing, "PaintTeal", (0, -0.06, 1.5), parent=head, bevel=0.02, segs=3, name="housing")
    p.box((0.3, 0.1, 0.16), (0, -0.3, 1.58), "PaintTeal", parent=head, bevel=0.02)
    for sx in (-0.055, 0.055):
        p.cyl(0.035, 0.08, (sx, -0.38, 1.6), "DarkSteel", axis="Y", segs=20, parent=head)
        p.add(bm_lathe([(0.03, 0.0), (0.042, -0.01), (0.048, -0.05), (0.044, -0.065), (0.03, -0.06), (0.028, -0.01)], 20, "Y", closed=True),
              "Rubber", (sx, -0.42, 1.6), parent=head, smooth=60)
    p.decal(0.2, 0.1, (0, -0.351, 1.44), "screen_target_id", parent=head)
    p.box((0.24, 0.02, 0.13), (0, -0.338, 1.44), "BlackPlastic", parent=head, bevel=0.006)
    p.plate(0.3, 0.06, (0, -0.31, 1.73), "label_periscope", parent=head, frame="PaintGraphite")
    for side in (-1, 1):
        h = p.pivot("HandleL" if side < 0 else "HandleR", (side * 0.22, -0.15, 1.52), parent=head,
                    interact="periscope_handle", rotate_axis="X", min_deg=-90, max_deg=0, note="fold down to stow")
        p.box((0.05, 0.08, 0.08), (side * 0.025, 0, 0), "DarkSteel", parent=h, bevel=0.01)
        p.cyl(0.018, 0.2, (side * 0.13, 0, 0), "Chrome", axis="X", segs=12, parent=h)
        p.add(bm_lathe([(0.0, 0.0), (0.03, 0.0), (0.034, 0.03), (0.034, 0.15), (0.03, 0.18), (0.0, 0.18)], 16, "X"),
              "Rubber", (side * 0.18 if side > 0 else -0.36, 0, 0), parent=h)
        push_button(p, (side * 0.13 - 0.0 + side * 0.24, 0, 0), rot=(0, 0, side * 90), m="PaintRed", r=0.014, parent=h,
                    name="Mark" if side > 0 else "Zoom", interact="mark_target" if side > 0 else "zoom")
    p.anchor("operate", (0, -0.85, 0), note="anchor rotates with Head in game")
    return p.finish()


def sonar_station(name="SonarStation"):
    """Wall desk with the green sonar CRT, knobs, headphones on a hook."""
    p = Prop(name, category="station", station="sonar")
    W, D = 1.05, 0.62
    for sx in (-1, 1):
        p.box((0.04, D - 0.05, 0.74), (sx * (W / 2 - 0.05), -D / 2 + 0.02, 0.37), "PaintGraphite", bevel=0.008)
    p.box((W, D, 0.04), (0, -D / 2, 0.76), "PaintCream", bevel=0.01)
    p.box((W - 0.1, 0.03, 0.12), (0, -0.05, 0.69), "PaintGraphite", bevel=0.006)
    # instrument tower
    p.box((W, 0.3, 1.0), (0, -0.15, 0.78 + 0.5), "PaintSeafoam", bevel=0.02, segs=3)
    p.screen(0.46, 0.46, (0, -0.302, 1.32), "screen_sonar", bezel=0.05, depth=0.045)
    p.add(bm_torus(0.26, 0.015, 48, 8, "Y"), "Chrome", (0, -0.33, 1.32), smooth=180)
    for k, (x, z, nm) in enumerate([(-0.4, 1.5, "Gain"), (-0.4, 1.3, "Bearing"), (0.4, 1.5, "Range"), (0.4, 1.3, "Filter")]):
        knob(p, (x, -0.302, z), r=0.035, name=nm + "Knob", interact="dial")
    for k in range(5):
        toggle(p, (-0.3 + k * 0.15, -0.302, 0.96), name=f"Switch{k + 1}", up=k in (0, 3))
    indicator(p, (0.4, -0.302, 1.05), m="LampGreen")
    indicator(p, (-0.4, -0.302, 1.05), m="LampAmber")
    slots(p, (0.4, -0.302, 0.96), w=0.12, h=0.06, n=4)
    p.plate(0.5, 0.09, (0, -0.31, 1.69), "label_sonar")
    # headphones on a hook
    p.box((0.02, 0.06, 0.02), (W / 2 + 0.01, -0.12, 1.55), "Chrome", bevel=0.004)
    hp = p.pivot("Headphones", (W / 2 + 0.03, -0.16, 1.5), interact="pickup")
    p.add(bm_torus(0.09, 0.012, 32, 8, "Y", angle=math.pi), "BlackPlastic", (0, 0, 0.0), (0, 0, 90), parent=hp, smooth=180)
    for sy in (-1, 1):
        p.cyl(0.045, 0.035, (0, sy * 0.095, -0.03), "Leather", axis="Y", segs=20, parent=hp, bevel=0.01)
    p.tube([(0, 0.11, -0.05), (0.02, 0.12, -0.25), (-0.05, 0.05, -0.62), (-0.2, 0.05, -0.7)], 0.004, "BlackPlastic",
           round_r=0.1, parent=hp)
    p.anchor("operate", (0, -D - 0.35, 0))
    return p.finish()


def ballast_panel(name="BallastPanel"):
    """Wall-mounted dive/ballast panel: hull-opening lamps, depth gauge, BLOW/VENT/FLOOD wheels, trim levers."""
    p = Prop(name, category="station", station="ballast")
    W, H, z0 = 1.5, 1.35, 0.55
    p.box((W, 0.18, H), (0, -0.09, z0 + H / 2), "PaintSeafoam", bevel=0.02, segs=3)
    p.box((W + 0.04, 0.2, 0.05), (0, -0.1, z0 + H + 0.02), "PaintGraphite", bevel=0.01)
    p.box((W + 0.04, 0.2, 0.05), (0, -0.1, z0 - 0.02), "PaintGraphite", bevel=0.01)
    f = -0.182
    p.plate(0.6, 0.1, (0, f - 0.005, z0 + H - 0.09), "label_ballast")
    gauge(p, (0, f, z0 + 0.98), r=0.17, face="gauge_depth", name="DepthGauge", needle_deg=-80)
    gauge(p, (-0.5, f, z0 + 1.05), r=0.08, face="gauge_pressure", name="PressureGauge", needle_deg=10)
    gauge(p, (0.5, f, z0 + 1.05), r=0.08, face="gauge_air", name="AirGauge", needle_deg=-20)
    # "christmas tree" hull opening indicators
    p.box((0.52, 0.02, 0.14), (0, f - 0.005, z0 + 0.7), "BlackPlastic", bevel=0.006)
    for k in range(12):
        indicator(p, (-0.22 + (k % 6) * 0.088, f - 0.016, z0 + 0.73 - (k // 6) * 0.06),
                  m="LampGreen" if k not in (3, 8) else "LampRed", r=0.012)
    p.screen(0.28, 0.21, (-0.5, f - 0.002, z0 + 0.72), "screen_ballast", bezel=0.025, depth=0.03)
    for k in range(3):
        indicator(p, (0.42 + k * 0.08, f, z0 + 0.72), m=["LampGreen", "LampAmber", "LampRed"][k], r=0.016)
    for k, lbl in enumerate(["blow", "vent", "flood"]):
        x = -0.45 + k * 0.45
        p.box((0.06, 0.12, 0.06), (x, f - 0.06, z0 + 0.35), "DarkSteel", bevel=0.008)
        handwheel(p, (x, f - 0.14, z0 + 0.35), r=0.12, name=lbl.title() + "Valve", interact="ballast_" + lbl,
                  m=["PaintRed", "PaintMustard", "PaintTeal"][k])
        p.decal(0.15, 0.047, (x, f - 0.001, z0 + 0.15), "label_" + lbl)
    # trim levers on the right edge
    for k in range(2):
        lv = p.pivot(f"TrimLever{k + 1}", (W / 2 - 0.05 + 0.03, -0.12, z0 + 0.55 + k * 0.25), (0, 0, 0),
                     interact="lever", rotate_axis="Y", min_deg=-35, max_deg=35)
        p.box((0.03, 0.03, 0.06), (0.01, 0, 0), "DarkSteel", parent=lv, bevel=0.005)
        p.cyl(0.01, 0.2, (0.11, 0, 0), "Chrome", axis="X", segs=10, parent=lv)
        p.sphere(0.028, (0.22, 0, 0), "PaintRed", parent=lv, segs=16, rings=8)
    # feed pipes into the panel
    for x, m in [(-0.6, "PaintRed"), (-0.2, "PaintMustard"), (0.2, "PaintTeal"), (0.6, "Copper")]:
        p.cyl(0.03, z0, (x, -0.06, z0 / 2), m, segs=12)
        p.cyl(0.045, 0.03, (x, -0.06, z0 - 0.06), m, segs=16, bevel=0.004)
    p.anchor("operate", (0, -0.75, 0))
    return p.finish()
