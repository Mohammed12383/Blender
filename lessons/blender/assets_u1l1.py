"""Unit 1 / Lesson 1 (origin of the Earth): solar system, ancient myths, Big Bang, drifting continents, plates, layers."""
import math
import random

import bpy

from . import kit, chars, props
from .assets_lib import asset
from .kit import V, box, capsule, cone, cyl, empty, ico, mat, sphere, torus, curve, tex_mat, stripes_mat
from .props import glow, poly_slab, arrow, rock, cloud, thermometer, flame, tree_palm

R = math.radians
G = "u1l1"


def ease(x):
    return x * x * (3 - 2 * x)


# ═══════════════════════ continents / Pangaea ═══════════════════════
CONT = {
    "africa": ([(-17, 15), (-17, 21), (-13, 27), (-6, 35), (10, 37), (11, 33), (20, 32), (32, 31), (34, 28), (38, 18), (43, 12), (51, 12), (46, 5), (40, -3), (40, -10), (35, -20),
                (33, -26), (27, -34), (19, -35), (15, -27), (12, -17), (13, -6), (9, 3), (8, 4), (-4, 5), (-8, 4), (-13, 8)], "#f2a33a"),
    "samerica": ([(-80, -3), (-77, 8), (-62, 10), (-52, 5), (-35, -5), (-35, -9), (-39, -15), (-41, -22), (-48, -28), (-58, -35), (-65, -41), (-68, -52), (-72, -54), (-74, -45),
                  (-73, -37), (-71, -30), (-70, -18), (-76, -14), (-81, -5)], "#e8584f"),
    "namerica": ([(-168, 66), (-140, 70), (-125, 70), (-95, 72), (-80, 68), (-62, 60), (-55, 50), (-66, 44), (-76, 36), (-81, 25), (-97, 26), (-97, 18), (-88, 15), (-83, 9),
                  (-77, 8), (-86, 13), (-105, 20), (-112, 30), (-123, 38), (-125, 48), (-135, 58), (-150, 60), (-165, 62)], "#4aa3df"),
    "greenland": ([(-55, 60), (-45, 60), (-20, 70), (-20, 82), (-60, 82), (-73, 78), (-55, 68)], "#e9f2ff"),
    "eurasia": ([(-10, 36), (-9, 43), (-4, 48), (3, 51), (8, 55), (10, 58), (5, 62), (15, 69), (30, 71), (60, 69), (80, 73), (105, 77), (140, 72), (170, 70), (180, 66), (160, 60), (142, 53),
                 (140, 46), (130, 42), (125, 38), (122, 30), (120, 22), (108, 18), (106, 10), (100, 13), (98, 8), (103, 1), (98, 16), (92, 22), (90, 27), (80, 31), (71, 29), (62, 25), (57, 25),
                 (56, 27), (48, 30), (50, 26), (56, 24), (59, 22), (52, 16), (43, 13), (35, 28), (34, 31), (36, 36), (27, 37), (26, 40), (23, 37), (19, 41), (13, 45), (18, 40), (16, 38), (9, 44), (3, 43),
                 (-1, 37), (-6, 36)], "#8bc34a"),
    "india": ([(71, 29), (80, 31), (90, 27), (88, 22), (80, 15), (77, 8), (72, 20), (67, 25)], "#ab6bd6"),
    "australia": ([(114, -22), (122, -18), (130, -12), (137, -12), (142, -11), (146, -19), (153, -26), (150, -37), (140, -38), (131, -31), (115, -34), (113, -26)], "#ffb84d"),
    "antarctica": ([(-70, -76), (-35, -69), (5, -67), (45, -69), (85, -75), (65, -85), (5, -88), (-45, -85)], "#f4fbff"),
}
# keyframe offsets (dx, dy, rot_deg) in map degrees about each piece's centroid: Pangaea layout vs today
PAN = {
    "africa": (-2, -2, -8), "samerica": (34, 8, 38), "namerica": (52, -6, -22), "greenland": (44, -2, -22), "eurasia": (-2, 5, 10),
    "india": (-27, -42, -28), "australia": (-44, -30, 25), "antarctica": (34, 24, 10),
}
# progress (0 = Pangaea, 1 = today) at the four stages: 360, 200, 60 million years ago, today
STAGES = {
    "africa": [0, 0.06, 0.9, 1], "samerica": [0, 0.1, 0.75, 1], "namerica": [0, 0.12, 0.7, 1], "greenland": [0, 0.12, 0.75, 1], "eurasia": [0, 0.08, 0.92, 1],
    "india": [0, 0.15, 0.55, 1], "australia": [0, 0.05, 0.45, 1], "antarctica": [0, 0.04, 0.8, 1],
}


def _stage_progress(name, u):
    """u in 0..3 continuous stage index."""
    ks = STAGES[name]
    i = min(int(u), 2)
    f = ease(u - i) if u < 3 else 1
    return ks[i] + (ks[i + 1] - ks[i]) * f


