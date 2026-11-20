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
    # route-planning pod hung on the front edge: cursor stick, ADD / DEL waypoint keys, zoom knob
    pod = Vector((0.5, -W / 2 - 0.1, H - 0.06))
    p.box((0.46, 0.2, 0.08), pod + Vector((0, 0.0, -0.02)), "PaintGraphite", rot=(-14, 0, 0), bevel=0.012)
    p.box((0.4, 0.16, 0.01), pod + Vector((0, -0.004, 0.022)), "PaintSeafoam", rot=(-14, 0, 0), bevel=0.003)
    for sx in (-1, 1):
        p.box((0.03, 0.12, 0.05), (pod.x + sx * 0.17, -W / 2 - 0.02, H - 0.09), "PaintGraphite", bevel=0.006)
    cstick = p.pivot("CursorStick", pod + Vector((-0.11, 0, 0.03)), interact="joystick", rotate_axes="XY", max_deg=20)
    p.add(bm_lathe([(0.0, 0.0), (0.035, 0.0), (0.03, 0.014), (0.012, 0.03), (0.0, 0.034)], 18), "Rubber", parent=cstick)
    p.cyl(0.007, 0.06, (0, 0, 0.06), "Chrome", segs=10, parent=cstick)
    p.sphere(0.022, (0, 0, 0.1), "BlackPlastic", parent=cstick, segs=16, rings=8)
    for k, (lbl, mm) in enumerate([("add_wpt", "LampGreen"), ("del_wpt", "PaintRed")]):
        bx = pod.x + 0.02 + k * 0.09
        push_button(p, (bx, pod.y + 0.01, pod.z + 0.03), rot=(-90 + 14, 0, 0), m=mm, r=0.019,
                    name="AddWaypoint" if k == 0 else "DelWaypoint", interact="waypoint")
        p.decal(0.08, 0.026, (bx, pod.y - 0.055, pod.z + 0.017), f"label_{lbl}", rot=(-76, 0, 0))
    knob(p, (pod.x + 0.17, pod.y + 0.01, pod.z + 0.03), rot=(-76, 0, 0), r=0.024, name="ChartZoom", interact="dial", m="Bakelite")
    p.decal(0.36, 0.05, (pod.x, pod.y + 0.075, pod.z + 0.055), "label_route", rot=(-76, 0, 0))
    # the watch keeps its coffee and sandwiches on the end of the frame
    for k, (y, mm) in enumerate([(0.36, "EnamelCream"), (-0.34, "EnamelBlue")]):
        p.add(bm_lathe([(0, 0), (0.038, 0), (0.042, 0.1), (0.036, 0.1), (0.032, 0.012), (0, 0.012)], 20), mm, (-L / 2 + 0.1, y, H), smooth=40, name="mug")
        p.add(bm_torus(0.026, 0.006, 12, 6, "Y"), mm, (-L / 2 + 0.1, y + 0.045, H + 0.055), smooth=180)
        p.cyl(0.033, 0.004, (-L / 2 + 0.1, y, H + 0.09), "Coffee", segs=16)
    p.cyl(0.085, 0.012, (-L / 2 + 0.1, 0.02, H + 0.006), "PaintWhite", segs=24, bevel=0.003)
    for k in range(2):
        p.box((0.075, 0.075, 0.03), (-L / 2 + 0.1 + (k - 0.5) * 0.03, 0.02 + (k - 0.5) * 0.04, H + 0.03 + k * 0.03), "Bun",
              rot=(0, 0, 20 + k * 35), bevel=0.008)
    # end stand with NAVIGATION plate
    p.box((0.05, 0.4, 0.3), (L / 2 + 0.04, 0, H + 0.08), "PaintGraphite", rot=(0, -12, 0), bevel=0.008)
    p.plate(0.36, 0.068, (L / 2 + 0.07, 0, H + 0.14), "label_navigation", rot=(0, 0, 90))
    p.use_camera((0, -W / 2 - 0.42, 1.68), (0, 0.02, H - 0.02), lens=24)
    p.use_camera((0, W / 2 + 0.42, 1.68), (0, -0.02, H - 0.02), lens=24, name="CAM_use_back")
    p.hand("L", (-0.35, -W / 2 + 0.04, H + 0.02), "palm")
    p.hand("R", (0.39, -W / 2 - 0.1, H + 0.04), "grip", control="CursorStick")
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
    # steering wheel on a column in front of the console (turns with the rudder)
    p.cyl(0.035, 0.22, (0, -D / 2 - 0.08, 0.98), "DarkSteel", axis="Y", segs=16, rot=(-25, 0, 0), bevel=0.006)
    handwheel(p, (0, -D / 2 - 0.2, 1.03), rot=(-25, 0, 0), r=0.2, name="SteerWheel", interact="steer_wheel", m="PaintRed", spokes=6)
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
    p.use_camera((0, -1.0, 1.66), (0, -0.12, 1.12), lens=24)                # stand back enough to see the wheel and the scope
    p.hand("R", (0.2, -D / 2 - 0.25, 1.07), "grip", control="SteerWheel")
    p.hand("L", (-0.2, -D / 2 - 0.25, 1.07), "grip", control="SteerWheel")
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
    # AIM stick: trains the torpedo course on the target scope when nothing is locked
    p.cyl(0.06, 0.02, (-0.09, -0.12, desk_z + 0.01), "DarkSteel", segs=24, bevel=0.004)
    stick = p.pivot("AimStick", (-0.09, -0.12, desk_z + 0.02), interact="joystick", rotate_axes="XY", max_deg=20)
    p.add(bm_lathe([(0.0, 0.0), (0.045, 0.0), (0.04, 0.018), (0.018, 0.045), (0.0, 0.05)], 20), "Rubber", parent=stick)
    p.cyl(0.008, 0.09, (0, 0, 0.09), "Chrome", segs=12, parent=stick)
    p.add(bm_lathe([(0, 0.13), (0.02, 0.14), (0.024, 0.18), (0.02, 0.21), (0.0, 0.22)], 20), "BlackPlastic", parent=stick)
    p.decal(0.1, 0.034, (-0.09, -0.24, desk_z + 0.001), "label_aim", rot=(-90, 0, 0))
    # TUBE + / TUBE - step the tube selection
    for k, (dx, nm, lbl) in enumerate([(0, "TubeUp", "label_tube_up"), (0.1, "TubeDown", "label_tube_down")]):
        push_button(p, (-W / 2 + 0.1 + dx, -0.12, desk_z + 0.006), rot=(-90, 0, 0), m="PaintCream", r=0.022, name=nm, interact="button")
        p.decal(0.09, 0.03, (-W / 2 + 0.1 + dx, -0.2, desk_z + 0.001), lbl, rot=(-90, 0, 0))
    # DECOY (noisemaker) launch button
    p.cyl(0.042, 0.012, (0.43, -0.12, desk_z + 0.006), "DarkSteel", segs=24, bevel=0.003)
    push_button(p, (0.43, -0.12, desk_z + 0.012), rot=(-90, 0, 0), m="PaintNavy", r=0.032, name="DecoyButton", interact="decoy")
    p.decal(0.11, 0.036, (0.43, -0.24, desk_z + 0.001), "label_decoy", rot=(-90, 0, 0))
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
    p.use_camera((0, -0.75, 1.62), (0, -0.05, 1.12), lens=24)
    p.hand("R", (0.2, -0.13, 1.08), "press", control="FireButton")
    p.hand("L", (-0.09, -0.13, 1.2), "grip", control="AimStick")
    p.anchor("operate", (0, -D / 2 - 0.45, 0))
    return p.finish()


