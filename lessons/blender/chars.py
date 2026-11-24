"""Lesson characters, all built from bevelled primitives in a chunky clay-toy style.

terra()    - Terra, the cartoon Earth host of the geology units
kid()      - Salem / Maryam, the two student explorers
elder()    - Jiddi, the storytelling grandfather (majlis storyteller)
professor()- Professor Wegener-style scientist for the continental-drift story

Every builder returns a root empty. Poses rotate arm/leg pivots, so one model gives many stills.
"""
import math

import bpy

from . import kit
from .kit import V, capsule, cone, cyl, empty, face, mat, sphere, torus, box, tex_mat, stripes_mat, curve

R = math.radians


def _arm(root, side, shoulder, length, r, sleeve, hand, rot, hand_r=None, name="arm"):
    """Arm pivot at `shoulder`; sleeve capsule hangs along -Z. rot=(x, y, z) degrees at the pivot."""
    hand_r = hand_r or r * 1.25
    fwd, out = rot[0], rot[1]
    sgn = 1 if side == "L" else -1       # left pivot is on -X: outward swing is +Y-rotation
    pv = empty(f"{name}{side}", shoulder, root, (R(-fwd), R(sgn * out), 0))
    a = capsule(r, length, (0, 0, -length / 2 - r * 0.2), sleeve)
    a.parent = pv
    h = sphere(hand_r, (0, 0, -length - r * 0.9), hand, seg=24, rings=12)
    h.parent = pv
    return pv


def _leg(root, x, hip_z, length, r, mat_leg, mat_shoe, rot=(0, 0, 0), shoe_len=1.6):
    pv = empty("leg", (x, 0, hip_z), root, (R(rot[0]), R(rot[1]), R(rot[2])))
    l = capsule(r, length, (0, 0, -length / 2), mat_leg)
    l.parent = pv
    s = sphere(r * 1.25, (0, -r * 0.6, -length - r * 0.2), mat_shoe, scale=(1.0, shoe_len * 0.95, 0.7), seg=24, rings=12)
    s.parent = pv
    sole = sphere(r * 1.27, (0, -r * 0.6, -length - r * 0.55), mat("#f4f1ea", 0.6, sss=0), scale=(1.0, shoe_len * 0.97, 0.28), seg=24, rings=10)
    sole.parent = pv
    return pv


# ═════════════════════════════ Terra ═════════════════════════════
def terra(expr="smile", brow="up", pose="idle", helmet=True, look=(0, 0), root_loc=(0, 0, 0), spin=0.0):
    root = empty("Terra", root_loc)
    earth = tex_mat("noise", "#2f7bf0", "#52c970", scale=1.7, detail=5, rough=0.42, mid=0.52, contrast=0.025, sss=0.15, coat=0.3, bump=0.0)
    globe = sphere(1.0, (0, 0, 0), earth, seg=96, rings=48)
    globe.parent = root
    globe.rotation_euler = (0, 0, R(spin))
    # ice caps
    for z, sgn in ((0.93, 1), (-0.93, -1)):
        cap = sphere(0.36, (0, 0, z), mat("#f5fbff", 0.5, sss=0.1), scale=(1, 1, 0.34), seg=32, rings=12)
        cap.parent = root
    # cloud puffs
    cm = mat("#ffffff", 0.7, sss=0.05, coat=0)
    for (x, y, z, s) in ((0.5, -0.78, 0.45, 0.12), (0.64, -0.7, 0.35, 0.09), (-0.7, -0.6, -0.3, 0.1), (-0.78, -0.5, -0.38, 0.07)):
        p = sphere(s, (x, y, z), cm, scale=(1.5, 0.6, 0.8), seg=20, rings=10)
        p.parent = root
    face(root, -0.955, eye_dx=0.22, eye_z=0.06, eye_r=0.12, expr=expr, brow=brow, scale=1.18, mouth_z=-0.16, look=look)
    glove = mat("#ffffff", 0.45, sss=0.05)
    skin = mat("#2f7bf0", 0.4)
    P = {
        "idle":   dict(aL=(0, 14), aR=(0, 14)),
        "wave":   dict(aL=(0, 14), aR=(0, 150)),
        "point":  dict(aL=(0, 14), aR=(70, 40)),
        "cheer":  dict(aL=(0, 150), aR=(0, 150)),
        "think":  dict(aL=(0, 14), aR=(125, 25)),
        "shrug":  dict(aL=(20, 65), aR=(20, 65)),
        "present": dict(aL=(60, 50), aR=(60, 50)),
    }[pose]
    _arm(root, "L", (-0.97, 0, -0.1), 0.42, 0.11, skin, glove, P["aL"])
    _arm(root, "R", (0.97, 0, -0.1), 0.42, 0.11, skin, glove, P["aR"])
    shoe = mat("#e63946", 0.35, coat=0.5)
    for x in (-0.34, 0.34):
        _leg(root, x, -0.9, 0.22, 0.12, skin, shoe)
    if helmet:
        hm = mat("#ffc61a", 0.3, coat=0.6)
        d = sphere(0.5, (0, 0.02, 0.9), hm, scale=(1, 1, 0.62), seg=48, rings=24)
        d.parent = root
        br = cyl(0.55, 0.05, (0, -0.1, 0.77), hm, scale=(1, 1.1, 1), seg=48)
        br.rotation_euler = (R(-8), 0, 0)
        br.parent = root
        lamp = sphere(0.1, (0, -0.42, 0.95), mat("#fff7c2", 0.2, emit="#ffe680", emit_strength=6, sss=0), scale=(1, 0.7, 1), seg=20, rings=10)
        lamp.parent = root
        lamp_ring = torus(0.1, 0.025, (0, -0.4, 0.95), mat("#c9c9c9", 0.3, metal=0.6), rot=(R(90), 0, 0))
        lamp_ring.parent = root
        stripe = cyl(0.12, 0.62, (0, -0.02, 1.05), mat("#e63946", 0.4), rot=(R(-8), 0, 0), seg=24, scale=(1, 1, 0.3))
        stripe.rotation_euler = (R(78), 0, 0)
        stripe.parent = root
    return root