class World:
    def __init__(self, big=True):
        self.S = 0.1
        ocean = mat("#2370d6", 0.55, sss=0.1, coat=0.05)
        o = box((38, 19.5, 0.5), (0, 0, -0.25), ocean, bevel=0.2)
        rim = box((39.2, 20.7, 0.35), (0, 0, -0.45), mat("#0f3f8f", 0.5), bevel=0.2)
        self.parts = {}
        for n, (pts, col) in CONT.items():
            ob, (cx, cy) = poly_slab(pts, self.S, 0.32, mat(col, 0.5, sss=0.15), 0.05, n)
            self.parts[n] = (ob, cx, cy)

    def set(self, u):
        for n, (ob, cx, cy) in self.parts.items():
            p = _stage_progress(n, u)
            dx, dy, rt = PAN[n]
            k = 1 - p
            ob.location = ((cx + dx * k) * self.S, (cy + dy * k) * self.S, 0.17)
            ob.rotation_euler = (0, 0, R(rt * k))


def _world_cam():
    kit.camera((0, -17, 27), (0, -0.2, 0), lens=30)


def _world_scene(ctx, u):
    kit.studio(scale=2.6, key=500, amb=0.7)
    w = World()
    w.set(u)
    _world_cam()
    return w


for key, (u, nm) in {"pangaea_360": (0, "pangaea_360"), "pangaea_200": (1, "pangaea_200"), "pangaea_60": (2, "pangaea_60"), "pangaea_now": (3, "pangaea_now")}.items():
    def _mk(u=u):
        def f(ctx):
            _world_scene(ctx, u)
            ctx.still()
        return f
    asset(key, size=(700, 394), samples=24, group=G)(_mk())


@asset("pangaea_drift", size=(700, 394), loop=(96, 12), samples=10, group=G)
def pangaea_drift(ctx):
    w = _world_scene(ctx, 0)

    def upd(i, t):
        # hold 0.8 s at each stage, drift between them
        hold, move = 6, 22
        seg = hold + move
        pos = i % (seg * 3 + hold)
        s = pos // seg
        r = pos - s * seg
        u = s + (max(0, r - hold) / move if s < 3 else 0)
        w.set(min(u, 3))
    ctx.loop(upd)


# ═══════════════════════ solar system ═══════════════════════
@asset("solar_system", size=(700, 390), loop=(72, 12), samples=12, group=G)
def solar_system(ctx):
    kit.studio(scale=2.0, key=200, fill=120, rim=250, amb=0.35, top="#dbe8ff", bottom="#cdd8ff")
    kit.world("#8a9bd8", "#4a4a9a", 0.5)
    sun = sphere(0.62, (0, 0, 0), glow("#ffb81f", 7), seg=48, rings=24)
    sphere(0.8, (0, 0, 0), glow("#ffd24a", 1.6, 0.25), seg=32, rings=16)
    sphere(1.0, (0, 0, 0), glow("#ff9a1f", 0.8, 0.12), seg=32, rings=16)
    spec = [("mercury", 1.0, 0.1, "#9b9b9b", 4), ("venus", 1.38, 0.16, "#e6b45a", 3), ("earth", 1.78, 0.2, None, 2), ("mars", 2.15, 0.14, "#d8573a", 2),
            ("jupiter", 2.7, 0.4, "#d9a066", 1), ("saturn", 3.3, 0.34, "#e8cf8f", 1), ("uranus", 3.85, 0.25, "#7fe0e0", 1), ("neptune", 4.3, 0.24, "#4a6fe3", 1)]
    pl = []
    for name, orb, rad, col, rev in spec:
        torus(orb, 0.012, (0, 0, 0), glow("#ffffff", 0.9, 0.5), scale=(1, 0.42, 1))
        if name == "earth":
            m = tex_mat("noise", "#2f7bf0", "#52c970", scale=2.0, mid=0.52, contrast=0.025, rough=0.4)
        elif name == "jupiter":
            m = stripes_mat("#e0b07a", "#b9763f", scale=7, axis="Z", rough=0.6)
        else:
            m = mat(col, 0.5, sss=0.1)
        p = sphere(rad, (orb, 0, 0), m, seg=48, rings=24)
        if name == "saturn":
            rg = torus(rad * 1.6, rad * 0.16, (0, 0, 0), mat("#d7c08a", 0.5), scale=(1, 1, 0.12))
            rg.parent = p
            rg.rotation_euler = (R(25), 0, 0)
        if name == "earth":
            torus(0.38, 0.03, (0, 0, 0), glow("#ffe14d", 6)).parent = p
        pl.append((p, orb, rev, rad))
    kit.camera((0, -9.5, 5.2), (0, 0.1, 0), lens=42)

    def upd(i, t):
        for k, (p, orb, rev, rad) in enumerate(pl):
            a = t * math.tau * rev + k * 0.9
            p.location = (math.cos(a) * orb, math.sin(a) * orb * 0.42, 0)
            p.rotation_euler = (0, 0, t * math.tau * 3)
    ctx.loop(upd)


# ═══════════════════════ ancient myths ═══════════════════════
def globe_buddy(loc, r=0.4, expr="oh", brow="worried"):
    root = empty("buddy", loc)
    earth = tex_mat("noise", "#2f7bf0", "#52c970", scale=2.4, mid=0.52, contrast=0.025, rough=0.4)
    g = sphere(r, (0, 0, 0), earth, seg=48, rings=24)
    g.parent = root
    kit.face(root, -r * 0.96, eye_dx=0.2 * r, eye_z=0.06 * r, eye_r=0.12 * r, expr=expr, brow=brow, scale=r * 1.15, mouth_z=-0.16 * r / 1.0 if False else -0.16, blush="#ff8aa1")
    return root


