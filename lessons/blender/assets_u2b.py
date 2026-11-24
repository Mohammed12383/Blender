"""Unit 2 / Lessons 3-4: rivers (stages, falls, canyon, delta, fan) and the sea (waves, cliffs, caves, arches, beaches)."""
import math
import random

import bmesh
import bpy

from . import kit, props
from .assets_lib import asset
from .kit import V, box, capsule, cone, cyl, empty, ico, mat, sphere, torus, curve, tex_mat, strata_mat
from .props import glow, rock, arrow, prism_xz, poly_slab, tree_palm, cloud, house
from .assets_u2a import eased, sandmat, sand_slab

R = math.radians
G = "u2b"
WATER = ("#2f9bff", 0.12)


def watermat(color="#3aa6ff", alpha=1.0):
    return mat(color, 0.12, coat=0.85, sss=0.2, alpha=alpha)


def grass():
    return mat("#6bbf59", 0.8, sss=0.12, coat=0)


def pine(loc, h=1.4):
    root = empty("pine", loc)
    cyl(0.07, 0.4, (0, 0, 0.2), mat("#6b4a2d", 0.7), seg=8).parent = root
    for k in range(3):
        cone(0.45 - k * 0.1, 0.0, h * 0.55, (0, 0, 0.45 + k * h * 0.28 + h * 0.2), mat("#2c7a4a", 0.8, sss=0.1, coat=0), seg=10).parent = root
    return root


def river_curve(pts, width, y_off=0.0, z=0.08, color="#3aa6ff"):
    cu = curve([(x, y + y_off, z) for x, y in pts], width, watermat(color), name="river", res=24)
    cu.scale = (1, 1, 0.22)
    return cu


# ═══════════════════ river life: backgrounds ═══════════════════
def _river_scene(stage):
    kit.studio(scale=4.0, key=1800, fill=500, rim=350, amb=1.0, top="#bfe0ff", bottom="#ffe9d0")
    rnd = random.Random(7)
    if stage == "young":
        box((60, 60, 0.5), (0, 0, -0.25), grass(), bevel=0.0)
        # steep V valley: two mountain walls
        for sx in (-1, 1):
            for k in range(4):
                h = rnd.uniform(5, 8)
                cone(rnd.uniform(3.5, 5), 0.0, h, (sx * (4.8 + k * 0.6), 2.5 + k * 5.0, h / 2), tex_mat("noise", "#7a6a5c", "#a08c78", scale=2.5, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.3), seg=14)
        pts = [(0.4 * math.sin(i * 0.6), -10 + i * 2.2) for i in range(14)]
        river_curve(pts, 0.35)
        for k in range(10):
            sphere(0.3, (rnd.uniform(-0.6, 0.6), -9 + k * 2.6, 0.25), mat("#f4fbff", 0.9, sss=0.1, coat=0), scale=(1.3, 1, 0.6))
            rock(rnd.uniform(0.25, 0.5), (rnd.uniform(-1.0, 1.0), -9 + k * 2.4 + 1.0, 0.25), "#7b7f88", seed=k, squash=0.7)
        for k in range(14):
            pine((rnd.choice([-1, 1]) * rnd.uniform(1.8, 4.0), -8 + k * 1.8, 0.0), rnd.uniform(1.0, 1.8))
        kit.camera((0, -16, 5.5), (0, 4, 1.8), lens=36)
    elif stage == "mature":
        box((60, 60, 0.5), (0, 0, -0.25), grass(), bevel=0.0)
        for sx in (-1, 1):
            for k in range(4):
                h = rnd.uniform(3, 4.5)
                cone(rnd.uniform(4, 6), 0.0, h, (sx * (9 + k * 1.0), 6 + k * 5.0, h / 2 - 0.2), mat("#7aa56b", 0.85, sss=0.1, coat=0), seg=12)
        pts = [(2.2 * math.sin(i * 0.7), -10 + i * 2.2) for i in range(14)]
        river_curve(pts, 0.65)
        for k in range(10):
            box((7.5, 1.6, 0.06), (-4.5 if k % 2 else 4.5, -8 + k * 2.4, 0.04), mat("#e4c95a" if k % 3 else "#4cb04a", 0.8, sss=0.1, coat=0), bevel=0.0)
            if k % 3 == 0:
                house((rnd.choice([-5, 5]), -7 + k * 2.4, 0.05), 0.55)
        for k in range(10):
            pine((rnd.choice([-1, 1]) * rnd.uniform(3.5, 7), -8 + k * 2.2, 0.0), 1.1)
        kit.camera((0, -16, 6.5), (0, 4, 1.2), lens=36)
    else:
        box((60, 60, 0.5), (0, 0, -0.25), mat("#8fc965", 0.8, sss=0.12, coat=0), bevel=0.0)
        pts = [(3.4 * math.sin(i * 0.95), -10 + i * 1.6) for i in range(18)]
        river_curve(pts, 0.95)
        cu = curve([(-5.5, -2.0, 0.07), (-6.6, -1.0, 0.07), (-6.6, 1.0, 0.07), (-5.5, 2.0, 0.07), (-4.7, 0.5, 0.07), (-4.7, -0.6, 0.07)], 0.4, watermat("#4fb4ff"), cyclic=True, name="oxbow")
        cu.scale = (1, 1, 0.22)
        for k in range(12):
            box((6.5, 1.4, 0.06), (rnd.choice([-8, 8]), -9 + k * 1.8, 0.04), mat(rnd.choice(["#e4c95a", "#4cb04a", "#b9d84a"]), 0.8, sss=0.1, coat=0), bevel=0.0)
        for k in range(6):
            cone(rnd.uniform(3, 4.5), 0.0, 1.6, (rnd.uniform(-18, 18), 24 + rnd.uniform(0, 5), 0.6), mat("#9ac286", 0.9, sss=0.1, coat=0), seg=12)
        kit.camera((0, -15, 7.5), (0, 3, 0.6), lens=36)


