"""Unit 1 / Lesson 2 (internal forces): earthquakes, volcanoes, folding and faulting."""
import math
import random

import bpy

from . import kit, chars, props
from .assets_lib import asset
from .kit import V, box, capsule, cone, cyl, empty, ico, mat, sphere, torus, curve, tex_mat, strata_mat
from .props import glow, arrow, rock, cloud, prism_xz, house, tower_building
from .assets_u1l1 import CONT, World, PAN

R = math.radians
G = "u1l2"
STRATA = ["#e8a24a", "#c9704a", "#8e6f9a", "#6aa8a0", "#d9c26a"]


def ground_block(w=10.0, d=5.0, depth=3.2, strata=True, grass=True, loc_y=0.0):
    """Cut-away ground: front (-Y) face shows the rock layers."""
    if strata:
        m = strata_mat(["#9a6a4a", "#7d5a46", "#8a8f98", "#6b7078"], 0.8, "Z", "Object", 0.75, offset=0.0)
    else:
        m = mat("#8a6a4a", 0.8)
    b = box((w, d, depth - 0.3), (0, loc_y, -(depth - 0.3) / 2 - 0.0), m, bevel=0.04)
    if grass:
        box((w + 0.04, d + 0.04, 0.3), (0, loc_y, 0.0 + 0.0), mat("#5bc25b", 0.6, sss=0.15), bevel=0.05)
    return b


@asset("quake_diagram", size=(900, 580), samples=28, group=G)
def quake_diagram(ctx):
    kit.studio(scale=2.6, key=700, amb=0.8)
    ground_block(11.0, 4.0, 4.2)
    fy = -2.05
    # focus (hypocentre): spiky glowing star on the cut face, epicentre on the surface above it
    star = ico(0.32, (-2.3, fy, -2.6), glow("#ff3b30", 6), sub=1)
    star.scale = (1, 0.5, 1)
    for k in (1, 2, 3):
        t = torus(0.55 * k + 0.2, 0.035, (-2.3, fy - 0.02, -2.6), glow("#ffb347", 3.5, 0.9), rot=(R(90), 0, 0))
    sphere(0.22, (-2.3, fy, 0.18), glow("#ffe14d", 5), scale=(1, 0.5, 1))
    torus(0.38, 0.04, (-2.3, fy, 0.17), glow("#ffe14d", 5), rot=(0, 0, 0))
    cyl(0.03, 2.75, (-2.3, fy, -1.2), glow("#ffffff", 2), seg=8)          # focus -> epicentre
    cyl(0.03, 6.5, (0.95, fy - 0.01, 0.2), glow("#ffffff", 2), rot=(0, R(90), 0), seg=8)  # epicentre -> city (surface)
    L = math.hypot(6.5, 2.8)
    cyl(0.03, L, (0.95, fy, -1.2), glow("#ffffff", 2), rot=(0, R(90 - math.degrees(math.atan2(2.8, 6.5))), 0), seg=8)
    for x, s, hgt in ((3.3, 1.0, 1.5), (4.2, 0.9, 2.2), (4.9, 0.85, 1.4)):
        if hgt > 2:
            tower_building((x, -0.4, 0.15), s, hgt)
        else:
            house((x, -0.4, 0.15), s)
    tree = props.tree_palm((6.3, -0.5, 0.1), 1.4, 5, 0.7)
    kit.camera((0.2, -13.5, 3.4), (-0.2, 0, -0.9), lens=40)
    ctx.still()


