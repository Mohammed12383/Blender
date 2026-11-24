"""Unit 3 (Islamic civilisation): tabletop-story props. People of early Islam are never drawn:
armies are faceless pawns with banners, scholars are turbans on stands with books, cities are domes and minarets."""
import math
import random

import bpy

from . import kit, props
from .assets_lib import asset
from .kit import V, box, capsule, cone, cyl, empty, ico, mat, sphere, torus, curve, tex_mat, strata_mat, stripes_mat
from .props import glow, rock, arrow, prism_xz, poly_slab, tree_palm, house
from .assets_u1l1 import CONT

R = math.radians
G = "u3"
GOLD = lambda: mat("#e0b43a", 0.25, metal=0.9)


# ═══════════════════ scholars: turbans on stands ═══════════════════
def turban_stand(main, trim, loc=(0, 0, 0), s=1.0, book=True):
    root = empty("turban", loc)
    wood = mat("#6b4527", 0.5, coat=0.35)
    cyl(0.95, 0.5, (0, 0, 0.25), wood, seg=48).parent = root
    torus(0.95, 0.04, (0, 0, 0.5), GOLD()).parent = root
    cyl(0.12, 0.7, (0, 0, 0.85), wood, seg=16).parent = root
    mm, tm = mat(main, 0.85, sss=0.04, coat=0), mat(trim, 0.7, sss=0.04, coat=0)
    for k in range(4):
        torus(0.62 - k * 0.02, 0.2, (0, 0, 1.45 + k * 0.1), mm if k % 2 == 0 else tm, scale=(1, 1.04, 0.75)).parent = root
    sphere(0.55, (0, 0, 1.85), mm, scale=(1, 1, 0.6), seg=40, rings=20).parent = root
    sphere(0.14, (0, -0.64, 1.6), mat("#e0b43a", 0.2, metal=0.9), seg=16, rings=8).parent = root
    tail = curve([(0.55, 0.0, 1.45), (0.78, 0.0, 1.0), (0.82, 0.0, 0.62)], 0.12, tm)
    tail.parent = root
    if book:
        bk = mat("#1f6f50", 0.5, coat=0.3)
        for sx in (-1, 1):
            b = box((0.5, 0.08, 0.7), (sx * 0.27, -1.2, 0.72), mat("#fffdf5", 0.7, sss=0), rot=(R(-35), 0, R(sx * 12)), bevel=0.01)
            b.parent = root
            for k in range(4):
                box((0.36, 0.01, 0.015), (sx * 0.27, -1.24, 0.72 + (k - 1.5) * 0.12), mat("#3a3030", 0.5, sss=0), rot=(R(-35), 0, R(sx * 12)), bevel=0).parent = root
        box((1.2, 0.12, 0.78), (0, -1.14, 0.64), bk, rot=(R(-35), 0, 0), bevel=0.03).parent = root
    root.scale = (s, s, s)
    return root


TURBANS = {"green": ("#1f8f5f", "#f4c542"), "blue": ("#2a5fbf", "#ffffff"), "gold": ("#d9a21b", "#7a1f35"), "red": ("#b3262e", "#f4e3c0"),
           "purple": ("#6a2a9c", "#f4c542"), "teal": ("#1a8a8a", "#f4e3c0"), "orange": ("#e8761e", "#ffffff"), "white": ("#f4efe2", "#2a5fbf")}
for nm, (a, b) in TURBANS.items():
    def _mk(a=a, b=b):
        def f(ctx):
            kit.studio(scale=1.5)
            turban_stand(a, b)
            kit.camera((0, -9.0, 2.6), (0, 0, 1.5), lens=46)
            ctx.still()
        return f
    asset(f"turban_{nm}", size=(420, 460), samples=34, group=G)(_mk())


@asset("turban_row", size=(760, 300), samples=34, group=G)
def turban_row(ctx):
    kit.studio(scale=2.0)
    for i, (nm, (a, b)) in enumerate(list(TURBANS.items())[:7]):
        turban_stand(a, b, (-5.4 + i * 1.8, 0, 0), 0.8, book=False)
    kit.camera((0, -12.5, 3.2), (0, 0, 1.3), lens=44)
    ctx.still()


# ═══════════════════ armies as pawns + banners ═══════════════════
def pawn(loc, color, spear=True):
    root = empty("pawn", loc)
    cone(0.26, 0.1, 0.62, (0, 0, 0.31), mat(color, 0.55, sss=0.05, coat=0.2), seg=24).parent = root
    sphere(0.16, (0, 0, 0.72), mat("#f4e9d2", 0.5, sss=0.1, coat=0.1), seg=20, rings=10).parent = root
    cone(0.2, 0.0, 0.18, (0, 0, 0.88), mat("#8a93a0", 0.3, metal=0.8), seg=20).parent = root
    if spear:
        cyl(0.025, 1.4, (0.22, 0, 0.8), mat("#6b4a2d", 0.6), seg=8).parent = root
        cone(0.05, 0.0, 0.16, (0.22, 0, 1.58), mat("#c9ced6", 0.2, metal=0.9), seg=8).parent = root
    return root


