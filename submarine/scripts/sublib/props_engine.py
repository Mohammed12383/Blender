"""Engine room: diesel engines, motor-generators, shaft lines, engine control console, fuel station,
jerrycans, oil cans and stores shelving.

Engines run along X (flywheel at +X). `s` is the side the service gear faces (+1 = +Y, -1 = -Y),
so the port and starboard engines both present their gauges, valves and buttons to the catwalk.
"""

import math

import bmesh
from mathutils import Matrix, Vector

from .core import (Prop, R, bm_box, bm_cyl, bm_disc, bm_extrude, bm_lathe, bm_plate_with_holes, bm_sweep, bm_torus,
                   circle, rect, rrect, rounded_path, sag_path)
from .props_common import gauge, handwheel, indicator, knob, louver, push_button, toggle


def static_dial(p, loc, rot, r, face, parent=None):
    """Small gauge without a moving needle (keeps the node count down)."""
    from mathutils import Euler
    e = Euler([R(a) for a in rot])

    def off(v):
        v = Vector(v)
        v.rotate(e)
        return Vector(loc) + v
    p.cyl(r * 1.05, 0.03, off((0, 0.015, 0)), "PaintGraphite", rot=rot, axis="Y", segs=20, parent=parent, name="dialcup")
    p.add(bm_torus(r, r * 0.13, 20, 6, "Y"), "Brass", off((0, -0.001, 0)), rot, parent, smooth=180, name="dialbezel")
    p.add(bm_disc(r * 0.92, 20), face, off((0, -0.0005, 0)), rot, parent, uv="keep", smooth=False, name="dialface")
    p.box((0.003, 0.002, r * 0.7), off((r * 0.15, -0.003, r * 0.2)), "PaintRed", rot=(rot[0], rot[1] + 35, rot[2]), bevel=0,
          parent=parent, name="dialneedle")


def _belt(p, centers, radii, x, m="Rubber", parent=None):
    """V-belt wrapped around pulleys (YZ plane at x)."""
    pts = []
    n = len(centers)
    cx = sum(c[0] for c in centers) / n
    cz = sum(c[1] for c in centers) / n
    order = sorted(range(n), key=lambda i: math.atan2(centers[i][1] - cz, centers[i][0] - cx))
    for i in order:
        (y, z), r = centers[i], radii[i]
        a0 = math.atan2(z - cz, y - cx)
        for k in range(-6, 7):
            a = a0 + k * math.pi / 14
            pts.append(Vector((x, y + math.cos(a) * (r + 0.012), z + math.sin(a) * (r + 0.012))))
    bm = bm_sweep(pts, [(-0.012, -0.008), (0.012, -0.008), (0.009, 0.008), (-0.009, 0.008)], caps=False, closed_path=True,
                  up=(1, 0, 0))
    p.add(bm, m, parent=parent, smooth=60, name="belt")