@asset("seismograph", size=(540, 540), loop=(36, 12), samples=10, group=G)
def seismograph(ctx):
    kit.studio(scale=1.5)
    steel = mat("#5c6b7a", 0.35, metal=0.7, sss=0, coat=0.3)
    base = empty("base", (0, 0, 0))
    box((5.6, 2.4, 0.3), (0.6, 0, 0.15), mat("#3a3f4a", 0.5), bevel=0.05).parent = base
    box((0.3, 0.3, 3.9), (-1.7, 0.0, 2.1), steel, bevel=0.03).parent = base
    box((2.6, 0.3, 0.3), (-0.45, 0.0, 4.0), steel, bevel=0.03).parent = base
    coil = curve([(0.7 + 0.17 * math.cos(i * 0.9), 0.17 * math.sin(i * 0.9), 3.85 - i * 0.075) for i in range(24)], 0.035, mat("#d4a017", 0.3, metal=0.8), name="spring")
    weight = empty("weight", (0.7, 0, 0))
    cyl(0.45, 0.95, (0, 0, 1.7), mat("#c0392b", 0.4, coat=0.4), seg=32).parent = weight
    cyl(0.03, 0.9, (0, 0, 2.35), steel, seg=8).parent = weight
    # pen arm to the drum
    cyl(0.03, 1.7, (0.95, 0, 1.95), steel, rot=(0, R(90), 0), seg=8).parent = weight
    cone(0.06, 0.0, 0.22, (1.8, 0, 1.86), mat("#1c1230", 0.3), rot=(R(180), 0, 0), seg=12).parent = weight
    # drum (axis along X) with a wavy trace on the paper
    drum = empty("drum", (2.5, 0, 1.15))
    cyl(0.75, 1.5, (0, 0, 0), mat("#fff7e0", 0.7, sss=0.1, coat=0), rot=(0, R(90), 0), seg=64).parent = drum
    for sx in (-1, 1):
        cyl(0.8, 0.08, (sx * 0.78, 0, 0), steel, rot=(0, R(90), 0), seg=48).parent = drum
    N = 160
    pts = []
    for i in range(N + 1):
        a = i / N * math.tau
        env = math.sin(min(1, a / math.tau) * math.pi) ** 1.1
        pts.append((0.28 * env * math.sin(a * 13), math.cos(a) * 0.76, math.sin(a) * 0.76))
    tr = curve(pts, 0.022, mat("#1c1230", 0.4, sss=0), name="trace")
    tr.parent = drum
    kit.camera((1.0, -9.6, 4.2), (1.2, 0, 2.0), lens=44)

    def upd(i, t):
        a = t * math.tau
        amp = 0.07 * math.sin(a * 6) * (0.5 + 0.5 * math.sin(a))
        base.location.x = amp * 1.5
        tr.rotation_euler = (t * math.tau, 0, 0)
    ctx.loop(upd)


@asset("volcano_parts", size=(820, 660), samples=28, group=G)
def volcano_parts(ctx):
    kit.studio(scale=2.4, key=700, amb=0.8)
    # ground mound
    rk = tex_mat("noise", "#6b4a38", "#8f6b52", scale=1.4, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.4)
    cone_o = cone(4.3, 1.0, 3.8, (0, 0, 1.9), rk, seg=64)
    cutter = box((10, 5, 8), (0, -2.5, 2.5), mat("#fff"), bevel=0.0)
    cutter.hide_render = True
    bm = cone_o.modifiers.new("cut", "BOOLEAN")
    bm.object = cutter
    bm.operation = "DIFFERENCE"
    bm.solver = "EXACT"
    box((11, 6, 0.3), (0, 0, 0.0), mat("#5bc25b", 0.6, sss=0.15), bevel=0.06)
    lava = glow("#ff6a1a", 4.5)
    deep = glow("#ff3b1a", 3.5)
    # section inlays on the cut plane (y = 0)
    ch = sphere(1.15, (0, 0.03, 0.55), deep, scale=(1.6, 0.12, 0.7))
    cd = cyl(0.26, 2.7, (0, 0.03, 2.0), lava, rot=(0, 0, 0), seg=24, scale=(1, 0.12, 1))
    sv = cyl(0.14, 2.2, (1.15, 0.03, 1.45), lava, rot=(0, R(42), 0), seg=20, scale=(1, 0.12, 1))
    sphere(0.3, (1.95, 0.03, 2.3), lava, scale=(1, 0.2, 0.7))
    sphere(0.55, (0, 0.03, 3.85), lava, scale=(1.6, 0.2, 0.35))
    # lava flows down the right slope + from the side vent
    for k in range(5):
        sphere(0.26 - k * 0.02, (1.0 + k * 0.32, 0.05, 3.55 - k * 0.55), lava, scale=(1.0, 0.7, 0.6))
    for k in range(4):
        sphere(0.2 - k * 0.02, (2.0 + k * 0.28, 0.05, 2.2 - k * 0.5), lava, scale=(1.0, 0.6, 0.6))
    # ash cloud
    smoke = mat("#6d6a76", 0.9, sss=0.1, coat=0)
    for x, z, s in ((0, 5.0, 0.7), (-0.5, 5.6, 0.85), (0.6, 5.9, 0.9), (0.0, 6.5, 1.0), (-0.9, 6.5, 0.7), (1.1, 6.6, 0.7), (0.3, 7.2, 0.8)):
        sphere(s, (x, 0.2, z), smoke, scale=(1, 0.8, 0.85), seg=24, rings=12)
    kit.camera((0, -13.5, 4.0), (0, 0, 3.2), lens=40)
    ctx.still()