def army(color, flag, loc=(0, 0, 0), s=1.0):
    root = empty("army", loc)
    cyl(1.7, 0.2, (0, 0, 0.1), mat("#6b4527", 0.55, coat=0.3), seg=48).parent = root
    for r in range(3):
        for c in range(5):
            pawn((-1.0 + c * 0.5, -0.6 + r * 0.55, 0.2), color).parent = root
    cyl(0.04, 2.6, (0, 0.9, 1.5), mat("#6b4a2d", 0.5), seg=10).parent = root
    box((1.2, 0.04, 0.8), (0.62, 0.9, 2.5), mat(flag, 0.6, sss=0.05, coat=0), bevel=0.01).parent = root
    box((1.2, 0.045, 0.14), (0.62, 0.9, 2.5), mat("#f4c542", 0.4, metal=0.5), bevel=0.0).parent = root
    root.scale = (s, s, s)
    return root


for nm, (c, f) in {"green": ("#1f8f5f", "#1f8f5f"), "blue": ("#2a5fbf", "#2a5fbf"), "red": ("#b3262e", "#b3262e")}.items():
    def _mk(c=c, f=f):
        def fn(ctx):
            kit.studio(scale=1.6)
            army(c, f)
            kit.camera((0, -10.5, 3.6), (0, 0.3, 1.2), lens=44)
            ctx.still()
        return fn
    asset(f"army_{nm}", size=(460, 400), samples=32, group=G)(_mk())


@asset("mushaf_spear", size=(420, 560), samples=34, group=G)
def mushaf_spear(ctx):
    kit.studio(scale=1.8)
    wood = mat("#6b4a2d", 0.5, coat=0.2)
    for x, h, tilt in ((-1.1, 4.0, -6), (0.0, 4.8, 0), (1.1, 3.8, 6)):
        sp = empty("spear", (x, 0, 0))
        cyl(0.05, h, (0, 0, h / 2), wood, seg=10).parent = sp
        cone(0.1, 0.0, 0.3, (0, 0, h + 0.15), mat("#c9ced6", 0.2, metal=0.9), seg=12).parent = sp
        bk = empty("book", (0, 0, h + 0.1), sp)
        box((0.8, 0.14, 1.0), (0, 0, 0.5), mat("#1f6f50", 0.45, coat=0.4), bevel=0.04).parent = bk
        box((0.6, 0.16, 0.8), (0, 0, 0.5), mat("#e0b43a", 0.3, metal=0.9), bevel=0.02).parent = bk
        box((0.5, 0.17, 0.7), (0, 0, 0.5), mat("#1f6f50", 0.45, coat=0.4), bevel=0.02).parent = bk
        torus(0.14, 0.03, (0, -0.1, 0.5), GOLD(), rot=(R(90), 0, 0)).parent = bk
        sp.rotation_euler = (0, R(tilt), 0)
    cyl(1.7, 0.15, (0, 0, 0.05), mat("#c9a572", 0.9, sss=0.03, coat=0), seg=48)
    kit.camera((0, -12.5, 3.0), (0, 0, 2.7), lens=46)
    ctx.still()


@asset("scroll_two", size=(420, 420), samples=32, group=G)
def scroll_two(ctx):
    kit.studio(scale=1.4)
    pap = mat("#f6e7c1", 0.7, sss=0.02, coat=0)
    for k, (z, rot) in enumerate(((0.45, 8), (1.15, -6))):
        sc = empty("scroll", (0, 0, z))
        cyl(0.26, 2.0, (0, 0, 0), pap, rot=(0, R(90), 0), seg=32).parent = sc
        for sx in (-1, 1):
            cyl(0.12, 0.28, (sx * 1.1, 0, 0), mat("#8b5a2b", 0.4, coat=0.3), rot=(0, R(90), 0), seg=20).parent = sc
            sphere(0.14, (sx * 1.28, 0, 0), mat("#8b5a2b", 0.4, coat=0.3), seg=16, rings=8).parent = sc
        sphere(0.18, (0.2, -0.26, 0.0), mat("#b3262e", 0.4, coat=0.4), scale=(1, 0.5, 1)).parent = sc
        for i in range(5):
            box((1.3 - i * 0.1, 0.01, 0.03), (-0.2, -0.27, 0.12 - i * 0.07), mat("#3a3030", 0.5, sss=0), bevel=0).parent = sc
        sc.rotation_euler = (0, 0, R(rot))
    kit.camera((0, -7.2, 1.9), (0, 0, 0.8), lens=50)
    ctx.still()


