"""Sea creatures (rigged, for procedural swim/attack animation), the enemy submarine,
and repair props (wrench, hull patch). Creatures face +X.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

from . import core, exterior
from .core import Prop, R, mat, box_uv
from .sdf import Shape
from .humans import sdf_part, rigid, _auto_weight

V = Vector

core.MATLIB.update({
    "SquidSkin": dict(color="#6b1f3a", roughness=0.35, coat=0.5),
    "SquidBelly": dict(color="#c98a92", roughness=0.4, coat=0.4),
    "CreatureEye": dict(color="#e8c22e", roughness=0.05, coat=1.0, emission=("#ffb400", 0.6)),
    "SharkSkin": dict(color="#5d6f7c", roughness=0.45, coat=0.2),
    "SharkBelly": dict(color="#e3e1d8", roughness=0.5),
    "HullCharcoal": dict(color="#2b2f33", roughness=0.5, coat=0.2),
    "HullRedStripe": dict(color="#9b2a22", roughness=0.5),
    "RubberRed": dict(color="#b53526", roughness=0.7),
})


def _rig(name, col, chains):
    """chains: list of (bone_prefix, [points], parent_bone or None). Returns armature."""
    ad = bpy.data.armatures.new(name + "_Skeleton")
    arm = bpy.data.objects.new(name, ad)
    col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for prefix, pts, parent in chains:
        prev = eb.get(parent)
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            bn = f"{prefix}{k + 1}" if len(pts) > 2 else prefix
            e = ad.edit_bones.new(bn)
            e.head, e.tail = V(a), V(b)
            if prev:
                e.parent = prev
            prev = e
            eb[bn] = e
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def _merge(name, arm, col, parts):
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
    return body


def giant_squid(col, name="GiantSquid"):
    """~13 m squid: mantle, fins, big glowing eyes, 8 arms with suckers and 2 clubbed tentacles."""
    S = Shape(blend=0.25)
    S.capsule((0.2, 0, 0), (-5.2, 0, 0.1), 1.05, 0.22)
    S.ellipsoid((-2.0, 0, 0.05), (2.7, 1.0, 0.95))
    S.ellipsoid((0.7, 0, 0), (0.95, 0.88, 0.82), k=0.3)
    for s in (-1, 1):
        S.ellipsoid((-4.6, s * 0.95, 0.1), (0.95, 1.1, 0.1), k=0.25)
        S.sphere((0.75, s * 0.7, 0.18), 0.36, op="sub", k=0.08)   # eye sockets
    chains = [("Mantle", [(0.0, 0, 0), (-2.5, 0, 0.05), (-5.2, 0, 0.1)], None)]
    arms = []
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        base = V((1.3, math.cos(a) * 0.48, math.sin(a) * 0.48))
        d = V((1.0, math.cos(a) * 0.35, math.sin(a) * 0.35)).normalized()
        pts, rad = [base], [0.26]
        for j in range(6):
            d = (d + V((0, math.cos(a) * 0.12, math.sin(a) * 0.12 - 0.04))).normalized()
            pts.append(pts[-1] + d * 0.72)
            rad.append(0.24 * (1 - (j + 1) / 7) + 0.035)
        S.chain(pts, rad, k=0.12)
        arms.append(pts)
        chains.append((f"Arm{k + 1}_", [p.copy() for p in pts], "Mantle1"))
    for s in (-1, 1):
        base = V((1.3, s * 0.2, -0.2))
        pts, rad = [base], [0.14]
        d = V((1, s * 0.08, -0.05)).normalized()
        for j in range(9):
            d = (d + V((0, s * 0.03, 0.02 * math.sin(j)))).normalized()
            pts.append(pts[-1] + d * 0.95)
            rad.append(0.1)
        S.chain(pts, rad, k=0.08)
        S.ellipsoid(pts[-1] + d * 0.35, (0.55, 0.22, 0.16), rot=V((1, 0, 0)).rotation_difference(d), k=0.12)
        chains.append((f"Tentacle{'L' if s > 0 else 'R'}_", [p.copy() for p in pts] + [pts[-1] + d * 0.8], "Mantle1"))
    body = sdf_part(name + "_body", S, 0.05, col, ["SquidSkin", "SquidBelly"], budget=16000)
    import numpy as np
    nz = np.array([p.normal.z for p in body.data.polygons])
    body.data.polygons.foreach_set("material_index", (nz < -0.35).astype(np.int32))
    parts = [body]
    eyes = []
    for s in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.3)
        me = bpy.data.meshes.new("eye")
        bm.to_mesh(me)
        bm.free()
        me.transform(Matrix.Translation((0.78, s * 0.64, 0.18)))
        o = bpy.data.objects.new(name + "_eye", me)
        col.objects.link(o)
        me.materials.append(mat("CreatureEye"))
        me.shade_smooth()
        eyes.append(rigid(o, "Mantle1"))
        pupil = bpy.data.meshes.new("pupil")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.12)
        bm.to_mesh(pupil)
        bm.free()
        pupil.transform(Matrix.Diagonal((1.6, 0.4, 0.8, 1)))
        pupil.transform(Matrix.Translation((0.82, s * 0.92, 0.18)))
        po = bpy.data.objects.new(name + "_pupil", pupil)
        col.objects.link(po)
        pupil.materials.append(mat("BlackPlastic"))
        eyes.append(rigid(po, "Mantle1"))
    # suckers along the underside of each arm
    sk = Shape(blend=0.0)
    for pts in arms:
        for j in range(1, 6):
            a, b = pts[j], pts[j + 1]
            c = (a + b) / 2
            inward = -V((0, c.y, c.z)).normalized() * 0.12
            sk.sphere(c + inward, 0.06 * (1 - j / 7))
    suck = sdf_part(name + "_suckers", sk, 0.025, col, ["SquidBelly"], budget=3000)
    arm = _rig(name, col, chains)
    arm["creature"] = "giant_squid"
    arm["note"] = "animate Arm*/Tentacle* bones with travelling sine waves; Mantle pulses for jet swimming"
    _auto_weight([body, suck], arm)
    for o in eyes:
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
    _merge(name, arm, col, [body, suck] + eyes)
    return arm


def shark(col, name="Shark"):
    """5 m shark with a 6-bone spine for tail-swish swimming."""
    S = Shape(blend=0.12)
    pts = [V((2.5, 0, 0.05)), V((1.6, 0, 0.0)), V((0.5, 0, 0.0)), V((-0.6, 0, 0.0)), V((-1.6, 0, 0.05)), V((-2.4, 0, 0.1))]
    S.chain(pts, [0.12, 0.42, 0.52, 0.42, 0.22, 0.09], k=0.25)
    S.ellipsoid((2.0, 0, -0.02), (0.75, 0.38, 0.3), k=0.2)
    S.ellipsoid((0.4, 0, 0.62), (0.45, 0.06, 0.55), rot=Quaternion((0, 1, 0), R(-25)), k=0.08)  # dorsal fin
    for s in (-1, 1):
        S.ellipsoid((0.95, s * 0.6, -0.28), (0.45, 0.6, 0.05), rot=Quaternion((1, 0, 0), R(s * -25)) @ Quaternion((0, 0, 1), R(s * 25)), k=0.1)
        for g in range(4):
            S.capsule((1.45 - g * 0.12, s * 0.39, 0.12), (1.45 - g * 0.12, s * 0.39, -0.12), 0.012, op="sub", k=0.01)
    S.ellipsoid((-2.75, 0, 0.55), (0.25, 0.05, 0.65), rot=Quaternion((0, 1, 0), R(-35)), k=0.1)   # caudal fin
    S.ellipsoid((-2.65, 0, -0.35), (0.2, 0.05, 0.4), rot=Quaternion((0, 1, 0), R(40)), k=0.1)
    S.ellipsoid((2.2, 0, -0.22), (0.35, 0.28, 0.04), op="sub", k=0.03)   # mouth line
    body = sdf_part(name + "_body", S, 0.025, col, ["SharkSkin", "SharkBelly"], budget=9000)
    import numpy as np
    nz = np.array([p.normal.z for p in body.data.polygons])
    cz = np.array([p.center.z for p in body.data.polygons])
    body.data.polygons.foreach_set("material_index", ((nz < -0.2) & (cz < 0.05)).astype(np.int32))
    eyes = []
    for s in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.05)
        me = bpy.data.meshes.new("eye")
        bm.to_mesh(me)
        bm.free()
        me.transform(Matrix.Translation((2.2, s * 0.27, 0.12)))
        o = bpy.data.objects.new(name + "_eye", me)
        col.objects.link(o)
        me.materials.append(mat("BlackPlastic"))
        me.shade_smooth()
        eyes.append(o)
    arm = _rig(name, col, [("Spine", [V((2.6, 0, 0.05))] + pts[1:] + [V((-2.9, 0, 0.1))], None)])
    arm["creature"] = "shark"
    _auto_weight([body], arm)
    for o in eyes:
        rigid(o, "Spine1")
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
    _merge(name, arm, col, [body] + eyes)
    return arm


def enemy_submarine():
    """Charcoal hull with a red stripe; same layout as ours."""
    root = exterior.submarine("EnemySubmarine")
    root["team"] = "enemy"
    root["target_type"] = "submarine"
    root["hit_points"] = 3
    swap = {"HullTeal": "HullCharcoal", "AntiFoul": "HullRedStripe", "DeckGreen": "PaintGraphite"}
    for o in core.hierarchy(root):
        if o.type == "MESH":
            for i, m in enumerate(o.data.materials):
                if m and m.name in swap:
                    o.data.materials[i] = mat(swap[m.name])
    return root


def wrench(name="Wrench"):
    """Large adjustable wrench (pickup used to fix leaks)."""
    p = Prop(name, category="pickup", interact="pickup", item="wrench")
    p.add(core.bm_extrude(core.rrect(0.32, 0.034, 0.016, 4), 0.016), "Steel", (-0.05, 0, 0), (90, 0, 0), bevel=0.003)
    p.add(core.bm_extrude(core.rrect(0.2, 0.044, 0.02, 4), 0.026), "RubberRed", (-0.11, 0, 0), (90, 0, 0), bevel=0.004)
    head = core.bm_extrude([(0.0, -0.035), (0.07, -0.04), (0.11, -0.01), (0.11, 0.06), (0.085, 0.06), (0.085, 0.015),
                            (0.04, 0.015), (0.03, 0.035), (0.0, 0.035)], 0.02)
    p.add(head, "Steel", (0.1, 0, 0), (90, 0, 0), bevel=0.003, name="head")
    jaw = p.pivot("Jaw", (0.17, 0, 0.03), interact="adjust", translate_axis="X")
    p.box((0.025, 0.02, 0.05), (0, 0, 0), "Steel", parent=jaw, bevel=0.003)
    p.cyl(0.012, 0.03, (0.13, 0, -0.005), "DarkSteel", axis="Y", segs=12)
    for k in range(6):
        p.box((0.002, 0.024, 0.026), (0.12 + k * 0.004, 0, -0.005), "Steel", bevel=0)
    p.anchor("grip", (-0.12, 0, 0))
    return p.finish()


def leak_patch(name="HullPatch"):
    """Bolted repair patch that appears where a leak was fixed (flat on the wall, facing -Y)."""
    p = Prop(name, category="decor", note="spawned by the game after a repair")
    p.cyl(0.16, 0.012, (0, -0.006, 0), "DarkSteel", axis="Y", segs=32, bevel=0.003)
    p.cyl(0.13, 0.008, (0, -0.014, 0), "Steel", axis="Y", segs=32, bevel=0.002)
    for k in range(8):
        a = k * math.pi / 4
        p.cyl(0.012, 0.012, (math.cos(a) * 0.135, -0.018, math.sin(a) * 0.135), "Brass", axis="Y", segs=6)
    p.add(core.bm_torus(0.16, 0.006, 32, 6, "Y"), "Rubber", (0, -0.004, 0), smooth=180)
    return p.finish()


def leak_crack(name="HullCrack"):
    """Torn, bent plate where water sprays in (spawned by the game at a leak point, facing -Y)."""
    p = Prop(name, category="decor", note="spawned by the game at a leak; emit spray along -Y")
    import random
    rnd = random.Random(2)
    for k in range(7):
        a = k * 2 * math.pi / 7 + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(0.07, 0.14)
        shard = core.bm_extrude([(0, -0.015), (L, -0.004), (L * 1.05, 0.004), (0, 0.015)], 0.006)
        bmesh.ops.rotate(shard, verts=shard.verts, matrix=Matrix.Rotation(R(-60), 3, "Y"))
        bmesh.ops.rotate(shard, verts=shard.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
        bmesh.ops.rotate(shard, verts=shard.verts, matrix=Matrix.Rotation(a, 3, "Y"))
        p.add(shard, "PaintCream", (0, -0.005, 0), bevel=0.001, name="shard")
    p.cyl(0.035, 0.01, (0, 0.0, 0), "BlackPlastic", axis="Y", segs=16)
    p.anchor("spray", (0, -0.03, 0), rot=(90, 0, 0))
    return p.finish()