def diesel_engine(name="DieselEngine", s=-1, label="label_diesel1", engine_id=1):
    """8-cylinder marine diesel. Origin at the centre of the bedplate on the pit floor."""
    p = Prop(name, category="machine", station="engine", engine=engine_id, service_side=s)
    Y = lambda y: s * y
    face = (0, 0, 0) if s < 0 else (0, 0, 180)
    m = "PaintEngine"
    pitch, n, x0 = 0.62, 8, -2.17
    xs = [x0 + i * pitch for i in range(n)]
    # bedplate and holding-down feet
    for sy in (-1, 1):
        p.box((5.8, 0.14, 0.22), (-0.15, sy * 0.58, 0.11), "PaintGraphite", bevel=0.01)
        for k in range(6):
            fx = -2.85 + k * 1.08
            p.box((0.24, 0.3, 0.04), (fx, sy * 0.68, 0.02), "DarkSteel", bevel=0.005)
            p.bolts([(fx - 0.07, sy * 0.76, 0.045), (fx + 0.07, sy * 0.76, 0.045)], axis="Z", r=0.018, h=0.03)
    # sump, crankcase, inspection doors
    p.box((4.9, 0.86, 0.42), (-0.15, 0, 0.26), m, bevel=0.03)
    p.cyl(0.03, 0.06, (-2.45, Y(0.44), 0.12), "Brass", axis="Y", segs=12)
    p.box((5.4, 1.06, 0.82), (-0.1, 0, 0.82), m, bevel=0.03, segs=3)
    for sy in (-1, 1):
        for x in xs:
            door = bm_extrude(rrect(0.42, 0.36, 0.06, 4), 0.026)
            p.add(door, m, (x, sy * 0.535, 0.82), (90, 0, 0), bevel=0.006, name="door")
            p.bolts([(x + dx, sy * 0.552, 0.82 + dz) for dx in (-0.17, 0.17) for dz in (-0.13, 0.13)], r=0.013, h=0.014)
            p.cyl(0.035, 0.03, (x, sy * 0.56, 0.82), "Brass", axis="Y", segs=12)
    # cylinder block with webs
    p.box((5.1, 0.9, 0.62), (-0.15, 0, 1.52), m, bevel=0.02)
    for i in range(n + 1):
        p.box((0.045, 0.96, 0.6), (x0 - pitch / 2 + i * pitch, 0, 1.52), m, bevel=0.006)
    # heads, studs, rocker covers, injectors, exhaust stubs, head thermometers, fuel lines
    for i, x in enumerate(xs):
        p.box((0.56, 0.88, 0.24), (x, 0, 1.95), m, bevel=0.02)
        for dx in (-0.2, 0.2):
            for dy in (-0.33, 0.33):
                p.cyl(0.026, 0.045, (x + dx, dy, 2.09), "Steel", segs=6)
        p.box((0.46, 0.62, 0.14), (x, 0, 2.14), "PaintRed", bevel=0.045, segs=3)
        for dx in (-0.12, 0.12):
            p.sphere(0.022, (x + dx, 0, 2.215), "Chrome", segs=10, rings=5)
        if i % 2 == 0:
            p.cyl(0.035, 0.05, (x + 0.13, Y(0.17), 2.235), "BlackPlastic", segs=12)
        p.cyl(0.03, 0.14, (x - 0.06, Y(0.5), 2.0), "Steel", axis="Y", segs=10)
        p.cyl(0.024, 0.03, (x - 0.06, Y(0.58), 2.0), "Brass", axis="Y", segs=6)
        p.tube([(x - 0.06, Y(0.6), 2.0), (x - 0.06, Y(0.66), 1.96), (x - 0.02, Y(0.68), 1.7), (x + 0.05, Y(0.66), 1.52)],
               0.008, "Copper", segs=6, round_r=0.05)
        p.tube([(x, Y(-0.44), 1.95), (x, Y(-0.6), 1.95), (x + 0.08, Y(-0.7), 1.86)], 0.065, "DarkSteel", segs=12, round_r=0.08)
        static_dial(p, (x + 0.18, Y(0.445), 1.93), face, 0.032, "gauge_pressure")
        if i in (0, n - 1):
            p.add(bm_torus(0.05, 0.012, 16, 6, "Y"), "Steel", (x, 0, 2.27), smooth=180)
    # fuel injection pump with delivery valves and rail
    p.box((4.7, 0.17, 0.22), (-0.25, Y(0.62), 1.4), "PaintGraphite", bevel=0.02)
    for x in xs:
        p.cyl(0.025, 0.09, (x + 0.05, Y(0.64), 1.55), "Brass", segs=8)
    p.cyl(0.02, 4.8, (-0.25, Y(0.72), 1.3), "Copper", axis="X", segs=10)
    p.box((5.0, 0.18, 0.16), (-0.2, Y(0.52), 1.75), "PaintGray", bevel=0.03)          # intake manifold
    # lagged exhaust manifold
    p.cyl(0.11, 5.0, (-0.2, Y(-0.74), 1.85), "DarkSteel", axis="X", segs=20)
    for k in range(10):
        p.cyl(0.128, 0.13, (-2.6 + k * 0.55, Y(-0.74), 1.85), "Lagging", axis="X", segs=20, bevel=0.01)
    # turbocharger, air filter, exhaust uptake with bellows
    tx = -3.05
    p.tube([(-2.7, Y(-0.74), 1.85), (tx, Y(-0.74), 1.85), (tx, Y(-0.5), 2.02)], 0.1, "DarkSteel", segs=16, round_r=0.12)
    p.add(bm_torus(0.16, 0.1, 24, 10, "X"), "DarkSteel", (tx, Y(-0.42), 2.05), smooth=180, name="turbine")
    p.cyl(0.13, 0.2, (tx, Y(-0.42), 2.05), "DarkSteel", axis="X", segs=20)
    p.cyl(0.06, 0.32, (tx, Y(-0.22), 2.05), "Steel", axis="Y", segs=12)
    p.add(bm_torus(0.15, 0.09, 24, 10, "X"), "Steel", (tx, Y(-0.02), 2.05), smooth=180, name="compressor")
    p.cyl(0.12, 0.18, (tx, Y(-0.02), 2.05), "Steel", axis="X", segs=20)
    pleat = [(0.0, 0.0), (0.16, 0.0)] + [((0.17 if k % 2 else 0.19), 0.02 + k * 0.016) for k in range(20)] + [(0.16, 0.36), (0.0, 0.36)]
    p.lathe(pleat, (tx, Y(0.12), 2.05), "PaintGray", segs=32, axis="Y", rot=(0, 0, 180 if s < 0 else 0), smooth=30)
    p.tube([(tx, Y(-0.02), 2.15), (tx + 0.15, Y(0.2), 2.25), (-2.6, Y(0.52), 1.9)], 0.07, "Steel", segs=12, round_r=0.12)
    up = [(tx, Y(-0.42), 2.17), (tx, Y(-0.42), 2.45)]
    p.tube(up, 0.11, "DarkSteel", segs=16)
    bell = [(0.12 if k % 2 else 0.14, k * 0.03) for k in range(11)]
    p.lathe([(0.0, 0.0)] + bell + [(0.0, 0.3)], (tx, Y(-0.42), 2.45), "Steel", segs=24, smooth=30)
    p.tube([(tx, Y(-0.42), 2.75), (tx, Y(-0.42), 4.0)], 0.12, "Lagging", segs=16)
    for k in range(4):
        p.cyl(0.128, 0.05, (tx, Y(-0.42), 2.9 + k * 0.3), "DarkSteel", segs=16)
    # front end: timing cover, pulleys, belts, water pump, heat exchanger, coolant pipes, coolant valve
    tc = bm_extrude(rrect(0.95, 1.0, 0.22, 6), 0.1)
    p.add(tc, m, (-2.9, 0, 0.95), (0, 90, 0), bevel=0.02, name="timing")
    pulleys = [((0.0, 0.62), 0.2), ((0.28, 1.08), 0.11), ((-0.28, 1.08), 0.11)]
    for (py, pz), r in pulleys:
        p.cyl(r, 0.06, (-3.0, py, pz), "DarkSteel", axis="X", segs=24, bevel=0.006)
        p.cyl(r * 0.3, 0.08, (-3.0, py, pz), "Steel", axis="X", segs=12)
    _belt(p, [(py, pz) for (py, pz), _ in pulleys], [r for _, r in pulleys], -3.0)
    p.add(bm_torus(0.11, 0.06, 20, 8, "X"), "PaintTeal", (-2.98, Y(0.28), 1.08), smooth=180, name="waterpump")
    p.cyl(0.21, 1.1, (-3.05, 0, 1.55), "PaintTeal", axis="Y", segs=24, bevel=0.01)
    for sy in (-1, 1):
        p.cyl(0.235, 0.05, (-3.05, sy * 0.55, 1.55), "PaintTeal", axis="Y", segs=24, bevel=0.006)
        p.bolts([(-3.05 + math.cos(a) * 0.2, sy * 0.58, 1.55 + math.sin(a) * 0.2) for a in [k * math.pi / 4 for k in range(8)]],
                r=0.012, h=0.02)
    p.tube([(-3.05, Y(0.3), 1.33), (-3.05, Y(0.42), 1.2), (-2.75, Y(0.6), 1.15), (2.3, Y(0.6), 1.15)], 0.045, "PaintTeal",
           segs=12, round_r=0.12)
    p.tube([(-3.05, Y(-0.3), 1.76), (-2.9, Y(-0.35), 2.0), (-2.6, Y(0.0), 2.32), (2.2, Y(0.0), 2.32)], 0.04, "PaintTeal",
           segs=12, round_r=0.1)
    cv = handwheel(p, (-2.55, Y(0.73), 1.15), rot=face, r=0.1, name="CoolantValve", interact="coolant_valve",
                   engine=engine_id, m="PaintTeal")
    p.decal(0.12, 0.04, (-2.55, Y(0.705), 1.32), "label_coolant", rot=face)
    # lube oil: filters, cooler, filler neck with cap
    for k, x in enumerate((0.55, 0.95)):
        p.cyl(0.08, 0.3, (x, Y(0.63), 0.95), "PaintMustard", segs=20, bevel=0.01)
        p.cyl(0.085, 0.04, (x, Y(0.63), 1.12), "DarkSteel", segs=20)
    p.cyl(0.12, 1.0, (0.75, Y(0.65), 0.62), "PaintEngine", axis="X", segs=20, bevel=0.01)
    p.cyl(0.04, 0.2, (-1.5, Y(0.5), 2.02), "DarkSteel", segs=12)
    oil = p.pivot("OilFiller", (-1.5, Y(0.5), 2.13), interact="oil_filler", engine=engine_id, rotate_axis="Z")
    p.cyl(0.055, 0.04, (0, 0, 0), "PaintMustard", segs=16, bevel=0.008, parent=oil)
    p.box((0.09, 0.015, 0.02), (0, 0, 0.025), "PaintMustard", parent=oil, bevel=0.003)
    p.decal(0.1, 0.035, (-1.5, Y(0.62), 1.98), "label_oil", rot=face)
    # starter motor and governor
    p.cyl(0.12, 0.42, (-2.55, Y(-0.58), 0.62), "PaintGraphite", axis="X", segs=16, bevel=0.01)
    p.box((0.3, 0.22, 0.3), (-2.75, Y(0.42), 1.45), "PaintGraphite", bevel=0.02)
    # flywheel (spins) with ring gear, under a safety guard; coupling
    fw = p.pivot("Flywheel", (2.85, 0, 0.82), interact="spin", rotate_axis="X", engine=engine_id)
    p.cyl(0.62, 0.14, (0, 0, 0), "DarkSteel", axis="X", segs=48, bevel=0.01, parent=fw)
    for k in range(48):
        a = k * math.pi / 24
        p.box((0.1, 0.03, 0.04), (0, math.cos(a) * 0.635, math.sin(a) * 0.635), "Steel", rot=(math.degrees(a), 0, 0),
              bevel=0, parent=fw, name="tooth")
    for k in range(6):
        a = k * math.pi / 3
        p.cyl(0.07, 0.16, (0, math.cos(a) * 0.36, math.sin(a) * 0.36), "BlackPlastic", axis="X", segs=12, parent=fw)
    guard = bm_lathe([(0.7, -0.12), (0.73, -0.12), (0.73, 0.14), (0.7, 0.14)], 32, "X", closed=True, angle=math.pi)
    bmesh.ops.rotate(guard, verts=guard.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
    p.add(guard, "PaintMustard", (2.85, 0, 0.82), smooth=40, name="guard")
    p.cyl(0.26, 0.14, (3.02, 0, 0.82), "Steel", axis="X", segs=24, bevel=0.01)
    p.bolts([(3.1, math.cos(a) * 0.2, 0.82 + math.sin(a) * 0.2) for a in [k * math.pi / 4 for k in range(8)]], axis="X", r=0.015, h=0.03)
    # local control panel on the service side
    px = 2.15
    p.box((0.05, 0.05, 0.75), (px - 0.25, Y(0.62), 1.8), "DarkSteel", bevel=0.005)
    p.box((0.05, 0.05, 0.75), (px + 0.25, Y(0.62), 1.8), "DarkSteel", bevel=0.005)
    panel_y = 0.7
    p.box((0.62, 0.12, 0.5), (px, Y(panel_y), 2.25), "PaintGraphite", bevel=0.015)
    f = Y(panel_y + 0.061)
    gauge(p, (px - 0.17, f, 2.36), rot=face, r=0.055, face="gauge_pressure", name="OilGauge", needle_deg=-30)
    gauge(p, (px + 0.0, f, 2.36), rot=face, r=0.055, face="gauge_air", name="TempGauge", needle_deg=-60)
    gauge(p, (px + 0.17, f, 2.36), rot=face, r=0.055, face="gauge_depth", name="RpmGauge", needle_deg=-120)
    push_button(p, (px - 0.15, f, 2.14), rot=face, m="LampGreen", r=0.03, name="StartButton", interact="engine_start", engine=engine_id)
    push_button(p, (px + 0.0, f, 2.14), rot=face, m="PaintRed", r=0.03, name="StopButton", interact="engine_stop", engine=engine_id)
    lamp = p.pivot("FaultLamp", (px + 0.16, f, 2.14), face, interact="fault_lamp", engine=engine_id)
    p.cyl(0.026, 0.015, (0, 0.006, 0), "Chrome", axis="Y", segs=16, parent=lamp)
    p.add(core_sphere(0.02), "LampOff", (0, -0.006, 0), parent=lamp, smooth=180, name="lens")
    p.decal(0.08, 0.025, (px - 0.15, Y(panel_y + 0.0625), 2.06), "label_start", rot=face)
    p.decal(0.08, 0.025, (px + 0.0, Y(panel_y + 0.0625), 2.06), "label_stop", rot=face)
    p.plate(0.34, 0.06, (px, Y(panel_y + 0.064), 2.55), label, rot=face)
    p.plate(0.5, 0.08, (0.2, Y(0.462), 1.66), "label_engine_maker", rot=face, frame="Brass", depth=0.006)
    p.decal(0.12, 0.15, (-1.0, Y(0.451), 1.38), "sign_hot", rot=face)
    # interaction anchors and hand targets (catwalk side)
    p.anchor("service", (0.0, Y(1.45), 1.2), engine=engine_id)
    p.anchor("fault_point", (xs[3] - 0.06, Y(0.62), 2.0), engine=engine_id, note="injector bank: fix faults here with a wrench")
    p.use_camera((px - 0.1, Y(1.55), 2.75), (px, Y(0.6), 2.15), lens=30, name="CAM_panel")
    p.hand("R", (px - 0.15, Y(panel_y + 0.1), 2.14), "press", control="StartButton")
    p.hand("L", (-2.55, Y(0.86), 1.15 + 0.1), "grip", control="CoolantValve")
    return p.finish()


def core_sphere(r):
    from .core import bm_sphere
    return bm_sphere(r, 16, 8)


def motor_generator(name="MotorGenerator", s=-1, engine_id=1):
    """Electric motor-generator coupled behind each diesel. Origin at its front coupling, axis along +X."""
    p = Prop(name, category="machine", engine=engine_id)
    Y = lambda y: s * y
    L, r, cz = 1.8, 0.6, 0.82
    p.box((L + 0.2, 1.1, 0.16), (L / 2, 0, 0.08), "PaintGraphite", bevel=0.01)
    for sy in (-1, 1):
        p.box((L, 0.12, 0.3), (L / 2, sy * 0.42, 0.3), "PaintGraphite", bevel=0.01)
    p.cyl(r, L, (L / 2, 0, cz), "PaintNavy", axis="X", segs=48, bevel=0.02)
    for k in range(14):
        p.add(bm_torus(r + 0.012, 0.014, 48, 6, "X"), "PaintNavy", (0.12 + k * (L - 0.24) / 13, 0, cz), smooth=180, name="fin")
    for x, sgn in ((0.0, -1), (L, 1)):
        dome = bm_lathe([(0.0, 0.0), (r * 0.95, 0.0), (r * 0.8, 0.12), (r * 0.4, 0.2), (0.0, 0.22)], 40, "X")
        if sgn < 0:
            bmesh.ops.rotate(dome, verts=dome.verts, matrix=Matrix.Rotation(R(180), 3, "Z"))
        p.add(dome, "PaintNavy", (x, 0, cz), smooth=50, name="endbell")
        louver(p, (x + sgn * 0.13, 0.0, cz + 0.32), rot=(0, 0, 90 * sgn), w=0.3, h=0.12, n=4)
    p.box((0.42, 0.3, 0.36), (L * 0.55, Y(-0.68), cz + 0.25), "PaintGraphite", bevel=0.02)
    p.bolts([(L * 0.55 + dx, Y(-0.835), cz + 0.25 + dz) for dx in (-0.16, 0.16) for dz in (-0.14, 0.14)], r=0.012, h=0.012)
    for k in range(3):
        p.tube([(L * 0.45 + k * 0.1, Y(-0.7), cz + 0.07), (L * 0.45 + k * 0.1, Y(-0.75), cz - 0.3),
                (L * 0.45 + k * 0.1 + 0.2, Y(-0.9), -0.02)], 0.028, "BlackPlastic", segs=10, round_r=0.2)
    p.decal(0.3, 0.06, (L * 0.5, Y(-0.611) if s < 0 else Y(-0.611), cz + 0.02), "label_engine_maker",
            rot=(0, 0, 180) if s < 0 else (0, 0, 0))
    p.cyl(0.25, 0.14, (-0.07, 0, cz), "Steel", axis="X", segs=24, bevel=0.01)
    sh = p.pivot("Shaft", (L + 0.2, 0, cz), interact="spin", rotate_axis="X")
    p.cyl(0.09, 0.4, (0.2, 0, 0), "Chrome", axis="X", segs=16, parent=sh)
    return p.finish()


def shaft_line(name="ShaftLine", length=2.6):
    """Propeller shaft with bearing blocks, running to the aft bulkhead. Origin at its forward end, z = shaft axis."""
    p = Prop(name, category="machine")
    sh = p.pivot("Shaft", (0, 0, 0), interact="spin", rotate_axis="X")
    p.cyl(0.09, length, (length / 2, 0, 0), "Chrome", axis="X", segs=20, parent=sh)
    for k in range(3):
        p.add(bm_torus(0.1, 0.012, 20, 6, "X"), "Brass", (0.3 + k * (length - 0.6) / 2, 0, 0), parent=sh, smooth=180)
    for k in range(2):
        x = 0.6 + k * (length - 1.2)
        p.box((0.3, 0.42, 0.26), (x, 0, -0.08), "PaintGraphite", bevel=0.02)
        p.box((0.36, 0.6, 0.06), (x, 0, -0.25), "PaintGraphite", bevel=0.01)
        p.cyl(0.03, 0.06, (x, 0, 0.08), "Brass", segs=10)
    return p.finish()


def engine_console(name="EngineConsole"):
    """Manoeuvring console for both diesels: gauges, START/STOP, throttles, fault lamps, live status screen."""
    p = Prop(name, category="station", station="engine_control")
    W, D = 2.3, 0.7
    p.box((W - 0.1, D - 0.1, 0.1), (0, 0, 0.05), "PaintGraphite", bevel=0.01)
    p.box((W, D, 0.92), (0, 0, 0.56), "PaintSeafoam", bevel=0.02, segs=3)
    p.box((W + 0.04, D + 0.06, 0.05), (0, -0.02, 1.045), "PaintGraphite", bevel=0.01)
    p.box((W, 0.32, 0.85), (0, 0.19, 1.5), "PaintSeafoam", bevel=0.02, segs=3)
    f = 0.19 - 0.16 - 0.003
    p.screen(0.56, 0.4, (0, f, 1.55), "screen_engine", bezel=0.04, depth=0.035)
    p.plate(0.8, 0.12, (0, f - 0.004, 1.86), "label_engine_control")
    for e, sx in ((1, -1), (2, 1)):
        cx = sx * 0.78
        p.plate(0.36, 0.06, (cx, f - 0.004, 1.86), f"label_diesel{e}")
        gauge(p, (cx - 0.16, f, 1.66), r=0.07, face="gauge_depth", name=f"Rpm{e}", needle_deg=-120)
        gauge(p, (cx + 0.0, f, 1.66), r=0.07, face="gauge_air", name=f"Temp{e}", needle_deg=-60)
        gauge(p, (cx + 0.16, f, 1.66), r=0.07, face="gauge_pressure", name=f"Oil{e}", needle_deg=-40)
        push_button(p, (cx - 0.12, f, 1.4), m="LampGreen", r=0.035, name=f"Start{e}", interact="engine_start", engine=e)
        push_button(p, (cx + 0.04, f, 1.4), m="PaintRed", r=0.035, name=f"Stop{e}", interact="engine_stop", engine=e)
        lamp = p.pivot(f"Fault{e}", (cx + 0.18, f, 1.4), interact="fault_lamp", engine=e)
        p.cyl(0.028, 0.015, (0, 0.006, 0), "Chrome", axis="Y", segs=16, parent=lamp)
        p.add(core_sphere(0.022), "LampOff", (0, -0.006, 0), parent=lamp, smooth=180, name="lens")
        th = p.pivot(f"Throttle{e}", (cx, -D / 2 + 0.2, 1.07), interact="lever", engine=e, rotate_axis="X", min_deg=-30, max_deg=30)
        p.box((0.06, 0.05, 0.05), (0, 0, 0.0), "DarkSteel", parent=th, bevel=0.008)
        p.cyl(0.012, 0.22, (0, 0, 0.11), "Chrome", segs=10, parent=th)
        p.sphere(0.03, (0, 0, 0.23), "Bakelite", parent=th, segs=14, rings=7)
        p.box((0.16, 0.18, 0.02), (cx, -D / 2 + 0.2, 1.06), "PaintGraphite", bevel=0.004)
    gauge(p, (0, f, 1.27), r=0.06, face="gauge_air", name="ChargeAmmeter", needle_deg=20)
    louver(p, (0, -D / 2 - 0.002, 0.45), w=1.6, h=0.24, n=6)
    p.use_camera((0, -0.78, 1.75), (0, 0.05, 1.4), lens=26)
    p.hand("L", (-0.9, f - 0.1, 1.4), "press", control="Start1")
    p.hand("R", (0.66, f - 0.1, 1.4), "press", control="Start2")
    p.anchor("operate", (0, -D / 2 - 0.45, 0))
    return p.finish()


def fuel_station(name="FuelStation"):
    """Diesel day tank with sight glass and filler, plus a hand-lever fuel transfer pump (pump it up and down)."""
    p = Prop(name, category="station", station="fuel")
    tx = -0.35
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        p.cyl(0.03, 0.4, (tx + math.cos(a) * 0.32, -0.45 + math.sin(a) * 0.32, 0.2), "PaintGraphite", segs=10)
    tank = bm_lathe([(0.0, 0.0), (0.4, 0.0), (0.43, 0.04), (0.43, 1.5), (0.4, 1.56), (0.12, 1.62), (0.0, 1.62)], 40)
    p.add(tank, "PaintRed", (tx, -0.45, 0.4), smooth=50, name="tank")
    for z in (0.75, 1.55):
        p.add(bm_torus(0.435, 0.012, 40, 6), "DarkSteel", (tx, -0.45, z), smooth=180)
    # sight glass with a fuel column the game scales by the fuel level
    p.cyl(0.03, 1.3, (tx, -0.9, 1.2), "Glass", segs=12)
    for z in (0.53, 1.87):
        p.box((0.06, 0.06, 0.05), (tx, -0.88, z), "Brass", bevel=0.006)
    lvl = p.pivot("FuelLevel", (tx, -0.9, 0.56), interact="fuel_level", scale_axis="Z", note="scale Z = day tank fraction")
    p.cyl(0.022, 1.28, (0, 0, 0.64), "FuelAmber", segs=10, parent=lvl)
    p.decal(0.2, 0.05, (tx, -0.882, 2.0), "label_fuel")
    gauge(p, (tx + 0.3, -0.83, 1.4), rot=(0, 0, -30), r=0.06, face="gauge_air", name="FuelGauge", needle_deg=-100)
    # filler neck with cap (jerrycans are poured here)
    p.cyl(0.05, 0.16, (tx + 0.18, -0.45, 2.08), "DarkSteel", segs=14)
    cap = p.pivot("FillerCap", (tx + 0.18, -0.45, 2.17), interact="fuel_filler", rotate_axis="Z")
    p.cyl(0.07, 0.04, (0, 0, 0), "PaintMustard", segs=16, bevel=0.008, parent=cap)
    # transfer pump on a stand, with a long lever
    px = 0.55
    p.box((0.32, 0.32, 0.06), (px, -0.35, 0.03), "PaintGraphite", bevel=0.008)
    p.cyl(0.05, 0.7, (px, -0.35, 0.4), "PaintGraphite", segs=14)
    body = bm_lathe([(0.0, 0.0), (0.11, 0.0), (0.12, 0.03), (0.12, 0.35), (0.09, 0.4), (0.0, 0.42)], 32)
    p.add(body, "PaintMustard", (px, -0.35, 0.75), smooth=50, name="pumpbody")
    p.box((0.06, 0.14, 0.18), (px, -0.35, 1.25), "DarkSteel", bevel=0.01)
    lever = p.pivot("PumpLever", (px, -0.35, 1.3), interact="pump_lever", rotate_axis="X", min_deg=-28, max_deg=28,
                    note="pump strokes move fuel from the main tanks into the day tank")
    p.box((0.05, 0.08, 0.06), (0, 0, 0), "DarkSteel", parent=lever, bevel=0.008)
    p.cyl(0.018, 0.75, (0, -0.38, 0.0), "Chrome", axis="Y", segs=12, parent=lever)
    p.add(bm_lathe([(0, 0), (0.03, 0.0), (0.034, 0.03), (0.034, 0.17), (0.03, 0.2), (0, 0.2)], 16, "Y"), "PaintRed",
          (0, -0.79, 0), parent=lever, smooth=50)
    p.tube([(px, -0.25, 0.85), (px, -0.05, 0.85), (px, -0.05, 2.15), (tx, -0.05, 2.15), (tx, -0.3, 2.05)], 0.025, "Copper",
           segs=10, round_r=0.08)
    p.tube([(px, -0.45, 0.78), (px, -0.6, 0.6), (px, -0.6, -0.02)], 0.03, "DarkSteel", segs=10, round_r=0.1)
    p.plate(0.6, 0.1, (0.1, -0.012, 2.35), "label_fuel_transfer")
    p.use_camera((0.4, -1.45, 1.75), (0.2, -0.35, 1.15), lens=28)
    p.hand("R", (px, -1.1, 1.3), "grip", control="PumpLever")
    p.anchor("operate", (px, -1.3, 0))
    p.anchor("filler", (tx + 0.18, -0.45, 2.2))
    return p.finish()


def jerrycan(name="Jerrycan"):
    """20-litre fuel can (carry it to the day tank filler)."""
    p = Prop(name, category="pickup", interact="carry", item="fuel_can")
    p.box((0.17, 0.34, 0.44), (0, 0, 0.22), "PaintRed", bevel=0.02, segs=2)
    for sx in (-1, 1):
        for d in (1, -1):
            p.box((0.012, 0.03, 0.34), (sx * 0.086, 0, 0.22), "PaintRed", rot=(d * 32, 0, 0), bevel=0.004)
    for y in (-0.08, 0.0, 0.08):
        p.box((0.03, 0.025, 0.06), (0, y, 0.47), "PaintRed", bevel=0.006)
    p.box((0.03, 0.2, 0.025), (0, 0, 0.505), "PaintRed", bevel=0.008)
    p.cyl(0.03, 0.05, (0, 0.13, 0.46), "DarkSteel", rot=(25, 0, 0), segs=12)
    return p.finish()


def oil_can(name="OilCan"):
    p = Prop(name, category="pickup", interact="carry", item="oil_can")
    p.add(bm_lathe([(0, 0), (0.1, 0), (0.102, 0.01), (0.102, 0.24), (0.07, 0.29), (0.025, 0.3), (0, 0.3)], 32), "PaintMustard",
          smooth=50)
    p.add(bm_torus(0.101, 0.006, 32, 6), "DarkSteel", (0, 0, 0.12), smooth=180)
    p.decal(0.08, 0.03, (0, -0.103, 0.16), "label_oil")
    p.tube([(0.0, 0.0, 0.29), (0.06, 0.0, 0.36), (0.16, 0.0, 0.42)], 0.008, "Brass", segs=8)
    p.tube([(-0.08, 0, 0.24), (-0.1, 0, 0.33), (-0.03, 0, 0.36)], 0.008, "DarkSteel", segs=8, round_r=0.04)
    return p.finish()


def stores_shelf(name="StoresShelf", W=1.6, D=0.5, H=1.9):
    """Heavy steel shelving with crates and boxes (pickups like jerrycans are placed separately)."""
    p = Prop(name, category="storage")
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((0.05, 0.05, H), (sx * (W / 2 - 0.025), -D / 2 + sy * (D / 2 - 0.025), H / 2), "PaintMustard", bevel=0.006)
    import random
    rnd = random.Random(9)
    for z in (0.12, 0.72, 1.32):
        p.box((W, D, 0.03), (0, -D / 2, z), "PaintGray", bevel=0.005)
        x = -W / 2 + 0.1
        while x < W / 2 - 0.3:
            w = rnd.uniform(0.25, 0.45)
            h = rnd.uniform(0.15, 0.35)
            if rnd.random() < 0.7 and z > 0.5:
                p.box((w, D * 0.8, h), (x + w / 2, -D / 2, z + 0.015 + h / 2), rnd.choice(["PaintOlive", "CuttingBoard", "PaintNavy", "PaintCream"]),
                      bevel=0.01)
            x += w + 0.06
    p.box((W, 0.02, 0.08), (0, -D + 0.01, 1.85), "PaintGraphite", bevel=0.003)
    p.plate(0.4, 0.07, (0, -0.012, H + 0.12), "label_stores")
    for k in range(3):
        p.anchor(f"slot{k + 1}", (-W / 2 + 0.3 + k * 0.5, -D / 2, 0.135), slot=k + 1)
    return p.finish()
