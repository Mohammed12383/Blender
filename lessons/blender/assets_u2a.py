"""Unit 2 / Lessons 1-2: weathering (frost, heat flakes, roots, Taj Mahal, acid rain, caves...) and wind erosion (desert forms, camel, dunes)."""
import math
import random

import bpy

from . import kit, props
from .assets_lib import asset
from .kit import V, box, capsule, cone, cyl, empty, ico, mat, sphere, torus, curve, tex_mat, strata_mat
from .props import glow, rock, arrow, prism_xz, house, tree_palm, cloud
from .assets_u1l1 import animal_eye
from .assets_u1l3 import _chunk

R = math.radians
G = "u2a"
SAND = ("#e9c98a", "#d6ae6a")


def sandmat(scale=6, rough=0.9):
    return tex_mat("noise", SAND[0], SAND[1], scale=scale, detail=5, mid=0.5, contrast=0.3, rough=rough, sss=0.05, coat=0)


def sand_slab(w=9, d=6, h=0.5, z=-0.25):
    return box((w, d, h), (0, 0, z), sandmat(), bevel=0.15)


def eased(t):
    return 0.5 - 0.5 * math.cos(t * math.tau)


# ═══════════════════ Taj Mahal ═══════════════════
def taj(loc=(0, 0, 0), s=1.0):
    root = empty("taj", loc)
    marble = mat("#f7f2e8", 0.35, sss=0.15, coat=0.25)
    gold = mat("#e0b43a", 0.25, metal=0.9)
    box((7.6, 7.6, 0.8), (0, 0, 0.4), marble, bevel=0.05).parent = root
    box((3.6, 3.6, 2.8), (0, 0, 2.2), marble, bevel=0.12).parent = root
    # arched iwan on the front
    box((1.5, 0.15, 2.0), (0, -1.85, 2.0), mat("#2f4f6f", 0.5), bevel=0.05).parent = root
    cyl(0.75, 0.15, (0, -1.85, 3.0), mat("#2f4f6f", 0.5), rot=(R(90), 0, 0), seg=32).parent = root
    # main onion dome
    sphere(1.35, (0, 0, 4.5), marble, scale=(1, 1, 1.15), seg=64, rings=32).parent = root
    cyl(0.9, 0.5, (0, 0, 3.7), marble, seg=48).parent = root
    cone(0.35, 0.0, 0.8, (0, 0, 6.35), marble, seg=32).parent = root
    cone(0.07, 0.0, 0.7, (0, 0, 6.9), gold, seg=12).parent = root
    # four small domes
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.28, 0.9, (sx * 1.35, sy * 1.35, 4.05), marble, seg=24).parent = root
            sphere(0.38, (sx * 1.35, sy * 1.35, 4.65), marble, scale=(1, 1, 1.1)).parent = root
            cone(0.05, 0.0, 0.3, (sx * 1.35, sy * 1.35, 5.1), gold, seg=8).parent = root
            # minarets at the corners of the platform
            cyl(0.22, 4.6, (sx * 3.4, sy * 3.4, 3.1), marble, seg=24).parent = root
            cyl(0.34, 0.12, (sx * 3.4, sy * 3.4, 4.0), marble, seg=24).parent = root
            cyl(0.28, 0.4, (sx * 3.4, sy * 3.4, 5.4), marble, seg=24).parent = root
            sphere(0.34, (sx * 3.4, sy * 3.4, 5.75), marble, scale=(1, 1, 0.9)).parent = root
    root.scale = (s, s, s)
    return root


def cypress(loc, h=1.6):
    root = empty("cyp", loc)
    cone(0.35, 0.0, h, (0, 0, h / 2 + 0.1), mat("#2c6b3f", 0.8, sss=0.1, coat=0), seg=16).parent = root
    cyl(0.05, 0.2, (0, 0, 0.1), mat("#6b4a2d", 0.7), seg=8).parent = root
    return root


@asset("bg_agra", size=(1280, 720), bg=True, samples=34, group=G)
def bg_agra(ctx):
    kit.studio(scale=4.0, key=1800, fill=500, rim=350, amb=1.0, top="#bfe0ff", bottom="#ffe9d0")
    box((60, 60, 0.5), (0, 0, -0.25), mat("#6bbf59", 0.8, sss=0.1, coat=0), bevel=0.0)
    box((3.0, 18, 0.12), (0, -4, 0.05), mat("#3ba6e0", 0.1, coat=0.8, sss=0.1), bevel=0.02)       # reflecting pool
    box((6.0, 18.5, 0.1), (0, -4, 0.02), mat("#d9c8a0", 0.7), bevel=0.0)
    taj((0, 9.5, 0.0), 1.15)
    for k in range(6):
        for sx in (-1, 1):
            cypress((sx * 2.1, -9 + k * 3.0, 0.0), 1.9)
    kit.camera((0, -17.5, 3.2), (0, 6, 3.6), lens=38)
    ctx.still()