@asset("volcano_erupt", size=(560, 560), loop=(48, 12), samples=10, group=G)
def volcano_erupt(ctx):
    kit.studio(scale=2.2, key=600, amb=0.7)
    rk = tex_mat("noise", "#6b4a38", "#8f6b52", scale=1.4, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.4)
    cone(3.6, 0.9, 3.4, (0, 0, 1.7), rk, seg=64)
    cyl(0.9, 0.05, (0, 0, 3.42), glow("#ff5a14", 5), seg=32)
    lava = glow("#ff6a1a", 5)
    rnd = random.Random(3)
    bombs = []
    for i in range(26):
        o = sphere(rnd.uniform(0.12, 0.28), (0, 0, 3.4), glow(rnd.choice(["#ff6a1a", "#ffb02e", "#ff3b1a"]), 6), seg=12, rings=6)
        bombs.append((o, rnd.uniform(0, 1), rnd.uniform(-1, 1), rnd.uniform(-0.5, 0.5), rnd.uniform(3.5, 6)))
    smoke = [sphere(0.5, (0, 0, 4), mat(c, 0.9, sss=0.1, coat=0), seg=20, rings=10) for c in ("#5f5b69", "#77737f", "#4f4b59", "#6d6a76", "#85818e", "#5f5b69", "#77737f", "#6d6a76")]
    flows = [sphere(0.28, (0, 0, 0), lava, scale=(1, 0.8, 0.7), seg=16, rings=8) for _ in range(10)]
    kit.camera((0, -13.0, 4.8), (0, 0, 3.6), lens=40)

    def upd(i, t):
        for o, ph, vx, vy, vz in bombs:
            p = (t + ph) % 1.0
            o.location = (vx * 2.2 * p, vy * 1.2 * p, 3.4 + vz * p - 5.5 * p * p * 1.2)
            o.scale = (max(0.001, 1 - p * 0.3),) * 3 if p < 0.95 else (0.001,) * 3
        for k, s in enumerate(smoke):
            p = (t + k / len(smoke)) % 1.0
            s.location = (math.sin(k * 2 + t * 6.28) * 0.5 * p * 2, 0.2, 4.1 + p * 3.2)
            sc = 0.4 + p * 1.2
            s.scale = (sc,) * 3 if 0.02 < p < 0.97 else (0.001,) * 3
        for k, f in enumerate(flows):
            p = (t * 1 + k / len(flows)) % 1.0
            side = 1 if k % 2 else -1
            f.location = (side * (0.7 + p * 2.5), -0.3 - 0.35 * (k % 3), 3.2 - p * 3.0)
            f.scale = (0.001,) * 3 if p > 0.97 else (1 - p * 0.4,) * 3
    ctx.loop(upd)