# ═════════════════════════════ people ═════════════════════════════
POSES = {
    #            (forward°, outward°) for left and right arm
    "idle":     ((0, 12), (0, 12)),
    "wave":     ((0, 12), (0, 160)),
    "point":    ((0, 12), (85, 30)),
    "pointup":  ((0, 12), (0, 175)),
    "cheer":    ((0, 160), (0, 160)),
    "think":    ((0, 12), (125, 22)),
    "shrug":    ((25, 68), (25, 68)),
    "present":  ((70, 45), (70, 45)),
    "hold":     ((75, 12), (75, 12)),
    "surprise": ((10, 120), (10, 120)),
    "explain":  ((50, 50), (95, 25)),
}


def person(kind="salem", expr="smile", pose="idle", brow="up", look=(0, 0), prop=None, root_loc=(0, 0, 0), tilt=0.0):
    """kind: salem | maryam | jidd | prof"""
    root = empty(kind, root_loc)
    skin_hex = {"salem": "#d9a066", "maryam": "#e2ad7a", "jidd": "#c98f5a", "prof": "#f0c8a4"}[kind]
    skin = mat(skin_hex, 0.42, sss=0.2)
    white = mat("#f7f4ec", 0.8, sss=0.05, coat=0.0)
    # body
    if kind == "salem":
        robe = white
    elif kind == "maryam":
        robe = stripes_mat("#e8486b", "#ffb84d", scale=2.2, axis="Z", rough=0.7)
    elif kind == "jidd":
        robe = white
    else:
        robe = mat("#e8572a", 0.7, sss=0.05, coat=0.05)
    body = cone(0.68, 0.44, 1.4, (0, 0, 0.8), robe, seg=48, bevel=0.0)
    body.parent = root
    hem = torus(0.68, 0.035, (0, 0, 0.12), mat("#d4a017" if kind != "prof" else "#fff4e6", 0.4, metal=0.0, sss=0), scale=(1, 1, 1))
    hem.parent = root
    neck = cyl(0.2, 0.2, (0, 0, 1.52), skin, seg=24)
    neck.parent = root
    # head
    head = sphere(0.64, (0, 0, 2.05), skin, scale=(1.0, 0.94, 0.98), seg=64, rings=32)
    head.parent = root
    head.rotation_euler = (0, R(tilt), 0)
    for sx in (-1, 1):
        ear = sphere(0.12, (sx * 0.62, 0.02, 2.02), skin, scale=(0.5, 0.7, 1.0), seg=16, rings=10)
        ear.parent = root
    nose = sphere(0.075, (0, -0.6, 1.93), skin, scale=(1, 0.9, 1), seg=16, rings=10)
    nose.parent = root
    face(root, -0.575, eye_dx=0.24, eye_z=2.07 - 0.0, eye_r=0.115, expr=expr, brow=brow, scale=1.0, mouth_z=1.78, look=look,
         blush="#ff8aa1" if kind in ("salem", "maryam", "prof") else None) if False else None
    _kid_face(root, expr, brow, look, kind)
    # clothing / accessories per character
    if kind == "salem":
        _kuma(root)
        tas = cyl(0.025, 0.4, (0, -0.2, 1.3), mat("#b5651d", 0.6), rot=(R(8), 0, 0), seg=12)
        tas.parent = root
        sleeve, hand = white, skin
    elif kind == "maryam":
        _lihaf(root)
        sleeve, hand = robe, skin
    elif kind == "jidd":
        _elder_extras(root, white, skin)
        sleeve, hand = mat("#4a3426", 0.7, sss=0.05), skin
    else:
        _prof_extras(root, skin)
        sleeve, hand = robe, mat("#5a3a2a", 0.8, sss=0.0)
    # arms
    a = POSES[pose]
    _arm(root, "L", (-0.52, 0, 1.38), 0.5, 0.15, sleeve, hand, a[0], hand_r=0.17)
    _arm(root, "R", (0.52, 0, 1.38), 0.5, 0.15, sleeve, hand, a[1], hand_r=0.17)
    # sandals
    sh = mat("#6b4423", 0.5, coat=0.3)
    for x in (-0.22, 0.22):
        s = sphere(0.16, (x, -0.35, 0.06), sh, scale=(1.0, 1.7, 0.45), seg=20, rings=10)
        s.parent = root
    if prop:
        _prop(root, prop)
    return root