@asset("taj_mahal", size=(640, 520), samples=30, group=G)
def taj_mahal(ctx):
    kit.studio(scale=3.0, key=900, amb=0.9)
    taj((0, 0, 0), 1.0)
    kit.camera((0, -19, 6.0), (0, 0, 3.4), lens=42)
    ctx.still()


@asset("acid_rain", size=(1024, 576), loop=(36, 12), bg=True, samples=10, group=G)
def acid_rain(ctx):
    kit.studio(scale=3.0, key=1000, fill=400, rim=200, amb=0.6, top="#9aa6a0", bottom="#cfd2b8")
    kit.world("#7e8a78", "#b8bba0", 0.7)
    box((60, 40, 0.5), (0, 8, -0.25), mat("#6b8f55", 0.85, sss=0.1, coat=0), bevel=0.0)
    taj((6.2, 8.0, 0.0), 0.62)
    # factory
    box((4.2, 2.6, 2.0), (-4.6, 3.0, 1.0), mat("#8a6a52", 0.8, sss=0.05, coat=0), bevel=0.05)
    for x in (-5.4, -3.8):
        cyl(0.42, 3.4, (x, 3.0, 3.6), mat("#b5523b", 0.6), seg=24)
        torus(0.43, 0.06, (x, 3.0, 5.2), mat("#f0e6d0", 0.5), rot=(0, 0, 0))
    smoke = [sphere(0.5, (0, 0, 0), mat("#4b4a50", 0.9, sss=0.1, coat=0), seg=16, rings=8) for _ in range(14)]
    clouds = [sphere(1.4, (x, 6, 7.2), mat("#848f79", 0.9, sss=0.1, coat=0), scale=(1.8, 1, 0.7)) for x in (-6, -2, 2, 6)]
    rnd = random.Random(5)
    drops = [(sphere(0.07, (0, 0, 0), glow("#c9ff4a", 4), scale=(0.5, 0.5, 2.2), seg=8, rings=6), rnd.uniform(0, 1), rnd.uniform(-9, 10), rnd.uniform(1, 9)) for _ in range(60)]
    kit.camera((0, -15, 4.8), (0, 4, 3.6), lens=36)

    def upd(i, t):
        for k, s in enumerate(smoke):
            p = (t + k / len(smoke)) % 1.0
            x = -5.4 if k % 2 else -3.8
            s.location = (x + 2.2 * p, 3.0, 5.4 + 3.0 * p)
            s.scale = (0.4 + 1.2 * p,) * 3
        for d, ph, x, y in drops:
            p = (t * 2 + ph) % 1.0
            d.location = (x + 1.5 * p, y, 7.0 - p * 7.0)
            d.rotation_euler = (0, R(15), 0)
    ctx.loop(upd)


@asset("rust_nail", size=(420, 420), samples=30, group=G)
def rust_nail(ctx):
    kit.studio(scale=1.2)
    steel = mat("#7a8794", 0.3, metal=0.8, sss=0, coat=0.2)
    rust = tex_mat("noise", "#8a3b12", "#d9792a", scale=8, detail=8, mid=0.5, contrast=0.2, rough=0.85, sss=0, coat=0)
    for x, rot, m in ((-0.5, 14, rust), (0.45, -22, steel), (0.0, 6, rust)):
        n = empty("nail", (x, 0, 0.1))
        cyl(0.07, 1.8, (0, 0, 0.9), m, seg=16).parent = n
        cyl(0.2, 0.1, (0, 0, 1.82), m, seg=24).parent = n
        cone(0.07, 0.0, 0.25, (0, 0, 0.0), m, seg=16).parent = n
        n.rotation_euler = (0, R(rot), 0)
    for x, z in ((-1.1, 1.9), (0.9, 2.2)):
        sphere(0.14, (x, -0.2, z), mat("#3b8cff", 0.1, coat=0.8, sss=0.3), seg=16, rings=8)
    kit.camera((0, -6.5, 1.6), (0, 0, 1.0), lens=50)
    ctx.still()


# ═══════════════════ weathering loops ═══════════════════
def _split_rock(loc_z=0.0):
    rk = tex_mat("noise", "#7d7a80", "#a29da5", scale=3.5, detail=6, mid=0.5, contrast=0.3, rough=0.8, sss=0.02, coat=0, bump=0.3)
    L = _chunk(rk, (-0.9, 0, 0.9), 1.0, scale=(0.9, 1.0, 1.0), seed=2, bump=0.12, sub=3)
    Rr = _chunk(rk, (0.9, 0, 0.9), 1.0, scale=(0.9, 1.0, 1.0), seed=3, bump=0.12, sub=3)
    return L, Rr