@asset("volcano_model", size=(520, 520), loop=(36, 12), samples=10, group=G)
def volcano_model(ctx):
    kit.studio(scale=1.4)
    sand = tex_mat("noise", "#d8b878", "#e8cc92", scale=3.0, detail=5, mid=0.5, contrast=0.3, rough=0.9, sss=0.05, coat=0)
    box((5.2, 5.2, 0.25), (0, 0, 0.0), mat("#9a7a52", 0.7), bevel=0.05)
    cone(2.1, 0.55, 1.7, (0, 0, 0.98), sand, seg=48)
    glass = mat("#bfe8ff", 0.1, alpha=0.4, coat=0.5, sss=0)
    cyl(0.42, 1.5, (0, 0, 1.2), glass, seg=32)
    cyl(0.45, 0.2, (0, 0, 1.95), glass, seg=32)
    liq = mat("#e63b2e", 0.3, emit="#e63b2e", emit_strength=0.35, sss=0, coat=0.5)
    cyl(0.36, 0.75, (0, 0, 0.9), liq, seg=24)
    foam = mat("#ff5a46", 0.4, sss=0.2, coat=0.5)
    blobs = [sphere(0.22, (0, 0, 2.0), foam, seg=16, rings=8) for _ in range(14)]
    streams = [sphere(0.2, (0, 0, 2.0), foam, scale=(1, 1, 0.8), seg=16, rings=8) for _ in range(10)]
    kit.camera((0, -8.0, 4.3), (0, 0, 1.2), lens=45)

    def upd(i, t):
        for k, b in enumerate(blobs):
            p = (t + k / len(blobs)) % 1.0
            b.location = (math.sin(k * 1.7) * 0.5 * p, math.cos(k * 1.3) * 0.5 * p, 1.95 + 1.1 * math.sin(p * math.pi) * (0.7 + (k % 3) * 0.2))
            b.scale = (0.5 + 0.8 * math.sin(p * math.pi),) * 3
        for k, s in enumerate(streams):
            p = (t + k / len(streams)) % 1.0
            a = k * 0.63 + 0.3
            r = 0.5 + p * 1.9
            s.location = (math.cos(a) * r, math.sin(a) * r, 2.0 - p * 1.7)
            s.scale = (0.001,) * 3 if p > 0.96 else (1 - 0.4 * p,) * 3
    ctx.loop(upd)


@asset("quake_zones", size=(700, 394), loop=(24, 12), samples=10, group=G)
def quake_zones(ctx):
    kit.studio(scale=2.6, key=500, amb=0.7)
    w = World()
    w.set(3)
    zones = {
        "pacific": [(-170, 55), (-150, 60), (-135, 55), (-125, 48), (-120, 36), (-110, 24), (-97, 16), (-85, 8), (-78, -2), (-72, -18), (-71, -35), (-74, -48),
                    (-165, -50), (178, -42), (172, -36), (160, -10), (146, -6), (125, 8), (122, 18), (140, 36), (143, 45), (155, 55), (170, 60)],
        "atlantic": [(-20, 65), (-30, 52), (-28, 35), (-20, 20), (-14, 5), (-12, -15), (-5, -35), (0, -50)],
        "europe": [(-8, 37), (2, 40), (12, 41), (16, 38), (24, 37), (30, 38), (40, 38), (48, 34), (56, 28), (62, 27)],
        "sea": [(95, 5), (100, -2), (105, -6), (112, -8), (120, -8), (128, -4), (130, 0)],
        "rift": [(40, 14), (38, 6), (36, -4), (34, -14), (33, -20), (35, 33)],
    }
    mats = [glow("#ff3b1a", 5), glow("#ffb02e", 5)]
    dots = []
    for zn, pts in zones.items():
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 4))
            for k in range(n):
                f = k / n
                x = (a[0] + (b[0] - a[0]) * f) * 0.1
                y = (a[1] + (b[1] - a[1]) * f) * 0.1
                dots.append(sphere(0.17, (x, y, 0.42), mats[len(dots) % 2], seg=12, rings=8))
    kit.camera((0, -17, 27), (0, -0.2, 0), lens=30)

    def upd(i, t):
        for k, d in enumerate(dots):
            s = 0.8 + 0.5 * (0.5 + 0.5 * math.sin(t * math.tau * 2 + k * 0.35))
            d.scale = (s,) * 3
    ctx.loop(upd)