def animal_eye(parent, x, y, z, r=0.07):
    w = sphere(r, (x, y, z), mat("#fff", 0.2, sss=0), scale=(0.9, 0.6, 1.1), seg=20, rings=10)
    p = sphere(r * 0.6, (x, y - r * 0.4, z), mat("#1c1230", 0.3, sss=0), scale=(0.9, 0.6, 1.0), seg=16, rings=8)
    w.parent = parent
    p.parent = parent


@asset("bull_earth", size=(640, 520), samples=40, group=G)
def bull_earth(ctx):
    kit.studio(scale=1.4)
    root = empty("bull", (0, 0, 0))
    br = mat("#a86a3c", 0.55, sss=0.15)
    cream = mat("#f0d9b0", 0.6, sss=0.15, coat=0)
    body = sphere(1.0, (0, 0.2, 1.0), br, scale=(0.75, 1.15, 0.78), seg=48, rings=24)
    body.parent = root
    hump = sphere(0.45, (0, -0.5, 1.45), br, scale=(1, 1, 0.8))
    hump.parent = root
    head = sphere(0.5, (0, -1.15, 1.25), br, scale=(0.95, 0.9, 0.95), seg=48, rings=24)
    head.parent = root
    snout = sphere(0.3, (0, -1.55, 1.1), cream, scale=(1.1, 0.8, 0.8))
    snout.parent = root
    for sx in (-1, 1):
        sphere(0.045, (sx * 0.11, -1.8, 1.1), mat("#5a3320", 0.4, sss=0), seg=12, rings=8).parent = root
        animal_eye(root, sx * 0.22, -1.52, 1.38)
        sphere(0.2, (sx * 0.5, -1.0, 1.35), br, scale=(0.5, 0.9, 1.0)).parent = root
        sphere(0.12, (sx * 0.5, -1.0, 1.35), mat("#e8a79a", 0.5, sss=0), scale=(0.3, 0.6, 0.8)).parent = root
        hn = curve([(sx * 0.38, -1.15, 1.42), (sx * 0.7, -1.15, 1.55), (sx * 0.95, -1.15, 1.95), (sx * 0.88, -1.15, 2.3)], 0.085, mat("#fff4d6", 0.35, coat=0.4))
        hn.parent = root
        sphere(0.085, (sx * 0.88, -1.15, 2.3), mat("#fff4d6", 0.35, coat=0.4), seg=16, rings=8).parent = root
        for lx, ly in ((-0.4, -0.5), (0.4, -0.5), (-0.4, 0.85), (0.4, 0.85)):
            pass
    for lx, ly in ((-0.42, -0.45), (0.42, -0.45), (-0.42, 0.9), (0.42, 0.9)):
        cyl(0.16, 0.9, (lx, ly, 0.5), br, seg=24).parent = root
        sphere(0.17, (lx, ly - 0.02, 0.05), mat("#3a2a20", 0.4), scale=(1, 1.1, 0.6)).parent = root
    tail = curve([(0, 1.3, 1.2), (0.2, 1.55, 1.0), (0.35, 1.5, 0.6), (0.3, 1.5, 0.35)], 0.04, br)
    tail.parent = root
    sphere(0.12, (0.3, 1.5, 0.3), mat("#3a2a20", 0.6), scale=(1, 1, 1.4)).parent = root
    # the Earth balanced on one horn
    ball = globe_buddy((-0.88, -1.15, 2.78), 0.5)
    ball.parent = root
    root.rotation_euler = (0, 0, R(-26))
    kit.camera((0, -9.0, 3.0), (-0.2, -0.3, 1.45), lens=50)
    ctx.still()


@asset("turtle_elephants", size=(720, 600), samples=40, group=G)
def turtle_elephants(ctx):
    kit.studio(scale=1.6)
    root = empty("turtle", (0, 0, 0))
    shell = tex_mat("voronoi", "#2c8a4a", "#7fcf63", scale=3.2, mid=0.35, contrast=0.12, rough=0.45, sss=0.1)
    sphere(1.9, (0, 0, 0.45), shell, scale=(1.05, 1.0, 0.42), seg=64, rings=32).parent = root
    belly = mat("#e6cf8a", 0.55, sss=0.2, coat=0)
    sphere(1.95, (0, 0, 0.1), belly, scale=(1.08, 1.04, 0.22), seg=48, rings=24).parent = root
    skin = mat("#7fb04a", 0.5, sss=0.2)
    head = sphere(0.55, (0, -2.1, 0.55), skin, scale=(1, 1.1, 0.95), seg=48, rings=24)
    head.parent = root
    animal_eye(root, -0.22, -2.55, 0.75, 0.11)
    animal_eye(root, 0.22, -2.55, 0.75, 0.11)
    smile = curve([(-0.2, -2.64, 0.45), (0, -2.67, 0.4), (0.2, -2.64, 0.45)], 0.025, mat("#1c1230", 0.3, sss=0))
    smile.parent = root
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        fl = sphere(0.42, (sx * 1.55, sy * 0.95, 0.3), skin, scale=(1.3, 1.0, 0.55), seg=32, rings=16)
        fl.rotation_euler = (0, 0, R(sx * sy * 25))
        fl.parent = root
    cone(0.2, 0.0, 0.5, (0, 2.1, 0.3), skin, rot=(R(-90), 0, 0)).parent = root
    gray = mat("#9aa6b8", 0.55, sss=0.15)
    for ex, ey, fl in ((-0.8, -0.55, 1), (0.8, -0.55, -1), (-0.8, 0.6, 1), (0.8, 0.6, -1)):
        el = empty("ele", (ex, ey, 0.85), root)
        sphere(0.5, (0, 0, 0.55), gray, scale=(0.75, 1.05, 0.8), seg=32, rings=16).parent = el
        sphere(0.33, (0, -0.6, 0.75), gray, seg=32, rings=16).parent = el
        for lx, ly in ((-0.22, -0.3), (0.22, -0.3), (-0.22, 0.3), (0.22, 0.3)):
            cyl(0.1, 0.45, (lx, ly, 0.2), gray, seg=16).parent = el
        tr = curve([(0, -0.9, 0.7), (0, -1.05, 0.45), (0, -0.95, 0.2), (0, -0.8, 0.12)], 0.06, gray)
        tr.parent = el
        for sx in (-1, 1):
            sphere(0.2, (sx * 0.34, -0.55, 0.78), gray, scale=(0.3, 1, 1.1)).parent = el
            sphere(0.12, (sx * 0.14, -0.88, 0.85), mat("#fff", 0.2, sss=0), scale=(1, 1.2, 0.8)).parent = el
            animal_eye(el, sx * 0.14, -0.9, 0.82, 0.045)
        el.rotation_euler = (0, 0, R(fl * 12))
    ball = globe_buddy((0, 0, 2.55), 0.82, expr="oh")
    ball.parent = root
    root.rotation_euler = (0, 0, R(-18))
    kit.camera((0, -10.5, 4.2), (0, 0, 1.35), lens=50)
    ctx.still()


