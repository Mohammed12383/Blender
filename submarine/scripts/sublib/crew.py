"""Four original, stylised crew characters with a humanoid skeleton.

Each character is one skinned mesh made of rigid parts (every part follows exactly one bone),
built in T-pose facing -Y. Bone names follow a common humanoid layout (Hips, Spine, Chest, Neck,
Head, Shoulder/UpperArm/LowerArm/Hand, UpperLeg/LowerLeg/Foot with .L/.R) so standard animation
sets can be retargeted onto them.
"""

import math

import bpy
import bmesh
from mathutils import Matrix, Vector

from . import core
from .core import R, bm_box, bm_cyl, bm_lathe, bm_sphere, bm_torus, bm_extrude, box_uv, mat, rrect

SH_Z = 1.37  # shoulder / arm height in T-pose

BONES = [  # name, head, tail, parent
    ("Hips", (0, 0, 0.93), (0, 0, 1.05), None),
    ("Spine", (0, 0, 1.05), (0, 0, 1.22), "Hips"),
    ("Chest", (0, 0, 1.22), (0, 0, 1.42), "Spine"),
    ("Neck", (0, 0, 1.42), (0, 0, 1.52), "Chest"),
    ("Head", (0, 0, 1.52), (0, 0, 1.85), "Neck"),
]
for s, side in ((1, "L"), (-1, "R")):
    BONES += [
        (f"Shoulder.{side}", (s * 0.05, 0, SH_Z), (s * 0.2, 0, SH_Z), "Chest"),
        (f"UpperArm.{side}", (s * 0.2, 0, SH_Z), (s * 0.48, 0, SH_Z), f"Shoulder.{side}"),
        (f"LowerArm.{side}", (s * 0.48, 0, SH_Z), (s * 0.73, 0, SH_Z), f"UpperArm.{side}"),
        (f"Hand.{side}", (s * 0.73, 0, SH_Z), (s * 0.9, 0, SH_Z), f"LowerArm.{side}"),
        (f"UpperLeg.{side}", (s * 0.1, 0, 0.93), (s * 0.1, 0, 0.5), "Hips"),
        (f"LowerLeg.{side}", (s * 0.1, 0, 0.5), (s * 0.1, 0, 0.1), f"UpperLeg.{side}"),
        (f"Foot.{side}", (s * 0.1, 0, 0.1), (s * 0.1, -0.16, 0.03), f"LowerLeg.{side}"),
    ]

CHAR_MATS = {
    "Skin1": dict(color="#f2c6a0", roughness=0.55), "Skin2": dict(color="#d39a6a", roughness=0.55),
    "Skin3": dict(color="#8f5b3a", roughness=0.55), "Skin4": dict(color="#ebb894", roughness=0.55),
    "HairBlack": dict(color="#211b17", roughness=0.6), "HairBrown": dict(color="#5a3a22", roughness=0.6),
    "HairGinger": dict(color="#c4592a", roughness=0.6), "HairGray": dict(color="#a7a29a", roughness=0.6),
    "ClothNavy": dict(color="#22324a", roughness=0.8), "ClothMustard": dict(color="#d99a2b", roughness=0.85),
    "ClothOlive": dict(color="#59633f", roughness=0.85), "ClothTeal": dict(color="#2b7479", roughness=0.8),
    "ClothWhite": dict(color="#eeece4", roughness=0.8), "ClothRed": dict(color="#c23b2b", roughness=0.8),
    "ClothCharcoal": dict(color="#34373c", roughness=0.85), "ClothKhaki": dict(color="#b49b6c", roughness=0.85),
    "BootBlack": dict(color="#1d1d20", roughness=0.35, coat=0.4), "BootBrown": dict(color="#5b3a24", roughness=0.45),
    "EyeWhite": dict(color="#f7f4ee", roughness=0.2), "Pupil": dict(color="#1b2430", roughness=0.1, coat=1.0),
    "Lips": dict(color="#9c4a44", roughness=0.4), "Gold": dict(color="#d9a441", metallic=1.0, roughness=0.3),
    "GlassLens": dict(color="#9fd3e0", roughness=0.05, coat=1.0),
    "ChefCheck": dict(tex="floor_tiles", tile=0.35, roughness=0.85),
}
core.MATLIB.update(CHAR_MATS)