@asset("seismic_station", size=(520, 520), samples=28, group=G)
def seismic_station(ctx):
    kit.studio(scale=1.6)
    box((2.2, 2.2, 0.3), (0, 0, 0.0), mat("#6bbf59", 0.7), bevel=0.05)
    box((1.3, 1.1, 0.9), (0, 0.3, 0.6), mat("#f4e2c0", 0.7, sss=0.1, coat=0), bevel=0.04)
    cyl(0.07, 2.6, (-0.5, -0.4, 1.4), mat("#8a93a0", 0.4, metal=0.7))
    d = sphere(0.55, (-0.5, -0.55, 2.7), mat("#e8eef5", 0.3, metal=0.3, coat=0.5), scale=(1, 0.25, 1), seg=32, rings=16)
    d.rotation_euler = (R(60), 0, R(-20))
    sphere(0.07, (-0.35, -0.8, 2.95), mat("#e63b2e", 0.3))
    for k, r in enumerate((0.8, 1.2, 1.6)):
        torus(r, 0.02, (0.3, -0.7, 3.8 + k * 0.5), glow("#6be3ff", 3, 0.85), rot=(R(70), 0, 0))
    sat = empty("sat", (1.3, 0, 5.4))
    box((0.7, 0.7, 0.7), (0, 0, 0), mat("#d4a017", 0.3, metal=0.8), bevel=0.04).parent = sat
    for sx in (-1, 1):
        box((1.1, 0.05, 0.6), (sx * 1.0, 0, 0), mat("#2a4fbf", 0.25, coat=0.6), bevel=0.01).parent = sat
    kit.camera((0, -10, 3.4), (0.2, 0, 2.5), lens=45)
    ctx.still()


def _layers_mesh(prefix, comp, amp, mats):
    """Folded strata ribbon blocks for the loop: comp = lateral squeeze 0..1, amp = fold amplitude."""
    objs = []
    n = 5
    L = 7.0
    for k in range(n):
        z0, z1 = k * 0.5, (k + 1) * 0.5
        xs = [(-L / 2 + L * i / 60) * (1 - 0.18 * comp) for i in range(61)]
        top, bot = [], []
        for i, x in enumerate(xs):
            u = i / 60
            w = amp * 0.9 * math.sin(u * math.pi * 2 * 1.0 + 0.0) * math.sin(u * math.pi) ** 0.5
            top.append((x, z1 + w))
            bot.append((x, z0 + w))
        pts = top + bot[::-1]
        o = prism_xz(pts, 2.6, mats[k % len(mats)], f"{prefix}{k}", bevel=0.0)
        objs.append(o)
    return objs


@asset("fold_layers", size=(640, 460), loop=(48, 12), samples=10, group=G)
def fold_layers(ctx):
    kit.studio(scale=1.8, key=500)
    mats = [mat(c, 0.55, sss=0.1) for c in STRATA]
    kit.camera((0, -11.5, 4.3), (0, 0, 1.3), lens=44)
    a1 = arrow((-4.6, -1.5, 1.2), (-3.3, -1.5, 1.2))
    a2 = arrow((4.6, -1.5, 1.2), (3.3, -1.5, 1.2))
    cur = []

    def upd(i, t):
        for o in cur:
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(me)
        cur.clear()
        k = 0.5 - 0.5 * math.cos(t * math.tau)
        cur.extend(_layers_mesh("f", k, 0.55 * k, mats))
    ctx.loop(upd)


def _fault(ctx, kind):
    kit.studio(scale=1.8, key=500)
    m = strata_mat(STRATA, 0.5, "Z", "Object", 0.55, offset=0.25)
    Wd = 3.2
    if kind == "strike":
        pass
    # fault plane runs from (0, -2) to (slant, +2) in XZ
    sl = 1.4 if kind != "strike" else 0.0
    if kind == "reverse":
        sl = -1.4
    foot = prism_xz([(-4.0, -2.0), (0.0 - sl * 0.0 + 0.0, -2.0), (sl, 1.2), (-4.0, 1.2)] if False else [(-4.0, -2.0), (-sl / 2 * 0 + 0.7 * (1 if sl >= 0 else -1) * 0 + 0.0, -2.0), (sl, 1.0), (-4.0, 1.0)], 2.6, m, "foot", 0.0)
    hang = prism_xz([(0.0, -2.0), (4.0, -2.0), (4.0, 1.0), (sl, 1.0)], 2.6, m, "hang", 0.0)
    top_g = mat("#5bc25b", 0.6, sss=0.15)
    gf = prism_xz([(-4.0, 1.0), (sl, 1.0), (sl, 1.18), (-4.0, 1.18)], 2.7, top_g, "gf", 0.0)
    gh = prism_xz([(sl, 1.0), (4.0, 1.0), (4.0, 1.18), (sl, 1.18)], 2.7, top_g, "gh", 0.0)
    if kind == "normal":
        kit.camera((0, -10.5, 3.6), (0, 0, 0.0), lens=42)
        a1 = arrow((-1.0, -1.6, 2.4), (-2.6, -1.6, 2.4))
        a2 = arrow((1.0, -1.6, 2.4), (2.6, -1.6, 2.4))
    elif kind == "reverse":
        kit.camera((0, -10.5, 3.6), (0, 0, 0.0), lens=42)
        a1 = arrow((-2.9, -1.6, 2.4), (-1.3, -1.6, 2.4))
        a2 = arrow((2.9, -1.6, 2.4), (1.3, -1.6, 2.4))
    else:
        kit.camera((0, -9.0, 8.5), (0, 0, 0.0), lens=42)
        a1 = arrow((-1.5, -1.5, 1.6), (-3.0, -1.5, 1.6))
    return foot, hang, gf, gh, sl


