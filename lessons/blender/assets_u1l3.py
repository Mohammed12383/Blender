"""Unit 1 / Lesson 3 (rocks): rock & mineral icons, rock cycle stations, Oman's ophiolite."""
import math
import random

import bpy

from . import kit, props
from .assets_lib import asset
from .kit import V, box, cone, cyl, empty, ico, mat, sphere, torus, curve, tex_mat, strata_mat
from .props import glow, rock, arrow, prism_xz

R = math.radians
G = "u1l3"


def _chunk(material, loc=(0, 0, 0), s=1.0, scale=(1.15, 0.95, 0.8), seed=3, bump=0.22, sub=4):
    o = ico(1.0 * s, loc, material, sub=sub, scale=scale)
    d = o.modifiers.new("disp", "DISPLACE")
    t = bpy.data.textures.new(f"rc{seed}", "CLOUDS")
    t.noise_scale = 0.8
    d.texture = t
    d.strength = bump * s
    random.seed(seed)
    o.rotation_euler = (random.random(), random.random(), random.random() * 3)
    return o


def _block(material, loc=(0, 0, 0), size=(1.8, 1.4, 1.2), bevel=0.12):
    return box(size, loc, material, bevel=bevel)


def _icon(name, build, size=(420, 420), cam=((0, -4.6, 1.5), (0, 0, 0.72)), samples=28):
    def fn(ctx):
        kit.studio(scale=1.1)
        build()
        kit.camera(cam[0], cam[1], lens=50)
        ctx.still()
    asset(name, size=size, samples=samples, group=G)(fn)


def _granite():
    _chunk(tex_mat("noise", "#e9d6ca", "#4b4249", scale=14, detail=8, mid=0.5, contrast=0.11, rough=0.45, sss=0.02, coat=0.1), (0, 0, 0.8), 1.0)


def _basalt():
    _chunk(tex_mat("voronoi", "#15151a", "#4a4c55", scale=11, mid=0.12, contrast=0.07, rough=0.6, sss=0.0, coat=0.05), (0, 0, 0.8), 1.0, seed=5)


def _sandstone():
    _block(strata_mat(["#e8c488", "#d9a866", "#f0d4a0", "#c99458", "#e2b676"], 0.55, "Z", "Object", 0.8, offset=0.2), (0, 0, 0.7), (2.0, 1.5, 1.4), 0.1)


def _limestone():
    m = tex_mat("noise", "#f3e9d0", "#cdbf9a", scale=6, detail=6, mid=0.5, contrast=0.3, rough=0.7, sss=0.05, coat=0)
    _chunk(m, (0, 0, 0.8), 1.0, scale=(1.2, 0.95, 0.8), seed=8, bump=0.15)
    for x, z in ((0.5, 1.2), (-0.5, 0.9)):
        sphere(0.24, (x, -0.85, z), mat("#fff8e6", 0.4, coat=0.3), scale=(1, 0.35, 0.85)).rotation_euler = (0, 0, R(20))


def _gneiss():
    _chunk(tex_mat("wave", "#e6ddd2", "#3d3942", scale=5, mid=0.5, contrast=0.08, rough=0.5, sss=0.02, coat=0.1), (0, 0, 0.8), 1.0, seed=2, bump=0.12)


def _marble():
    _chunk(tex_mat("noise", "#fbfbfb", "#8f98a6", scale=3.2, detail=10, mid=0.5, contrast=0.03, rough=0.25, sss=0.25, coat=0.4), (0, 0, 0.8), 1.0, seed=6, bump=0.08)


def _quartz():
    gl = mat("#f7e8f0", 0.12, coat=0.7, sss=0.2)
    random.seed(4)
    for k in range(9):
        a = k / 9 * math.tau
        r = 0.5 + 0.2 * (k % 3)
        h = 0.9 + 0.5 * random.random() + (0.5 if k == 0 else 0)
        o = cyl(0.17 + 0.05 * (k % 2), h, (math.cos(a) * r * 0.5, math.sin(a) * r * 0.5, h / 2 + 0.1), gl, seg=6)
        o.rotation_euler = (math.sin(a) * 0.35, -math.cos(a) * 0.35, random.random())
        t = cone(0.19 + 0.05 * (k % 2), 0.0, 0.35, (math.cos(a) * r * 0.5 + math.sin(a) * 0.35 * h * 0.5, math.sin(a) * r * 0.5 - math.cos(a) * 0.35 * h * 0.5, h + 0.25), gl, seg=6)
        t.rotation_euler = (math.sin(a) * 0.35, -math.cos(a) * 0.35, random.random())
    sphere(0.9, (0, 0, 0.0), mat("#6b5a52", 0.7, coat=0), scale=(1.3, 1.3, 0.35))