CREW = [
    dict(name="Crew_Navigator", role="navigator", skin="Skin1", hair="HairGray", hair_style="short", beard=True,
         mustache=True, hat="officer", top="ClothNavy", sleeve="ClothNavy", pants="ClothNavy", shoes="BootBlack",
         coat=True, build=1.0),
    dict(name="Crew_Gunner", role="weapons_officer", skin="Skin3", hair="HairBlack", hair_style="short", hat="beanie",
         hat_color="ClothRed", top="ClothMustard", sleeve="ClothMustard", pants="ClothOlive", shoes="BootBlack",
         turtleneck=True, build=1.15, watch=True),
    dict(name="Crew_Loader", role="torpedo_loader", skin="Skin4", hair="HairGinger", hair_style="messy", hat="goggles",
         top="ClothWhite", sleeve="ClothWhite", short_sleeves=True, overalls="ClothTeal", pants="ClothTeal",
         gloves="ClothMustard", shoes="BootBrown", build=1.05),
    dict(name="Crew_Cook", role="cook", skin="Skin2", hair="HairBrown", hair_style="short", hat="cookcap",
         top="ClothWhite", sleeve="ClothWhite", pants="ChefCheck", shoes="BootBlack", apron=True, scarf="ClothTeal",
         glasses=True, chef_buttons=True, build=1.12, belly=1.15),
]


class Builder:
    def __init__(self, name, col):
        self.name = name
        self.col = col
        self.parts = []

    def add(self, bm, m, bone, loc=(0, 0, 0), rot=(0, 0, 0), smooth=180, scale=None):
        me = bpy.data.meshes.new(f"{self.name}_part")
        bm.to_mesh(me)
        bm.free()
        if scale:
            me.transform(Matrix.Diagonal((*scale, 1)))
        me.transform(Matrix.Translation(Vector(loc)) @ (Matrix.Rotation(R(rot[2]), 4, "Z") @ Matrix.Rotation(R(rot[1]), 4, "Y")
                                                        @ Matrix.Rotation(R(rot[0]), 4, "X")))
        me.materials.append(mat(m))
        if smooth:
            me.shade_smooth()
            if smooth < 180:
                me.set_sharp_from_angle(angle=R(smooth))
        box_uv(me, mat(m).get("tile", 1.0))
        o = bpy.data.objects.new(f"{self.name}_part", me)
        self.col.objects.link(o)
        vg = o.vertex_groups.new(name=bone)
        vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
        self.parts.append(o)
        return o

    def sphere(self, r, loc, m, bone, scale=(1, 1, 1), segs=24, rings=12):
        return self.add(bm_sphere(r, segs, rings, scale), m, bone, loc)

    def cyl(self, r, h, loc, m, bone, r2=None, axis="Z", segs=20, rot=(0, 0, 0)):
        return self.add(bm_cyl(r, h, segs, r2, axis), m, bone, loc, rot, smooth=50)

    def box(self, size, loc, m, bone, bevel=0.0, rot=(0, 0, 0)):
        bm = bm_box(*size)
        if bevel:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=3, profile=0.5, affect="EDGES",
                            clamp_overlap=True)
        return self.add(bm, m, bone, loc, rot, smooth=180 if bevel else False)


def _clipped_sphere(r, scale, keep):
    bm = bm_sphere(r, 32, 16, scale)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co)], context="VERTS")
    return bm