def _binocular(r, a, n=40):
    """Outline (CCW, XY) of two overlapping circles of radius r centred at x = +-a."""
    h = math.sqrt(max(r * r - a * a, 1e-6))
    t0, t1 = math.atan2(h, -a), math.atan2(h, a)
    pts = [(a + r * math.cos(-t0 + 2 * t0 * k / n), r * math.sin(-t0 + 2 * t0 * k / n)) for k in range(n + 1)]
    pts += [(-a + r * math.cos(t1 + (2 * math.pi - 2 * t1) * k / n), r * math.sin(t1 + (2 * math.pi - 2 * t1) * k / n)) for k in range(1, n)]
    return pts


_TO_FRONT = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))     # plate XY -> XZ, plate depth (+Z) -> -Y (towards the viewer)


def _front(bm):
    for v in bm.verts:
        v.co = _TO_FRONT @ v.co
    return bm


def _slot_screw(p, loc, r=0.011, parent=None, rot=0):
    p.cyl(r, 0.008, loc, "DarkSteel", axis="Y", segs=14, bevel=0.002, parent=parent, name="screw")
    p.box((r * 1.6, 0.003, r * 0.28), (loc[0], loc[1] - 0.004, loc[2]), "BlackPlastic", rot=(0, rot, 0), bevel=0, parent=parent, name="slot")