@asset("throne_chair", size=(420, 520), samples=34, group=G)
def throne_chair(ctx):
    kit.studio(scale=1.5)
    wood = mat("#6b4527", 0.45, coat=0.4)
    box((1.6, 1.4, 0.3), (0, 0, 0.95), wood, bevel=0.05)
    box((1.4, 1.2, 0.2), (0, 0, 1.15), mat("#a3242e", 0.7, sss=0.05, coat=0), bevel=0.08)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.1, 0.95, (sx * 0.7, sy * 0.6, 0.47), wood, seg=12)
        box((0.14, 1.2, 0.6), (sx * 0.78, 0, 1.45), wood, bevel=0.04)
    box((1.6, 0.18, 2.2), (0, 0.62, 2.1), wood, bevel=0.06)
    cyl(0.8, 0.18, (0, 0.62, 3.2), wood, rot=(R(90), 0, 0), seg=40)
    torus(0.55, 0.04, (0, 0.5, 2.3), GOLD(), rot=(R(90), 0, 0))
    sphere(0.12, (0, 0.5, 2.3), GOLD())
    kit.camera((2.0, -8.5, 2.9), (0, 0, 1.8), lens=46)
    ctx.still()


@asset("ship_icon", size=(520, 440), samples=32, group=G)
def ship_icon(ctx):
    kit.studio(scale=1.7)
    wood = mat("#8a5a34", 0.55, sss=0.1, coat=0.2)
    sphere(2.3, (0, 0, 0.8), wood, scale=(1.0, 0.4, 0.26), seg=64, rings=32)
    box((3.6, 0.7, 0.08), (0, 0, 1.0), mat("#c9a572", 0.7), bevel=0.02)
    cyl(0.07, 3.4, (0, 0, 2.6), mat("#4a2f1b", 0.6), seg=10)
    box((1.9, 0.05, 1.7), (0, -0.05, 3.0), mat("#f4efe2", 0.7, sss=0.08, coat=0), bevel=0.01)
    box((1.9, 0.055, 0.25), (0, -0.05, 3.0), mat("#2a5fbf", 0.6), bevel=0.0)
    for k in range(6):
        for sy in (-1, 1):
            cyl(0.025, 1.8, (-1.5 + k * 0.6, sy * 0.95, 0.7), mat("#4a2f1b", 0.6), rot=(R(sy * 70), 0, 0), seg=8)
    cyl(2.9, 0.08, (0, 0, 0.35), mat("#2f8fe0", 0.15, coat=0.8, sss=0.2), seg=48, scale=(1, 0.5, 1))
    kit.camera((0, -10.5, 2.8), (0, 0, 1.8), lens=46)
    ctx.still()


# ═══════════════════ cities ═══════════════════
STONE = lambda: mat("#f0e4c8", 0.75, sss=0.08, coat=0)


def dome(loc, r, color, parent=None, h=1.0):
    o = sphere(r, loc, mat(color, 0.35, sss=0.1, coat=0.35), scale=(1, 1, h), seg=40, rings=20)
    if parent:
        o.parent = parent
    return o


def minaret(loc, h, parent, body="#f0e4c8", cap="#1f8f5f", r=0.2):
    cyl(r, h, (loc[0], loc[1], h / 2), mat(body, 0.7, sss=0.08, coat=0), seg=20).parent = parent
    cyl(r * 1.6, 0.12, (loc[0], loc[1], h * 0.82), mat(body, 0.7), seg=20).parent = parent
    cyl(r * 1.2, 0.35, (loc[0], loc[1], h + 0.15), mat(body, 0.7), seg=20).parent = parent
    cone(r * 1.35, 0.0, 0.7, (loc[0], loc[1], h + 0.6), mat(cap, 0.4, coat=0.3), seg=20).parent = parent
    sphere(0.06, (loc[0], loc[1], h + 1.0), GOLD()).parent = parent


def courtyard(root, w=7, d=5):
    box((w + 1.0, d + 1.0, 0.25), (0, 0, 0.12), mat("#d9c8a0", 0.8, sss=0.03, coat=0), bevel=0.05).parent = root


def city_scene(name, build, size=(480, 440), cam=((0, -13, 5.0), (0, 0, 1.8))):
    def f(ctx):
        kit.studio(scale=2.4, key=800, amb=0.9)
        build()
        kit.camera(cam[0], cam[1], lens=44)
        ctx.still()
    asset(name, size=size, samples=32, group=G)(f)