def build(spec, col):
    b = Builder(spec["name"], col)
    k = spec.get("build", 1.0)
    belly = spec.get("belly", 1.0)
    skin, top, sleeve, pants = spec["skin"], spec["top"], spec.get("sleeve", spec["top"]), spec["pants"]

    # ---- legs and feet
    for s, side in ((1, "L"), (-1, "R")):
        x = s * 0.1 * k
        b.cyl(0.072 * k, 0.46, (x, 0, 0.72), pants, f"UpperLeg.{side}", r2=0.09 * k)
        b.sphere(0.07 * k, (x, 0, 0.5), pants, f"LowerLeg.{side}")
        b.cyl(0.058 * k, 0.42, (x, 0, 0.3), pants, f"LowerLeg.{side}", r2=0.07 * k)
        b.cyl(0.07 * k, 0.2, (x, 0, 0.17), spec["shoes"], f"LowerLeg.{side}", r2=0.066 * k)
        b.box((0.13 * k, 0.28, 0.1), (x, -0.05, 0.05), spec["shoes"], f"Foot.{side}", bevel=0.04)
        b.box((0.135 * k, 0.29, 0.02), (x, -0.05, 0.01), "Rubber", f"Foot.{side}", bevel=0.008)

    # ---- hips, belt, torso
    b.box((0.36 * k, 0.24 * k, 0.2), (0, 0, 0.95), pants, "Hips", bevel=0.07)
    prof = [(0.0, 0.97), (0.17, 0.98), (0.19 * belly, 1.05), (0.205 * belly, 1.15), (0.215, 1.27), (0.218, 1.35),
            (0.19, 1.42), (0.12, 1.47), (0.06, 1.49), (0.0, 1.49)]
    b.add(bm_lathe(prof, 32), top, "Spine", scale=(k, 0.64 * k * (1.08 if belly > 1 else 1), 1))
    if not spec.get("overalls"):
        b.box((0.375 * k, 0.255 * k, 0.05), (0, 0, 1.03), "BootBrown" if not spec.get("coat") else "BootBlack", "Hips", bevel=0.02)
        b.box((0.06, 0.02, 0.045), (0, -0.13 * k, 1.03), "Gold", "Hips", bevel=0.006)

    # ---- outfits
    front = lambda z: -(0.205 * belly if z < 1.2 else 0.216) * 0.64 * k  # torso front surface (approx.)
    if spec.get("coat"):
        b.add(bm_lathe([(0.2 * k, 1.0), (0.215 * k, 0.88), (0.235 * k, 0.74), (0.23 * k, 0.73), (0.205 * k, 0.87), (0.188 * k, 1.0)], 32,
                       closed=True), top, "Hips", scale=(1, 0.72, 1))
        tri = bm_extrude([(-0.065, 0.0), (0.065, 0.0), (0.0, -0.15)], 0.012)
        b.add(tri, "ClothWhite", "Spine", loc=(0, front(1.35) + 0.004, 1.43), rot=(90, 0, 0))
        for side in (-1, 1):
            lap = bm_extrude([(0.0, 0.0), (side * 0.075, 0.0), (side * 0.11, -0.09), (side * 0.02, -0.17)], 0.014)
            b.add(lap, top, "Spine", loc=(0, front(1.35) - 0.002, 1.44), rot=(90, 0, 0))
            for zz in (1.27, 1.18, 1.09):
                b.sphere(0.012, (side * 0.06, front(zz) - 0.004, zz), spec.get("buttons", "Gold"), "Spine", segs=10, rings=6)
            b.box((0.13, 0.085, 0.02), (side * 0.17 * k, 0, 1.445), "Gold", "Spine", bevel=0.006)
            b.box((0.12, 0.075, 0.024), (side * 0.17 * k, 0, 1.448), top, "Spine", bevel=0.005)
    if spec.get("turtleneck"):
        b.add(bm_torus(0.068, 0.03, 24, 10), top, "Neck", loc=(0, 0, 1.475))
    if spec.get("overalls"):
        ov = spec["overalls"]
        b.box((0.37 * k, 0.26 * k, 0.12), (0, 0, 1.02), ov, "Hips", bevel=0.04)
        b.box((0.24, 0.03, 0.24), (0, front(1.2) - 0.006, 1.2), ov, "Spine", bevel=0.01)
        b.box((0.1, 0.012, 0.07), (0, front(1.2) - 0.024, 1.2), ov, "Spine", bevel=0.005)
        for side in (-1, 1):
            b.sphere(0.014, (side * 0.09, front(1.3) - 0.02, 1.3), "Gold", "Spine", segs=10, rings=6)
            strap = core.bm_sweep(core.rounded_path([Vector((side * 0.09, front(1.3) - 0.01, 1.3)),
                                                     Vector((side * 0.11, -0.1, 1.46)),
                                                     Vector((side * 0.11, 0.1, 1.46)),
                                                     Vector((side * 0.07, 0.13 * k, 1.1))], 0.05, 4),
                                  [(-0.022, -0.004), (0.022, -0.004), (0.022, 0.004), (-0.022, 0.004)], up=(1, 0, 0))
            b.add(strap, ov, "Spine", smooth=40)
        # tool belt with a wrench
        b.box((0.38 * k, 0.27 * k, 0.04), (0, 0, 0.97), "BootBrown", "Hips", bevel=0.015)
        b.box((0.08, 0.05, 0.1), (0.15 * k, -0.11 * k, 0.92), "BootBrown", "Hips", bevel=0.015)
        b.box((0.025, 0.012, 0.2), (0.15 * k, -0.14 * k, 0.9), "Steel", "Hips", bevel=0.004)
    if spec.get("apron"):
        ap = bm_extrude(rrect(0.36 * k, 0.66, 0.05, 4), 0.012)
        b.add(ap, "Ticking", "Hips", loc=(0, -0.155 * k * belly, 0.84), rot=(90, 0, 0), smooth=40)
        b.box((0.025, 0.008, 0.3), (0.11, front(1.3) - 0.008, 1.3), "Ticking", "Spine", rot=(0, 18, 0))
        b.box((0.025, 0.008, 0.3), (-0.11, front(1.3) - 0.008, 1.3), "Ticking", "Spine", rot=(0, -18, 0))
    if spec.get("chef_buttons"):
        for side in (-1, 1):
            for zz in (1.35, 1.27):
                b.sphere(0.011, (side * 0.07, front(zz) - 0.003, zz), "BlackPlastic", "Spine", segs=10, rings=6)
    if spec.get("scarf"):
        b.add(bm_torus(0.07, 0.022, 24, 8), spec["scarf"], "Neck", loc=(0, -0.005, 1.455))
        b.add(bm_extrude([(-0.04, 0.0), (0.04, 0.0), (0.0, -0.07)], 0.015), spec["scarf"], "Chest",
              loc=(0, -0.085, 1.45), rot=(90, 0, 0), smooth=40)

    # ---- arms (T-pose along ±X)
    for s, side in ((1, "L"), (-1, "R")):
        b.sphere(0.078 * k, (s * 0.21 * k, 0, SH_Z), sleeve, f"UpperArm.{side}")
        if spec.get("short_sleeves"):
            b.cyl(0.07 * k, 0.15, (s * 0.28, 0, SH_Z), sleeve, f"UpperArm.{side}", axis="X")
            b.cyl(0.054 * k, 0.24, (s * 0.37, 0, SH_Z), skin, f"UpperArm.{side}", axis="X")
            arm_m = skin
        else:
            b.cyl(0.064 * k, 0.28, (s * 0.35, 0, SH_Z), sleeve, f"UpperArm.{side}", axis="X")
            arm_m = sleeve
        b.sphere(0.056 * k, (s * 0.48, 0, SH_Z), arm_m, f"LowerArm.{side}")
        b.cyl(0.054 * k, 0.25, (s * 0.6, 0, SH_Z), arm_m, f"LowerArm.{side}", axis="X", r2=0.046 * k,
              rot=(0, 0, 0) if s > 0 else (0, 0, 180))
        if not spec.get("short_sleeves"):
            b.add(bm_torus(0.05 * k, 0.012, 20, 6, "X"), sleeve, f"LowerArm.{side}", loc=(s * 0.71, 0, SH_Z))
        if spec.get("watch") and s > 0:
            b.add(bm_torus(0.047 * k, 0.01, 20, 6, "X"), "BlackPlastic", f"LowerArm.{side}", loc=(s * 0.68, 0, SH_Z))
            b.cyl(0.02, 0.012, (s * 0.68, 0, SH_Z + 0.048), "Gold", f"LowerArm.{side}")
        hand = spec.get("gloves", skin)
        b.sphere(0.043 * k, (s * 0.735, 0, SH_Z), hand, f"Hand.{side}", segs=16, rings=8)
        b.box((0.115, 0.105, 0.055), (s * 0.795, 0, SH_Z), hand, f"Hand.{side}", bevel=0.022)
        for f in range(4):
            yy = -0.036 + f * 0.024
            b.cyl(0.0135, 0.08 - abs(f - 1.5) * 0.008, (s * 0.88, yy, SH_Z - 0.004), hand, f"Hand.{side}", axis="X")
        b.cyl(0.016, 0.07, (s * 0.79, -0.066, SH_Z - 0.004), hand, f"Hand.{side}", axis="X", rot=(0, 0, s * -50))

    # ---- neck and head
    b.cyl(0.056, 0.13, (0, 0.005, 1.5), skin, "Neck")
    hz = 1.665
    b.sphere(0.145, (0, 0, hz), skin, "Head", scale=(1, 0.95, 1.1), segs=32, rings=16)
    b.sphere(0.12, (0, -0.02, hz - 0.075), skin, "Head", scale=(1.05, 0.9, 0.8), segs=32, rings=16)
    for s in (-1, 1):
        b.sphere(0.04, (s * 0.145, 0.0, hz - 0.01), skin, "Head", scale=(0.45, 0.8, 1.0))
        b.sphere(0.026, (s * 0.055, -0.125, hz + 0.015), "EyeWhite", "Head", scale=(1, 0.6, 1.1), segs=16, rings=8)
        b.sphere(0.014, (s * 0.055, -0.139, hz + 0.013), "Pupil", "Head", segs=12, rings=6)
        b.box((0.06, 0.014, 0.014), (s * 0.057, -0.133, hz + 0.058), spec["hair"], "Head", bevel=0.005, rot=(0, s * 7, 0))
    b.sphere(0.032, (0, -0.148, hz - 0.025), skin, "Head", scale=(0.9, 1.0, 1.15))
    mouth_y = -0.146 if spec.get("beard") else -0.134
    mo = bm_torus(0.03, 0.006, 16, 6, "Y", angle=math.pi)
    b.add(mo, "Lips", "Head", loc=(0, mouth_y, hz - 0.068))  # lower half-ring = smile
    if spec.get("glasses"):
        for s in (-1, 1):
            b.add(bm_torus(0.032, 0.004, 24, 6, "Y"), "BlackPlastic", "Head", loc=(s * 0.056, -0.152, hz + 0.014))
            b.cyl(0.003, 0.13, (s * 0.12, -0.08, hz + 0.02), "BlackPlastic", "Head", axis="Y", segs=6)
        b.cyl(0.003, 0.04, (0, -0.155, hz + 0.02), "BlackPlastic", "Head", axis="X", segs=6)

    # ---- hair, beard
    style = spec.get("hair_style", "short")
    if style in ("short", "messy"):
        hair = _clipped_sphere(0.153, (1.03, 1.0, 1.1),
                               lambda c: c.z > -0.01 and not (c.y < -0.07 and c.z < 0.075))
        b.add(hair, spec["hair"], "Head", loc=(0, 0.012, hz + 0.01))
        if style == "messy":
            for k2, (x, y, z, rx) in enumerate([(0.05, -0.08, 0.15, 30), (-0.03, -0.1, 0.14, 40), (0.0, 0.0, 0.18, 0),
                                                (-0.08, -0.03, 0.15, 10), (0.08, 0.05, 0.14, -20)]):
                b.add(bm_cyl(0.035, 0.08, 10, 0.0), spec["hair"], "Head", loc=(x, y, hz + z), rot=(rx, k2 * 20 - 30, 0), smooth=40)
    if spec.get("beard"):
        beard = _clipped_sphere(0.128, (1.06, 0.95, 0.86), lambda c: c.z < 0.02 and c.y < 0.04)
        b.add(beard, spec["hair"], "Head", loc=(0, -0.02, hz - 0.07))
    if spec.get("mustache"):
        for s in (-1, 1):
            b.sphere(0.03, (s * 0.027, -0.15, hz - 0.052), spec["hair"], "Head", scale=(1.0, 0.45, 0.4), segs=12, rings=6)

    # ---- hats
    hat = spec.get("hat")
    if hat == "officer":
        b.cyl(0.158, 0.055, (0, 0.005, hz + 0.135), "ClothNavy", "Head", segs=32)
        b.add(bm_lathe([(0.15, 0.0), (0.19, 0.05), (0.192, 0.065), (0.17, 0.075), (0.0, 0.08)], 32), "ClothWhite", "Head",
              loc=(0, 0.005, hz + 0.16), smooth=60)
        visor = bm_lathe([(0.12, 0.0), (0.2, 0.0), (0.2, 0.012), (0.12, 0.012)], 24, closed=True, angle=math.pi)
        b.add(visor, "BootBlack", "Head", loc=(0, -0.02, hz + 0.105), rot=(14, 0, 180), smooth=50)
        b.box((0.04, 0.012, 0.03), (0, -0.155, hz + 0.14), "Gold", "Head", bevel=0.004)
        b.box((0.16, 0.012, 0.01), (0, -0.155, hz + 0.115), "Gold", "Head", bevel=0.003)
    elif hat == "beanie":
        cap = _clipped_sphere(0.162, (1.03, 1.0, 1.05), lambda c: c.z > 0.02)
        b.add(cap, spec["hat_color"], "Head", loc=(0, 0.01, hz + 0.03))
        b.add(bm_torus(0.158, 0.028, 32, 8), spec["hat_color"], "Head", loc=(0, 0.01, hz + 0.065), scale=(1.03, 1.0, 1.0))
        b.sphere(0.042, (0, 0.01, hz + 0.205), spec["hat_color"], "Head")
    elif hat == "goggles":
        b.add(bm_torus(0.155, 0.012, 32, 6), "BlackPlastic", "Head", loc=(0, 0.005, hz + 0.1), rot=(-12, 0, 0))
        for s in (-1, 1):
            b.cyl(0.04, 0.035, (s * 0.055, -0.14, hz + 0.115), "Brass", "Head", axis="Y", rot=(-15, 0, 0))
            b.cyl(0.032, 0.006, (s * 0.055, -0.16, hz + 0.12), "GlassLens", "Head", axis="Y", rot=(-15, 0, 0))
    elif hat == "cookcap":
        cap = bm_lathe([(0.155, 0.0), (0.162, 0.09), (0.1, 0.105), (0.0, 0.108)], 40)
        b.add(cap, "ClothWhite", "Head", loc=(0, 0.01, hz + 0.09), smooth=60)
        for a in range(12):
            ang = a * math.pi / 6
            b.box((0.012, 0.012, 0.085), (math.cos(ang) * 0.158, 0.01 + math.sin(ang) * 0.158, hz + 0.135), "ClothWhite",
                  "Head", bevel=0.004, rot=(0, 0, math.degrees(ang)))

    return _assemble(spec, col, b)