def periscope(name="Periscope", ceiling=2.9):
    """Periscope column with a detailed eyepiece station on the Head pivot, which trains 360 deg about Z.

    The eyepiece box carries: twin-ocular eyepiece in a rubber hood (the lens shows `screen_periscope`, the game
    renders the live view into it), bearing compass card, target-identification screen with MARK / CLEAR
    buttons, a numbered contact-tag slider, ZOOM and TILT knobs, and two training handles with knurled grips."""
    p = Prop(name, category="station", station="periscope")
    # ---- fixed column
    p.cyl(0.32, 0.04, (0, 0, 0.02), "PaintGraphite", segs=40, bevel=0.01)
    p.add(bm_torus(0.26, 0.02, 40, 8), "Hazard", (0, 0, 0.045), smooth=180)
    p.cyl(0.14, ceiling + 0.4, (0, 0, (ceiling + 0.4) / 2), "Steel", segs=32)
    for z in (0.5, 0.9, 2.25, 2.6):
        p.cyl(0.15, 0.03, (0, 0, z), "DarkSteel", segs=32, bevel=0.005)
    p.cyl(0.3, 0.08, (0, 0, ceiling - 0.04), "PaintGraphite", segs=40, bevel=0.01)
    p.bolts([(math.cos(a) * 0.25, math.sin(a) * 0.25, ceiling - 0.085) for a in [k * math.pi / 4 for k in range(8)]], axis="Z", r=0.012)
    p.add(bm_torus(0.2, 0.025, 48, 8), "Brass", (0, 0, 0.98), smooth=180)
    for k in range(36):
        a = k * math.pi / 18
        p.box((0.012, 0.03, 0.025 if k % 3 else 0.04), (math.cos(a) * 0.235, math.sin(a) * 0.235, 0.98), "PaintGraphite",
              rot=(0, 0, math.degrees(a) + 90), bevel=0)
    # ---- rotating head
    head = p.pivot("Head", (0, 0, 0), interact="periscope_train", rotate_axis="Z")
    p.cyl(0.19, 0.12, (0, 0, 1.06), "PaintGraphite", segs=40, bevel=0.012, parent=head)
    p.cyl(0.19, 0.08, (0, 0, 2.02), "PaintGraphite", segs=40, bevel=0.012, parent=head)
    W, D, z0, z1 = 0.66, 0.3, 0.98, 1.96
    yf = -0.05 - D                                      # front face of the box
    p.box((W, D, z1 - z0), (0, -0.05 - D / 2, (z0 + z1) / 2), "PaintTeal", bevel=0.035, segs=1, parent=head, name="housing")
    p.box((W - 0.12, 0.05, 0.12), (0, -0.04, 1.06), "PaintTeal", bevel=0.015, parent=head)       # straps to the collars
    p.box((W - 0.12, 0.05, 0.1), (0, -0.04, 1.97), "PaintTeal", bevel=0.015, parent=head)
    for sx in (-1, 1):
        for sz in (z0 + 0.05, z1 - 0.05):
            _slot_screw(p, (sx * (W / 2 - 0.05), yf - 0.004, sz), parent=head, rot=35 * sx)
    # lower control panel (dark inset with screws)
    p.box((W - 0.07, 0.012, 0.36), (0, yf - 0.004, 1.19), "PaintGraphite", bevel=0.01, parent=head, name="panel")
    for sx in (-1, 1):
        for sz in (1.03, 1.35):
            _slot_screw(p, (sx * (W / 2 - 0.07), yf - 0.012, sz), r=0.008, parent=head, rot=-20)
    # ---- eyepiece: metal frame, rubber hood, lens
    ez = 1.69
    frame = _front(bm_plate_with_holes(_binocular(0.15, 0.125), [list(reversed(_binocular(0.112, 0.112)))], 0.025))
    p.add(frame, "DarkSteel", (0, yf, ez), parent=head, smooth=40, name="eyeframe")
    hood = _front(bm_plate_with_holes(_binocular(0.138, 0.118), [list(reversed(_binocular(0.108, 0.11)))], 0.075))
    p.add(hood, "Rubber", (0, yf - 0.02, ez), parent=head, smooth=40, name="eyehood")
    lip = _front(bm_plate_with_holes(_binocular(0.146, 0.118), [list(reversed(_binocular(0.13, 0.118)))], 0.012))
    p.add(lip, "Rubber", (0, yf - 0.085, ez), parent=head, smooth=40, name="eyelip")
    outline = _binocular(0.108, 0.11, 48)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    xs, ys = [q[0] for q in outline], [q[1] for q in outline]
    face = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in outline])
    for loop in face.loops:
        loop[uvl].uv = ((loop.vert.co.x - min(xs)) / (max(xs) - min(xs)), (loop.vert.co.y - min(ys)) / (max(ys) - min(ys)))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    p.add(_front(bm), "screen_periscope", (0, yf - 0.012, ez), parent=head, uv="keep", smooth=False, name="Lens")
    # ---- bearing compass
    cz = 1.475
    p.add(bm_torus(0.072, 0.012, 40, 8, "Y"), "DarkSteel", (0, yf - 0.012, cz), parent=head, smooth=180, name="compassbezel")
    p.cyl(0.075, 0.02, (0, yf + 0.0, cz), "BlackPlastic", axis="Y", segs=40, parent=head)
    card = p.pivot("CompassCard", (0, yf - 0.012, cz), parent=head, interact="compass", rotate_axis="Y", note="turns with the bearing")
    p.add(bm_disc(0.064, 48), "compass_card", (0, 0, 0), (0, 0, 0), card, uv="keep", smooth=False, name="card")
    p.extrude([(-0.012, 0.0), (0.012, 0.0), (0.0, 0.026)], 0.004, (0, yf - 0.02, cz + 0.042), "LampBlue", rot=(90, 0, 180),
              parent=head, name="lubber")
    p.cyl(0.01, 0.008, (0, yf - 0.02, cz), "Chrome", axis="Y", segs=12, parent=head)
    # ---- target identification screen with MARK / CLEAR
    sz = 1.255
    p.plate(0.3, 0.032, (0, yf - 0.012, sz + 0.095), "label_target_id", parent=head, depth=0.006)
    p.screen(0.28, 0.13, (0, yf - 0.012, sz), "screen_target_id", parent=head, bezel=0.022, depth=0.03, frame="BlackPlastic")
    for side, nm, lab in ((-1, "MarkButton", "label_mark"), (1, "ClearButton", "label_clear")):
        bx = side * 0.235
        p.box((0.1, 0.02, 0.12), (bx, yf - 0.014, sz), "PaintGraphite", bevel=0.008, parent=head)
        for dz in (-0.048, 0.048):
            _slot_screw(p, (bx - 0.038, yf - 0.025, sz + dz), r=0.006, parent=head)
            _slot_screw(p, (bx + 0.038, yf - 0.025, sz + dz), r=0.006, parent=head)
        btn = p.pivot(nm, (bx, yf - 0.026, sz), parent=head, interact="mark_target" if side < 0 else "clear_target", translate_axis="Y",
                      min=0, max=0.008)
        p.box((0.07, 0.016, 0.07), (0, -0.006, 0), "PaintMustard" if side < 0 else "PaintCream", bevel=0.008, parent=btn)
        p.decal(0.056, 0.018, (0, -0.0145, 0), lab, parent=btn)
    # ---- contact tag selector (numbered strip + slider)
    tz = 1.085
    p.box((0.36, 0.012, 0.11), (0, yf - 0.012, tz - 0.01), "DarkSteel", bevel=0.006, parent=head)
    p.decal(0.34, 0.043, (0, yf - 0.0185, tz + 0.02), "tag_strip", parent=head)
    p.box((0.32, 0.006, 0.012), (0, yf - 0.019, tz - 0.035), "BlackPlastic", bevel=0, parent=head, name="slot")
    sl = p.pivot("TagSlider", (-0.1488, yf - 0.02, tz - 0.035), parent=head, interact="tag_select", translate_axis="X", min=0, max=0.2975,
                 note="8 stops, 0.0425 m apart; stop 1 at the left")
    p.box((0.03, 0.03, 0.04), (0, -0.012, 0.0), "PaintRed", bevel=0.006, parent=sl, name="slidercap")
    for k in range(4):
        p.box((0.032, 0.004, 0.003), (0, -0.028, -0.013 + k * 0.009), "DarkSteel", bevel=0, parent=sl)
    # ---- ZOOM and TILT knobs
    for side, nm, cap, lab in ((-1, "ZoomKnob", "PaintRed", "label_zoom"), (1, "TiltKnob", "PaintNavy", "label_tilt")):
        kx = side * 0.255
        p.cyl(0.062, 0.012, (kx, yf - 0.012, tz), "Brass", axis="Y", segs=40, bevel=0.003, parent=head)
        p.decal(0.07, 0.018, (kx, yf - 0.012, tz + 0.085), lab, parent=head)
        kn = p.pivot(nm, (kx, yf - 0.018, tz), parent=head, interact="knob", rotate_axis="Y")
        p.cyl(0.05, 0.04, (0, -0.02, 0), "PaintSeafoam", axis="Y", segs=40, bevel=0.004, parent=kn, name="knurl")
        for k in range(28):
            a = k * 2 * math.pi / 28
            p.box((0.006, 0.036, 0.008), (math.cos(a) * 0.05, -0.02, math.sin(a) * 0.05), "PaintSeafoam",
                  rot=(0, -math.degrees(a), 0), bevel=0, parent=kn)
        p.add(bm_lathe([(0.0, 0.0), (0.03, 0.0), (0.032, 0.006), (0.026, 0.016), (0.0, 0.02)], 32, "Y"), cap,
              (0, -0.04, 0), (0, 0, 180), kn, smooth=50, name="cap")
        p.box((0.004, 0.004, 0.024), (0, -0.0605, 0.012), "PaintWhite", bevel=0, parent=kn, name="index")
    # ---- training handles: an angled bracket brings each knurled grip forward to where your hands are
    hz = 1.42                                            # chest height: where your hands naturally rest
    gy = -0.56                                           # flat brackets carry the grips out towards you
    for side in (-1, 1):
        root = (side * (W / 2 + 0.03), gy)
        h = p.pivot("HandleL" if side < 0 else "HandleR", (root[0], root[1], hz), parent=head,
                    interact="periscope_handle", rotate_axis="X", min_deg=-90, max_deg=0, note="fold down to stow")
        ax, ay = side * (W / 2 + 0.012), -0.16            # where the bracket is bolted to the box side
        # flat bracket: a thick plate running forward along the box side, bolted on with two hex bolts
        ln = abs(root[1] - ay)
        p.box((0.028, ln + 0.05, 0.12), (ax + side * 0.004, (ay + root[1]) / 2, hz), "PaintTeal", bevel=0.012,
              parent=head, name="bracket")
        for by in (ay - 0.035, ay - 0.1):
            p.cyl(0.013, 0.012, (ax + side * 0.024, by, hz), "DarkSteel", axis="X", segs=6, bevel=0.002, parent=head, name="bolt")
        # hub at the front end: the fold pivot, with a big slotted screw on its face
        p.cyl(0.05, 0.05, (root[0] - side * 0.006, root[1], hz), "PaintTeal", axis="X", segs=32, bevel=0.01, parent=head, name="hub")
        p.cyl(0.026, 0.01, (root[0] - side * 0.006, root[1] - 0.028, hz), "Steel", axis="Y", segs=24, bevel=0.003,
              parent=head, name="bigscrew")
        p.box((0.036, 0.004, 0.007), (root[0] - side * 0.006, root[1] - 0.034, hz), "BlackPlastic", rot=(0, 30, 0), bevel=0,
              parent=head)
        # shaft, collar and knurled rubber grip (turn with the handle when it folds)
        p.cyl(0.018, 0.034, (side * 0.036, 0, 0), "Chrome", axis="X", segs=16, parent=h, name="shaft")
        p.cyl(0.04, 0.016, (side * 0.055, 0, 0), "DarkSteel", axis="X", segs=32, bevel=0.005, parent=h, name="collar")
        L = 0.15
        prof = [(0.0, 0.0), (0.034, 0.0)]
        for k in range(11):
            prof += [(0.036, 0.008 + k * 0.0125), (0.032, 0.0142 + k * 0.0125)]
        prof += [(0.036, L - 0.006), (0.03, L), (0.0, L)]
        p.add(bm_lathe(prof, 28, "X"), "Rubber", (side * 0.062 if side > 0 else -0.062 - L, 0, 0), parent=h, smooth=40, name="grip")
    # ---- top: label and cables into the column
    p.plate(0.36, 0.06, (0, yf - 0.004, 1.9), "label_periscope", parent=head, depth=0.008)
    for k, (x, m) in enumerate([(-0.2, "BlackPlastic"), (0.16, "PaintRed"), (0.22, "BlackPlastic")]):
        p.tube([(x, -0.12, z1), (x, -0.12, z1 + 0.1), (x * 0.4, -0.02, z1 + 0.22), (x * 0.3, 0.0, z1 + 0.4)], 0.012, m, segs=8,
               round_r=0.06, parent=head)
    # ---- camera, hands, anchor
    p.use_camera((0, -1.0, 1.63), (0, -0.2, 1.42), lens=20, parent=head)
    gx = W / 2 + 0.03 + 0.062 + 0.045                    # middle of the grip, where the palm closes
    p.hand("L", (-gx, gy, hz), "bar", parent=head, control="HandleL")
    p.hand("R", (gx, gy, hz), "bar", parent=head, control="HandleR")
    p.anchor("operate", (0, -1.02, 0), note="anchor rotates with Head in game")
    return p.finish()