def _madinah():
    root = empty("madinah", (0, 0, 0))
    courtyard(root)
    box((4.6, 2.6, 1.4), (0, 0.2, 0.95), STONE(), bevel=0.06).parent = root
    dome((0, 0.2, 1.65), 1.0, "#1f8f5f", root, 1.0)
    dome((-1.5, 0.2, 1.62), 0.55, "#6fbf8f", root, 0.9)
    dome((1.5, 0.2, 1.62), 0.55, "#6fbf8f", root, 0.9)
    for sx in (-1, 1):
        for sy in (-1, 1):
            minaret((sx * 3.1, sy * 2.0, 0), 3.4, root, cap="#1f8f5f")
    for x in (-2.6, 0.0, 2.6):
        tree_palm((x, -2.6, 0.2), 1.0, 5, 0.6)


def _damascus():
    root = empty("dimashq", (0, 0, 0))
    courtyard(root)
    box((5.0, 2.4, 1.5), (0, 0.4, 1.0), mat("#e6d4a8", 0.75, sss=0.08, coat=0), bevel=0.06).parent = root
    dome((0, 0.4, 1.8), 1.15, "#8a9bb0", root, 0.95)
    for x in (-2.2, 0, 2.2):
        for z in (0.0,):
            box((1.5, 0.1, 0.9), (x, -0.85, 0.75), mat("#8a6a4a", 0.7), bevel=0.02).parent = root
    minaret((-2.8, -1.8, 0), 3.8, root, body="#e6d4a8", cap="#8a9bb0")
    minaret((2.8, -1.8, 0), 3.2, root, body="#e6d4a8", cap="#8a9bb0")
    minaret((2.8, 2.2, 0), 3.6, root, body="#e6d4a8", cap="#8a9bb0")
    for x in (-3.4, 3.6):
        tree_palm((x, -3.0, 0.2), 0.9, 5, 0.6)


def _kufa():
    root = empty("kufa", (0, 0, 0))
    mud = mat("#c9a572", 0.9, sss=0.05, coat=0)
    box((7.2, 5.2, 0.3), (0, 0, 0.15), mat("#b9955f", 0.9), bevel=0.05).parent = root
    for (w, d, x, y) in ((7.0, 0.4, 0, 2.5), (7.0, 0.4, 0, -2.5), (0.4, 5.0, 3.5, 0), (0.4, 5.0, -3.5, 0)):
        box((w, d, 1.2), (x, y, 0.9), mud, bevel=0.04).parent = root
    for k in range(10):
        box((0.3, 0.45, 0.3), (-3.2 + k * 0.7, -2.5, 1.65), mud, bevel=0.02).parent = root
    box((1.4, 0.5, 1.6), (0, -2.5, 1.0), mat("#4a3b33", 0.8), bevel=0.04).parent = root
    cyl(0.7, 0.5, (0, -2.5, 1.7), mud, rot=(R(90), 0, 0), seg=24).parent = root
    box((2.0, 1.6, 1.0), (-1.0, 0.4, 0.8), mud, bevel=0.05).parent = root
    dome((-1.0, 0.4, 1.3), 0.8, "#c97b4a", root, 0.9)
    minaret((1.6, 0.8, 0), 2.6, root, body="#c9a572", cap="#c97b4a", r=0.22)
    for x, y in ((2.4, -1.2), (-2.6, -1.4), (2.6, 1.6)):
        tree_palm((x, y, 0.3), 1.0, 6, 0.6)


def _baghdad():
    root = empty("baghdad", (0, 0, 0))
    for r, h, c in ((4.0, 0.5, "#c9a572"), (3.4, 0.75, "#d9b77a"), (2.8, 1.0, "#e6c98a"), (1.4, 1.4, "#f0e4c8")):
        cyl(r, h, (0, 0, h / 2), mat(c, 0.8, sss=0.05, coat=0), seg=64).parent = root
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        box((0.9, 0.7, 1.3), (math.cos(ang) * 3.9, math.sin(ang) * 3.9, 0.9), mat("#8a6a4a", 0.7), rot=(0, 0, ang), bevel=0.04).parent = root
    dome((0, 0, 1.8), 1.2, "#1f8f5f", root, 1.0)
    cyl(0.2, 1.8, (0, 0, 1.1), mat("#f0e4c8", 0.7), seg=16).parent = root
    cone(0.3, 0.0, 0.9, (0, 0, 3.3), mat("#e0b43a", 0.3, metal=0.9), seg=16).parent = root
    for a in range(8):
        tree_palm((math.cos(a * 0.785) * 4.7, math.sin(a * 0.785) * 4.7, 0.0), 0.8, 5, 0.5)


