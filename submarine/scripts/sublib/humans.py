"""Realistic crew characters.

Bodies, faces, hands, hair and clothing are sculpted with signed-distance shapes (sdf.py) and
polygonised, then decimated to game budgets. Every character shares one 51-bone humanoid rig
(Hips, Spine, Chest, Neck, Head; Shoulder/UpperArm/LowerArm/Hand; Thumb/Index/Middle/Ring/Pinky
1-3; UpperLeg/LowerLeg/Foot/Toes; .L/.R). Skin and clothing use automatic weights; rigid
accessories (buttons, hats, shoes, hair) follow one bone each.

Characters face -Y in T-pose, palms down. Left side = +X.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

from . import core
from .core import R, box_uv, mat
from .sdf import Shape

V = Vector

core.MATLIB.update({
    "SkinA": dict(color="#e2b294", roughness=0.42), "SkinB": dict(color="#c48e68", roughness=0.42),
    "SkinC": dict(color="#8a5a3c", roughness=0.4), "SkinD": dict(color="#efc6a8", roughness=0.42),
    "Lips": dict(color="#b06a62", roughness=0.35), "Nail": dict(color="#e9c4b4", roughness=0.2, coat=0.6),
    "HairGrey": dict(color="#9c968c", roughness=0.5), "HairDark": dict(color="#1d1814", roughness=0.45),
    "HairAuburn": dict(color="#9a3f1c", roughness=0.45), "HairChestnut": dict(color="#4a2e1b", roughness=0.45),
    "FabNavy": dict(color="#1f2d44", roughness=0.85, normal="paint_peel_n", normal_strength=0.5),
    "FabMustard": dict(color="#cf9128", roughness=0.9, normal="paint_peel_n", normal_strength=0.7),
    "FabOlive": dict(color="#545e3b", roughness=0.9, normal="paint_peel_n", normal_strength=0.5),
    "FabTeal": dict(color="#2a6f74", roughness=0.85, normal="paint_peel_n", normal_strength=0.5),
    "FabWhite": dict(color="#ecebe5", roughness=0.85, normal="paint_peel_n", normal_strength=0.4),
    "FabRed": dict(color="#b8372a", roughness=0.9, normal="paint_peel_n", normal_strength=0.6),
    "FabCheck": dict(tex="floor_tiles", tile=0.3, roughness=0.9),
    "Leather": dict(tex="leather_brown", tile=0.4, roughness=0.45, coat=0.3),
    "ShoeBlack": dict(color="#151517", roughness=0.3, coat=0.6), "ShoeBrown": dict(color="#56351f", roughness=0.45, coat=0.3),
    "Sole": dict(color="#2a2522", roughness=0.8),
    "GoldTrim": dict(color="#d7a33f", metallic=1.0, roughness=0.3),
    "LensGlass": dict(color="#a8d8e6", roughness=0.03, coat=1.0),
})
for e in ("eye_brown", "eye_blue", "eye_green", "eye_hazel"):
    core.MATLIB[e] = dict(tex=e, roughness=0.05, coat=1.0)
SKIN_SSS = {"SkinA", "SkinB", "SkinC", "SkinD"}

# ------------------------------------------------------------------ joints
HIPS, WAIST, CHEST, NECK, HEADB, TOP = V((0, 0, 0.98)), V((0, 0, 1.1)), V((0, 0, 1.28)), V((0, 0.012, 1.47)), \
    V((0, 0.01, 1.565)), V((0, 0.01, 1.8))


def limb(s):
    return dict(clav=V((s * 0.03, 0.0, 1.43)), shoulder=V((s * 0.185, 0.005, 1.44)), elbow=V((s * 0.465, 0.012, 1.44)),
                wrist=V((s * 0.725, 0.0, 1.44)), hip=V((s * 0.092, 0.0, 0.94)), knee=V((s * 0.097, -0.008, 0.515)),
                ankle=V((s * 0.1, 0.02, 0.088)), toe=V((s * 0.1, -0.11, 0.025)), toe_end=V((s * 0.1, -0.185, 0.02)))


def hand_points(s):
    """Finger joint chains for one hand (relative to the wrist joint), palm down, T-pose."""
    W = limb(s)["wrist"]

    def P(x, y, dz=0.0):
        return V((W.x + s * x, y, W.z + dz))

    out = {}
    for name, y0, spread, lens, r, x0 in [("Index", -0.029, -7, (0.043, 0.026, 0.021), 0.0092, 0.095),
                                          ("Middle", -0.009, -1, (0.047, 0.029, 0.023), 0.0094, 0.098),
                                          ("Ring", 0.011, 5, (0.044, 0.027, 0.022), 0.0089, 0.095),
                                          ("Pinky", 0.029, 12, (0.034, 0.021, 0.019), 0.0078, 0.085)]:
        p = P(x0, y0, 0.001)
        d = V((s * math.cos(R(spread)), math.sin(R(spread)), -0.08)).normalized()
        pts, rad = [p.copy()], [r * 1.05]
        for k, L in enumerate(lens):
            p = p + d * L
            pts.append(p.copy())
            rad.append(r * (0.93 - 0.07 * k))
            d = (d + V((0, 0, -0.16))).normalized()
        out[name] = (pts, rad)
    out["Thumb"] = ([P(0.01, -0.022, -0.003), P(0.042, -0.052, -0.008), P(0.067, -0.069, -0.011), P(0.088, -0.08, -0.013)],
                    [0.014, 0.0115, 0.0102, 0.0088])
    return out


# ---------------------------------------------------------------- skeleton

def skeleton_spec():
    bones = [("Hips", HIPS, WAIST, None), ("Spine", WAIST, CHEST, "Hips"), ("Chest", CHEST, NECK, "Spine"),
             ("Neck", NECK, HEADB, "Chest"), ("Head", HEADB, TOP, "Neck")]
    for s, sd in ((1, "L"), (-1, "R")):
        L = limb(s)
        hp = hand_points(s)
        bones += [(f"Shoulder.{sd}", L["clav"], L["shoulder"], "Chest"),
                  (f"UpperArm.{sd}", L["shoulder"], L["elbow"], f"Shoulder.{sd}"),
                  (f"LowerArm.{sd}", L["elbow"], L["wrist"], f"UpperArm.{sd}"),
                  (f"Hand.{sd}", L["wrist"], hp["Middle"][0][0], f"LowerArm.{sd}")]
        for f, (pts, _) in hp.items():
            for k in range(3):
                bones.append((f"{f}{k + 1}.{sd}", pts[k], pts[k + 1], f"Hand.{sd}" if k == 0 else f"{f}{k}.{sd}"))
        bones += [(f"UpperLeg.{sd}", L["hip"], L["knee"], "Hips"), (f"LowerLeg.{sd}", L["knee"], L["ankle"], f"UpperLeg.{sd}"),
                  (f"Foot.{sd}", L["ankle"], L["toe"], f"LowerLeg.{sd}"), (f"Toes.{sd}", L["toe"], L["toe_end"], f"Foot.{sd}")]
    return bones


def make_armature(name, col):
    arm_data = bpy.data.armatures.new(name + "_Skeleton")
    arm = bpy.data.objects.new(name, arm_data)
    col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for bn, head, tail, parent in skeleton_spec():
        e = arm_data.edit_bones.new(bn)
        e.head, e.tail = head, tail
        if any(bn.startswith(x) for x in ("UpperLeg", "LowerLeg", "Foot", "Toes")):
            e.align_roll(V((0, -1, 0)))
        else:
            e.align_roll(V((0, 0, 1)) if abs((tail - head).normalized().z) < 0.9 else V((0, -1, 0)))
        if parent:
            e.parent = eb[parent]
            e.use_connect = (head - eb[parent].tail).length < 1e-4
        eb[bn] = e
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


# --------------------------------------------------------------- mesh utils

def _finish_mesh(name, me, col, materials, decimate=None, tile=1.0):
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    if decimate and decimate < 1.0:
        mod = o.modifiers.new("Dec", "DECIMATE")
        mod.ratio = decimate
        core._bake(o)
    for m in materials:
        o.data.materials.append(mat(m))
    o.data.shade_smooth()
    box_uv(o.data, mat(materials[0]).get("tile", tile))
    return o


BUDGET = {"head": 7000, "hand": 2600, "nails": 400, "forearm": 1200, "brows": 300, "hair": 2400, "beard": 1800,
          "top": 6000, "pants": 4500, "shoe": 1200, "sole": 200}


def sdf_part(name, shape, res, col, materials, decimate=None, assign=None, budget=1500):
    """Polygonise a shape into an object, decimated to a triangle budget.

    assign = [(material_index, Shape, max_dist)] recolours faces near another shape (e.g. lips)."""
    me = shape.mesh(name, res)
    key = name.split("_")[-1].rstrip("-0123456789")
    target = BUDGET.get(key, budget)
    decimate = min(1.0, target / max(1, len(me.polygons)))
    o = _finish_mesh(name, me, col, materials, decimate)
    if assign:
        import numpy as np
        cs = np.array([p.center[:] for p in o.data.polygons], np.float32)
        idx = np.zeros(len(cs), np.int32)
        for mi, sh, dist in assign:
            idx[sh.field(cs) < dist] = mi
        o.data.polygons.foreach_set("material_index", idx)
    return o


def rigid(o, bone):
    vg = o.vertex_groups.new(name=bone)
    vg.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    return o


def bm_part(name, bm, col, m, bone, loc=(0, 0, 0), rot=None, scale=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if scale:
        me.transform(Matrix.Diagonal((*scale, 1)))
    if rot:
        me.transform(rot.to_matrix().to_4x4())
    me.transform(Matrix.Translation(V(loc)))
    o = _finish_mesh(name, me, col, [m])
    if not smooth:
        o.data.shade_flat()
    return rigid(o, bone)


def sss(name, weight=0.28):
    m = mat(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Subsurface Weight"].default_value = weight
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    b.inputs["Subsurface Scale"].default_value = 0.006
    return m


# ------------------------------------------------------------------- parts

def hands_shape(s, glove=False):
    W = limb(s)["wrist"]
    hp = hand_points(s)
    H = Shape(blend=0.011)
    d = V((s, 0, 0))
    H.capsule(W - d * 0.07 + V((0, -0.007, 0)), W + V((0, -0.007, 0)), 0.026, 0.024)
    H.capsule(W - d * 0.07 + V((0, 0.007, 0)), W + V((0, 0.007, 0)), 0.026, 0.024)
    c = W + d * 0.048 + V((0, 0.001, 0))
    H.ellipsoid(c, (0.05, 0.045, 0.0165))
    H.box(W + d * 0.05, (0.04, 0.038, 0.012), r=0.011, k=0.012)
    H.ellipsoid(W + d * 0.024 + V((0, -0.03, -0.004)), (0.032, 0.02, 0.016))
    H.ellipsoid(W + d * 0.042 + V((0, 0.033, -0.003)), (0.04, 0.014, 0.013))
    for f, (pts, rad) in hp.items():
        H.chain(pts, rad, k=0.0035 if f != "Thumb" else 0.006)
        if f != "Thumb":
            H.sphere(pts[0], rad[0] * 1.02, k=0.006)
    if glove:
        H.capsule(W - d * 0.03, W - d * 0.075, 0.036, 0.038, k=0.006)  # gauntlet cuff
    return H


def nails_shape(s):
    hp = hand_points(s)
    N = Shape(blend=0.0)
    for f, (pts, rad) in hp.items():
        d = (pts[3] - pts[2]).normalized()
        up = V((0, 0, 1)) if f != "Thumb" else V((0, 0.35, 1)).normalized()
        up = (up - d * up.dot(d)).normalized()
        q = V((1, 0, 0)).rotation_difference(d)
        c = pts[3] - d * 0.008 + up * rad[3] * 0.72
        N.ellipsoid(c, (0.0085, rad[3] * 0.82, 0.0026), rot=q)
    return N


def head_shape(build):
    """Head + neck. Returns (shape, lips_shape)."""
    S = Shape(blend=0.02)
    S.capsule((0, 0.012, 1.44), (0, 0.004, 1.6), 0.058 * build["neck"], 0.052)       # neck
    S.ellipsoid((0, 0.012, 1.695), (0.076, 0.098, 0.092))                             # cranium
    S.ellipsoid((0, -0.03, 1.64), (0.064, 0.072, 0.075))                              # face mass
    for s in (-1, 1):
        S.capsule((s * 0.058, 0.004, 1.602), (s * 0.016, -0.078, 1.562), 0.019 * build["jaw"], 0.017, k=0.025)  # jaw line
        S.ellipsoid((s * 0.052, -0.055, 1.655), (0.022, 0.016, 0.014), k=0.02)        # cheekbone
        S.ellipsoid((s * 0.077, 0.008, 1.672), (0.011, 0.025, 0.033), k=0.006)        # ear
        S.ellipsoid((s * 0.085, 0.004, 1.67), (0.006, 0.014, 0.019), op="sub", k=0.003)
    S.ellipsoid((0, -0.079, 1.564), (0.023, 0.017, 0.019), k=0.015)                   # chin
    S.capsule((-0.046, -0.082, 1.712), (0, -0.09, 1.716), 0.012, k=0.015)             # brow ridge
    S.capsule((0.046, -0.082, 1.712), (0, -0.09, 1.716), 0.012, k=0.015)
    for s in (-1, 1):
        S.ellipsoid((s * 0.032, -0.09, 1.688), (0.019, 0.014, 0.0125), op="sub", k=0.008)  # eye socket
    # nose
    S.capsule((0, -0.093, 1.702), (0, -0.112, 1.65), 0.0075, 0.0105, k=0.01)
    S.sphere((0, -0.113, 1.646), 0.0132 * build["nose"], k=0.008)
    for s in (-1, 1):
        S.sphere((s * 0.0135, -0.103, 1.642), 0.0092, k=0.006)
        S.ellipsoid((s * 0.0072, -0.108, 1.6355), (0.0042, 0.0045, 0.0028), op="sub", k=0.002)
    # lips
    lips = Shape(blend=0.004)
    lips.chain([(-0.023, -0.09, 1.6115), (0, -0.0962, 1.6145), (0.023, -0.09, 1.6115)], [0.0038, 0.0056, 0.0038])
    lips.chain([(-0.019, -0.0885, 1.6015), (0, -0.0935, 1.5995), (0.019, -0.0885, 1.6015)], [0.004, 0.0064, 0.004])
    for prim in lips.prims:
        S.prims.append((prim[0], prim[1], "add", 0.004))
    S.capsule((-0.024, -0.0975, 1.6068), (0.024, -0.0975, 1.6068), 0.0011, op="sub", k=0.0015)  # mouth line
    # eyelids wrap around the eyeball (after the sockets so they survive)
    for s in (-1, 1):
        cx = s * 0.032
        S.chain([(cx - 0.0135, -0.0795, 1.6905), (cx, -0.0878, 1.6978), (cx + 0.0135, -0.0795, 1.6905)], [0.0028, 0.0042, 0.0028], k=0.004)
        S.chain([(cx - 0.0125, -0.0792, 1.6845), (cx, -0.0858, 1.6802), (cx + 0.0125, -0.0792, 1.6845)], [0.0016, 0.0019, 0.0016], k=0.003)
    if build.get("adams"):
        S.ellipsoid((0, -0.045, 1.5), (0.012, 0.012, 0.018), k=0.012)
    return S, lips


def hair_shape(style):
    H = Shape(blend=0.012)
    if style == "none":
        return None
    H.ellipsoid((0, 0.016, 1.702), (0.083, 0.105, 0.098))
    H.box((0, -0.08, 1.64), (0.2, 0.06, 0.095), op="sub", k=0.006)       # face
    H.box((0, 0.02, 1.52), (0.2, 0.2, 0.1), op="sub", k=0.006)           # below the hairline at the back
    for s in (-1, 1):
        H.ellipsoid((s * 0.08, 0.008, 1.66), (0.02, 0.032, 0.04), op="sub", k=0.006)  # around the ears
    if style == "messy":
        import random
        rnd = random.Random(3)
        for k in range(14):
            a = rnd.uniform(-2.6, 2.6)
            b = rnd.uniform(0.15, 1.2)
            base = V((math.sin(a) * 0.06 * b, 0.01 - math.cos(a) * 0.07 * b, 1.765 + 0.03 * (1.2 - b)))
            tip = base + V((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.05, 0.0), rnd.uniform(0.01, 0.03)))
            H.capsule(base, tip, 0.016, 0.004, k=0.012)
    if style == "short":
        H.ellipsoid((0, -0.045, 1.745), (0.06, 0.05, 0.03), k=0.02)       # swept front
    return H


def beard_shape(full=True):
    B = Shape(blend=0.01)
    if full:
        B.ellipsoid((0, -0.035, 1.598), (0.07, 0.073, 0.058))
        B.box((0, -0.03, 1.7), (0.1, 0.1, 0.063), op="sub", k=0.008)
        B.ellipsoid((0, -0.1, 1.6065), (0.021, 0.03, 0.0085), op="sub", k=0.003)
        B.ellipsoid((0, -0.02, 1.62), (0.055, 0.06, 0.045), op="sub", k=0.004)
    B.chain([(-0.03, -0.098, 1.614), (-0.012, -0.106, 1.62), (0, -0.107, 1.621), (0.012, -0.106, 1.62), (0.03, -0.098, 1.614)],
            [0.004, 0.0065, 0.006, 0.0065, 0.004])
    return B


def brows_shape(build):
    B = Shape(blend=0.003)
    for s in (-1, 1):
        B.chain([(s * 0.015, -0.0955, 1.711), (s * 0.033, -0.096, 1.716), (s * 0.052, -0.087, 1.712)],
                [0.0035 * build["brow"], 0.0042 * build["brow"], 0.0025])
    return B


def torso_shape(b, sleeves="long", loose=1.0):
    """Shirt / jacket / sweater body. b = girth factor, belly adds to the waist."""
    T = Shape(blend=0.04)
    g, bel = b["girth"], b["belly"]
    T.ellipsoid((0, 0.006, 1.0), (0.165 * g, 0.115 * g * bel, 0.1))
    T.ellipsoid((0, -0.004 - 0.02 * (bel - 1), 1.12), (0.152 * g * (1 + 0.3 * (bel - 1)), 0.106 * g * bel, 0.11))
    T.ellipsoid((0, -0.008, 1.29), (0.172 * g, 0.118 * g, 0.14))
    T.capsule((-0.165 * g, 0.006, 1.415), (0.165 * g, 0.006, 1.415), 0.068 * g)
    T.capsule((0, 0.02, 1.4), (0, 0.016, 1.48), 0.062 * g, 0.056)
    for s in (-1, 1):
        L = limb(s)
        T.capsule(L["shoulder"] + V((0, 0, -0.005)), L["elbow"], 0.063 * g * loose, 0.05 * g * loose, k=0.03)
        if sleeves == "long":
            T.capsule(L["elbow"], L["wrist"] - V((s * 0.012, 0, 0)), 0.048 * g * loose, 0.039 * loose, k=0.02)
        elif sleeves == "short":
            T.capsule(L["shoulder"], L["shoulder"] + (L["elbow"] - L["shoulder"]) * 0.45, 0.07 * g, 0.064 * g, k=0.02)
    return T


def forearm_skin_shape(s, g):
    L = limb(s)
    F = Shape(blend=0.02)
    F.capsule(L["shoulder"] + (L["elbow"] - L["shoulder"]) * 0.3, L["elbow"], 0.054 * g, 0.044 * g)
    F.capsule(L["elbow"], L["wrist"], 0.043 * g, 0.03)
    return F


def pants_shape(b, loose=1.0):
    P = Shape(blend=0.03)
    g = b["girth"]
    P.ellipsoid((0, 0.012, 0.985), (0.168 * g, 0.12 * g * b["belly"], 0.11))
    for s in (-1, 1):
        L = limb(s)
        P.capsule(L["hip"] + V((0, 0, 0.02)), L["knee"], 0.088 * g * loose, 0.063 * loose, k=0.03)
        P.capsule(L["knee"], L["ankle"] + V((0, -0.005, 0.03)), 0.061 * loose, 0.05 * loose, k=0.02)
    return P


def shoe_shape(s, boot=False):
    L = limb(s)
    S = Shape(blend=0.02)
    x = L["ankle"].x
    S.ellipsoid((x, -0.045, 0.048), (0.047, 0.125, 0.045))
    S.sphere((x, 0.04, 0.05), 0.045)
    S.ellipsoid((x, -0.11, 0.035), (0.042, 0.06, 0.032))
    if boot:
        S.capsule((x, 0.02, 0.06), (x, 0.022, 0.21), 0.058, 0.055)
    S.box((x, 0, -0.03), (0.2, 0.3, 0.03), op="sub", k=0.0)
    sole = Shape(blend=0.0)
    sole.box((x, -0.043, 0.008), (0.046, 0.128, 0.009), r=0.008)
    return S, sole


# --------------------------------------------------------------- characters

CREW = [
    dict(name="Crew_Navigator", role="navigator", skin="SkinA", eyes="eye_blue", hair="HairGrey", hair_style="short",
         beard=True, top="FabNavy", top_style="jacket", pants="FabNavy", shoes="ShoeBlack", hat="officer",
         build=dict(girth=1.0, belly=1.05, neck=1.0, jaw=1.0, nose=1.05, brow=1.1, adams=True)),
    dict(name="Crew_Gunner", role="weapons_officer", skin="SkinC", eyes="eye_brown", hair="HairDark", hair_style="short",
         beard=False, top="FabMustard", top_style="sweater", pants="FabOlive", shoes="ShoeBlack", boots=True, hat="beanie",
         hat_m="FabRed", build=dict(girth=1.12, belly=1.0, neck=1.15, jaw=1.15, nose=1.1, brow=1.2, adams=True)),
    dict(name="Crew_Loader", role="torpedo_loader", skin="SkinD", eyes="eye_green", hair="HairAuburn", hair_style="messy",
         beard=False, top="FabWhite", top_style="tshirt", pants="FabTeal", overalls=True, shoes="ShoeBrown", boots=True,
         gloves="FabMustard", hat="goggles", build=dict(girth=1.04, belly=1.0, neck=1.0, jaw=1.0, nose=0.95, brow=0.9, adams=True)),
    dict(name="Crew_Cook", role="cook", skin="SkinB", eyes="eye_hazel", hair="HairChestnut", hair_style="short",
         beard=False, mustache=True, top="FabWhite", top_style="chef", pants="FabCheck", shoes="ShoeBlack", apron=True,
         scarf="FabTeal", glasses=True, hat="cookcap",
         build=dict(girth=1.1, belly=1.22, neck=1.1, jaw=1.05, nose=1.15, brow=1.0, adams=False)),
]


def _sphere_bm(r, segs=16, rings=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    return bm


def _eye(name, s, col, eyetex):
    c = V((s * 0.032, -0.0775, 1.6885))
    r = 0.0122
    bm = _sphere_bm(r, 24, 12)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = (co.x / (2 * r) * 0.98 + 0.5, co.z / (2 * r) * 0.98 + 0.5)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.transform(Matrix.Translation(c))
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    me.materials.append(mat(eyetex))
    me.shade_smooth()
    return rigid(o, "Head")


def _auto_weight(objs, arm):
    for o in objs:
        bpy.context.view_layer.objects.active = arm
        for ob in bpy.context.view_layer.objects:
            ob.select_set(False)
        o.select_set(True)
        arm.select_set(True)
        with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[o, arm],
                                       selected_editable_objects=[o, arm]):
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")


def build(spec, col):
    name, b = spec["name"], spec["build"]
    for sk in SKIN_SSS:
        sss(sk)
    skinned, rigid_parts = [], []

    # skin: head/neck, hands (+ forearms for short sleeves)
    head, lips = head_shape(b)
    skinned.append(sdf_part(name + "_head", head, 0.0026, col, [spec["skin"], "Lips"], decimate=0.25,
                            assign=[(1, lips, 0.0004)]))
    gl = spec.get("gloves")
    for s in (-1, 1):
        skinned.append(sdf_part(name + f"_hand{s}", hands_shape(s, bool(gl)), 0.0024, col, [gl or spec["skin"]], decimate=0.18))
        if not gl:
            nails = sdf_part(name + f"_nails{s}", nails_shape(s), 0.0012, col, ["Nail"], decimate=0.4)
            hp = hand_points(s)
            # nails follow the last finger bone they sit on
            import numpy as np
            sd = "L" if s > 0 else "R"
            tips = {f: hp[f][0][3] for f in hp}
            for f in tips:
                vg = nails.vertex_groups.get(f"{f}3.{sd}") or nails.vertex_groups.new(name=f"{f}3.{sd}")
                ids = [v.index for v in nails.data.vertices if (v.co - tips[f]).length < 0.02]
                vg.add(ids, 1.0, "REPLACE")
            rigid_parts.append(nails)
        if spec["top_style"] == "tshirt":
            skinned.append(sdf_part(name + f"_forearm{s}", forearm_skin_shape(s, b["girth"]), 0.004, col, [spec["skin"]],
                                    decimate=0.3))
    for s in (-1, 1):
        rigid_parts.append(_eye(name + f"_eye{s}", s, col, spec["eyes"]))
    rigid_parts.append(rigid(sdf_part(name + "_brows", brows_shape(b), 0.0015, col, [spec["hair"]], decimate=0.4), "Head"))
    hs = hair_shape(spec["hair_style"])
    if hs:
        rigid_parts.append(rigid(sdf_part(name + "_hair", hs, 0.003, col, [spec["hair"]], decimate=0.3), "Head"))
    if spec.get("beard") or spec.get("mustache"):
        rigid_parts.append(rigid(sdf_part(name + "_beard", beard_shape(bool(spec.get("beard"))), 0.0025, col, [spec["hair"]],
                                          decimate=0.3), "Head"))

    # clothing
    style = spec["top_style"]
    sleeves = "short" if style == "tshirt" else "long"
    skinned.append(sdf_part(name + "_top", torso_shape(b, sleeves, 1.06 if style == "jacket" else 1.0), 0.006, col,
                            [spec["top"]], decimate=0.35))
    skinned.append(sdf_part(name + "_pants", pants_shape(b, 1.04 if spec.get("overalls") else 1.0), 0.006, col,
                            [spec["pants"]], decimate=0.35))
    for s, sd in ((1, "L"), (-1, "R")):
        sh, sole = shoe_shape(s, spec.get("boots", False))
        rigid_parts.append(rigid(sdf_part(name + f"_shoe{s}", sh, 0.004, col, [spec["shoes"]], decimate=0.35), f"Foot.{sd}"))
        rigid_parts.append(rigid(sdf_part(name + f"_sole{s}", sole, 0.004, col, ["Sole"], decimate=0.5), f"Foot.{sd}"))
    rigid_parts += _details(spec, col)

    # rig
    arm = make_armature(name, col)
    arm["role"] = spec["role"]
    arm["character"] = True
    arm["height_m"] = 1.8
    _auto_weight(skinned, arm)
    for o in rigid_parts:
        o.parent = arm
        mod = o.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
    # merge into one skinned mesh
    parts = [c for c in arm.children if c.type == "MESH"]
    import os
    if os.environ.get("CREW_DEBUG"):
        for c in sorted(parts, key=lambda c: -len(c.data.polygons))[:12]:
            print("  part", c.name, len(c.data.polygons))
    me = bpy.data.meshes.new(name + "_Mesh")
    me.uv_layers.new(name="UVMap")  # join keeps only UV layers the target already has
    body = bpy.data.objects.new(name + "_Mesh", me)
    col.objects.link(body)
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm
    with bpy.context.temp_override(active_object=body, object=body, selected_objects=parts + [body],
                                   selected_editable_objects=parts + [body]):
        bpy.ops.object.join()
    core.clean_slots(body.data)
    return arm


def _details(spec, col):
    """Rigid accessories: collars, buttons, belts, pockets, hats, glasses, apron..."""
    from .core import bm_box, bm_cyl, bm_torus, bm_lathe
    out = []
    n = spec["name"]
    st = spec["top_style"]
    g = spec["build"]["girth"]
    bel = spec["build"]["belly"]
    front = lambda z: -(0.118 * g if z > 1.2 else 0.106 * g * bel) - 0.004
    if st == "jacket":
        for s in (-1, 1):
            for z in (1.31, 1.22, 1.13):
                out.append(bm_part(n + "_btn", _sphere_bm(0.009, 12, 6), col, "GoldTrim", "Spine",
                                   (s * 0.055, front(z) - 0.004, z)))
            out.append(bm_part(n + "_epaulette", bm_box(0.12, 0.07, 0.014), col, "GoldTrim", "Chest", (s * 0.15 * g, 0.004, 1.48)))
            out.append(bm_part(n + "_epaul2", bm_box(0.115, 0.065, 0.016), col, "FabNavy", "Chest", (s * 0.15 * g, 0.004, 1.483)))
            L = limb(s)
            out.append(bm_part(n + "_cuff", bm_torus(0.041, 0.005, 24, 6, "X"), col, "GoldTrim", f"LowerArm.{'L' if s > 0 else 'R'}",
                               L["wrist"] - V((s * 0.04, 0, 0))))
        out.append(bm_part(n + "_shirt", bm_box(0.05, 0.01, 0.07), col, "FabWhite", "Chest", (0, -0.072, 1.45),
                           rot=Quaternion((1, 0, 0), R(-12))))
        out.append(bm_part(n + "_tie", bm_box(0.016, 0.008, 0.075), col, "PaintNavy", "Chest", (0, -0.0785, 1.445),
                           rot=Quaternion((1, 0, 0), R(-12))))
        coll = Shape(blend=0.01)
        coll.capsule((-0.06, -0.045, 1.47), (0, -0.08, 1.4), 0.012)
        coll.capsule((0.06, -0.045, 1.47), (0, -0.08, 1.4), 0.012)
        out.append(rigid(sdf_part(n + "_lapels", coll, 0.003, col, ["FabNavy"], decimate=0.4), "Chest"))
        out.append(bm_part(n + "_belt", bm_cyl(0.17 * g, 0.04, 40), col, "ShoeBlack", "Hips", (0, 0.006, 1.045),
                           scale=(1, 0.115 / 0.17 * bel + 0.02, 1)))
    if st == "sweater":
        out.append(bm_part(n + "_turtle", bm_torus(0.062, 0.026, 32, 10), col, spec["top"], "Neck", (0, 0.012, 1.485)))
        for s in (-1, 1):
            L = limb(s)
            out.append(bm_part(n + "_rib", bm_torus(0.04, 0.008, 24, 6, "X"), col, spec["top"],
                               f"LowerArm.{'L' if s > 0 else 'R'}", L["wrist"] - V((s * 0.02, 0, 0))))
    if st == "chef":
        for s in (-1, 1):
            for z in (1.34, 1.27, 1.2):
                out.append(bm_part(n + "_btn", _sphere_bm(0.008, 10, 5), col, "BlackPlastic", "Spine", (s * 0.06, front(z) - 0.004, z)))
        out.append(bm_part(n + "_collar", bm_cyl(0.068, 0.04, 32), col, "FabWhite", "Neck", (0, 0.012, 1.475)))
    if spec.get("scarf"):
        out.append(bm_part(n + "_scarf", bm_torus(0.07, 0.016, 32, 8), col, spec["scarf"], "Neck", (0, 0.006, 1.5)))
        sh = Shape(blend=0.006)
        sh.capsule((0, -0.075, 1.48), (-0.01, -0.09, 1.42), 0.014, 0.008)
        sh.capsule((0, -0.075, 1.48), (0.015, -0.088, 1.43), 0.012, 0.007)
        out.append(rigid(sdf_part(n + "_knot", sh, 0.003, col, [spec["scarf"]], decimate=0.5), "Chest"))
    if spec.get("apron"):
        ap = Shape(blend=0.02)
        ap.box((0, -0.106 * g * bel - 0.012, 0.86), (0.16 * g, 0.008, 0.26), r=0.006)
        out.append(rigid(sdf_part(n + "_apron", ap, 0.005, col, ["Ticking"], decimate=0.4), "Hips"))
        bib = Shape(blend=0.01)
        bib.box((0, front(1.25) - 0.012, 1.24), (0.1, 0.008, 0.1), r=0.006)
        out.append(rigid(sdf_part(n + "_bib", bib, 0.004, col, ["Ticking"], decimate=0.5), "Spine"))
    if spec.get("overalls"):
        bib = Shape(blend=0.01)
        bib.box((0, front(1.2) - 0.012, 1.17), (0.12, 0.014, 0.13), r=0.01)
        bib.box((0, front(1.2) - 0.026, 1.18), (0.05, 0.004, 0.045), r=0.003)
        for s in (-1, 1):
            bib.capsule((s * 0.09, front(1.3) - 0.01, 1.29), (s * 0.1, -0.06, 1.47), 0.011)
            bib.capsule((s * 0.1, -0.06, 1.47), (s * 0.1, 0.06, 1.47), 0.011)
            bib.capsule((s * 0.1, 0.06, 1.47), (s * 0.07, 0.12 * g, 1.1), 0.011)
        out.append(rigid(sdf_part(n + "_bib", bib, 0.004, col, [spec["pants"]], decimate=0.4), "Spine"))
        for s in (-1, 1):
            out.append(bm_part(n + "_ovbtn", _sphere_bm(0.009, 12, 6), col, "GoldTrim", "Spine", (s * 0.09, front(1.3) - 0.02, 1.29)))
        out.append(bm_part(n + "_toolbelt", bm_cyl(0.175 * g, 0.045, 40), col, "Leather", "Hips", (0, 0.01, 0.96),
                           scale=(1, 0.72, 1)))
        out.append(bm_part(n + "_pouch", bm_box(0.08, 0.05, 0.1), col, "Leather", "Hips", (0.15 * g, -0.1, 0.9)))
        out.append(bm_part(n + "_wrench", bm_box(0.02, 0.01, 0.2), col, "Steel", "Hips", (0.15 * g, -0.13, 0.88)))
    if st in ("sweater", "tshirt") and not spec.get("overalls"):
        out.append(bm_part(n + "_belt", bm_cyl(0.17 * g, 0.04, 40), col, "Leather", "Hips", (0, 0.006, 1.045),
                           scale=(1, 0.72, 1)))
        out.append(bm_part(n + "_buckle", bm_box(0.05, 0.012, 0.04), col, "GoldTrim", "Hips", (0, -0.124 * g, 1.045)))
        for s in (-1, 1):  # cargo pockets
            out.append(bm_part(n + "_pocket", bm_box(0.03, 0.09, 0.12), col, spec["pants"], f"UpperLeg.{'L' if s > 0 else 'R'}",
                               (s * (0.092 + 0.08 * g), 0.0, 0.72)))
    # hats
    hat = spec.get("hat")
    if hat == "officer":
        crown = Shape(blend=0.01)
        crown.ellipsoid((0, 0.0, 1.818), (0.107, 0.12, 0.034))
        crown.box((0, 0, 1.7), (0.2, 0.2, 0.1), op="sub", k=0.0)
        out.append(rigid(sdf_part(n + "_capcrown", crown, 0.003, col, ["FabWhite"], decimate=0.4), "Head"))
        band = Shape(blend=0.004)
        band.ellipsoid((0, 0.008, 1.777), (0.088, 0.108, 0.03))
        out.append(rigid(sdf_part(n + "_capband", band, 0.003, col, ["FabNavy"], decimate=0.4), "Head"))
        vis = Shape(blend=0.0)
        vis.ellipsoid((0, -0.098, 1.758), (0.07, 0.048, 0.006), rot=Quaternion((1, 0, 0), R(-18)))
        out.append(rigid(sdf_part(n + "_visor", vis, 0.002, col, ["ShoeBlack"], decimate=0.5), "Head"))
        out.append(bm_part(n + "_badge", bm_box(0.03, 0.008, 0.025), col, "GoldTrim", "Head", (0, -0.106, 1.785)))
    elif hat == "beanie":
        bn = Shape(blend=0.01)
        bn.ellipsoid((0, 0.012, 1.728), (0.088, 0.109, 0.092))
        bn.box((0, 0, 1.6), (0.2, 0.2, 0.09), op="sub", k=0.0)
        bn.ellipsoid((0, 0.012, 1.705), (0.092, 0.113, 0.024), k=0.004)
        bn.sphere((0, 0.012, 1.83), 0.03, k=0.01)
        out.append(rigid(sdf_part(n + "_beanie", bn, 0.004, col, [spec["hat_m"]], decimate=0.4), "Head"))
    elif hat == "cookcap":
        cc = Shape(blend=0.012)
        cc.ellipsoid((0, 0.012, 1.79), (0.09, 0.11, 0.07))
        cc.box((0, 0, 1.66), (0.2, 0.2, 0.065), op="sub", k=0.0)
        cc.box((0, 0, 1.92), (0.2, 0.2, 0.08), op="sub", k=0.01)
        for k in range(14):
            a = 2 * math.pi * k / 14
            cc.capsule((math.cos(a) * 0.088, 0.012 + math.sin(a) * 0.108, 1.735), (math.cos(a) * 0.092, 0.012 + math.sin(a) * 0.112, 1.83),
                       0.008, k=0.006)
        out.append(rigid(sdf_part(n + "_cookcap", cc, 0.003, col, ["FabWhite"], decimate=0.4), "Head"))
    elif hat == "goggles":
        gg = Shape(blend=0.004)
        gg.ellipsoid((0, 0.012, 1.745), (0.086, 0.107, 0.012))
        out.append(rigid(sdf_part(n + "_strap", gg, 0.003, col, ["BlackPlastic"], decimate=0.4), "Head"))
        for s in (-1, 1):
            c = V((s * 0.033, -0.095, 1.75))
            out.append(bm_part(n + "_lensring", bm_torus(0.022, 0.007, 24, 8, "Y"), col, "Brass", "Head", c,
                               rot=Quaternion((1, 0, 0), R(-25))))
            out.append(bm_part(n + "_lens", bm_cyl(0.019, 0.004, 24, axis="Y"), col, "LensGlass", "Head", c + V((0, -0.003, 0.001)),
                               rot=Quaternion((1, 0, 0), R(-25))))
    if spec.get("glasses"):
        for s in (-1, 1):
            out.append(bm_part(n + "_rim", bm_torus(0.017, 0.0018, 24, 6, "Y"), col, "BlackPlastic", "Head", (s * 0.032, -0.1, 1.688)))
            out.append(bm_part(n + "_temple", bm_cyl(0.0016, 0.1, 6, axis="Y"), col, "BlackPlastic", "Head", (s * 0.072, -0.05, 1.69)))
        out.append(bm_part(n + "_bridge", bm_cyl(0.0016, 0.03, 6, axis="X"), col, "BlackPlastic", "Head", (0, -0.103, 1.692)))
    return out


def build_all(col=None):
    col = col or core.collection("Crew")
    return [build(spec, col) for spec in CREW]


# ------------------------------------------------------------------ posing

def _rot(arm, bone, axis, deg):
    pb = arm.pose.bones[bone]
    bpy.context.view_layer.update()
    head = pb.head.copy()
    pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(R(deg), 4, axis) @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


def curl(arm, side, amount=1.0, thumb=0.6, fingers=("Index", "Middle", "Ring", "Pinky")):
    """Curl fingers (0 = flat, 1 = fist). Works in any arm pose (rotates about each bone's local X)."""
    for f in fingers:
        for k in (1, 2, 3):
            pb = arm.pose.bones[f"{f}{k}.{side}"]
            pb.rotation_mode = "XYZ"
            pb.rotation_euler.x += R(70 if k == 1 else 85) * amount * (1 if side == "L" else 1)
    for k in (2, 3):
        pb = arm.pose.bones[f"Thumb{k}.{side}"]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler.x += R(40) * thumb
    bpy.context.view_layer.update()


def pose(arm, kind="relaxed"):
    for s, sd in ((1, "L"), (-1, "R")):
        if kind == "wave" and sd == "R":
            _rot(arm, f"UpperArm.{sd}", "Y", -35 * s)
            _rot(arm, f"LowerArm.{sd}", "Y", -80 * s)
            continue
        if kind == "operate":
            _rot(arm, f"UpperArm.{sd}", "Y", 72 * s)
            _rot(arm, f"UpperArm.{sd}", "Z", -22 * s)
            _rot(arm, f"UpperArm.{sd}", "X", -38)
            _rot(arm, f"LowerArm.{sd}", "X", -55)
            curl(arm, sd, 0.35, 0.3)
        else:
            _rot(arm, f"UpperArm.{sd}", "Y", 74 * s)
            _rot(arm, f"LowerArm.{sd}", "X", -14)
            curl(arm, sd, 0.3, 0.2)


def place_copy(src, col, loc, rot_z=0.0, kind="relaxed"):
    a = src.copy()
    col.objects.link(a)
    for ch in src.children:
        c = ch.copy()
        col.objects.link(c)
        c.parent = a
        for m in c.modifiers:
            if m.type == "ARMATURE":
                m.object = a
    a.location = loc
    a.rotation_euler = (0, 0, R(rot_z))
    bpy.context.view_layer.update()
    pose(a, kind)
    return a


# ------------------------------------------------------- first-person arms

def arm_sleeve_shape(s, b, sleeves="long", loose=1.0):
    L = limb(s)
    g = b["girth"]
    S = Shape(blend=0.03)
    S.capsule(L["shoulder"] - V((s * 0.04, 0, 0)), L["elbow"], 0.064 * g * loose, 0.05 * g * loose)
    if sleeves == "long":
        S.capsule(L["elbow"], L["wrist"] - V((s * 0.012, 0, 0)), 0.048 * g * loose, 0.039 * loose, k=0.02)
    else:
        S.box(L["shoulder"] + (L["elbow"] - L["shoulder"]) * 0.75, (0.25, 0.2, 0.2), op="sub", k=0.0)
    return S


def build_fp_arms(spec, col):
    """First-person arms (hands + sleeves) on the same 51-bone skeleton as the full character.

    Parent the armature to the game camera so the 'Head' bone sits at the camera; pose the hands
    onto a station's HAND_L / HAND_R targets with two-bone IK and curl fingers by hand_pose."""
    name = "FPArms_" + spec["name"].split("_", 1)[1]
    b = spec["build"]
    for sk in SKIN_SSS:
        sss(sk)
    skinned, rigid_parts = [], []
    gl = spec.get("gloves")
    short = spec["top_style"] == "tshirt"
    for s in (-1, 1):
        skinned.append(sdf_part(name + f"_hand{s}", hands_shape(s, bool(gl)), 0.0022, col, [gl or spec["skin"]], budget=3500))
        skinned.append(sdf_part(name + f"_sleeve{s}", arm_sleeve_shape(s, b, "short" if short else "long",
                                                                        1.06 if spec["top_style"] == "jacket" else 1.0),
                                0.005, col, [spec["top"]], budget=2500))
        if short:
            skinned.append(sdf_part(name + f"_forearm{s}", forearm_skin_shape(s, b["girth"]), 0.004, col, [spec["skin"]], budget=1500))
        if not gl:
            nails = sdf_part(name + f"_nails{s}", nails_shape(s), 0.0012, col, ["Nail"], budget=500)
            hp = hand_points(s)
            sd = "L" if s > 0 else "R"
            for f in hp:
                vg = nails.vertex_groups.new(name=f"{f}3.{sd}")
                vg.add([v.index for v in nails.data.vertices if (v.co - hp[f][0][3]).length < 0.02], 1.0, "REPLACE")
            rigid_parts.append(nails)
        L = limb(s)
        sd = "L" if s > 0 else "R"
        if spec["top_style"] == "jacket":
            rigid_parts.append(bm_part(name + "_cuff", core.bm_torus(0.041, 0.005, 24, 6, "X"), col, "GoldTrim",
                                       f"LowerArm.{sd}", L["wrist"] - V((s * 0.04, 0, 0))))
    arm = make_armature(name, col)
    arm["role"] = spec["role"]
    arm["first_person"] = True
    arm["eye_offset"] = [0.0, -0.08, 1.69]
    _auto_weight(skinned, arm)
    for o in rigid_parts:
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
    parts = [c for c in arm.children if c.type == "MESH"]
    me = bpy.data.meshes.new(name + "_Mesh")
    me.uv_layers.new(name="UVMap")
    body = bpy.data.objects.new(name + "_Mesh", me)
    col.objects.link(body)
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm
    with bpy.context.temp_override(active_object=body, object=body, selected_objects=parts + [body],
                                   selected_editable_objects=parts + [body]):
        bpy.ops.object.join()
    core.clean_slots(body.data)
    return arm