@asset("frost_wedging", size=(560, 440), loop=(48, 12), samples=10, group=G)
def frost_wedging(ctx):
    kit.studio(scale=1.6)
    L, Rr = _split_rock()
    ice = mat("#bfe8ff", 0.1, coat=0.8, sss=0.0)
    wedge = ico(0.55, (0, 0.0, 0.9), ice, sub=2, scale=(0.3, 0.9, 1.5))
    snow = [sphere(0.06, (0, 0, 0), mat("#ffffff", 0.5, sss=0), seg=8, rings=6) for _ in range(18)]
    rnd = random.Random(2)
    pos = [(rnd.uniform(-2.2, 2.2), rnd.uniform(-0.8, 0.8), rnd.uniform(0, 1)) for _ in snow]
    kit.camera((0, -7.4, 2.6), (0, 0, 1.0), lens=45)

    def upd(i, t):
        g = 0.08 + 0.42 * eased(t)
        L.location.x = -0.55 - g
        Rr.location.x = 0.55 + g
        wedge.scale = (0.2 + 0.9 * g, 0.9, 1.5)
        for s, (x, y, ph) in zip(snow, pos):
            p = (t * 2 + ph) % 1.0
            s.location = (x, y, 3.6 - p * 3.2)
    ctx.loop(upd)


@asset("root_crack", size=(560, 460), loop=(48, 12), samples=10, group=G)
def root_crack(ctx):
    kit.studio(scale=1.6)
    L, Rr = _split_rock()
    trunk = mat("#8a5a34", 0.7, coat=0)
    leaf = mat("#4cc25b", 0.6, sss=0.1, coat=0)
    root = cone(0.35, 0.05, 2.0, (0, 0.0, 1.9), trunk, seg=16)
    foli = [sphere(0.5, (dx, 0, 3.2 + dz), leaf, seg=16, rings=8) for dx, dz in ((0, 0.2), (-0.5, -0.1), (0.5, -0.1), (0, 0.65))]
    kit.camera((0, -7.8, 2.8), (0, 0, 1.6), lens=45)

    def upd(i, t):
        g = 0.05 + 0.4 * eased(t)
        L.location.x = -0.5 - g
        Rr.location.x = 0.5 + g
        root.scale = (0.8 + 1.2 * g, 0.8 + 1.2 * g, 1)
        for k, f in enumerate(foli):
            f.scale = (0.9 + 0.12 * math.sin(t * 6.28 + k),) * 3
    ctx.loop(upd)


@asset("thermal_flake", size=(480, 480), loop=(48, 12), samples=10, group=G)
def thermal_flake(ctx):
    kit.studio(scale=1.5)
    rk = tex_mat("noise", "#8a6d5a", "#b0907a", scale=3, detail=6, mid=0.5, contrast=0.3, rough=0.8, sss=0.02, coat=0, bump=0.2)
    core = _chunk(rk, (0, 0, 0.9), 1.0, scale=(1.2, 1.0, 0.95), seed=4, bump=0.1, sub=3)
    flakes = []
    for k in range(4):
        a = k * 1.4 + 0.3
        f = sphere(0.72, (0, 0, 0.9), rk, scale=(1.35, 1.15, 0.12), seg=24, rings=12)
        flakes.append((f, a))
    sun = sphere(0.45, (-1.8, 1.0, 3.2), glow("#ffb81f", 7), seg=24, rings=12)
    moon = sphere(0.4, (1.8, 1.0, 3.2), glow("#dfe8ff", 3), seg=24, rings=12)
    kit.camera((0, -7.2, 2.4), (0, 0, 1.6), lens=45)

    def upd(i, t):
        day = eased(t)
        sun.scale = (max(0.001, day),) * 3
        moon.scale = (max(0.001, 1 - day),) * 3
        core.scale = (1.0 + 0.05 * day,) * 3
        for k, (f, a) in enumerate(flakes):
            lift = max(0.0, day - 0.25 * k) * 0.55
            f.location = (math.cos(a) * 0.6 * lift * 2, -0.2 - lift * 0.9, 0.9 + math.sin(a) * 0.5 * lift + k * 0.05)
            f.rotation_euler = (R(60 * lift), R(25 * k), R(-30 * lift * (1 if k % 2 else -1)))
            f.scale = (1.0 - 0.1 * k, 1.0, 1.0)
    ctx.loop(upd)