for stage in ("young", "mature", "old"):
    def _mk(stage=stage):
        def f(ctx):
            _river_scene(stage)
            ctx.still()
        return f
    asset(f"river_{stage}", size=(1280, 720), bg=True, samples=22, group=G)(_mk())


@asset("river_parts", size=(640, 520), samples=34, group=G)
def river_parts(ctx):
    kit.studio(scale=3.0, key=900, amb=0.9)
    box((11, 9, 0.5), (0, 0.5, -0.25), grass(), bevel=0.2)
    rnd = random.Random(4)
    # mountains (drainage basin) at the back with tributaries
    for x, h in ((-3.5, 2.6), (-1.0, 3.2), (1.8, 2.8), (4.0, 2.2)):
        cone(1.9, 0.0, h, (x, 3.6, h / 2), tex_mat("noise", "#7a6a5c", "#a08c78", scale=2.5, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.3), seg=14)
        cone(0.7, 0.0, 0.9, (x, 3.6, h - 0.35), mat("#f7fbff", 0.5, sss=0.1, coat=0), seg=14)
    for pts in ([(-3.4, 3.2), (-2.4, 2.2), (-1.0, 1.4), (0.0, 0.6)], [(3.8, 3.0), (2.8, 2.0), (1.6, 1.2), (0.0, 0.6)], [(-0.6, 3.2), (-0.3, 2.2), (0.0, 1.4), (0.0, 0.6)]):
        river_curve(pts, 0.1)
    # main channel with meanders to the sea
    pts = [(0.0, 0.6), (-1.2, -0.4), (0.6, -1.4), (-0.9, -2.4), (0.3, -3.3)]
    river_curve(pts, 0.25)
    cu = curve([(1.6, -1.6, 0.08), (2.3, -1.2, 0.08), (2.3, -0.4, 0.08), (1.6, 0.0, 0.08), (1.3, -0.6, 0.08), (1.3, -1.2, 0.08)], 0.15, watermat(), cyclic=True, name="oxbow")
    cu.scale = (1, 1, 0.22)
    box((8.0, 2.6, 0.06), (0, -1.2, 0.04), mat("#9ad25a", 0.8, sss=0.1, coat=0), bevel=0.0)       # flood plain
    # delta + sea
    box((11, 3.2, 0.3), (0, -5.6, -0.1), watermat("#2e86e0"), bevel=0.1)
    poly_slab([(-0.4, 0), (0.9, 0), (2.2, -2.2), (1.1, -2.6), (0.0, -2.4), (-1.1, -2.6), (-2.2, -2.2)], 0.6, 0.12, mat("#e8cf9a", 0.9, sss=0.05, coat=0), 0.02, "delta").__getitem__(0).location.__setitem__(slice(0, 3), (0.2, -3.6, 0.1))
    for x, y in ((-3.2, -1.2), (3.2, 0.2)):
        tree_palm((x, y, 0.0), 0.9, 6, 0.5)
    kit.camera((0, -9.5, 7.5), (0, 0.0, 0.0), lens=40)
    ctx.still()