STATUS_PAGES = ["noise", "air", "engines", "power", "leaks", "flood", "fire", "heat"]


def ship_status(name="ShipStatus"):
    """Standing diagnostics console: system-page screen, eight page keys, guarded GENERAL ALARM, side handles.

    Faces -Y. The game draws the selected page (noise, air, engines, power, leaks, flooding, fire, crew) on
    screen_status; Page1..Page8 and AlarmButton push in along +Y.
    """
    p = Prop(name, category="station", station="status")
    W = 1.0
    # lower cabinet with a desk top, upper instrument tower set back
    p.box((W - 0.08, 0.44, 0.1), (0, -0.02, 0.05), "PaintGraphite", bevel=0.01)
    p.box((W, 0.48, 0.86), (0, -0.02, 0.1 + 0.43), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.04, 0.54, 0.05), (0, -0.04, 0.985), "PaintGraphite", bevel=0.01)
    louver(p, (0, -0.262, 0.42), w=0.7, h=0.22, n=5)
    yf = -0.03                                       # tower front face
    p.box((W, 0.3, 0.98), (0, yf + 0.15, 1.01 + 0.49), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.02, 0.32, 0.04), (0, yf + 0.15, 2.0), "PaintGraphite", bevel=0.008)
    # inset face panel (darker) holding screen + keys
    p.box((W - 0.16, 0.012, 0.86), (0, yf - 0.006, 1.47), "PaintSeafoam", bevel=0.006)
    yp = yf - 0.012
    p.screen(0.56, 0.36, (0, yp, 1.64), "screen_status", bezel=0.035, depth=0.03)
    for sx in (-1, 1):                              # screen bezel screws
        for sz in (-1, 1):
            _slot_screw(p, (sx * 0.31, yp - 0.016, 1.64 + sz * 0.2), r=0.008, rot=sx * sz * 30)
    # eight page keys: two rows of four, labelled, back-lit
    for k, pg in enumerate(STATUS_PAGES):
        x, z = -0.255 + (k % 4) * 0.12, 1.33 - (k // 4) * 0.085
        p.box((0.112, 0.02, 0.076), (x, yp + 0.0, z), "BlackPlastic", bevel=0.004)          # key well
        key = p.pivot(f"Page{k + 1}", (x, yp - 0.012, z), interact="page_button", translate_axis="Y", min=0, max=0.008,
                      page=pg)
        p.box((0.1, 0.022, 0.064), (0, 0, 0), "PaintCream", parent=key, bevel=0.006)
        p.decal(0.086, 0.027, (0, -0.0115, 0), f"label_pg_{pg}", parent=key)
    # general alarm: big red mushroom under a hinged guard on a hazard plate
    ax, az = 0.33, 1.3
    p.box((0.16, 0.012, 0.2), (ax, yp - 0.002, az), "Hazard", bevel=0.004)
    alarm = p.pivot("AlarmButton", (ax, yp - 0.01, az), interact="alarm", translate_axis="Y", min=0, max=0.012)
    p.cyl(0.032, 0.03, (0, -0.012, 0), "DarkSteel", axis="Y", segs=24, parent=alarm)
    p.add(bm_lathe([(0, 0), (0.05, 0), (0.052, -0.01), (0.045, -0.026), (0, -0.032)], 28, "Y"), "PaintRed",
          (0, -0.026, 0), parent=alarm, smooth=40)
    guard = p.pivot("AlarmGuard", (ax, yp - 0.02, az + 0.075), interact="guard", rotate_axis="X", min_deg=-110, max_deg=0)
    p.box((0.13, 0.006, 0.15), (0, -0.05, -0.075), "LampRed", parent=guard, bevel=0.002)            # flip-up cover
    for sx in (-1, 1):
        p.box((0.006, 0.05, 0.15), (sx * 0.062, -0.025, -0.075), "LampRed", parent=guard, bevel=0.002)
    p.decal(0.15, 0.03, (ax, yp - 0.009, az - 0.125), "label_general_alarm")
    # status lamps and a few toggles on the desk
    for k in range(6):
        indicator(p, (-0.36 + k * 0.08, yp - 0.006, 1.86), m=["LampGreen", "LampGreen", "LampAmber", "LampGreen", "LampRed", "LampGreen"][k], r=0.012)
    for k in range(4):
        toggle(p, (-0.3 + k * 0.1, -0.2, 1.01), rot=(-90, 0, 0), name=f"DeskToggle{k + 1}", up=k % 2 == 0)
    p.plate(0.5, 0.08, (0, yp - 0.004, 1.94 - 0.03), "label_ship_status")
    # side handles to hold on to when the boat rolls (vertical, on the tower front edges)
    for side in (-1, 1):
        grab_rail(p, (side * (W / 2 - 0.035), yf - 0.01, 1.2), (side * (W / 2 - 0.035), yf - 0.01, 1.78), standoff=0.06,
                  axis_out=(0, -1, 0), r=0.017)
        louver(p, (side * (W / 2 + 0.002), 0.05, 1.5), rot=(0, 0, side * -90), w=0.2, h=0.4, n=7)
    p.use_camera((0, -0.82, 1.64), (0, -0.05, 1.47), lens=24)
    p.hand("L", (-(W / 2 - 0.035), yf - 0.075, 1.45), "grip", control="HandleL")
    p.hand("R", (0.0, yp - 0.03, 1.29), "press", control="Page2")
    p.anchor("operate", (0, -0.75, 0))
    return p.finish()


def mission_wall(name="MissionWall"):
    """Control-room wall unit: big MISSION MAP screen, MISSION board, BOW and STERN camera monitors, desk. Faces -Y."""
    p = Prop(name, category="station", station="mission")
    W = 1.95
    # desk cabinets
    p.box((W - 0.08, 0.44, 0.1), (0, -0.25, 0.05), "PaintGraphite", bevel=0.01)
    p.box((W, 0.5, 0.86), (0, -0.25, 0.1 + 0.43), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.04, 0.56, 0.05), (0, -0.27, 0.985), "PaintGraphite", bevel=0.01)
    for k in range(3):
        x = -0.64 + k * 0.64
        p.box((0.56, 0.014, 0.66), (x, -0.505, 0.52), "PaintCream", bevel=0.008)
        louver(p, (x, -0.515, 0.52), w=0.4, h=0.3, n=6)
        p.box((0.012, 0.02, 0.12), (x + 0.24, -0.522, 0.6), "Chrome", bevel=0.003)
    # upper unit, set back against the hull
    p.box((W, 0.22, 1.14), (0, -0.11, 1.01 + 0.57), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.02, 0.26, 0.04), (0, -0.12, 2.17), "PaintGraphite", bevel=0.008)
    yf = -0.222
    p.box((1.12, 0.012, 0.86), (-0.12, yf - 0.004, 1.6), "PaintSeafoam", bevel=0.006)
    p.screen(0.98, 0.6, (-0.12, yf - 0.01, 1.58), "screen_mission_map", bezel=0.04, depth=0.04)
    p.plate(0.5, 0.07, (-0.12, yf - 0.014, 1.99), "label_mission_map")
    p.screen(0.34, 0.52, (0.69, yf, 1.58), "screen_mission", bezel=0.03, depth=0.035)
    p.plate(0.3, 0.06, (0.69, yf - 0.004, 1.95), "label_mission")
    for k, (z, lbl) in enumerate([(1.8, "label_bow_cam"), (1.38, "label_stern_cam")]):
        p.screen(0.3, 0.22, (-0.81, yf, z), f"screen_extcam{k + 1}", bezel=0.025, depth=0.03)
        p.decal(0.18, 0.032, (-0.81, yf - 0.02, z - 0.138), lbl)
    # map zoom knob and camera switch on the desk, a strip of lamps, two keyboards
    knob(p, (-0.62, -0.3, 1.01), rot=(-90, 0, 0), r=0.035, name="MapZoom", interact="dial", m="Bakelite")
    p.decal(0.1, 0.032, (-0.62, -0.39, 1.011), "label_zoom", rot=(-90, 0, 0))
    push_button(p, (-0.81, -0.3, 1.012), rot=(-90, 0, 0), m="PaintMustard", r=0.026, name="CamSwitch", interact="button")
    p.decal(0.1, 0.032, (-0.81, -0.39, 1.011), "label_view", rot=(-90, 0, 0))
    for x, w in [(-0.12, 0.46), (0.69, 0.3)]:
        p.box((w, 0.15, 0.022), (x, -0.33, 1.022), "BlackPlastic", rot=(7, 0, 0), bevel=0.006)
        for row in range(3):
            for col in range(int(w / 0.032)):
                p.box((0.022, 0.022, 0.008), (x - w / 2 + 0.022 + col * 0.032, -0.37 + row * 0.035, 1.034 + row * 0.004),
                      "PaintCream" if (row + col) % 7 else "PaintMustard", bevel=0.002, name="key")
    for k in range(10):
        indicator(p, (-0.75 + k * 0.17, yf - 0.004, 2.1), m=["LampGreen", "LampAmber", "LampGreen", "LampRed"][k % 4], r=0.01)
    for side in (-1, 1):
        grab_rail(p, (side * (W / 2 - 0.03), yf - 0.01, 1.2), (side * (W / 2 - 0.03), yf - 0.01, 1.9), standoff=0.06,
                  axis_out=(0, -1, 0), r=0.017)
    p.use_camera((0, -1.25, 1.62), (0, -0.2, 1.52), lens=21)
    p.hand("L", (-0.5, -0.38, 1.03), "palm")
    p.hand("R", (-0.62, -0.32, 1.06), "knob", control="MapZoom")
    p.anchor("operate", (0, -0.9, 0))
    return p.finish()