def _calcite():
    gl = mat("#fff2c9", 0.15, coat=0.6, sss=0.25)
    o = box((1.3, 1.3, 1.3), (0, 0, 0.9), gl, bevel=0.06)
    o.rotation_euler = (R(18), R(-14), R(35))
    o.scale = (1, 1, 0.8)
    o2 = box((0.8, 0.8, 0.8), (0.9, -0.3, 0.45), gl, bevel=0.05)
    o2.rotation_euler = (R(-10), R(15), R(60))


def _magma():
    lava = tex_mat("noise", "#d92b0a", "#ffc02e", scale=2.4, detail=6, mid=0.5, contrast=0.35, rough=0.5, emit=2.2, sss=0, coat=0.2)
    sphere(1.0, (0, 0, 0.9), lava, scale=(1.2, 1, 0.8), seg=64, rings=32)
    sphere(0.35, (0.4, -0.7, 1.0), glow("#ffe27a", 4), scale=(1, 0.5, 0.7))
    rnd = random.Random(2)
    for k in range(6):
        sphere(rnd.uniform(0.1, 0.22), (rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.2), rnd.uniform(1.3, 1.9)), glow("#ff9a2a", 5))


def _sediment():
    sand = tex_mat("noise", "#e8cf9a", "#cfae72", scale=8, detail=5, mid=0.5, contrast=0.3, rough=0.9, sss=0.05, coat=0)
    sphere(1.3, (0, 0, 0.1), sand, scale=(1.2, 1, 0.55), seg=48, rings=24)
    rnd = random.Random(7)
    for k in range(14):
        sphere(rnd.uniform(0.05, 0.12), (rnd.uniform(-0.9, 0.9), rnd.uniform(-0.7, 0.5), rnd.uniform(0.35, 0.65)), mat(rnd.choice(["#9a7a52", "#b9b2a6", "#8a8f98", "#c9a066"]), 0.6, sss=0.02, coat=0))


def _metamorphic():
    bm = strata_mat(["#e6ddd2", "#3d3942", "#c9b8a8", "#5a5260"], 0.35, "Z", "Object", 0.5, offset=0.1)
    o = _chunk(bm, (0, 0, 0.8), 1.0, scale=(1.2, 0.95, 0.85), seed=11, bump=0.1)


for nm, fn in (("rock_granite", _granite), ("rock_basalt", _basalt), ("rock_sandstone", _sandstone), ("rock_limestone", _limestone), ("rock_gneiss", _gneiss),
               ("rock_marble", _marble), ("min_quartz", _quartz), ("min_calcite", _calcite), ("rock_magma", _magma), ("sediment_pile", _sediment), ("rock_metamorphic", _metamorphic)):
    _icon(nm, fn)


@asset("rocks_silica", size=(760, 300), samples=32, group=G)
def rocks_silica(ctx):
    kit.studio(scale=1.6)
    specs = [("#f0e0d6", "#8a7a78", 12, 1), ("#c9bfb4", "#4a4650", 12, 2), ("#4a4c52", "#16161b", 11, 3), ("#2a3a2c", "#0a0e0b", 11, 4)]
    for i, (c1, c2, sc, seed) in enumerate(specs):
        m = tex_mat("noise", c1, c2, scale=sc, detail=8, mid=0.5, contrast=0.12, rough=0.5, sss=0.02, coat=0.12)
        _chunk(m, (-3.6 + i * 2.4, 0, 0.8), 0.95, seed=seed)
    kit.camera((0, -10.5, 2.6), (0, 0, 0.7), lens=50)
    ctx.still()


