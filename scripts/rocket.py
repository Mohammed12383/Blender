"""Build a stylised toy rocket on a launch pad, then save, export and render it.

Run from the repository root:
    python scripts/rocket.py            # full-quality render
    python scripts/rocket.py --preview  # fast, low-sample render

Outputs:
    models/rocket.blend  - full scene (rocket, pad, backdrop, lights, camera)
    models/rocket.glb    - rocket + pad only, for game engines / web viewers
    renders/rocket.png   - rendered image
"""

import math
import os
import sys

import bpy  # must come before bmesh/mathutils when bpy is used as a pip module
import bmesh
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEW = "--preview" in sys.argv


# ---------------------------------------------------------------- helpers

def srgb(hex_str):
    """'#RRGGBB' (sRGB) -> linear RGBA, which is what Blender materials expect."""
    h = hex_str.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material(name, color, metallic=0.0, roughness=0.5, coat=0.0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = coat
    if emission:
        bsdf.inputs["Emission Color"].default_value = srgb(emission[0])
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


def new_object(name, mesh, mat=None, collection=None, smooth=True):
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    return obj


def lathe(name, profile, segments=96):
    """Revolve a list of (radius, z) points around the Z axis into a mesh.

    Points with radius 0 collapse to a single pole vertex, so closed ends
    (bottom caps, nose tips) come out as clean triangle fans.
    """
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))] * segments)
        else:
            rings.append([
                bm.verts.new((r * math.cos(2 * math.pi * i / segments),
                              r * math.sin(2 * math.pi * i / segments), z))
                for i in range(segments)
            ])
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            quad = [a[i], a[j], b[j], b[i]]
            unique = list(dict.fromkeys(quad))  # drop repeated pole verts
            if len(unique) >= 3:
                bm.faces.new(unique)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def polygon_mesh(name, points_xz):
    """A single flat face in the XZ plane (used for fin outlines)."""
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0, z)) for x, z in points_xz]
    bm.faces.new(verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def add_modifier(obj, kind, **props):
    mod = obj.modifiers.new(kind.title(), kind)
    for key, value in props.items():
        setattr(mod, key, value)
    return mod


# ------------------------------------------------------------------- scene

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

rocket_col = bpy.data.collections.new("Rocket")
set_col = bpy.data.collections.new("Set")
scene.collection.children.link(rocket_col)
scene.collection.children.link(set_col)

WHITE = material("Hull White", "#f2efe9", roughness=0.35, coat=0.6)
RED = material("Rocket Red", "#e01a2f", roughness=0.3, coat=0.8)
METAL = material("Brushed Metal", "#b8bcc2", metallic=1.0, roughness=0.28)
DARK_METAL = material("Nozzle Metal", "#3a3d42", metallic=1.0, roughness=0.4)
GLASS = material("Window Glass", "#1b3a5c", roughness=0.05, coat=1.0)
CONCRETE = material("Pad Concrete", "#8d9095", roughness=0.8)
STRIPE = material("Hazard Yellow", "#f2c12e", roughness=0.5)
BACKDROP = material("Backdrop", "#9cc5e6", roughness=0.9)

# Camera direction (azimuth in the XY plane, measured from +X).
CAM_DIST, CAM_HEIGHT, CAM_AZ = 10.0, 2.6, math.radians(-62)
FACE = CAM_AZ + math.radians(14)  # window turned slightly off-axis for a 3/4 look

# --- hull: egg-shaped body with a closed, rounded bottom
def hull_radius(z):
    return 0.60 - 0.14 * ((z - 1.25) / 0.9) ** 2

BODY_BOTTOM, BODY_TOP = 0.35, 2.2
body_profile = [(0.0, 0.30), (0.26, 0.305), (0.40, 0.325)]
steps = 40
for k in range(steps + 1):
    z = BODY_BOTTOM + (BODY_TOP - BODY_BOTTOM) * k / steps
    body_profile.append((hull_radius(z), z))
body = new_object("Hull", lathe("Hull", body_profile), WHITE, rocket_col)

# --- nose cone: rounded ogive sitting on the hull
R_TOP, NOSE_LEN = hull_radius(BODY_TOP), 1.05
nose_profile = [(0.0, BODY_TOP - 0.02), (R_TOP - 0.01, BODY_TOP - 0.02)]
for k in range(41):
    u = k / 40
    nose_profile.append((R_TOP * (1 - u ** 2) ** 0.55, BODY_TOP + NOSE_LEN * u))
new_object("Nose Cone", lathe("Nose Cone", nose_profile), RED, rocket_col)

# --- trim rings: metal seam under the nose, red band near the base
seam = bpy.data.meshes.new("Seam Ring")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=96, radius1=R_TOP + 0.018,
                      radius2=R_TOP + 0.018, depth=0.07)