@asset("waterfall", size=(580, 460), loop=(36, 12), samples=10, group=G)
def waterfall(ctx):
    kit.studio(scale=2.0, key=600, amb=0.9)
    rk = tex_mat("noise", "#7a6a5c", "#a08c78", scale=2.5, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.3)
    box((6.0, 3.2, 3.2), (0, 2.4, 1.6), rk, bevel=0.15)
    box((6.4, 3.6, 0.5), (0, 2.4, 3.35), mat("#5a4a42", 0.75, sss=0, coat=0), bevel=0.1)
    box((10, 4.0, 0.3), (0, -1.4, 0.0), grass(), bevel=0.1)
    box((2.2, 4.4, 0.12), (0, 5.2, 3.7), watermat(), bevel=0.02)              # river above
    sheet = box((2.0, 0.18, 3.4), (0, 0.78, 1.8), watermat(alpha=0.8), bevel=0.02)
    pool = cyl(1.8, 0.1, (0, -0.2, 0.1), watermat("#3aa6ff"), seg=40, scale=(1.2, 1, 1))
    rnd = random.Random(3)
    drops = [(sphere(0.12, (0, 0, 0), mat("#ffffff", 0.2, coat=0.6, sss=0), seg=8, rings=6), rnd.uniform(0, 1), rnd.uniform(-0.8, 0.8)) for _ in range(50)]
    foam = [(sphere(0.2, (0, 0, 0), mat("#f4fbff", 0.8, sss=0, coat=0), seg=10, rings=6), rnd.uniform(0, 1), rnd.uniform(-1, 1)) for _ in range(16)]
    kit.camera((0, -9.0, 3.6), (0, 0.5, 1.8), lens=42)

    def upd(i, t):
        for d, ph, x in drops:
            p = (t * 2 + ph) % 1.0
            d.location = (x, 0.55 - p * 0.3, 3.6 - p * 3.5)
        for f, ph, x in foam:
            p = (t * 1.5 + ph) % 1.0
            f.location = (x * (0.5 + p), -0.3 - p * 0.8, 0.25 + 0.2 * math.sin(p * 3.14))
            f.scale = (max(0.001, 1 - p * 0.7),) * 3
    ctx.loop(upd)


@asset("waterfall_section", size=(640, 480), samples=32, group=G)
def waterfall_section(ctx):
    kit.studio(scale=2.0, key=600, amb=0.9)
    box((7, 2.4, 0.4), (0, 0, 0.0), mat("#4a3b33", 0.9), bevel=0.1)
    hard = mat("#4a4650", 0.55, sss=0, coat=0)
    soft = mat("#d9b27a", 0.85, sss=0.05, coat=0)
    box((3.2, 2.4, 1.0), (-2.0, 0, 2.3), hard, bevel=0.08)                 # hard cap on top, left plateau
    box((3.2, 2.4, 1.4), (-2.0, 0, 1.2), soft, bevel=0.08)                 # soft layer under it (undercut visible)
    box((2.4, 2.4, 1.7), (-1.9, 0, 0.35 + 0.6), soft, bevel=0.08)
    box((1.9, 2.4, 0.6), (-0.5, 0, 3.0), mat("#222"), bevel=0.0).hide_render = True
    # undercut notch in the soft layer
    notch = box((1.3, 2.6, 0.9), (-0.45, 0, 1.4), mat("#222"), bevel=0.0)
    notch.hide_render = True
    # overhanging cap
    box((1.5, 2.4, 0.4), (-0.05, 0, 2.5), hard, bevel=0.06)
    box((2.0, 2.4, 0.2), (2.6, 0, 0.35), watermat(), bevel=0.03)
    box((0.22, 2.2, 2.5), (0.7, 0, 1.4), watermat(alpha=0.8), bevel=0.02)
    arrow((1.2, -1.5, 0.9), (0.2, -1.5, 0.9), "#ff3b3b")
    kit.camera((0, -9.0, 3.0), (-0.3, 0, 1.5), lens=40)
    ctx.still()