def _assemble(spec, col, b):
    name = spec["name"]
    me = bpy.data.meshes.new(name + "_Mesh")
    me.uv_layers.new(name="UVMap")
    body = bpy.data.objects.new(name + "_Mesh", me)
    col.objects.link(body)
    with bpy.context.temp_override(active_object=body, object=body, selected_objects=b.parts + [body],
                                   selected_editable_objects=b.parts + [body]):
        bpy.ops.object.join()
    core.clean_slots(body.data)
    # armature
    arm_data = bpy.data.armatures.new(name + "_Skeleton")
    arm = bpy.data.objects.new(name, arm_data)
    col.objects.link(arm)
    arm["role"] = spec["role"]
    arm["height_m"] = 1.86
    arm["character"] = True
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for bn, head, tail, parent in BONES:
        e = arm_data.edit_bones.new(bn)
        e.head, e.tail = head, tail
        e.roll = 0
        if parent:
            e.parent = eb[parent]
            e.use_connect = False
        eb[bn] = e
    bpy.ops.object.mode_set(mode="OBJECT")
    body.parent = arm
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return arm


def build_all(col=None):
    col = col or core.collection("Crew")
    return [build(spec, col) for spec in CREW]


# ------------------------------------------------------------------ posing

def _rot_bone(arm, bone, axis, deg):
    """Rotate a pose bone about a world axis through its head (armature space)."""
    pb = arm.pose.bones[bone]
    bpy.context.view_layer.update()
    head = pb.head.copy()
    m = Matrix.Translation(head) @ Matrix.Rotation(R(deg), 4, axis) @ Matrix.Translation(-head)
    pb.matrix = m @ pb.matrix
    bpy.context.view_layer.update()