def _oman_fort():
    root = empty("fort", (0, 0, 0))
    stone = mat("#d9b77a", 0.85, sss=0.05, coat=0)
    box((8, 5, 0.3), (0, 0, 0.15), mat("#c9a572", 0.9), bevel=0.05).parent = root
    cyl(1.9, 3.8, (-0.4, 0.4, 2.1), stone, seg=48).parent = root
    cyl(2.05, 0.35, (-0.4, 0.4, 4.1), stone, seg=48).parent = root
    for k in range(14):
        a = k / 14 * math.tau
        box((0.4, 0.4, 0.45), (-0.4 + math.cos(a) * 2.0, 0.4 + math.sin(a) * 2.0, 4.5), stone, bevel=0.03).parent = root
    cyl(0.9, 2.4, (2.8, -1.2, 1.5), stone, seg=32).parent = root
    for k in range(8):
        a = k / 8 * math.tau
        box((0.28, 0.28, 0.32), (2.8 + math.cos(a) * 0.95, -1.2 + math.sin(a) * 0.95, 2.85), stone, bevel=0.02).parent = root
    box((6.5, 0.5, 1.1), (0, -2.2, 0.7), stone, bevel=0.04).parent = root
    for x in (-3.0, 3.4):
        tree_palm((x, -1.2, 0.2), 1.3, 6, 0.8)


def _cairo():
    root = empty("cairo", (0, 0, 0))
    courtyard(root)
    box((4.0, 2.6, 1.6), (0, 0.2, 1.0), mat("#e0c590", 0.75, sss=0.08, coat=0), bevel=0.06).parent = root
    dome((0, 0.2, 1.8), 1.2, "#b0b8c4", root, 1.1)
    minaret((-2.6, -1.6, 0), 4.4, root, body="#e0c590", cap="#b0b8c4")
    minaret((2.6, -1.6, 0), 4.0, root, body="#e0c590", cap="#b0b8c4")
    for x in (-3.4, 3.4):
        tree_palm((x, 1.4, 0.2), 1.0, 5, 0.6)


def _town(seed):
    root = empty("town", (0, 0, 0))
    rnd = random.Random(seed)
    box((7.0, 5.0, 0.3), (0, 0, 0.15), mat("#d9c8a0", 0.85), bevel=0.05).parent = root
    for k in range(7):
        w, d, h = rnd.uniform(0.9, 1.4), rnd.uniform(0.9, 1.3), rnd.uniform(0.7, 1.3)
        box((w, d, h), (rnd.uniform(-2.8, 2.8), rnd.uniform(-1.6, 1.8), 0.3 + h / 2), mat(rnd.choice(["#e6d4a8", "#f0e4c8", "#d9b77a"]), 0.85, sss=0.05, coat=0), bevel=0.04).parent = root
    box((1.5, 1.4, 1.2), (0, 0, 0.9), STONE(), bevel=0.05).parent = root
    dome((0, 0, 1.55), 0.7, "#1f8f5f", root, 0.9)
    minaret((1.0, 0.0, 0), 2.4, root, cap="#1f8f5f", r=0.17)
    tree_palm((-2.9, -1.5, 0.3), 1.0, 6, 0.7)
    tree_palm((2.9, -1.2, 0.3), 1.1, 5, 0.7)


def _rome():
    root = empty("rome", (0, 0, 0))
    st = mat("#d9c8a8", 0.8, sss=0.05, coat=0)
    for k, (r, z) in enumerate(((3.2, 0.0), (3.0, 1.2), (2.8, 2.4))):
        cyl(r, 1.2, (0, 0, z + 0.6), st, seg=64).parent = root
        for a in range(28):
            ang = a / 28 * math.tau
            box((0.32, 0.12, 0.7), (math.cos(ang) * (r + 0.02), math.sin(ang) * (r + 0.02), z + 0.55), mat("#4a3b33", 0.8), rot=(0, 0, ang + math.pi / 2), bevel=0).parent = root
    cyl(2.5, 0.2, (0, 0, 3.65), st, seg=64).parent = root
    cyl(2.3, 0.05, (0, 0, 3.72), mat("#b9955f", 0.9), seg=64).parent = root
    for x in (-4.2, 4.2):
        tree_palm((x, -1.0, 0.0), 1.1, 5, 0.7)


city_scene("city_madinah", _madinah)
city_scene("city_damascus", _damascus)
city_scene("city_kufa", _kufa)
city_scene("city_baghdad", _baghdad, cam=((0, -13.5, 7.0), (0, 0, 1.2)))
city_scene("city_oman_fort", _oman_fort)
city_scene("city_cairo", _cairo)
city_scene("city_town_a", lambda: _town(3))
city_scene("city_town_b", lambda: _town(8))
city_scene("city_rome", _rome, cam=((0, -13.5, 5.5), (0, 0, 1.8)))