CCTV_ROOMS = ["torpedo", "battery", "engine", "galley", "mess", "quarters"]


def camera_console(name="CameraConsole"):
    """Standing CCTV console: live screen of the compartment cameras, six CAM keys, side handles. Faces -Y."""
    p = Prop(name, category="station", station="cameras")
    W = 0.86
    p.box((W - 0.08, 0.42, 0.1), (0, -0.02, 0.05), "PaintGraphite", bevel=0.01)
    p.box((W, 0.46, 0.86), (0, -0.02, 0.1 + 0.43), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.04, 0.52, 0.05), (0, -0.04, 0.985), "PaintGraphite", bevel=0.01)
    louver(p, (0, -0.252, 0.42), w=0.56, h=0.22, n=5)
    yf = -0.03
    p.box((W, 0.3, 0.98), (0, yf + 0.15, 1.01 + 0.49), "PaintCream", bevel=0.02, segs=3)
    p.box((W + 0.02, 0.32, 0.04), (0, yf + 0.15, 2.0), "PaintGraphite", bevel=0.008)
    p.box((W - 0.14, 0.012, 0.84), (0, yf - 0.006, 1.47), "PaintSeafoam", bevel=0.006)
    yp = yf - 0.012
    p.screen(0.5, 0.36, (0, yp, 1.64), "screen_cctv", bezel=0.035, depth=0.03)
    for k, room in enumerate(CCTV_ROOMS):
        x, z = -0.2 + (k % 3) * 0.2, 1.33 - (k // 3) * 0.085
        p.box((0.17, 0.02, 0.07), (x, yp, z), "BlackPlastic", bevel=0.004)
        key = p.pivot(f"Cam{k + 1}", (x, yp - 0.012, z), interact="page_button", translate_axis="Y", min=0, max=0.008, room=room)
        p.box((0.155, 0.022, 0.058), (0, 0, 0), "PaintCream", parent=key, bevel=0.006)
        p.decal(0.13, 0.03, (0, -0.0115, 0), f"label_cam_{room}", parent=key)
    for k in range(5):
        indicator(p, (-0.3 + k * 0.15, yp - 0.006, 1.86), m="LampRed" if k == 0 else "LampGreen", r=0.011)
    p.plate(0.42, 0.075, (0, yp - 0.004, 1.94 - 0.03), "label_cameras")
    for side in (-1, 1):
        grab_rail(p, (side * (W / 2 - 0.03), yf - 0.01, 1.2), (side * (W / 2 - 0.03), yf - 0.01, 1.78), standoff=0.06,
                  axis_out=(0, -1, 0), r=0.017)
    p.use_camera((0, -0.8, 1.64), (0, -0.05, 1.47), lens=24)
    p.hand("L", (-(W / 2 - 0.03), yf - 0.075, 1.45), "grip")
    p.hand("R", (0.0, yp - 0.03, 1.29), "press", control="Cam2")
    p.anchor("operate", (0, -0.75, 0))
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
    # hydrophone training wheel on the desk front: turn it to listen in one direction
    p.box((0.16, 0.08, 0.12), (0, -D + 0.02, 0.84), "PaintGraphite", bevel=0.01)
    handwheel(p, (0, -D - 0.035, 0.86), rot=(0, 0, 0), r=0.13, name="TrainWheel", interact="sonar_wheel", m="PaintNavy", spokes=3)
    p.decal(0.2, 0.04, (0, -D + 0.005, 0.735), "label_train")
    # signal-strength meter beside the scope
    gauge(p, (-0.4, -0.302, 1.08), r=0.06, face="gauge_signal", name="SignalGauge", needle_deg=-60)
    # PING and LOCK push buttons
    for x, nm, lbl, mm in [(0.3, "PingButton", "label_ping", "PaintRed"), (0.46, "LockButton", "label_lock", "PaintNavy")]:
        push_button(p, (x, -0.302, 1.07), m=mm, r=0.03, name=nm, interact="button")
        p.decal(0.11, 0.035, (x, -0.304, 1.0), lbl)
    # GAIN slider 1..10
    p.box((0.42, 0.012, 0.05), (0, -0.302, 0.96), "BlackPlastic", bevel=0.004)
    p.decal(0.4, 0.04, (0, -0.31, 0.96), "sign_scale_10")
    sl = p.pivot("GainSlider", (-0.1, -0.312, 0.96), interact="slider", translate_axis="X", min=-0.18, max=0.18)
    p.box((0.03, 0.02, 0.06), (0, 0, 0), "PaintRed", parent=sl, bevel=0.005)
    p.decal(0.12, 0.03, (-0.32, -0.304, 0.96), "label_gain")
    p.plate(0.5, 0.09, (0, -0.31, 1.69), "label_sonar")
    # headphones on a hook
    p.box((0.02, 0.06, 0.02), (W / 2 + 0.01, -0.12, 1.55), "Chrome", bevel=0.004)
    hp = p.pivot("Headphones", (W / 2 + 0.03, -0.16, 1.5), interact="pickup")
    p.add(bm_torus(0.09, 0.012, 32, 8, "Y", angle=math.pi), "BlackPlastic", (0, 0, 0.0), (0, 0, 90), parent=hp, smooth=180)
    for sy in (-1, 1):
        p.cyl(0.045, 0.035, (0, sy * 0.095, -0.03), "Leather", axis="Y", segs=20, parent=hp, bevel=0.01)
    p.tube([(0, 0.11, -0.05), (0.02, 0.12, -0.25), (-0.05, 0.05, -0.62), (-0.2, 0.05, -0.7)], 0.004, "BlackPlastic",
           round_r=0.1, parent=hp)
    p.use_camera((0, -0.9, 1.55), (0, -0.3, 1.32), lens=26)
    p.hand("R", (0.11, -D - 0.09, 0.9), "grip", control="TrainWheel")
    p.hand("L", (-0.11, -D - 0.09, 0.9), "grip", control="TrainWheel")
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
    p.screen(0.38, 0.28, (-0.485, f - 0.002, z0 + 0.8), "screen_ballast", bezel=0.025, depth=0.03)     # dive profile
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
    p.use_camera((0, -1.0, 1.55), (0, -0.2, 1.12), lens=24)
    p.hand("L", (-0.1, -0.335, z0 + 0.4), "grip", control="VentValve")
    p.hand("R", (0.1, -0.335, z0 + 0.4), "grip", control="VentValve")
    p.anchor("operate", (0, -0.75, 0))
    return p.finish()