def pose_relaxed(arm, wave=False, lean=0.0):
    """Arms down in a relaxed stance (for renders). Use reset_pose() before exporting."""
    for s, side in ((1, "L"), (-1, "R")):
        if wave and side == "R":
            _rot_bone(arm, f"UpperArm.{side}", "Y", -40 * s)   # raise
            _rot_bone(arm, f"LowerArm.{side}", "Y", -75 * s)   # bend the forearm up
            continue
        _rot_bone(arm, f"UpperArm.{side}", "Y", 72 * s)        # lower to the side
        _rot_bone(arm, f"LowerArm.{side}", "X", -12)           # slight bend forward
    if lean:
        _rot_bone(arm, "Spine", "X", lean)


def pose_operate(arm, reach=38, bend=55):
    """Both hands forward at waist/console height (working a station)."""
    for s, side in ((1, "L"), (-1, "R")):
        _rot_bone(arm, f"UpperArm.{side}", "Y", 72 * s)
        _rot_bone(arm, f"UpperArm.{side}", "Z", -22 * s)
        _rot_bone(arm, f"UpperArm.{side}", "X", -reach)
        _rot_bone(arm, f"LowerArm.{side}", "X", -bend)


def place_copy(src, col, loc, rot_z=0.0, pose="relaxed"):
    """Posed copy of a character (shares mesh + skeleton data) for renders."""
    a = src.copy()
    col.objects.link(a)
    for ch in src.children:
        c = ch.copy()
        col.objects.link(c)
        c.parent = a
        c.modifiers["Armature"].object = a
    a.location = loc
    a.rotation_euler = (0, 0, R(rot_z))
    bpy.context.view_layer.update()
    if pose == "wave":
        pose_relaxed(a, wave=True)
    elif pose == "operate":
        pose_operate(a)
    elif pose == "relaxed":
        pose_relaxed(a)
    return a


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