@asset("igneous_types", size=(820, 560), samples=30, group=G)
def igneous_types(ctx):
    kit.studio(scale=2.4, key=650, amb=0.8)
    # cut-away ground
    box((9.0, 3.6, 3.4), (0, 0, -1.7), strata_mat(["#8a6a4a", "#7d5a46", "#8a8f98", "#6b7078"], 0.85, "Z", "Object", 0.8), bevel=0.05)
    box((9.04, 3.64, 0.25), (0, 0, 0.0), mat("#5bc25b", 0.6, sss=0.15), bevel=0.05)
    # intrusive pluton (coarse crystals) deep inside, with dikes
    gran = tex_mat("noise", "#f1d6cb", "#463d44", scale=16, detail=8, mid=0.5, contrast=0.12, rough=0.4, sss=0.02, coat=0.15)
    sphere(1.45, (-1.8, -1.55, -2.0), gran, scale=(1.3, 0.25, 0.8), seg=48, rings=24)
    for x, ang in ((-0.6, -40), (0.2, -25)):
        c = cyl(0.12, 3.0, (x, -1.76, -1.0), glow("#ff6a1a", 3), rot=(0, R(ang), 0), seg=16)
    # volcano with surface lava (fine-grained basalt)
    cone(1.7, 0.45, 1.6, (2.2, -0.4, 0.95), tex_mat("voronoi", "#17171c", "#4a4c55", scale=9, mid=0.12, contrast=0.07, rough=0.6, sss=0, coat=0.05), seg=48)
    for k in range(4):
        sphere(0.2 - k * 0.02, (2.9 + k * 0.4, -0.55, 0.85 - k * 0.2), glow("#ff6a1a", 4), scale=(1, 0.8, 0.6))
    smoke = mat("#6d6a76", 0.9, sss=0.1, coat=0)
    for x, z, s in ((2.2, 2.2, 0.5), (2.0, 2.7, 0.6), (2.5, 2.9, 0.55)):
        sphere(s, (x, -0.3, z), smoke, scale=(1, 0.8, 0.85))
    kit.camera((0, -11.5, 2.2), (0, 0, -0.5), lens=40)
    ctx.still()


@asset("fossil_layers", size=(720, 520), samples=30, group=G)
def fossil_layers(ctx):
    kit.studio(scale=2.0, key=600, amb=0.8)
    cols = ["#e8c488", "#c9704a", "#d9c26a", "#8e6f9a", "#6aa8a0"]
    for k, c in enumerate(cols):
        box((6.0, 2.6, 0.62), (0, 0, k * 0.62 + 0.31), mat(c, 0.7, sss=0.08, coat=0), bevel=0.04)
    shell = mat("#fff8e6", 0.4, coat=0.3)
    for x, z, k in ((-2.0, 0.31, 0), (-0.8, 0.93, 1), (1.2, 0.93, 1), (-1.6, 1.55, 2), (2.0, 1.55, 2), (0.4, 2.17, 3)):
        o = sphere(0.3, (x, -1.32, z), shell, scale=(1, 0.25, 0.8))
        o.rotation_euler = (0, 0, R(k * 15))
    # fish skeleton in layer 3
    for dx in range(5):
        capsule = cyl(0.03, 0.4 - dx * 0.03, (-0.3 + dx * 0.15, -1.32, 2.2), shell, seg=8)
    cyl(0.03, 0.95, (0.0, -1.32, 2.2), shell, rot=(0, R(90), 0), seg=8)
    sphere(0.2, (-0.7, -1.32, 2.2), shell, scale=(1, 0.3, 0.9))
    cone(0.22, 0.0, 0.3, (0.65, -1.32, 2.2), shell, rot=(0, R(-90), 0), seg=3)
    kit.camera((0, -10.5, 4.2), (0, 0, 1.55), lens=42)
    ctx.still()


@asset("porous_rock", size=(520, 440), samples=28, group=G)
def porous_rock(ctx):
    kit.studio(scale=1.4)
    m = tex_mat("voronoi", "#2b2118", "#d9b27a", scale=9, mid=0.16, contrast=0.025, rough=0.8, sss=0.03, coat=0)
    box((2.6, 1.9, 1.6), (0, 0, 0.8), m, bevel=0.1)
    for x, z in ((-0.6, 2.8), (0.4, 3.5), (0.9, 2.5)):
        sphere(0.14, (x, -0.4, z), mat("#3b8cff", 0.1, coat=0.8, sss=0.3), seg=20, rings=10)
        cone(0.09, 0.0, 0.28, (x, -0.4, z + 0.2), mat("#3b8cff", 0.1, coat=0.8, sss=0.3), seg=20)
    kit.camera((0, -8.0, 2.6), (0, 0, 1.4), lens=45)
    ctx.still()