# ═══════════════════ books & library ═══════════════════
@asset("book_open_icon", size=(480, 400), samples=32, group=G)
def book_open_icon(ctx):
    kit.studio(scale=1.5)
    cover = mat("#1f6f50", 0.45, coat=0.4)
    box((3.4, 2.4, 0.18), (0, 0, 0.09), cover, bevel=0.06)
    for sx in (-1, 1):
        pg = box((1.5, 2.1, 0.25), (sx * 0.76, 0, 0.3), mat("#fffdf5", 0.7, sss=0.05, coat=0), rot=(0, R(sx * -6), 0), bevel=0.03)
        for k in range(7):
            box((1.1, 0.02, 0.03), (sx * 0.78, -0.8 + k * 0.26, 0.44), mat("#3a3030", 0.5, sss=0), rot=(0, R(sx * -6), 0), bevel=0)
    sphere(0.5, (0, 0.0, 1.6), glow("#ffe9a0", 3, 0.5), seg=24, rings=12)
    for k in range(6):
        a = k * 1.047
        cone(0.07, 0.0, 0.5, (math.cos(a) * 0.8, 0.0, 1.6 + math.sin(a) * 0.8), glow("#ffe9a0", 5), rot=(0, R(90) - a, 0), seg=8)
    kit.camera((0, -6.8, 3.6), (0, 0, 0.7), lens=48)
    ctx.still()


@asset("library_stack", size=(460, 520), samples=32, group=G)
def library_stack(ctx):
    kit.studio(scale=1.5)
    rnd = random.Random(5)
    cols = ["#1f6f50", "#a3242e", "#2a5fbf", "#d9a21b", "#6a2a9c", "#1a8a8a"]
    z = 0.0
    for k in range(6):
        w, d, h = rnd.uniform(2.2, 2.8), rnd.uniform(1.6, 2.0), rnd.uniform(0.28, 0.4)
        o = box((w, d, h), (rnd.uniform(-0.1, 0.1), 0, z + h / 2), mat(cols[k], 0.5, coat=0.3), bevel=0.04)
        o.rotation_euler = (0, 0, R(rnd.uniform(-8, 8)))
        box((w - 0.1, d - 0.08, h - 0.08), (o.location.x, -0.06, z + h / 2), mat("#fffdf5", 0.7, sss=0, coat=0), bevel=0.01).rotation_euler = (0, 0, R(0))
        z += h
    box((2.4, 1.7, 0.3), (0, 0, z + 0.15), mat("#1f6f50", 0.45, coat=0.4), bevel=0.04)
    torus(0.4, 0.03, (0, -0.86, z + 0.15), GOLD(), rot=(R(90), 0, 0))
    sphere(0.38, (0, 0, z + 1.6), glow("#ffe9a0", 3, 0.45), seg=24, rings=12)
    kit.camera((0, -8.5, 3.4), (0, 0, 1.6), lens=46)
    ctx.still()


@asset("lantern_icon", size=(380, 520), samples=34, group=G)
def lantern_icon(ctx):
    kit.studio(scale=1.4, amb=0.5)
    brass = mat("#c99a2a", 0.3, metal=0.9)
    cyl(0.1, 0.9, (0, 0, 3.9), brass, seg=12)
    cone(0.9, 0.12, 0.7, (0, 0, 3.15), brass, seg=24)
    cyl(0.78, 1.7, (0, 0, 1.9), glow("#ffc65a", 2.2, 0.85), seg=24)
    for a in range(8):
        ang = a / 8 * math.tau
        cyl(0.04, 1.8, (math.cos(ang) * 0.8, math.sin(ang) * 0.8, 1.9), brass, seg=8)
    for z in (1.5, 2.3):
        for a in range(6):
            ang = a / 6 * math.tau + 0.2
            sphere(0.1, (math.cos(ang) * 0.79, math.sin(ang) * 0.79, z), glow("#fff2b8", 6), scale=(1, 1, 1.4))
    cyl(0.9, 0.2, (0, 0, 0.95), brass, seg=24)
    cone(0.7, 0.05, 0.6, (0, 0, 0.55), brass, rot=(R(180), 0, 0), seg=24)
    sphere(0.12, (0, 0, 0.15), brass)
    kit.camera((0, -9.0, 2.2), (0, 0, 2.0), lens=48)
    ctx.still()


# ═══════════════════ the story rooms ═══════════════════
def arch_niche(x, w=1.8, h=3.0, z0=0.0, y=3.9, color="#9a6a42"):
    box((w, 0.2, h), (x, y, z0 + h / 2), mat(color, 0.8, sss=0.05, coat=0), bevel=0.03)
    cyl(w / 2, 0.2, (x, y, z0 + h), mat(color, 0.8, sss=0.05, coat=0), rot=(R(90), 0, 0), seg=32)