def _kid_face(root, expr, brow, look, kind):
    # face features sit on the head sphere (radius 0.64, centre z=2.05), depth -0.6
    face(root, -0.585, eye_dx=0.235, eye_z=2.03, eye_r=0.125, expr=expr, brow=brow, scale=1.0, mouth_z=1.76, look=look,
         blush="#ff7d9a" if kind != "jidd" else None)
    # re-centre: face() offsets z by scale, so features above are authored in world-z; nothing else to do


def _kuma(root):
    cap = mat("#fbfaf5", 0.85, sss=0.02, coat=0.0)
    dome = sphere(0.62, (0, 0.02, 2.46), cap, scale=(1.0, 0.96, 0.5), seg=48, rings=20)
    dome.parent = root
    band = cyl(0.63, 0.2, (0, 0.02, 2.4), stripes_mat("#d4a017", "#1f7a5c", scale=6, axis="X", rough=0.5), seg=64)
    band.parent = root
    for z, c in ((2.29, "#d4a017"),):
        r = torus(0.63, 0.02, (0, 0.02, z), mat(c, 0.4, metal=0.6), scale=(1, 1, 1))
        r.parent = root
    top = sphere(0.06, (0, 0.02, 2.7), mat("#d4a017", 0.4, metal=0.5), seg=16, rings=8)
    top.parent = root


def _lihaf(root):
    sc = stripes_mat("#2b9eb3", "#ffd166", scale=2.8, axis="Z", rough=0.7)
    sc2 = mat("#2b9eb3", 0.7, sss=0.04)
    shell = sphere(0.72, (0, 0.17, 2.1), sc2, scale=(1.0, 0.95, 1.0), seg=64, rings=32)
    shell.parent = root
    drape = cone(0.9, 0.52, 0.95, (0, 0.14, 1.42), sc2, seg=48)
    drape.parent = root
    trim = torus(0.66, 0.035, (0, -0.02, 2.05), mat("#ffd166", 0.4, metal=0.2), rot=(R(90), 0, 0), scale=(1, 1.04, 1.0))
    trim.parent = root
    trim.location = (0, -0.45, 2.05)
    trim.scale = (0.8, 0.8, 0.8)
    flower = sphere(0.09, (0.5, -0.5, 2.5), mat("#ff5d8f", 0.4), seg=20, rings=10)
    flower.parent = root