bm.to_mesh(seam); bm.free()
seam_obj = new_object("Seam Ring", seam, METAL, rocket_col)
seam_obj.location.z = BODY_TOP
add_modifier(seam_obj, "SOLIDIFY", thickness=0.03, offset=1.0)
add_modifier(seam_obj, "BEVEL", width=0.008, segments=2)

band_profile = []
for k in range(13):
    z = 0.62 + 0.18 * k / 12
    band_profile.append((hull_radius(z) + 0.012, z))
band = new_object("Red Band", lathe("Red Band", band_profile), RED, rocket_col)
add_modifier(band, "SOLIDIFY", thickness=0.012, offset=-1.0)

# --- engine bell (thin shell)
nozzle_profile = [(0.20, 0.40), (0.22, 0.31), (0.27, 0.20), (0.34, 0.11), (0.38, 0.07)]
nozzle = new_object("Engine Bell", lathe("Engine Bell", nozzle_profile), DARK_METAL, rocket_col)
add_modifier(nozzle, "SOLIDIFY", thickness=0.025, offset=0.0)
add_modifier(nozzle, "SUBSURF", levels=1, render_levels=2)

# --- porthole: metal rim + domed glass, facing the camera
WIN_Z = 1.5
win_r = hull_radius(WIN_Z)
direction = Vector((math.cos(FACE), math.sin(FACE), 0))
bpy.ops.mesh.primitive_torus_add(major_radius=0.19, minor_radius=0.04,
                                 major_segments=64, minor_segments=16)
rim = bpy.context.object
rim.name = "Porthole Rim"
rim.data.materials.append(METAL)
for poly in rim.data.polygons:
    poly.use_smooth = True
bpy.context.scene.collection.objects.unlink(rim)
rocket_col.objects.link(rim)
rim.location = direction * (win_r - 0.015) + Vector((0, 0, WIN_Z))
rim.rotation_euler = (math.radians(90), 0, FACE + math.radians(90))

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24)
glass = bpy.context.object
glass.name = "Porthole Glass"
glass.data.materials.append(GLASS)
for poly in glass.data.polygons:
    poly.use_smooth = True
bpy.context.scene.collection.objects.unlink(glass)
rocket_col.objects.link(glass)
glass.location = direction * (win_r - 0.03) + Vector((0, 0, WIN_Z))
glass.scale = (0.17, 0.06, 0.17)
glass.rotation_euler = (0, 0, FACE + math.radians(90))

# --- fins: swept outline, thickened and bevelled, arrayed around the hull
fin_outline = [(0.38, 1.12), (0.38, 0.34), (0.90, 0.02), (1.06, 0.0),
               (1.08, 0.14), (0.98, 0.42), (0.72, 0.78)]
for i, offset in enumerate((60, 180, 300)):
    fin = new_object(f"Fin {i + 1}", polygon_mesh(f"Fin {i + 1}", fin_outline),
                     RED, rocket_col, smooth=False)
    fin.rotation_euler.z = FACE + math.radians(offset)
    add_modifier(fin, "SOLIDIFY", thickness=0.07, offset=0.0)
    add_modifier(fin, "BEVEL", width=0.025, segments=3, limit_method='ANGLE')
    add_modifier(fin, "WEIGHTED_NORMAL", keep_sharp=True)