@asset("soil_profile", size=(600, 520), samples=30, group=G)
def soil_profile(ctx):
    kit.studio(scale=2.0, key=500, amb=0.8)
    box((6.0, 3.0, 0.9), (0, 0, 3.55), mat("#4a3322", 0.9, sss=0.05, coat=0), bevel=0.04)
    box((6.0, 3.0, 0.9), (0, 0, 2.65), mat("#8a5f3a", 0.9, sss=0.05, coat=0), bevel=0.04)
    wr = box((6.0, 3.0, 1.0), (0, 0, 1.7), mat("#b09a82", 0.9, sss=0.0, coat=0), bevel=0.04)
    rnd = random.Random(2)
    for k in range(12):
        rock(rnd.uniform(0.18, 0.32), (rnd.uniform(-2.5, 2.5), -1.55, rnd.uniform(1.3, 2.1)), "#7b7f88", seed=k, squash=0.5)
    box((6.0, 3.0, 1.2), (0, 0, 0.6), mat("#6b7078", 0.7, sss=0.0, coat=0), bevel=0.04)
    box((6.04, 3.04, 0.12), (0, 0, 4.07), mat("#5bc25b", 0.6, sss=0.15), bevel=0.03)
    sphere(0.4, (-1.5, -0.6, 4.4), mat("#4cc25b", 0.6, sss=0.1), seg=16, rings=8)
    cyl(0.05, 0.5, (-1.5, -0.6, 4.2), mat("#8a5a34", 0.7), seg=8)
    cyl(0.03, 1.0, (-1.5, -1.5, 3.2), mat("#d9c8a0", 0.8), seg=8)
    kit.camera((0, -10.5, 3.6), (0, 0, 2.1), lens=42)
    ctx.still()