def _elder_extras(root, white, skin):
    hair = mat("#f2f2f0", 0.7, sss=0.1)
    # beard
    for i, (x, y, z, r) in enumerate([(0, -0.42, 1.5, 0.27), (-0.33, -0.36, 1.66, 0.19), (0.33, -0.36, 1.66, 0.19), (0, -0.44, 1.34, 0.2),
                                       (-0.2, -0.46, 1.44, 0.17), (0.2, -0.46, 1.44, 0.17), (0, -0.4, 1.2, 0.14)]):
        b = sphere(r, (x, y, z), hair, seg=24, rings=12)
        b.parent = root
    for sx in (-1, 1):
        m = sphere(0.13, (sx * 0.11, -0.6, 1.83), hair, scale=(1.5, 0.7, 0.6), seg=20, rings=10)
        m.rotation_euler = (0, R(sx * -12), 0)
        m.parent = root
    # glasses
    gl = mat("#2b2118", 0.3, coat=0.5)
    for sx in (-1, 1):
        g = torus(0.15, 0.018, (sx * 0.235, -0.64, 2.03), gl, rot=(R(90), 0, 0))
        g.parent = root
    br = curve([(-0.09, -0.66, 2.03), (0, -0.67, 2.06), (0.09, -0.66, 2.03)], 0.015, gl)
    br.parent = root
    # masar (turban)
    cols = ["#7a1f35", "#d4a017", "#1f5f8b"]
    for i in range(4):
        t = torus(0.55 - i * 0.02, 0.15, (0, 0.0, 2.46 + i * 0.06), mat(cols[i % 3], 0.8, sss=0.03, coat=0.0), scale=(1, 1.05, 0.8))
        t.parent = root
        t.rotation_euler = (R(-6), 0, 0)
    cap = sphere(0.5, (0, 0.03, 2.62), mat("#7a1f35", 0.8, sss=0.03, coat=0), scale=(1, 1, 0.6), seg=32, rings=16)
    cap.parent = root
    # bisht cloak panels
    bis = mat("#3a2a20", 0.7, sss=0.05, coat=0.05)
    trim = mat("#d4a017", 0.35, metal=0.7)
    for sx in (-1, 1):
        p = cone(0.5, 0.28, 1.35, (sx * 0.32, -0.1, 0.82), bis, seg=32, scale=(0.55, 0.9, 1.0), rot=(0, R(sx * 3), 0))
        p.parent = root
        edge = cyl(0.025, 1.3, (sx * 0.1, -0.52, 0.85), trim, seg=12, rot=(R(6), 0, R(sx * 2)))
        edge.parent = root
    # cane
    cane = mat("#7a5230", 0.45, coat=0.35)
    shaft = cyl(0.035, 1.5, (0.78, -0.35, 0.78), cane, seg=16)
    shaft.parent = root
    crook = torus(0.1, 0.035, (0.88, -0.35, 1.55), cane, rot=(R(90), 0, 0))
    crook.parent = root


def _prof_extras(root, skin):
    hair = mat("#7b4a2b", 0.6, sss=0.1)
    # moustache
    for sx in (-1, 1):
        m = sphere(0.13, (sx * 0.1, -0.6, 1.83), hair, scale=(1.5, 0.7, 0.55), seg=20, rings=10)
        m.rotation_euler = (0, R(sx * -18), 0)
        m.parent = root
    # fur-lined hat with ear flaps
    hat = mat("#6b4f3a", 0.85, sss=0.05, coat=0)
    fur = mat("#f3ede2", 0.95, sss=0.1, coat=0)
    dome = sphere(0.7, (0, 0.04, 2.3), hat, scale=(1.0, 1.0, 0.7), seg=48, rings=24)
    dome.parent = root
    rim = torus(0.64, 0.12, (0, -0.02, 2.2), fur, scale=(1, 1.0, 0.9))
    rim.parent = root
    for sx in (-1, 1):
        fl = sphere(0.2, (sx * 0.7, 0.05, 1.9), hat, scale=(0.45, 0.7, 1.2), seg=20, rings=10)
        fl.parent = root
        tie = sphere(0.08, (sx * 0.7, -0.06, 1.6), fur, seg=14, rings=8)
        tie.parent = root
    pom = sphere(0.12, (0, 0.04, 2.8), fur, seg=20, rings=10)
    pom.parent = root
    # fur collar + scarf
    col = torus(0.5, 0.17, (0, 0, 1.45), fur, scale=(1, 1, 0.9))
    col.parent = root
    sc = torus(0.42, 0.1, (0, -0.05, 1.3), mat("#2a6fdb", 0.8, sss=0.03, coat=0), scale=(1, 1, 1))
    sc.parent = root
    # round glasses
    gl = mat("#2b2118", 0.3, coat=0.5)
    for sx in (-1, 1):
        g = torus(0.14, 0.016, (sx * 0.235, -0.62, 2.03), gl, rot=(R(90), 0, 0))
        g.parent = root