@asset("rapids", size=(580, 440), samples=32, group=G)
def rapids(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((9, 6, 0.4), (0, 0, -0.2), grass(), bevel=0.2)
    river_curve([(-4.2, -0.4), (-2.0, 0.5), (0.5, -0.4), (2.6, 0.4), (4.4, -0.1)], 0.9)
    rnd = random.Random(2)
    for k in range(14):
        rock(rnd.uniform(0.28, 0.5), (-3.8 + k * 0.58, rnd.uniform(-0.6, 0.6) + 0.25 * math.sin(k), 0.3), rnd.choice(["#5a5560", "#7b7f88", "#4a4650"]), seed=k, squash=0.8)
        sphere(0.22, (-3.8 + k * 0.58, rnd.uniform(-0.6, 0.6), 0.5), mat("#f4fbff", 0.9, sss=0.1, coat=0), scale=(1.3, 1, 0.6))
    kit.camera((0, -8.5, 5.0), (0, 0, 0.2), lens=40)
    ctx.still()


@asset("canyon", size=(560, 500), samples=34, group=G)
def canyon(ctx):
    kit.studio(scale=2.6, key=800, amb=0.9)
    st = strata_mat(["#c9704a", "#e0a064", "#b5603f", "#d98a52", "#a2502f"], 0.5, "Z", "Object", 0.85, offset=0.2)
    for sx in (-1, 1):
        for k in range(3):
            box((3.0, 8.0, 1.2), (sx * (2.1 + k * 0.8), 0, 0.6 + k * 1.2 - 1.2 + 0.2), st, bevel=0.08)
    box((1.4, 8.0, 0.2), (0, 0, -1.2), watermat(), bevel=0.02)
    kit.camera((0, -12, 6.0), (0, 0, 0.8), lens=42)
    ctx.still()


@asset("river_transport", size=(640, 400), loop=(48, 12), samples=10, group=G)
def river_transport(ctx):
    kit.studio(scale=2.0, key=600, amb=0.9)
    box((10, 3.0, 0.6), (0, 0, -0.3), mat("#8a6a4a", 0.9, sss=0.03, coat=0), bevel=0.1)
    box((10, 2.6, 3.0), (0, 0, 1.5), watermat(alpha=0.35), bevel=0.05)
    rnd = random.Random(4)
    silt = [(sphere(0.06, (0, 0, 0), mat("#c9a572", 0.8, sss=0, coat=0), seg=8, rings=6), rnd.uniform(0, 1), rnd.uniform(0.7, 2.7), rnd.uniform(-1, 1)) for _ in range(60)]
    sand = [(sphere(0.12, (0, 0, 0), mat("#e0b46a", 0.7, sss=0), seg=10, rings=6), rnd.uniform(0, 1), rnd.uniform(-0.9, 0.9)) for _ in range(10)]
    boul = [(sphere(0.32, (0, 0, 0.3), mat("#6f665f", 0.8, sss=0, coat=0), seg=14, rings=8), rnd.uniform(0, 1), rnd.uniform(-0.8, 0.8)) for _ in range(4)]
    for z in (0.5, 1.5, 2.5):
        arrow((-4.6, -1.5, z), (-3.4, -1.5, z), "#ffffff", r=0.05, head=0.2)
    kit.camera((0, -9.0, 3.0), (0, 0, 1.3), lens=42)

    def upd(i, t):
        for s, ph, z, y in silt:
            x = ((t + ph) % 1.0) * 9.0 - 4.5
            s.location = (x, y, z + 0.12 * math.sin(t * 12 + ph * 9))
        for s, ph, y in sand:
            p = (t * 3 + ph) % 1.0
            x = ((t + ph) % 1.0) * 9.0 - 4.5
            s.location = (x, y, 0.1 + 0.55 * 4 * p * (1 - p))
        for b, ph, y in boul:
            x = ((t * 0.6 + ph) % 1.0) * 9.0 - 4.5
            b.location = (x, y, 0.3)
            b.rotation_euler = (0, x * 2.5, 0)
    ctx.loop(upd)


@asset("floodplain", size=(560, 440), samples=32, group=G)
def floodplain(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((10, 6.5, 0.4), (0, 0, -0.2), mat("#8fc965", 0.8, sss=0.1, coat=0), bevel=0.2)
    box((9.0, 3.8, 0.1), (0, 0, 0.06), watermat("#4fb4ff", 0.55), bevel=0.02)          # flood water
    river_curve([(-4.5, -0.5), (-2.0, 0.9), (0.5, -0.8), (2.6, 0.8), (4.6, -0.2)], 0.6)
    for x, y in ((-3.0, 2.3), (2.0, -2.2), (3.8, 2.1)):
        house((x, y, 0.0), 0.55)
    for x, y in ((-1.2, -2.3), (0.9, 2.4)):
        tree_palm((x, y, 0.0), 0.8, 5, 0.5)
    kit.camera((0, -9.5, 6.4), (0, 0, 0.0), lens=40)
    ctx.still()


def _delta(shape):
    kit.studio(scale=2.4, key=700, amb=0.9)
    box((10, 6.5, 0.4), (0, 0, -0.2), watermat("#2e86e0"), bevel=0.2)
    box((10, 2.2, 0.4), (0, 2.6, -0.1), mat("#9ad25a", 0.8, sss=0.1, coat=0), bevel=0.1)
    sand = mat("#e8cf9a", 0.9, sss=0.05, coat=0)
    if shape == "arc":
        pts = [(0.0, 0.0)] + [(math.cos(a) * 2.6, -math.sin(a) * 2.2) for a in [k * math.pi / 14 for k in range(15)]]
        pts = [(math.cos(a) * 24, -math.sin(a) * 20) for a in [k * math.pi / 14 for k in range(15)]]
    elif shape == "bird":
        pts = [(-1, 0), (1, 0), (1.5, -4), (3.0, -8), (3.6, -12), (2.0, -13), (0.8, -9), (0.2, -15), (-0.9, -9), (-2.2, -13), (-3.6, -11), (-2.8, -7), (-1.5, -4)]
        pts = [(x * 6, y * 2.0) for x, y in pts]
    else:
        pts = [(-4, 0), (4, 0), (0, -14)]
        pts = [(x * 6, y * 1.6) for x, y in pts]
    o, c = poly_slab(pts, 0.1, 0.3, sand, 0.04, "delta")
    o.location = (0, 1.9 - 0.0, 0.0)
    cu = curve([(0, 4.0, 0.12), (0, 2.6, 0.12), (0, 1.9, 0.12)], 0.28, watermat(), name="river")
    cu.scale = (1, 1, 0.3)
    kit.camera((0, -9.5, 8.5), (0, 0.5, 0.0), lens=40)


for shp in ("arc", "bird", "tri"):
    def _mk(shp=shp):
        def f(ctx):
            _delta(shp)
            ctx.still()
        return f
    asset(f"delta_{shp}", size=(620, 420), samples=30, group=G)(_mk())


@asset("alluvial_fan", size=(600, 440), samples=32, group=G)
def alluvial_fan(ctx):
    kit.studio(scale=2.4, key=700, amb=0.9)
    sand_slab(10, 7, 0.5, -0.25)
    rk = tex_mat("noise", "#7a6a5c", "#a08c78", scale=2.5, detail=6, mid=0.5, contrast=0.3, rough=0.85, sss=0.02, coat=0, bump=0.35)
    for k, x in enumerate((-3.2, -1.0, 1.4, 3.4)):
        cone(1.8, 0.0, 3.4 + (k % 2) * 0.5, (x, 3.2, 1.7), rk, seg=12)
    fan = cone(3.6, 0.2, 0.5, (0.0, 0.2, 0.25), mat("#d9b27a", 0.9, sss=0.05, coat=0), scale=(1, 1, 1), seg=48)
    fan.rotation_euler = (0, 0, 0)
    # keep only the fan sector in front of the mountains by flattening it
    fan.scale = (1.15, 0.9, 0.45)
    fan.location = (0, 0.4, 0.22)
    river_curve([(0.0, 3.0), (0.0, 2.0), (0.4, 0.8), (0.0, -0.6), (-0.6, -1.5)], 0.2, color="#9a8a6a")
    for k in range(7):
        a = -0.9 + k * 0.3
        river_curve([(0.0, 1.8), (math.sin(a) * 1.6, 0.2 - math.cos(a) * 0.4), (math.sin(a) * 3.0, -1.0 - math.cos(a) * 0.6)], 0.05, color="#b49a74")
    kit.camera((0, -9.5, 6.2), (0, 0.4, 0.4), lens=40)
    ctx.still()


# ═══════════════════ the sea ═══════════════════
def wave_plane(size=(10, 6), n=36):
    me = bpy.data.meshes.new("sea")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=n, y_segments=n, size=1.0)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("sea", me)
    bpy.context.collection.objects.link(o)
    o.scale = (size[0] / 2, size[1] / 2, 1)
    o.data.materials.append(watermat("#2f8fe0"))
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    return o


def set_waves(o, t, amp=0.18, k=2.2, speed=1.0, base=0.0):
    me = o.data
    co = [0.0] * (len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    for i in range(len(me.vertices)):
        x, y = co[3 * i], co[3 * i + 1]
        co[3 * i + 2] = base + amp * math.sin(x * k * 2 - t * math.tau * speed + y * 1.3) * (0.6 + 0.4 * math.sin(y * 3))
    me.vertices.foreach_set("co", co)
    me.update()


@asset("cliff_waves", size=(600, 440), loop=(48, 12), samples=10, group=G)
def cliff_waves(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    st = strata_mat(["#e0a064", "#c9704a", "#d98a52", "#b5603f"], 0.5, "Z", "Object", 0.85, offset=0.2)
    box((6.0, 2.6, 3.4), (0, 3.2, 1.7), st, bevel=0.12)
    box((3.0, 2.6, 0.9), (0, 1.9, 0.55), mat("#d9b27a", 0.9, sss=0.05, coat=0), bevel=0.05)   # soft notch layer
    sea = wave_plane((11, 6), 40)
    sea.location = (0, -0.6, 0.3)
    foam = [sphere(0.16, (0, 0, 0), mat("#f4fbff", 0.8, sss=0, coat=0), seg=8, rings=6) for _ in range(20)]
    kit.camera((0, -9.0, 4.0), (0, 1.0, 1.4), lens=42)

    def upd(i, t):
        set_waves(sea, t, 0.17, 1.6, 1.0, 0.0)
        for k, f in enumerate(foam):
            p = (t * 2 + k / len(foam)) % 1.0
            f.location = (-3.0 + 6.0 * (k / len(foam)), 1.55 - 0.15 * p, 0.38 + 0.4 * math.sin(p * 3.14))
            f.scale = (max(0.001, math.sin(p * 3.14)),) * 3
    ctx.loop(upd)


def coast_base():
    kit.studio(scale=2.4, key=700, amb=0.9)
    box((11, 8, 0.4), (0, 0, -0.2), watermat("#2f8fe0"), bevel=0.2)


ROCK_COAST = lambda: strata_mat(["#e0a064", "#c9704a", "#d98a52", "#b5603f"], 0.5, "Z", "Object", 0.85, offset=0.2)


@asset("coast_cave", size=(620, 440), samples=34, group=G)
def coast_cave(ctx):
    coast_base()
    box((11, 3.5, 0.3), (0, 2.4, 0.0), mat("#e8cf9a", 0.9, sss=0.05, coat=0), bevel=0.05)
    cl = box((8.0, 3.2, 3.6), (0, 2.6, 1.8), ROCK_COAST(), bevel=0.15)
    cut = cyl(1.0, 3.0, (0.3, 1.0, 0.8), mat("#222"), rot=(R(90), 0, 0), seg=32, scale=(1, 1, 1))
    cut.hide_render = True
    b = cl.modifiers.new("cave", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    cut2 = box((2.0, 3.0, 1.0), (0.3, 1.0, 0.4), mat("#222"), bevel=0.0)
    cut2.hide_render = True
    b2 = cl.modifiers.new("cave2", "BOOLEAN"); b2.object = cut2; b2.operation = "DIFFERENCE"; b2.solver = "EXACT"
    box((2.2, 1.6, 0.12), (0.3, 0.5, 0.06), watermat(), bevel=0.02)
    kit.camera((0, -10, 3.8), (0, 1.0, 1.4), lens=40)
    ctx.still()


@asset("coast_arch", size=(620, 440), samples=34, group=G)
def coast_arch(ctx):
    coast_base()
    box((11, 2.4, 0.3), (0, 3.0, 0.0), mat("#e8cf9a", 0.9, sss=0.05, coat=0), bevel=0.05)
    hl = box((2.6, 5.4, 2.8), (0, 0.4, 1.4), ROCK_COAST(), bevel=0.15)
    cut = cyl(0.8, 3.0, (0, 0.2, 0.8), mat("#222"), rot=(R(90), 0, R(90)), seg=32)
    cut.hide_render = True
    b = hl.modifiers.new("arch", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    box((3.0, 1.6, 0.8), (0, 0.2, 0.0), mat("#222"), bevel=0.0).hide_render = True
    b2 = hl.modifiers.new("arch2", "BOOLEAN"); b2.object = bpy.data.objects[-1]; b2.operation = "DIFFERENCE"; b2.solver = "EXACT"
    box((8.0, 2.0, 3.6), (0, 3.4, 1.8), ROCK_COAST(), bevel=0.15)
    kit.camera((4.5, -9.0, 3.8), (0, 0.8, 1.2), lens=40)
    ctx.still()


@asset("coast_stack", size=(620, 440), samples=34, group=G)
def coast_stack(ctx):
    coast_base()
    box((11, 2.4, 0.3), (0, 3.2, 0.0), mat("#e8cf9a", 0.9, sss=0.05, coat=0), bevel=0.05)
    box((8.0, 2.0, 3.6), (0, 3.6, 1.8), ROCK_COAST(), bevel=0.15)
    for x, y, h in ((-0.4, 0.6, 3.0), (1.6, -0.8, 1.6)):
        cone(0.62, 0.45, h, (x, y, h / 2), ROCK_COAST(), seg=24)
    sphere(0.8, (-2.2, 0.8, 0.0), ROCK_COAST(), scale=(1, 1, 0.5))
    kit.camera((0, -10, 4.2), (0, 0.8, 1.4), lens=40)
    ctx.still()


@asset("coast_bay", size=(620, 440), samples=34, group=G)
def coast_bay(ctx):
    coast_base()
    sand = mat("#e8cf9a", 0.9, sss=0.05, coat=0)
    box((11, 2.0, 0.3), (0, 3.2, 0.0), sand, bevel=0.05)
    cl = ROCK_COAST()
    box((3.2, 3.6, 3.0), (-3.6, 1.4, 1.5), cl, bevel=0.2)
    box((3.2, 3.6, 3.0), (3.6, 1.4, 1.5), cl, bevel=0.2)
    box((4.2, 1.4, 0.3), (0, 2.5, 0.1), sand, bevel=0.1)
    kit.camera((0, -9.0, 6.0), (0, 1.0, 0.8), lens=40)
    ctx.still()


@asset("beach_tide", size=(560, 440), loop=(36, 12), samples=10, group=G)
def beach_tide(ctx):
    kit.studio(scale=2.0, key=600, amb=0.9)
    slope = box((10, 5.0, 0.4), (0, 2.0, 0.0), mat("#e8cf9a", 0.9, sss=0.05, coat=0), bevel=0.05)
    slope.rotation_euler = (R(-9), 0, 0)
    slope.location = (0, 2.4, 0.5)
    sea = box((10, 4.6, 0.7), (0, -1.0, 0.4), watermat("#2f8fe0", 0.85), bevel=0.05)
    sphere(0.5, (3.8, 4.0, 3.0), glow("#dfe8ff", 3))
    for x in (-4.2, -2.6):
        tree_palm((x, 4.6, 1.1), 0.9, 5, 0.6)
    arrow((4.4, 3.3, 3.0), (4.4, 2.5, 1.6), "#ffffff", r=0.04, head=0.2)
    kit.camera((0, -9.5, 3.8), (0, 1.0, 0.8), lens=42)

    def upd(i, t):
        h = eased(t)
        sea.location = (0, -1.0 + 1.7 * h, 0.15 + 0.4 * h)
    ctx.loop(upd)


@asset("coriolis_globe", size=(440, 440), samples=30, group=G)
def coriolis_globe(ctx):
    kit.studio(scale=1.4)
    sphere(1.0, (0, 0, 0), tex_mat("noise", "#2f7bf0", "#52c970", scale=1.7, detail=5, mid=0.52, contrast=0.025, rough=0.4), seg=64, rings=32)
    for sgn, col in ((1, "#ffd23f"), (-1, "#ff6b6b")):
        pts = [(-0.5 - 0.1 * k, -1.15 - 0.05 * k, sgn * (0.55 + 0.09 * k) * (1 + 0.0)) for k in range(0)]
        c = curve([(-0.7, -1.1, sgn * 0.5), (-0.1, -1.25, sgn * 0.55), (0.6, -1.1, sgn * (0.5 + sgn * -0.25))], 0.07, glow(col, 4), name="co")
        cone(0.14, 0.0, 0.3, (0.65, -1.07, sgn * (0.5 - sgn * 0.25)), glow(col, 4), rot=(R(-90), 0, R(-90 + sgn * 35)), seg=16)
    kit.camera((0, -4.6, 0.3), (0, 0, 0), lens=50)
    ctx.still()


@asset("longshore_drift", size=(640, 420), loop=(36, 12), samples=10, group=G)
def longshore_drift(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    box((10, 3.2, 0.3), (0, 2.6, 0.0), mat("#e8cf9a", 0.9, sss=0.05, coat=0), bevel=0.05)
    box((10, 4.0, 0.3), (0, -1.0, -0.05), watermat("#2f8fe0"), bevel=0.05)
    rnd = random.Random(2)
    waves = [box((3.0, 0.12, 0.12), (0, 0, 0.2), mat("#f4fbff", 0.5, sss=0, coat=0), bevel=0.03) for _ in range(5)]
    for w in waves:
        w.rotation_euler = (0, 0, R(-24))
    peb = [sphere(0.1, (0, 0, 0.2), mat(rnd.choice(["#8a7f78", "#c9a572", "#a8998a"]), 0.8, sss=0, coat=0), seg=10, rings=6) for _ in range(8)]
    arrow((-3.2, -2.3, 0.4), (-1.6, -0.3, 0.4), "#ffffff", r=0.05, head=0.2)
    kit.camera((0, -6.5, 9.5), (0, 0.7, 0.0), lens=38)

    def upd(i, t):
        for k, w in enumerate(waves):
            p = (t + k / len(waves)) % 1.0
            w.location = (-3.0 + k * 1.6 + 1.6 * p, -2.4 + 3.6 * p, 0.2)
            w.scale = (1, max(0.01, math.sin(p * 3.14)), 1)
        for k, s in enumerate(peb):
            p = (t * 2 + k / len(peb)) % 1.0
            seg = (t * 2 + k / len(peb)) % 2.0
            x = -4.0 + ((t + k / len(peb)) % 1.0) * 8.0
            y = 1.5 + (0.45 if (p < 0.5) else -0.15)
            s.location = (x, y + 0.2 * math.sin(p * 6.28), 0.2)
    ctx.loop(upd)


@asset("dhow", size=(520, 520), samples=38, group=G)
def dhow(ctx):
    kit.studio(scale=1.6)
    root = empty("dhow", (0, 0, 0))
    wood = mat("#8a5a34", 0.55, sss=0.1, coat=0.2)
    dark = mat("#5a3a22", 0.6, sss=0.05, coat=0.2)
    sphere(2.2, (0, 0, 0.9), wood, scale=(1.0, 0.45, 0.28), seg=64, rings=32).parent = root
    sphere(2.2, (0, 0, 0.78), dark, scale=(1.01, 0.46, 0.1), seg=64, rings=32).parent = root
    cone(0.18, 0.0, 1.0, (-2.35, 0, 1.35), wood, rot=(0, R(55), 0), seg=16).parent = root
    cone(0.25, 0.0, 1.1, (2.35, 0, 1.2), wood, rot=(0, R(-40), 0), seg=16).parent = root
    box((1.3, 0.8, 0.5), (1.3, 0, 1.4), dark, bevel=0.06).parent = root
    cyl(0.07, 3.6, (-0.2, 0, 2.7), dark, seg=12).parent = root
    cyl(0.05, 3.0, (-0.2, 0, 3.0), dark, rot=(0, R(-62), 0), seg=10, loc=(0.4, 0, 3.4)).parent = root
    sail = prism_xz([(-0.1, 1.0), (-2.2, 1.3), (1.2, 4.2)], 0.04, mat("#fff4d6", 0.7, sss=0.1, coat=0), "sail", 0.0)
    sail.parent = root
    sail.location = (0.0, 0.0, 0.0)
    for k in range(3):
        box((0.04, 0.05, 0.9), (-0.05 + k * 0.5, 0, 0.0), mat("#c9704a", 0.7), bevel=0.0)
    cyl(2.9, 0.08, (0, 0, 0.55), watermat("#2f8fe0", 0.9), seg=48, scale=(1, 0.55, 1)).parent = root
    root.rotation_euler = (0, 0, R(18))
    kit.camera((0, -10.5, 2.6), (0, 0, 2.0), lens=46)
    ctx.still()


@asset("beach_scene", size=(520, 400), samples=32, group=G)
def beach_scene(ctx):
    kit.studio(scale=1.8, key=500, amb=0.9)
    sphere(3.2, (0, 1.0, -1.5), mat("#e8cf9a", 0.9, sss=0.05, coat=0), scale=(1.3, 1, 0.45), seg=48, rings=24)
    box((9, 3.0, 0.3), (0, -2.2, 0.0), watermat("#2f8fe0"), bevel=0.1)
    for x in (-1.8, 1.6):
        tree_palm((x, 1.0, 0.1), 1.5, 8 * (1 if x > 0 else -1), 0.9)
    for x, y in ((-0.6, -0.2), (0.5, -0.5), (0.9, 0.2)):
        sphere(0.13, (x, y, 0.1), mat("#ffd2dc", 0.4, coat=0.4), scale=(1, 0.8, 0.6))
    kit.camera((0, -9.0, 3.2), (0, 0.4, 1.2), lens=44)
    ctx.still()