def room_floor(rug=True):
    box((26, 12, 0.3), (0, -1.5, -0.15), tex_mat("wave", "#7a4a2a", "#9a6a3c", scale=2.2, mid=0.5, contrast=0.35, rough=0.55, sss=0, coat=0.1), bevel=0.0)
    if rug:
        box((9, 5.0, 0.04), (0, -0.4, 0.03), strata_mat(["#a3242e", "#e0b43a", "#1f6f50", "#f4e3c0"], 0.35, "X", "Object", 0.9), bevel=0.0)
        box((8.6, 4.6, 0.045), (0, -0.4, 0.04), mat("#7a1f35", 0.9, sss=0.05, coat=0), bevel=0.0)
        box((7.6, 3.6, 0.05), (0, -0.4, 0.05), strata_mat(["#c9704a", "#f4e3c0", "#2a5fbf"], 0.5, "Y", "Object", 0.9), bevel=0.0)


@asset("majlis_bg", size=(1280, 720), bg=True, samples=34, group=G)
def majlis_bg(ctx):
    kit.studio(scale=3.2, key=1400, fill=450, rim=250, amb=0.5, top="#ffe9c9", bottom="#d8b48a")
    box((26, 0.4, 10), (0, 4.2, 4.6), mat("#d9b77a", 0.85, sss=0.05, coat=0), bevel=0.0)
    for x in (-8.0, -4.4, 4.4, 8.0):
        arch_niche(x, 2.0, 3.0, 1.0, 4.0, "#9a6a42")
    box((4.6, 0.25, 4.6), (0, 3.95, 3.2), glow("#ffe9b0", 2.6), bevel=0.0)                      # glowing window arch
    cyl(2.3, 0.25, (0, 3.95, 5.5), glow("#ffe9b0", 2.6), rot=(R(90), 0, 0), seg=40)
    room_floor()
    # cushions along the wall
    for x in (-9.5, -7.0, -4.5, 4.5, 7.0, 9.5):
        box((2.2, 1.0, 0.5), (x, 3.0, 0.3), mat("#a3242e" if int(abs(x)) % 2 else "#1f6f50", 0.8, sss=0.05, coat=0), bevel=0.2)
        box((2.0, 0.4, 1.0), (x, 3.55, 0.8), mat("#e0b43a" if int(abs(x)) % 2 else "#f4e3c0", 0.8, sss=0.05, coat=0), bevel=0.2)
    # lanterns hanging
    for x in (-3.0, 3.0):
        cyl(0.02, 2.0, (x, 1.0, 8.4), mat("#555", 0.5), seg=6)
        cyl(0.3, 0.6, (x, 1.0, 7.1), glow("#ffc65a", 2.5, 0.9), seg=16)
        cone(0.36, 0.05, 0.3, (x, 1.0, 7.5), mat("#c99a2a", 0.3, metal=0.9), seg=16)
    kit.camera((0, -13.5, 3.6), (0, 0, 3.6), lens=34)
    ctx.still()


@asset("library_bg", size=(1280, 720), bg=True, samples=34, group=G)
def library_bg(ctx):
    kit.studio(scale=3.2, key=1300, fill=450, rim=250, amb=0.5, top="#ffe9c9", bottom="#d8b48a")
    box((26, 0.4, 10), (0, 4.2, 4.6), mat("#c9a572", 0.85, sss=0.05, coat=0), bevel=0.0)
    rnd = random.Random(2)
    cols = ["#1f6f50", "#a3242e", "#2a5fbf", "#d9a21b", "#6a2a9c", "#1a8a8a", "#f4e3c0"]
    for bx in (-9.0, -5.2, 5.2, 9.0):
        box((3.0, 0.9, 7.4), (bx, 3.5, 3.7), mat("#5a3a22", 0.55, coat=0.2), bevel=0.04)
        for row in range(5):
            x = bx - 1.3
            while x < bx + 1.3:
                w = rnd.uniform(0.14, 0.26)
                hh = rnd.uniform(0.9, 1.2)
                box((w, 0.55, hh), (x + w / 2, 3.2, 0.7 + row * 1.4 + hh / 2 - 0.25), mat(rnd.choice(cols), 0.55, coat=0.2), bevel=0.015)
                x += w + 0.02
    for x in (-2.2, 2.2):
        cyl(0.28, 8.0, (x, 3.2, 4.0), mat("#e6d4a8", 0.7), seg=24)
    cyl(2.4, 0.3, (0, 3.9, 7.9), mat("#e6d4a8", 0.7), rot=(R(90), 0, 0), seg=40)
    box((4.2, 0.2, 5.0), (0, 4.05, 3.0), glow("#ffe9b0", 2.2), bevel=0.0)
    room_floor()
    box((2.4, 1.2, 0.9), (0, 1.6, 0.45), mat("#6b4527", 0.5, coat=0.3), bevel=0.05)
    for x in (-3.0, 3.0):
        cyl(0.02, 2.0, (x, 1.0, 8.6), mat("#555", 0.5), seg=6)
        cyl(0.3, 0.6, (x, 1.0, 7.3), glow("#ffc65a", 2.5, 0.9), seg=16)
    kit.camera((0, -13.5, 3.8), (0, 0, 3.6), lens=34)
    ctx.still()