@asset("fault_normal", size=(560, 400), loop=(36, 12), samples=10, group=G)
def fault_normal(ctx):
    foot, hang, gf, gh, sl = _fault(ctx, "normal")

    def upd(i, t):
        d = (0.5 - 0.5 * math.cos(t * math.tau)) * 0.7
        for o in (hang, gh):
            o.location = (d * 0.35, 0, -d)
    ctx.loop(upd)


@asset("fault_reverse", size=(560, 400), loop=(36, 12), samples=10, group=G)
def fault_reverse(ctx):
    foot, hang, gf, gh, sl = _fault(ctx, "reverse")

    def upd(i, t):
        d = (0.5 - 0.5 * math.cos(t * math.tau)) * 0.7
        for o in (hang, gh):
            o.location = (-d * 0.35, 0, d)
    ctx.loop(upd)


@asset("fault_strike", size=(560, 400), loop=(36, 12), samples=10, group=G)
def fault_strike(ctx):
    kit.studio(scale=1.8, key=500)
    m = strata_mat(STRATA, 0.5, "Z", "Object", 0.55, offset=0.25)
    a = prism_xz([(-4.0, -2.0), (4.0, -2.0), (4.0, 1.0), (-4.0, 1.0)], 1.6, m, "a", 0.0)
    b = prism_xz([(-4.0, -2.0), (4.0, -2.0), (4.0, 1.0), (-4.0, 1.0)], 1.6, m, "b", 0.0)
    ga = prism_xz([(-4.0, 1.0), (4.0, 1.0), (4.0, 1.18), (-4.0, 1.18)], 1.7, mat("#5bc25b", 0.6, sss=0.15), "ga", 0.0)
    gb = prism_xz([(-4.0, 1.0), (4.0, 1.0), (4.0, 1.18), (-4.0, 1.18)], 1.7, mat("#5bc25b", 0.6, sss=0.15), "gb", 0.0)
    kit.camera((0, -9.5, 8.0), (0, 0, 0.0), lens=42)
    ar1 = arrow((0.5, 0.9, 1.6), (2.2, 0.9, 1.6)); ar1.rotation_euler = (0, R(90), 0)
    ar2 = arrow((-0.5, -0.9, 1.6), (-2.2, -0.9, 1.6)); ar2.rotation_euler = (0, R(-90), 0)

    def upd(i, t):
        d = (0.5 - 0.5 * math.cos(t * math.tau)) * 1.2
        a.location = (d, 0.82, 0)
        ga.location = (d, 0.82, 0)
        b.location = (-d, -0.82, 0)
        gb.location = (-d, -0.82, 0)
        ar1.location = (d + 0.8, 1.0, 1.6)
        ar2.location = (-d - 0.8, -1.0, 1.6)
    ctx.loop(upd)


@asset("house_icon", size=(420, 420), samples=32, group=G)
def house_icon(ctx):
    kit.studio(scale=1.2)
    house((0, 0, -0.9), 1.6)
    tower_building((1.9, 0.5, -0.9), 0.9, 1.6, "#6ec1e4")
    kit.camera((0.5, -8.5, 0.9), (0.55, 0, 0.55), lens=45)
    ctx.still()