@asset("boulder_field", size=(640, 460), samples=28, group=G)
def boulder_field(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((10, 7, 0.5), (0, 0, -0.25), sandmat(), bevel=0.2)
    rnd = random.Random(6)
    for k in range(26):
        s = rnd.uniform(0.3, 0.75)
        ico(s, (rnd.uniform(-4.2, 4.2), rnd.uniform(-2.8, 2.8), s * 0.55), mat(rnd.choice(["#8a7f78", "#9c9087", "#7b726c", "#a8998a"]), 0.75, sss=0.02, coat=0), sub=3, scale=(1, 1, 0.8))
    kit.camera((0, -9.5, 5.2), (0, 0, 0.2), lens=40)
    ctx.still()


@asset("scree_slope", size=(640, 460), samples=28, group=G)
def scree_slope(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((10, 6, 0.5), (0, 0, -0.25), sandmat(), bevel=0.2)
    cl = tex_mat("noise", "#7a6a5c", "#a08c78", scale=3, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.4)
    box((9.0, 1.6, 5.0), (0, 2.0, 2.5), cl, bevel=0.2)
    cone(4.6, 0.3, 2.6, (0, 0.2, 1.3), mat("#9a8a7c", 0.9, sss=0.02, coat=0), scale=(1.3, 0.6, 1), seg=40)
    rnd = random.Random(8)
    for k in range(40):
        s = rnd.uniform(0.1, 0.34)
        rock(s, (rnd.uniform(-3.6, 3.6), rnd.uniform(-1.4, 0.6), rnd.uniform(0.1, 1.2) * (1 - abs(rnd.uniform(-1, 1)) * 0.0)), rnd.choice(["#8a7f78", "#a8998a", "#6f665f"]), seed=k, squash=0.7)
    kit.camera((0, -10.5, 4.0), (0, 0.5, 1.8), lens=40)
    ctx.still()


@asset("cave_stalactites", size=(640, 460), samples=34, group=G)
def cave_stalactites(ctx):
    kit.studio(scale=2.6, key=500, amb=0.5, top="#b9c3d6", bottom="#6a5a66")
    rk = tex_mat("noise", "#7a6a5c", "#a08c78", scale=2.6, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.35)
    blk = box((9, 4.5, 6), (0, 0, 3), rk, bevel=0.3)
    cut = sphere(2.8, (0, -2.6, 2.4), mat("#222"), scale=(1.1, 1.8, 0.95))
    cut.hide_render = True
    b = blk.modifiers.new("cave", "BOOLEAN")
    b.object = cut
    b.operation = "DIFFERENCE"
    b.solver = "EXACT"
    box((6, 4, 0.4), (0, -0.8, 0.2), mat("#4a3b33", 0.9), bevel=0.1)
    lime = mat("#f0e2c4", 0.35, sss=0.25, coat=0.4)
    rnd = random.Random(3)
    for k in range(9):
        x = rnd.uniform(-1.9, 1.9)
        h = rnd.uniform(0.6, 1.5)
        cone(0.2, 0.0, h, (x, rnd.uniform(-1.8, 0.2), 4.2 - h / 2 + 0.2), lime, rot=(R(180), 0, 0), seg=16)
    for k in range(6):
        h = rnd.uniform(0.4, 1.0)
        cone(0.22, 0.0, h, (rnd.uniform(-1.8, 1.8), rnd.uniform(-1.8, 0.0), 0.35 + h / 2), lime, seg=16)
    sphere(0.3, (0, -1.0, 2.0), glow("#ffd27a", 5))
    kit.camera((0, -11, 3.4), (0, 0, 2.2), lens=40)
    ctx.still()


# ═══════════════════ camel ═══════════════════
@asset("camel_idle", size=(520, 560), samples=40, group=G)
def camel_idle(ctx):
    kit.studio(scale=1.7)
    root = empty("camel", (0, 0, 0))
    fur = mat("#cfa05f", 0.75, sss=0.2, coat=0)
    dark = mat("#8a5f33", 0.8, sss=0.1, coat=0)
    sphere(1.0, (0, 0.1, 2.0), fur, scale=(0.75, 1.5, 0.7), seg=48, rings=24).parent = root
    sphere(0.5, (0, 0.1, 2.75), fur, scale=(0.9, 1.0, 0.95), seg=32, rings=16).parent = root              # hump
    # saddle blanket
    sphere(0.72, (0, 0.1, 2.05), mat("#d6403a", 0.7, sss=0.05, coat=0), scale=(1.05, 0.7, 0.72), seg=32, rings=16).parent = root
    for c in ("#ffd23f", "#1f8f6a"):
        sphere(0.725, (0, 0.1 + (0.18 if c == "#1f8f6a" else -0.18), 2.05), mat(c, 0.7, sss=0.05, coat=0), scale=(1.05, 0.06, 0.73), seg=32, rings=16).parent = root
    # neck + head
    neck = curve([(0, -1.25, 2.35), (0, -1.65, 2.8), (0, -1.75, 3.4), (0, -1.55, 3.9)], 0.3, fur)
    neck.parent = root
    head = sphere(0.42, (0, -1.7, 4.05), fur, scale=(0.85, 1.25, 0.9), seg=32, rings=16)
    head.parent = root
    sphere(0.3, (0, -2.12, 3.92), fur, scale=(0.9, 1.0, 0.75), seg=24, rings=12).parent = root
    for sx in (-1, 1):
        animal_eye(root, sx * 0.24, -1.95, 4.15, 0.09)
        sphere(0.12, (sx * 0.3, -1.45, 4.35), fur, scale=(0.5, 0.5, 1.1)).parent = root
        sphere(0.04, (sx * 0.1, -2.38, 3.95), dark, seg=8, rings=6).parent = root
    curve([(-0.18, -2.3, 3.78), (0, -2.33, 3.73), (0.18, -2.3, 3.78)], 0.022, mat("#1c1230", 0.3, sss=0)).parent = root
    # legs
    for lx, ly in ((-0.4, -0.7), (0.4, -0.7), (-0.4, 1.0), (0.4, 1.0)):
        capsule(0.14, 1.3, (lx, ly, 0.85), fur).parent = root
        sphere(0.17, (lx, ly - 0.03, 0.12), dark, scale=(1, 1.2, 0.5)).parent = root
    curve([(0, 1.55, 2.3), (0.05, 1.8, 1.9), (0.0, 1.85, 1.3)], 0.05, fur).parent = root
    sphere(0.1, (0, 1.85, 1.2), dark).parent = root
    root.rotation_euler = (0, 0, R(32))
    kit.camera((0, -10.0, 2.6), (0, 0, 2.2), lens=50)
    ctx.still()


# ═══════════════════ desert landforms ═══════════════════
def desert_cam(z=4.6, d=-10.0, lens=40, tz=0.6):
    kit.camera((0, d, z), (0, 0, tz), lens=lens)


@asset("mushroom_rock", size=(440, 520), samples=34, group=G)
def mushroom_rock(ctx):
    kit.studio(scale=1.4)
    sm = strata_mat(["#c9704a", "#e0a064", "#b5603f", "#d98a52"], 0.38, "Z", "Object", 0.85, offset=0.1)
    sand_slab(5, 4, 0.4, -0.2)
    base = cyl(0.55, 1.9, (0, 0, 1.0), sm, seg=40)
    d = base.modifiers.new("d", "DISPLACE"); t = bpy.data.textures.new("mr", "CLOUDS"); t.noise_scale = 0.6; d.texture = t; d.strength = 0.12
    cap = sphere(1.3, (0, 0, 2.3), sm, scale=(1.0, 1.0, 0.45), seg=48, rings=24)
    d2 = cap.modifiers.new("d", "DISPLACE"); d2.texture = t; d2.strength = 0.1
    sphere(0.3, (1.5, 0.6, 0.18), mat("#a0825c", 0.8), scale=(1, 1, 0.6))
    kit.camera((0, -8.0, 2.4), (0, 0, 1.4), lens=45)
    ctx.still()


@asset("wind_erosion", size=(560, 440), loop=(36, 12), samples=10, group=G)
def wind_erosion(ctx):
    kit.studio(scale=1.6)
    sm = strata_mat(["#c9704a", "#e0a064", "#b5603f", "#d98a52"], 0.38, "Z", "Object", 0.85, offset=0.1)
    sand_slab(7, 4, 0.4, -0.2)
    waist = cyl(0.55, 1.9, (0.8, 0, 1.0), sm, seg=40)
    cap = sphere(1.25, (0.8, 0, 2.3), sm, scale=(1.0, 1.0, 0.45), seg=48, rings=24)
    rnd = random.Random(4)
    grains = [(sphere(0.07, (0, 0, 0), mat(rnd.choice(["#f2d9a0", "#e0b46a", "#fff0c9"]), 0.7, sss=0), seg=8, rings=6), rnd.uniform(0, 1), rnd.uniform(-1.4, 1.4), rnd.uniform(0.15, 1.2)) for _ in range(70)]
    ars = [arrow((-3.3, -1.6, 0.8 + k * 0.6), (-2.2, -1.6, 0.8 + k * 0.6), "#ffffff", r=0.04, head=0.15) for k in range(3)]
    kit.camera((0, -8.2, 2.8), (0, 0, 1.3), lens=45)

    def upd(i, t):
        waist.scale = (1 - 0.18 * eased(t), 1 - 0.18 * eased(t), 1)
        for g, ph, y, z in grains:
            p = (t + ph) % 1.0
            g.location = (-3.5 + 7.0 * p, y, z + 0.25 * math.sin(p * 18 + ph * 6))
    ctx.loop(upd)


@asset("desert_depression", size=(620, 440), samples=32, group=G)
def desert_depression(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    disc = cyl(4.4, 1.2, (0, 0, -0.4), sandmat(), seg=64)
    cut = sphere(2.9, (0, 0, 0.55), mat("#222"), scale=(1, 1, 0.42), seg=48, rings=24)
    cut.hide_render = True
    b = disc.modifiers.new("bowl", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    cyl(1.5, 0.05, (0, 0, -0.38), mat("#2f9bff", 0.1, coat=0.8, sss=0.2), seg=40, scale=(1, 0.8, 1))
    cyl(1.9, 0.04, (0, 0, -0.395), mat("#3aa84f", 0.8, sss=0.1, coat=0), seg=40, scale=(1, 0.85, 1))
    for a in range(5):
        tree_palm((math.cos(a * 1.3) * 1.5, math.sin(a * 1.3) * 1.1 - 0.1, -0.35), 1.1, 6, 0.55)
    kit.camera((0, -9.5, 5.6), (0, 0, -0.2), lens=40)
    ctx.still()


@asset("hammada", size=(620, 440), samples=32, group=G)
def hammada(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    sand_slab(10, 6.5, 0.5, -0.25)
    sm = strata_mat(["#b5603f", "#d98a52", "#c9704a", "#e0a064"], 0.4, "Z", "Object", 0.85, offset=0.1)
    for x, y, w, d, h in ((-3.0, 0.5, 2.6, 2.2, 1.5), (0.4, -1.3, 2.0, 1.6, 1.1), (3.0, 1.0, 2.4, 2.4, 1.8)):
        box((w, d, h), (x, y, h / 2), sm, bevel=0.12)
    for x, y in ((-1.2, 0.3), (1.5, 0.4), (-2.0, -1.8), (3.2, -1.8)):
        sphere(0.55, (x, y, 0.0), sandmat(), scale=(1.5, 1, 0.3))
    kit.camera((0, -9.5, 5.0), (0, 0, 0.5), lens=40)
    ctx.still()


@asset("reg_plain", size=(620, 440), samples=32, group=G)
def reg_plain(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((10, 6.5, 0.5), (0, 0, -0.25), mat("#c9a572", 0.9, sss=0.03, coat=0), bevel=0.2)
    rnd = random.Random(9)
    for k in range(120):
        s = rnd.uniform(0.07, 0.2)
        ico(s, (rnd.uniform(-4.5, 4.5), rnd.uniform(-2.9, 2.9), s * 0.4), mat(rnd.choice(["#8a7f78", "#a8998a", "#6f665f", "#b5a590", "#7a6a5c"]), 0.8, sss=0, coat=0), sub=1, scale=(1, 1, 0.6))
    kit.camera((0, -9.5, 5.0), (0, 0, 0.3), lens=40)
    ctx.still()


@asset("inselberg", size=(620, 440), samples=32, group=G)
def inselberg(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    sand_slab(10, 6.5, 0.5, -0.25)
    gr = tex_mat("noise", "#b28a74", "#7d5a4a", scale=3.5, detail=7, mid=0.5, contrast=0.25, rough=0.7, sss=0.02, coat=0, bump=0.3)
    for x, y, r, hz in ((-2.8, 0.6, 1.5, 1.7), (0.6, -0.4, 1.9, 2.4), (3.2, 0.8, 1.2, 1.4)):
        o = sphere(r, (x, y, 0.0), gr, scale=(1, 0.9, hz / r), seg=48, rings=24)
        d = o.modifiers.new("d", "DISPLACE"); t = bpy.data.textures.new("ib", "CLOUDS"); t.noise_scale = 0.9; d.texture = t; d.strength = 0.18
    kit.camera((0, -9.5, 4.2), (0, 0, 1.0), lens=40)
    ctx.still()


@asset("yardang", size=(640, 440), samples=32, group=G)
def yardang(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    sand_slab(10, 6.5, 0.5, -0.25)
    sm = strata_mat(["#c9704a", "#e0a064"], 0.35, "Z", "Object", 0.85, offset=0.1)
    for k in range(4):
        o = sphere(1.0, (0, -2.1 + k * 1.4, 0.45), sm, scale=(3.6, 0.38, 0.9), seg=48, rings=24)
        d = o.modifiers.new("d", "DISPLACE"); t = bpy.data.textures.new(f"yd{k}", "CLOUDS"); t.noise_scale = 1.0; d.texture = t; d.strength = 0.1
    for k in range(3):
        arrow((-4.6, -2.2 + k * 2.0, 1.4), (-3.4, -2.2 + k * 2.0, 1.4), "#ffffff", r=0.05, head=0.2)
    kit.camera((0, -9.5, 5.2), (0, 0, 0.3), lens=40)
    ctx.still()


@asset("rock_arch", size=(640, 440), samples=34, group=G)
def rock_arch(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    sand_slab(10, 6.5, 0.5, -0.25)
    sm = strata_mat(["#b5603f", "#d98a52", "#c9704a", "#e0a064"], 0.4, "Z", "Object", 0.85, offset=0.1)
    wall = box((6.0, 1.8, 3.4), (0, 0, 1.7), sm, bevel=0.2)
    cut = cyl(1.0, 3.0, (0, 0, 1.0), mat("#222"), rot=(R(90), 0, 0), seg=40)
    cut.hide_render = True
    b = wall.modifiers.new("arch", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    box((1.9, 3.0, 1.1), (0, 0, 0.55), mat("#222"), bevel=0.0).hide_render = True
    b2 = wall.modifiers.new("arch2", "BOOLEAN"); b2.object = bpy.data.objects[-1]; b2.operation = "DIFFERENCE"; b2.solver = "EXACT"
    kit.camera((0, -9.5, 3.4), (0, 0, 1.7), lens=40)
    ctx.still()


@asset("butte_pillar", size=(440, 520), samples=32, group=G)
def butte_pillar(ctx):
    kit.studio(scale=1.4)
    sand_slab(5, 4, 0.4, -0.2)
    soft = strata_mat(["#e0a064", "#d98a52", "#c9704a"], 0.4, "Z", "Object", 0.85, offset=0.1)
    cone(0.75, 0.5, 2.6, (0, 0, 1.4), soft, seg=32)
    box((1.9, 1.5, 0.45), (0, 0, 2.85), mat("#5a4a42", 0.7, sss=0, coat=0), bevel=0.12)
    kit.camera((0, -8.0, 2.4), (0, 0, 1.5), lens=45)
    ctx.still()


@asset("sand_transport", size=(640, 400), loop=(48, 12), samples=10, group=G)
def sand_transport(ctx):
    kit.studio(scale=2.0, key=500, amb=0.9)
    box((10.0, 3.0, 0.5), (0, 0, -0.25), sandmat(), bevel=0.15)
    rnd = random.Random(3)
    dust = [(sphere(rnd.uniform(0.05, 0.1), (0, 0, 0), mat("#d8c6a0", 0.9, sss=0, alpha=0.6, coat=0), seg=8, rings=6), rnd.uniform(0, 1), rnd.uniform(-4.5, 4.5), rnd.uniform(1.6, 4.6)) for _ in range(60)]
    hop = [(sphere(0.1, (0, 0, 0), mat("#e0b46a", 0.7, sss=0), seg=10, rings=6), rnd.uniform(0, 1), rnd.uniform(-4.5, 0)) for _ in range(12)]
    gravel = [(sphere(0.17, (0, 0, 0.17), mat("#8a7f78", 0.8, sss=0, coat=0), seg=12, rings=8), rnd.uniform(0, 1)) for _ in range(6)]
    for k, z in enumerate((0.9, 2.2, 3.6)):
        arrow((-4.6, -1.3, z), (-3.2, -1.3, z), "#ffffff", r=0.05, head=0.2)
    kit.camera((0, -9.5, 3.0), (0, 0, 1.9), lens=40)

    def upd(i, t):
        for d, ph, x, z in dust:
            p = (t + ph) % 1.0
            d.location = (x + 3.0 * ((t * 1.0 + ph) % 1.0) - 1.5, -0.4, z + 0.3 * math.sin(p * 12))
        for h, ph, x in hop:
            p = (t * 2 + ph) % 1.0
            xx = (x + (t + ph) * 9.0) % 9.0 - 4.5
            h.location = (xx, -0.2, 0.12 + 1.0 * 4 * p * (1 - p))
        for g, ph in gravel:
            xx = ((t * 1.5 + ph) % 1.0) * 9.0 - 4.5
            g.location = (xx, -0.5 - ph * 0.8, 0.17)
            g.rotation_euler = (0, xx * 2, 0)
    ctx.loop(upd)


# dunes
def dune_base():
    kit.studio(scale=2.2, key=600, amb=0.9)
    sand_slab(10, 7, 0.5, -0.25)


def dune_cam():
    kit.camera((0, -9.5, 5.4), (0, 0, 0.2), lens=40)


@asset("dunes_barchan", size=(620, 420), samples=32, group=G)
def dunes_barchan(ctx):
    dune_base()
    sm = sandmat(4)
    for x, y, s in ((-1.5, 0.4, 1.0), (2.6, -1.6, 0.7)):
        o = sphere(1.6 * s, (x, y, 0.0), sm, scale=(1.0, 1.35, 0.5), seg=48, rings=24)
        cut = sphere(1.55 * s, (x + 1.2 * s, y, 0.18 * s), mat("#222"), scale=(1.0, 0.95, 0.9), seg=48, rings=24)
        cut.hide_render = True
        b = o.modifiers.new("c", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    arrow((-4.6, 2.6, 0.5), (-3.2, 2.6, 0.5), "#ffffff", r=0.05, head=0.22)
    dune_cam()
    ctx.still()


@asset("dunes_linear", size=(620, 420), samples=32, group=G)
def dunes_linear(ctx):
    dune_base()
    sm = sandmat(4)
    for k in range(4):
        sphere(1.0, (0, -2.4 + k * 1.6, 0.0), sm, scale=(4.2, 0.45, 0.55), seg=48, rings=24)
    arrow((-4.6, 2.9, 0.6), (-3.2, 2.9, 0.6), "#ffffff", r=0.05, head=0.22)
    dune_cam()
    ctx.still()


@asset("dunes_star", size=(620, 420), samples=32, group=G)
def dunes_star(ctx):
    dune_base()
    sm = sandmat(4)
    sphere(1.0, (0, 0, 0.0), sm, scale=(1.1, 1.1, 1.3), seg=48, rings=24)
    for k in range(5):
        a = k * 1.2566 + 0.3
        o = sphere(1.0, (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.0), sm, scale=(1.7, 0.45, 0.55), seg=48, rings=24)
        o.rotation_euler = (0, 0, a)
    for a in (0.5, 2.6, 4.4):
        arrow((math.cos(a) * 4.6, math.sin(a) * 3.2, 0.5), (math.cos(a) * 3.4, math.sin(a) * 2.4, 0.5), "#ffffff", r=0.05, head=0.22)
    dune_cam()
    ctx.still()


@asset("dunes_transverse", size=(620, 420), samples=32, group=G)
def dunes_transverse(ctx):
    dune_base()
    sm = sandmat(4)
    for k in range(6):
        o = sphere(1.0, (-3.6 + k * 1.45, 0.0, 0.0), sm, scale=(0.55, 3.0, 0.6), seg=48, rings=24)
        o.location.y = 0.25 * math.sin(k * 1.7)
    arrow((-4.6, -3.0, 0.8), (-3.4, -3.0, 0.8), "#ffffff", r=0.05, head=0.22)
    arrow((4.6, 3.0, 0.8), (3.4, 3.0, 0.8), "#ffffff", r=0.05, head=0.22)
    dune_cam()
    ctx.still()


@asset("loess_cliff", size=(620, 440), samples=32, group=G)
def loess_cliff(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((10, 6, 0.4), (0, 0, -0.2), mat("#c9a572", 0.9, sss=0.03, coat=0), bevel=0.2)
    lo = tex_mat("wave", "#e6bd5a", "#d4a43f", scale=8, mid=0.5, contrast=0.3, rough=0.9, sss=0.05, coat=0, bump=0.2)
    box((6.0, 3.0, 2.6), (0.5, 0.6, 1.3), lo, bevel=0.15)
    box((6.0, 1.6, 1.4), (0.5, -0.9, 0.7), lo, bevel=0.15)
    box((6.04, 3.04, 0.15), (0.5, 0.6, 2.62), mat("#6bbf59", 0.6, sss=0.15), bevel=0.04)
    for k in range(14):
        cone(0.1, 0.0, 0.5, (-1.8 + k * 0.4, 0.2 + (k % 3) * 0.5, 2.95), mat("#e8cf4a", 0.6, sss=0.1), seg=8)
    house((-2.0, 1.2, 2.68), 0.5)
    kit.camera((0, -9.5, 4.6), (0.3, 0, 1.4), lens=40)
    ctx.still()