# --- launch pad with a hazard stripe
pad_mesh = lathe("Launch Pad", [(0.0, 0.0), (1.55, 0.0), (1.62, -0.04),
                                (1.65, -0.14), (1.80, -0.20), (0.0, -0.20)])
pad = new_object("Launch Pad", pad_mesh, CONCRETE, set_col)
stripe = new_object("Pad Stripe", lathe("Pad Stripe", [(1.25, 0.004), (1.40, 0.004)]),
                    STRIPE, set_col)

# --- cyclorama backdrop (floor curving up into a wall, no visible horizon)
cyc = bmesh.new()
section = [(-14.0, 0.0), (2.5, 0.0)]
for k in range(1, 17):
    a = math.radians(90 * k / 16)
    section.append((2.5 + 4 * math.sin(a), 4 - 4 * math.cos(a)))
section.append((6.5, 14.0))
cols = []
for x in (-16.0, 16.0):
    cols.append([cyc.verts.new((x, y, z - 0.2)) for y, z in section])
for k in range(len(section) - 1):
    cyc.faces.new((cols[0][k], cols[1][k], cols[1][k + 1], cols[0][k + 1]))
cyc_mesh = bpy.data.meshes.new("Backdrop")
cyc.to_mesh(cyc_mesh)
cyc.free()
backdrop = new_object("Backdrop", cyc_mesh, BACKDROP, set_col)
backdrop.rotation_euler.z = CAM_AZ + math.radians(90)  # wall faces the camera

# ------------------------------------------------------- lights and camera

def area_light(name, power, size, loc, color="#ffffff"):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.size, data.color = power, size, srgb(color)[:3]
    obj = bpy.data.objects.new(name, data)
    set_col.objects.link(obj)
    obj.location = loc
    track = obj.constraints.new('TRACK_TO')
    track.target = target
    return obj

target = bpy.data.objects.new("Camera Target", None)
target.location = (0, 0, 1.45)
set_col.objects.link(target)

def around(az_deg, dist, height):
    a = CAM_AZ + math.radians(az_deg)
    return (dist * math.cos(a), dist * math.sin(a), height)

area_light("Key", 1400, 4.0, around(-45, 6.5, 5.5), "#fff4e6")
area_light("Fill", 350, 6.0, around(70, 7.0, 2.5), "#e6f0ff")
area_light("Rim", 900, 2.5, around(165, 5.0, 5.0), "#ffffff")

world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = srgb("#c9dcec")
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
scene.world = world

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 68
cam_data.dof.use_dof = True
cam_data.dof.focus_object = target
cam_data.dof.aperture_fstop = 5.6
camera = bpy.data.objects.new("Camera", cam_data)
set_col.objects.link(camera)
camera.location = around(0, CAM_DIST, CAM_HEIGHT)
track = camera.constraints.new('TRACK_TO')
track.target = target
scene.camera = camera

# ------------------------------------------------------------ render setup

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24 if PREVIEW else 192
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1080, 1350
scene.render.resolution_percentage = 50 if PREVIEW else 100
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Punchy'

# ----------------------------------------------------------------- outputs

blend_path = os.path.join(ROOT, "models", "rocket.blend")
glb_path = os.path.join(ROOT, "models", "rocket.glb")
png_path = os.path.join(ROOT, "renders", "rocket_preview.png" if PREVIEW else "rocket.png")
for p in (blend_path, glb_path, png_path):
    os.makedirs(os.path.dirname(p), exist_ok=True)

bpy.ops.wm.save_as_mainfile(filepath=blend_path)

bpy.ops.object.select_all(action='DESELECT')
for obj in list(rocket_col.objects) + [pad, stripe]:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
                          use_selection=True, export_apply=True)

scene.render.filepath = png_path
bpy.ops.render.render(write_still=True)
print(f"Saved:\n  {blend_path}\n  {glb_path}\n  {png_path}")