def _prop(root, kind):
    if kind == "book":
        b = box((0.36, 0.1, 0.46), (0.18, -0.82, 0.92), mat("#2563c9", 0.5, coat=0.3), rot=(R(-70), 0, R(10)), bevel=0.02)
        b.parent = root
        pg = box((0.32, 0.07, 0.42), (0.2, -0.83, 0.92), mat("#fffdf5", 0.6, sss=0), rot=(R(-70), 0, R(10)), bevel=0.01)
        pg.parent = root
    elif kind == "scroll":
        s = cyl(0.08, 0.6, (0.0, -0.9, 0.9), mat("#f6e7c1", 0.7, sss=0.02), rot=(0, R(90), R(10)), seg=20)
        s.parent = root
        for sx in (-1, 1):
            e = cyl(0.1, 0.05, (sx * 0.31, -0.9, 0.9), mat("#8b5a2b", 0.4), rot=(0, R(90), R(10)), seg=20)
            e.parent = root
    elif kind == "magnifier":
        l = torus(0.18, 0.03, (0.62, -0.7, 1.2), mat("#d4a017", 0.3, metal=0.7), rot=(R(90), 0, 0))
        l.parent = root
        g = cyl(0.17, 0.02, (0.62, -0.7, 1.2), mat("#bfe8ff", 0.05, sss=0, alpha=0.5, glass=True), rot=(R(90), 0, 0), seg=32)
        g.parent = root
        h = cyl(0.03, 0.35, (0.62, -0.7, 0.9), mat("#7a5230", 0.5), rot=(0, 0, 0), seg=12)
        h.parent = root


# ═════════════════════════════ the water drop (river story) ═════════════════════════════
def droplet(expr="smile", pose="idle", brow="up", look=(0, 0), root_loc=(0, 0, 0)):
    """A glossy water-drop buddy: used to tell the river's life story (youth / maturity / old age)."""
    root = empty("drop", root_loc)
    water = mat("#2f9bff", 0.08, coat=0.9, sss=0.35)
    sphere(0.95, (0, 0, 0.0), water, scale=(1, 0.95, 0.95), seg=64, rings=32).parent = root
    cone(0.74, 0.0, 1.15, (0, 0, 1.0), water, seg=64).parent = root
    sphere(0.17, (-0.35, -0.82, 0.35), mat("#ffffff", 0.2, sss=0, emit="#ffffff", emit_strength=0.8), scale=(0.7, 0.4, 1.3), seg=16, rings=8).parent = root
    face(root, -0.8, eye_dx=0.26, eye_z=0.12, eye_r=0.13, expr=expr, brow=brow, scale=1.2, mouth_z=-0.17, look=look, blush="#ff9ec0")
    skin = mat("#2f9bff", 0.15, coat=0.6, sss=0.3)
    glove = mat("#ffffff", 0.45, sss=0.05)
    arms = {"idle": ((0, 14), (0, 14)), "run": ((50, 25), (-50, 25)), "wave": ((0, 14), (0, 160)), "sleepy": ((0, 8), (0, 8))}[pose]
    _arm(root, "L", (-0.92, 0, -0.15), 0.4, 0.11, skin, glove, arms[0])
    _arm(root, "R", (0.92, 0, -0.15), 0.4, 0.11, skin, glove, arms[1])
    shoe = mat("#ffb703", 0.35, coat=0.5)
    legs = {"idle": ((0, 0, 0), (0, 0, 0)), "run": ((-35, 0, 0), (35, 0, 0)), "wave": ((0, 0, 0), (0, 0, 0)), "sleepy": ((0, 0, 0), (0, 0, 0))}[pose]
    for x, rot in ((-0.35, legs[0]), (0.35, legs[1])):
        _leg(root, x, -0.82, 0.2, 0.12, skin, shoe, rot=rot)
    return root