@asset("majlis_table", size=(520, 400), samples=32, group=G)
def majlis_table(ctx):
    kit.studio(scale=1.8, key=500, amb=0.9)
    cyl(3.2, 0.3, (0, 0, 0.8), mat("#6b4527", 0.45, coat=0.4), seg=64)
    for a in range(4):
        cyl(0.2, 0.8, (math.cos(a * 1.57) * 2.4, math.sin(a * 1.57) * 2.4, 0.4), mat("#4a2f1b", 0.5), seg=12)
    box((5.2, 3.8, 0.05), (0, 0, 0.97), mat("#f1e4c0", 0.8, sss=0.03, coat=0), bevel=0.0)
    for n, col in (("arabia", "#4cc9a0"), ("africa", "#e0c590"), ("eurasia", "#c9b27a")):
        pts = CONT["africa" if n == "africa" else "eurasia"][0]
    po, c = poly_slab(CONT["eurasia"][0], 0.055, 0.08, mat("#d9c59a", 0.85, sss=0.03, coat=0), 0.0, "eur")
    po.location = (-1.0, 0.5, 1.05)
    po.scale = (1, 1, 1)
    po2, c2 = poly_slab([(35, 30), (44, 31), (48, 29), (52, 24), (56, 25), (59, 22), (55, 17), (48, 14), (43, 13), (42, 19), (43, 24), (40, 28), (36, 29)], 0.055, 0.1, mat("#4cc9a0", 0.6, sss=0.08, coat=0.1), 0.0, "arabia")
    po2.location = (0.0, -0.2, 1.1)
    for x, y, col in ((-0.8, -0.8, "#1f8f5f"), (0.8, -0.4, "#2a5fbf"), (0.2, 0.7, "#b3262e")):
        p = pawn((x, y, 1.0), col, spear=False)
        p.scale = (0.7, 0.7, 0.7)
    kit.camera((0, -9.0, 6.5), (0, 0, 0.9), lens=44)
    ctx.still()


# ═══════════════════ the conquests map (loop) ═══════════════════
@asset("conquest_map", size=(640, 420), loop=(48, 12), samples=10, group=G)
def conquest_map(ctx):
    kit.studio(scale=2.2, key=600, amb=0.9)
    S = 0.1
    box((11.5, 7.0, 0.4), (3.0, 3.0, -0.2), mat("#2370d6", 0.55, sss=0.1, coat=0.05), bevel=0.2)
    for key, col in (("africa", "#e8d4a0"), ("eurasia", "#d9c59a")):
        o, c = poly_slab(CONT[key][0], S, 0.18, mat(col, 0.8, sss=0.05, coat=0), 0.02, key)
    regions = [
        ("hijaz", [(36, 29), (40, 28), (43, 24), (42, 19), (39, 20), (37, 24)], "#1fa387", 0),
        ("arabia", [(35, 30), (44, 31), (48, 29), (52, 24), (56, 25), (59, 22), (55, 17), (48, 14), (43, 13), (42, 19), (43, 24), (40, 28), (36, 29)], "#4cc9a0", 7),
        ("levant", [(35, 36), (42, 37), (46, 36), (48, 31), (44, 31), (35, 30), (34, 34)], "#f4c542", 15),
        ("persia", [(44, 39), (54, 38), (61, 36), (63, 28), (60, 25), (57, 26), (52, 28), (48, 30), (48, 33), (46, 36)], "#ff9a3c", 24),
        ("egypt", [(25, 31), (34, 31), (35, 29), (34, 22), (25, 22)], "#ef6a5b", 32),
        ("maghrib", [(-8, 35), (10, 37), (25, 31), (25, 22), (-8, 25)], "#d9534a", 38),
    ]
    objs = []
    for nm, pts, col, start in regions:
        o, c = poly_slab(pts, S, 0.12, mat(col, 0.5, sss=0.1, coat=0.1), 0.01, nm)
        o.location.z = 0.26
        objs.append((o, start))
    kit.camera((2.6, -3.0, 11.5), (2.8, 3.0, 0.0), lens=34)

    def upd(i, t):
        f = i
        for o, st in objs:
            p = max(0.0, min(1.0, (f - st) / 5.0))
            e = p * p * (3 - 2 * p)
            if f >= 46:
                e *= max(0.0, 1 - (f - 46) / 2.0)
            o.scale = (max(0.001, e), max(0.001, e), max(0.001, e))
    ctx.loop(upd)