# ═══════════════════════ Big Bang & star birth ═══════════════════════
@asset("bigbang", size=(560, 560), loop=(48, 12), samples=8, group=G)
def bigbang(ctx):
    kit.world("#10082a", "#10082a", 0.02)
    kit.area_light((0, -6, 3), (0, 0, 0), 60, 3)
    rnd = random.Random(5)
    cols = ["#ffd23f", "#ff8a3d", "#fff2c2", "#ff5d8f", "#6be3ff", "#ffffff"]
    mats = [glow(c, 6) for c in cols]
    parts = []
    for i in range(170):
        d = V((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        o = sphere(rnd.uniform(0.05, 0.16), (0, 0, 0), rnd.choice(mats), seg=10, rings=6)
        parts.append((o, d, rnd.uniform(0.55, 1.0)))
    core = sphere(0.3, (0, 0, 0), glow("#fff3b0", 9), seg=32, rings=16)
    halo = sphere(0.5, (0, 0, 0), glow("#ffb347", 1.5, 0.35), seg=24, rings=12)
    flash = sphere(1.0, (0, 0, 0), glow("#ffffff", 3, 0.55), seg=32, rings=16)
    ring = torus(1.0, 0.018, (0, 0, 0), glow("#fff2c2", 4, 0.45), rot=(R(70), 0, R(15)))
    kit.camera((0, -9.5, 0.4), (0, 0, 0), lens=50)

    def upd(i, t):
        p0 = 0.22
        if t < p0:
            k = t / p0
            r = 0.16 + 0.22 * k
            jit = 0.03 * math.sin(t * 160)
            core.scale = (r + jit,) * 3
            halo.scale = (r * 1.7,) * 3
            flash.scale = (0.001,) * 3
            ring.scale = (0.001,) * 3
            for o, d, s in parts:
                o.location = d * 0.05 * (0.5 + s)
                o.scale = (0.5 + k,) * 3
        else:
            k = (t - p0) / (1 - p0)
            e = 1 - (1 - k) ** 2.2
            fadeout = max(0.0, min(1.0, (1 - k) / 0.15))
            core.scale = (max(0.001, 0.38 * (1 - k * 0.9)),) * 3
            halo.scale = (max(0.001, 0.65 * (1 - k)),) * 3
            fl = max(0.001, 1 - k * 5)
            flash.scale = (3.6 * (1 - fl) ** 0.5 * (fl ** 0.7) + 0.001,) * 3
            ring.scale = (max(0.001, 3.8 * e * max(0.0, 1 - max(0.0, k - 0.35) / 0.4)),) * 3
            for o, d, s in parts:
                o.location = d * (e * 3.3 * s)
                o.scale = (max(0.001, fadeout * (1.0 - 0.4 * k)),) * 3
    ctx.loop(upd)


@asset("star_birth", size=(560, 560), loop=(48, 12), samples=8, group=G)
def star_birth(ctx):
    kit.world("#0c0724", "#0c0724", 0.02)
    kit.area_light((0, -6, 3), (0, 0, 0), 50, 3)
    rnd = random.Random(9)
    cols = ["#7f6bff", "#b26bff", "#ff7bd5", "#6bb8ff", "#c9b8ff"]
    mats = [glow(c, 2.2, 0.55) for c in cols]
    dust = []
    for i in range(130):
        r0 = rnd.uniform(1.0, 3.2)
        a0 = rnd.uniform(0, math.tau)
        z = rnd.gauss(0, 0.18)
        o = sphere(rnd.uniform(0.07, 0.2), (0, 0, 0), rnd.choice(mats), seg=12, rings=6)
        dust.append((o, r0, a0, z, rnd.uniform(0.7, 1.3)))
    star = sphere(0.5, (0, 0, 0), glow("#ffd23f", 8), seg=48, rings=24)
    halo = sphere(0.8, (0, 0, 0), glow("#ffb347", 1.4, 0.3), seg=24, rings=12)
    kit.camera((0, -8.0, 4.8), (0, 0, 0), lens=62)

    def upd(i, t):
        k = t
        for o, r0, a0, z, sp in dust:
            rr = r0 * (1 - 0.72 * ease(k)) + 0.5 * (1 - ease(k)) * 0
            a = a0 + t * math.tau * sp * 1.0 + (1 - rr / 3.3) * 2
            o.location = (math.cos(a) * rr, math.sin(a) * rr * 0.9, z * (1 - 0.6 * k))
            o.scale = (0.7 + 0.5 * k,) * 3
        s = 0.18 + 0.4 * ease(k)
        star.scale = (s / 0.5,) * 3
        halo.scale = (s * 2.0 / 0.8,) * 3
    ctx.loop(upd)


# ═══════════════════════ plates diorama ═══════════════════════
def _block_scene():
    kit.studio(scale=1.7, key=420)
    mant = tex_mat("noise", "#ff5a14", "#ffb02e", scale=0.9, detail=4, mid=0.5, contrast=0.3, rough=0.5, emit=0.55, sss=0, coat=0)
    box((7.4, 3.2, 1.7), (0, 0, -0.85), mant, bevel=0.08)
    kit.camera((0, -10.0, 4.4), (0, 0, -0.1), lens=44)


def _slab(x, w=3.45, depth=3.2, sign=1):
    root = empty("slab", (x, 0, 0))
    box((w, depth, 0.55), (0, 0, 0.275), mat("#8a5a3b", 0.65, sss=0.05, coat=0), bevel=0.06).parent = root
    box((w + 0.04, depth + 0.04, 0.16), (0, 0, 0.62), mat("#5bc25b", 0.6, sss=0.15), bevel=0.06).parent = root
    return root


@asset("plates_diverge", size=(640, 440), loop=(36, 12), samples=10, group=G)
def plates_diverge(ctx):
    _block_scene()
    a, b = _slab(-1.8), _slab(1.8)
    gap = box((1, 3.15, 0.5), (0, 0, 0.3), glow("#ff7a1a", 5), bevel=0.02)
    ar1 = arrow((-0.9, 0, 1.25), (-2.3, 0, 1.25))
    ar2 = arrow((0.9, 0, 1.25), (2.3, 0, 1.25))
    vol = [cone(0.4, 0.05, 0.6, (sx * 0.35, 0, 0.85), mat("#8a5a3b", 0.6), seg=24) for sx in (-1, 1)]

    def upd(i, t):
        d = 0.55 + 0.45 * math.sin(t * math.tau)
        a.location.x = -1.75 - d
        b.location.x = 1.75 + d
        gap.scale = (2 * d + 0.3, 3.15, 0.5)
        for sx, v in zip((-1, 1), vol):
            v.location.x = sx * (0.2 + d * 0.5)
            v.scale = (1, 1, 0.5 + 0.5 * d)
    ctx.loop(upd)


@asset("plates_converge", size=(640, 440), loop=(36, 12), samples=10, group=G)
def plates_converge(ctx):
    _block_scene()
    a, b = _slab(-1.8), _slab(1.8)
    ar1 = arrow((-3.2, 0, 1.25), (-1.6, 0, 1.25))
    ar2 = arrow((3.2, 0, 1.25), (1.6, 0, 1.25))
    snow = mat("#f7fbff", 0.5, sss=0.1, coat=0)
    peaks = []
    for k, (px, s) in enumerate(((-0.55, 0.8), (0.0, 1.25), (0.55, 0.85))):
        m = cone(0.75 * s, 0.0, 1.4 * s, (px, 0, 0.7), mat("#7a5a44", 0.7, sss=0.05, coat=0), seg=32)
        cap = cone(0.3 * s, 0.0, 0.5 * s, (px, 0, 0.7 + 0.45 * s), snow, seg=32)
        peaks.append((m, cap, px, s))

    def upd(i, t):
        k = 0.5 + 0.5 * math.sin(t * math.tau - 1.57)
        a.location.x = -1.75 - 0.9 * (1 - k)
        b.location.x = 1.75 + 0.9 * (1 - k)
        for m, cap, px, s in peaks:
            h = max(0.001, k)
            m.scale = (h, h, h)
            m.location = (px, 0, 0.5 + 0.7 * s * h)
            cap.scale = (h, h, h)
            cap.location = (px, 0, 0.5 + (1.4 * s * 0.8) * h)
    ctx.loop(upd)


@asset("plates_transform", size=(640, 440), loop=(36, 12), samples=10, group=G)
def plates_transform(ctx):
    kit.studio(scale=1.7, key=420)
    mant = tex_mat("noise", "#ff5a14", "#ffb02e", scale=0.9, detail=4, mid=0.5, contrast=0.3, rough=0.5, emit=0.55, sss=0, coat=0)
    box((7.4, 4.6, 1.7), (0, 0, -0.85), mant, bevel=0.08)
    kit.camera((0, -10.0, 6.8), (0, 0, -0.1), lens=44)
    a = _slab(0, w=7.0, depth=2.2)
    b = _slab(0, w=7.0, depth=2.2)
    a.location.y = 1.15
    b.location.y = -1.15
    ar1 = arrow((-2.0, 0.0, 1.45), (-3.3, 0.0, 1.45), "#ff3b3b")
    ar2 = arrow((2.0, 0.0, 1.45), (3.3, 0.0, 1.45), "#3b6bff")
    ar1.location = (-0.5, 1.2, 0.5)
    ar2.location = (0.5, -1.2, 0.5)
    ar2.rotation_euler = (0, 0, R(180))
    ar1.rotation_euler = (0, R(90), 0)
    ar2.rotation_euler = (0, R(-90), 0)

    def upd(i, t):
        d = math.sin(t * math.tau)
        a.location.x = 0.7 * d
        b.location.x = -0.7 * d
        ar1.location = (0.7 * d - 0.5, 1.15, 0.9)
        ar2.location = (-0.7 * d + 0.5, -1.15, 0.9)
    ctx.loop(upd)


# ═══════════════════════ Earth layers cutaway ═══════════════════════
@asset("earth_layers", size=(640, 640), samples=32, group=G)
def earth_layers(ctx):
    kit.studio(scale=1.3, key=480)
    cutter = box((2.2, 2.2, 2.2), (1.1, -1.1, 1.1), mat("#fff"), bevel=0.0)
    cutter.hide_render = True
    radii = [0.3, 0.55, 0.93, 1.0, 1.02]
    mats = [glow("#ffe34d", 2.4), mat("#ff9a1f", 0.45, emit="#ff7a00", emit_strength=1.0), mat("#e8452c", 0.5, emit="#b32a10", emit_strength=0.5, sss=0.2),
            mat("#7b4a2d", 0.7, sss=0.05), tex_mat("noise", "#2f7bf0", "#52c970", scale=1.7, detail=5, mid=0.52, contrast=0.025, rough=0.4)]
    spheres = [sphere(r, (0, 0, 0), mats[i], seg=96, rings=48) for i, r in enumerate(radii)]
    keep = []
    for i, s in enumerate(spheres):
        if i > 0:
            inner = sphere(radii[i - 1] - 0.0005, (0, 0, 0), mats[i - 1], seg=96, rings=48)
            inner.hide_render = True
            bm = s.modifiers.new("hole", "BOOLEAN")
            bm.object = inner
            bm.operation = "DIFFERENCE"
            bm.solver = "EXACT"
        bc = s.modifiers.new("cut", "BOOLEAN")
        bc.object = cutter
        bc.operation = "DIFFERENCE"
        bc.solver = "EXACT"
    kit.camera((3.4, -4.3, 2.8), (0, 0, 0.05), lens=52)
    ctx.still()


# ═══════════════════════ icons ═══════════════════════
@asset("icon_hot", size=(360, 460), samples=36, group=G)
def icon_hot(ctx):
    kit.studio(scale=1.0)
    thermometer((0, 0, -0.9), 0.85, "#ff3030")
    flame((-0.75, 0, -0.9), 0.9)
    flame((0.75, 0, -0.9), 0.75)
    kit.camera((0, -7, 0.55), (0, 0, 0.35), lens=50)
    ctx.still()


@asset("icon_cold", size=(360, 460), samples=36, group=G)
def icon_cold(ctx):
    kit.studio(scale=1.0)
    thermometer((0, 0, -0.9), 0.25, "#3b8cff")
    ice = mat("#bfe8ff", 0.12, coat=0.7, sss=0.0)
    for x, z, s, r in ((-0.8, -0.8, 0.45, 20), (0.78, -0.6, 0.35, -25), (0.7, 0.3, 0.28, 40)):
        ico(s, (x, 0, z), ice, sub=1, scale=(0.8, 0.8, 1.3)).rotation_euler = (0, 0, R(r))
    kit.camera((0, -7, 0.55), (0, 0, 0.35), lens=50)
    ctx.still()


@asset("icon_drop", size=(360, 400), samples=36, group=G)
def icon_drop(ctx):
    kit.studio(scale=0.9)
    m = mat("#2f9bff", 0.1, coat=0.8, sss=0.3)
    sphere(0.8, (0, 0, 0), m, seg=48, rings=24)
    cone(0.62, 0.0, 1.15, (0, 0, 0.92), m, seg=48)
    sphere(0.15, (-0.3, -0.62, 0.3), mat("#fff", 0.2, sss=0, emit="#ffffff", emit_strength=0.6), scale=(0.7, 0.5, 1.2))
    kit.camera((0, -6.2, 0.4), (0, 0, 0.45), lens=50)
    ctx.still()


@asset("icon_mountain_snow", size=(480, 420), samples=36, group=G)
def icon_mountain_snow(ctx):
    kit.studio(scale=1.0)
    rk = mat("#8a6a52", 0.7, sss=0.05, coat=0)
    snow = mat("#f7fbff", 0.5, sss=0.1, coat=0)
    for x, s in ((-0.9, 0.8), (0.0, 1.3), (0.95, 0.9)):
        cone(1.0 * s, 0.0, 2.0 * s, (x, 0, s), rk, seg=32)
        cone(0.45 * s, 0.0, 0.8 * s, (x, 0, 2 * s - 0.4 * s), snow, seg=32)
    cloud((-0.4, -0.5, 2.7), 0.6)
    cloud((1.2, -0.4, 2.2), 0.45)
    kit.camera((0, -8.0, 1.6), (0, 0, 1.35), lens=50)
    ctx.still()


@asset("icon_palm_snow", size=(440, 520), samples=36, group=G)
def icon_palm_snow(ctx):
    kit.studio(scale=1.0)
    snow = mat("#f7fbff", 0.5, sss=0.1, coat=0)
    sphere(1.1, (0, 0, -0.1), snow, scale=(1.2, 1, 0.38), seg=48, rings=24)
    sphere(0.45, (0.9, -0.4, 0.0), snow, scale=(1, 1, 0.8))
    tree_palm((0, 0, 0.1), 1.9, 8, 1.0)
    kit.camera((0, -7.2, 1.2), (0, 0, 1.2), lens=50)
    ctx.still()


@asset("icon_glacier", size=(480, 380), samples=36, group=G)
def icon_glacier(ctx):
    kit.studio(scale=1.0)
    ice = mat("#aee3ff", 0.15, coat=0.7, sss=0.3)
    for i, (x, y, s) in enumerate(((0, 0, 1.0), (-0.9, 0.3, 0.7), (0.95, 0.2, 0.75))):
        ico(0.9 * s, (x, y, 0.55 * s), ice, sub=2, scale=(1.5, 1.1, 0.8)).rotation_euler = (0, 0, i)
    sphere(1.7, (0.2, -0.2, -0.5), mat("#8a8f98", 0.7, sss=0.02, coat=0), scale=(1.4, 1.1, 0.5))
    for k in range(5):
        curve([(-1.3 + k * 0.1, -1.0, 0.45), (-0.3 + k * 0.08, -0.9, 0.6), (0.9 - k * 0.08, -0.9, 0.5)], 0.015, mat("#5a6672", 0.6, sss=0), loc=(0, 0, k * 0.0))
    kit.camera((0, -7.0, 2.6), (0, 0, 0.5), lens=50)
    ctx.still()


# ═══════════════════════ story backgrounds ═══════════════════════
@asset("bg_study", size=(1280, 720), bg=True, samples=48, group=G)
def bg_study(ctx):
    kit.studio(scale=3.2, key=1400, fill=400, rim=200, amb=0.5, top="#ffe9c9", bottom="#d8b48a")
    wall = mat("#c98f5f", 0.85, sss=0.05, coat=0)
    box((22, 0.4, 10), (0, 4.0, 4.4), wall, bevel=0.0)
    wd = tex_mat("wave", "#8a5a34", "#a9733f", scale=2.2, mid=0.5, contrast=0.35, rough=0.55, coord="Object", sss=0, coat=0.1)
    box((22, 12, 0.3), (0, -1.5, -0.15), wd, bevel=0.0)
    # window glowing
    box((3.4, 0.2, 3.6), (-4.2, 3.75, 4.6), glow("#bfe3ff", 3.2), bevel=0.0)
    for sx in (-1, 1):
        box((0.2, 0.3, 3.8), (-4.2 + sx * 1.7, 3.7, 4.6), mat("#5a3a22", 0.6), bevel=0.02)
    box((3.6, 0.3, 0.2), (-4.2, 3.7, 4.6), mat("#5a3a22", 0.6), bevel=0.02)
    # bookshelves
    box((4.4, 0.9, 6.6), (5.6, 3.3, 3.1), mat("#5a3a22", 0.6), bevel=0.04)
    rnd = random.Random(2)
    cols = ["#e8584f", "#4aa3df", "#f2a33a", "#6bbf59", "#b26bd6", "#fff1c9"]
    for row in range(4):
        x = 3.7
        while x < 7.4:
            w = rnd.uniform(0.18, 0.34)
            hgt = rnd.uniform(0.9, 1.35)
            box((w, 0.6, hgt), (x + w / 2, 2.9, 1.0 + row * 1.5 + hgt / 2 - 0.45), mat(rnd.choice(cols), 0.55), bevel=0.02)
            x += w + 0.03
    # desk
    box((6.0, 2.2, 0.28), (0.4, 1.4, 1.35), mat("#6b4527", 0.5, coat=0.3), bevel=0.05)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box((0.28, 0.28, 1.35), (0.4 + sx * 2.7, 1.4 + sy * 0.9, 0.67), mat("#4a2f1b", 0.6), bevel=0.03)
    # world map on wall
    box((4.2, 0.1, 2.8), (0.8, 3.7, 5.6), mat("#f4e9c9", 0.7, sss=0), bevel=0.04)
    for k, (cx, cz, sx_, sz_, col) in enumerate(((-0.6, 5.7, 0.7, 1.0, "#4aa3df"), (0.4, 5.7, 0.6, 0.9, "#6bbf59"), (1.4, 6.1, 1.1, 0.7, "#e8584f"), (1.2, 5.2, 0.6, 0.6, "#f2a33a"))):
        box((sx_, 0.08, sz_), (cx + 0.2, 3.6, cz - 0.1), mat(col, 0.6), bevel=0.02)
    # globe on the desk
    sphere(0.7, (-1.5, 1.4, 2.5), tex_mat("noise", "#2f7bf0", "#52c970", scale=1.9, mid=0.52, contrast=0.025, rough=0.4), seg=64, rings=32)
    torus(0.78, 0.03, (-1.5, 1.4, 2.5), mat("#d4a017", 0.3, metal=0.8), rot=(R(70), 0, R(10)))
    cyl(0.06, 0.55, (-1.5, 1.4, 1.75), mat("#d4a017", 0.3, metal=0.8))
    cyl(0.4, 0.08, (-1.5, 1.4, 1.54), mat("#6b4527", 0.5))
    # papers + lamp
    box((0.9, 0.7, 0.04), (1.0, 1.1, 1.51), mat("#fffdf5", 0.7, sss=0), rot=(0, 0, R(12)), bevel=0.01)
    box((0.9, 0.7, 0.04), (1.3, 1.5, 1.55), mat("#fffdf5", 0.7, sss=0), rot=(0, 0, R(-8)), bevel=0.01)
    cyl(0.05, 0.9, (2.4, 1.8, 1.95), mat("#2b2b2b", 0.4, metal=0.5))
    cone(0.5, 0.15, 0.5, (2.4, 1.8, 2.55), mat("#2c8a4a", 0.4), seg=32)
    sphere(0.14, (2.4, 1.8, 2.3), glow("#fff1b0", 6))
    kit.camera((0, -12.5, 4.1), (0, 0, 3.4), lens=34)
    ctx.still()


@asset("bg_arctic", size=(1280, 720), bg=True, samples=48, group=G)
def bg_arctic(ctx):
    kit.studio(scale=3.2, key=1500, fill=500, rim=300, amb=0.9, top="#9fd3ff", bottom="#ffe3f2")
    snow = mat("#f2f8ff", 0.75, sss=0.2, coat=0)
    ice = mat("#aee3ff", 0.2, coat=0.6, sss=0.3)
    ground = sphere(30, (0, 24, -29.5), snow, scale=(1.4, 1.0, 1.0), seg=64, rings=32)
    rnd = random.Random(4)
    for k in range(7):
        x = -14 + k * 4.6 + rnd.uniform(-1, 1)
        h = rnd.uniform(3, 6)
        cone(rnd.uniform(2.2, 3.4), 0.0, h, (x, 12 + rnd.uniform(0, 4), h / 2 - 0.2), ice if k % 2 else mat("#dfeaf7", 0.6, sss=0.2, coat=0), seg=6)
    for k in range(9):
        sphere(rnd.uniform(0.5, 1.3), (rnd.uniform(-10, 10), rnd.uniform(3, 9), 0.0), snow, scale=(1.4, 1, 0.5))
    # aurora ribbons
    for k, c in enumerate(("#6bffb0", "#8ae4ff", "#d78aff")):
        cu = curve([(-12 + k, 18, 8 + k * 0.6), (-5, 18, 11 + k), (2, 18, 9 + k * 0.5), (9, 18, 12), (14, 18, 9)], 0.9, glow(c, 1.6, 0.5), name=f"aurora{k}")
    kit.camera((0, -12.5, 2.6), (0, 0, 3.4), lens=34)
    ctx.still()


# ═══════════════════════ extra loops ═══════════════════════
@asset("fit_puzzle", size=(640, 400), loop=(48, 12), samples=10, group=G)
def fit_puzzle(ctx):
    kit.studio(scale=2.0, key=500, amb=0.7)
    box((19, 12.5, 0.5), (0, 0, -0.25), mat("#2370d6", 0.55, sss=0.1, coat=0.05), bevel=0.2)
    box((20.2, 13.7, 0.35), (0, 0, -0.45), mat("#0f3f8f", 0.5), bevel=0.2)
    parts = {}
    for n in ("africa", "samerica"):
        pts, col = CONT[n]
        ob, (cx, cy) = poly_slab(pts, 0.17, 0.4, mat(col, 0.5, sss=0.15), 0.06, n)
        parts[n] = (ob, cx, cy)
    kit.camera((0, -10, 13.5), (0.2, 0.3, 0), lens=34)

    def upd(i, t):
        k = 0.5 - 0.5 * math.cos(t * math.tau)       # 0 = today, 1 = fitted together
        for n, (ob, cx, cy) in parts.items():
            dx, dy, rt = PAN[n]
            ob.location = ((cx + dx * k * (1 if n == "samerica" else 0)) * 0.17 - 0.2, (cy + dy * k * (1 if n == "samerica" else 0)) * 0.17 + 0.2, 0.2)
            ob.rotation_euler = (0, 0, R(rt * k * (1 if n == "samerica" else 0)))
    ctx.loop(upd)


@asset("earth_spin", size=(420, 420), loop=(36, 12), samples=10, group=G)
def earth_spin(ctx):
    kit.studio(scale=1.2)
    tilt = empty("tilt", (0, 0, 0), rot=(R(23), 0, 0))
    g = sphere(1.0, (0, 0, 0), tex_mat("noise", "#2f7bf0", "#52c970", scale=1.7, detail=5, mid=0.52, contrast=0.025, rough=0.4), scale=(1, 1, 0.93), seg=96, rings=48)
    g.parent = tilt
    for z in (1.0, -1.0):
        cyl(0.025, 0.5, (0, 0, z * 1.13), mat("#fff", 0.3), seg=12).parent = tilt
    kit.camera((0, -4.6, 0.3), (0, 0, 0), lens=50)

    def upd(i, t):
        g.rotation_euler = (0, 0, t * math.tau)
    ctx.loop(upd)