@asset("metamorphic_press", size=(640, 460), samples=28, group=G)
def metamorphic_press(ctx):
    kit.studio(scale=1.5)
    bm = strata_mat(["#e8c488", "#c9704a", "#d9c26a", "#8e6f9a"], 0.4, "Z", "Object", 0.7, offset=0.1)
    box((2.0, 1.8, 1.6), (0, 0, 0.9), bm, bevel=0.1)
    for sx in (-1, 1):
        box((0.55, 2.2, 2.2), (sx * 1.7, 0, 1.0), mat("#5c6b7a", 0.35, metal=0.7, coat=0.3), bevel=0.05)
        arrow((sx * 3.5, -0.2, 1.1), (sx * 2.2, -0.2, 1.1))
    sphere(0.8, (0, -0.2, 0.1), glow("#ff6a1a", 3.0, 0.65), scale=(1.6, 1.3, 0.5))
    kit.camera((0, -9.0, 3.4), (0, 0, 1.1), lens=44)
    ctx.still()


@asset("ophiolite_stack", size=(760, 560), samples=30, group=G)
def ophiolite_stack(ctx):
    kit.studio(scale=2.4, key=650, amb=0.8)
    # from bottom: mantle, coarse gabbro, sheeted dikes, pillow lavas, with sea above
    box((6.0, 2.8, 1.0), (0, 0, 0.5), mat("#6b7a3c", 0.7, sss=0.05, coat=0), bevel=0.05)                   # mantle peridotite
    gab = tex_mat("noise", "#d9d4cc", "#2b2b30", scale=13, detail=8, mid=0.5, contrast=0.14, rough=0.5, sss=0.0, coat=0.1)
    box((6.0, 2.8, 1.0), (0, 0, 1.5), gab, bevel=0.05)                                                     # gabbro
    for k in range(14):
        box((0.22, 2.8, 0.9), (-2.8 + k * 0.43, 0, 2.5), mat("#ff8a3d" if k % 2 else "#4a4650", 0.6), bevel=0.02)   # dikes
    rnd = random.Random(2)
    for k in range(18):
        sphere(rnd.uniform(0.3, 0.45), (rnd.uniform(-2.6, 2.6), rnd.uniform(-1.1, 1.1), 3.2 + rnd.uniform(0, 0.15)), mat("#26272d", 0.4, coat=0.5), scale=(1, 1, 0.8), seg=24, rings=12)
    # copper deposit lumps + umber
    for k in range(4):
        sphere(0.2, (1.6 + k * 0.3, -1.45, 3.4 + (k % 2) * 0.1), mat("#2fa58a", 0.35, metal=0.4, coat=0.5), seg=16, rings=8)
    box((6.0, 2.8, 0.25), (0, 0, 3.65), mat("#7a3b24", 0.8, sss=0.05, coat=0), bevel=0.04)
    box((6.0, 2.8, 1.2), (0, 0, 4.45), mat("#4ab0e8", 0.1, alpha=0.35, coat=0.6, sss=0), bevel=0.04)
    kit.camera((2.2, -11.0, 5.4), (0, 0, 2.3), lens=42)
    ctx.still()


@asset("sediment_layers", size=(640, 460), loop=(48, 12), samples=10, group=G)
def sediment_layers(ctx):
    kit.studio(scale=1.7, key=500)
    box((6.4, 2.8, 0.3), (0, 0, -0.15), mat("#6b7078", 0.7), bevel=0.05)
    cols = ["#e8c488", "#c9704a", "#d9c26a", "#8e6f9a", "#6aa8a0"]
    layers = [box((6.0, 2.6, 0.5), (0, 0, 0.25 + k * 0.5), mat(c, 0.7, sss=0.08, coat=0), bevel=0.03) for k, c in enumerate(cols)]
    rnd = random.Random(3)
    grains = [(sphere(0.09, (0, 0, 3), mat(rnd.choice(cols), 0.5), seg=12, rings=8), rnd.uniform(0, 1), rnd.uniform(-2.5, 2.5), rnd.uniform(-1, 1)) for _ in range(40)]
    kit.camera((0, -10.0, 4.0), (0, 0, 1.2), lens=42)

    def upd(i, t):
        for k, l in enumerate(layers):
            p = max(0.0, min(1.0, (t * 5.6 - k)))
            e = p * p * (3 - 2 * p)
            l.scale = (1, 1, max(0.001, e))
            l.location.z = k * 0.5 + 0.25 * e
        for g, ph, x, y in grains:
            p = (t * 3 + ph) % 1.0
            g.location = (x, y, 3.2 - p * 2.2)
            g.scale = (0.001,) * 3 if p > 0.95 else (1,) * 3
    ctx.loop(upd)
