"""Core helpers: scene, materials, mesh builders, the Prop system, export.

Conventions (metres, Z up in Blender; glTF export converts to Y up):
  * Every prop is a root Empty with its origin where it touches the floor/wall.
  * Static geometry is merged into one mesh "<Prop>_Body".
  * Anything a player can move (door, lever, knob, joystick, needle...) is its own
    mesh with its origin on the hinge/axis, named "<Prop>_<Part>", and carries
    custom properties (exported as glTF "extras") describing the motion.
  * Interaction points are Empties named "<Prop>_INTERACT_<what>".
"""

import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector

from . import tex

R = math.radians
SUB_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ------------------------------------------------------------------ scene

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()


def collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def layer_collection(name, lc=None):
    lc = lc or bpy.context.view_layer.layer_collection
    if lc.name == name:
        return lc
    for child in lc.children:
        found = layer_collection(name, child)
        if found:
            return found
    return None


# -------------------------------------------------------------- materials
# name: (base colour or texture, options)
MATLIB = {
    # walls / structure
    "WallCream": dict(tex="wall_cream", normal="wall_cream_n", tile=2.0, roughness=0.55),
    "WallTeal": dict(tex="wall_teal", normal="wall_teal_n", tile=2.0, roughness=0.5),
    "WallNavy": dict(tex="wall_navy", normal="wall_navy_n", tile=2.0, roughness=0.5),
    "FloorPlate": dict(tex="floor_diamond", normal="floor_diamond_n", tile=1.0, metallic=0.8, roughness=0.45),
    "FloorTiles": dict(tex="floor_tiles", normal="floor_tiles_n", tile=2.0, roughness=0.35),
    # painted metals
    "PaintTeal": dict(tex="paint_teal", normal="paint_peel_n", roughness=0.45, normal_strength=0.35),
    "PaintSeafoam": dict(tex="paint_seafoam", normal="paint_peel_n", roughness=0.45, normal_strength=0.35),
    "PaintCream": dict(tex="paint_cream", normal="paint_peel_n", roughness=0.5, normal_strength=0.35),
    "PaintMustard": dict(tex="paint_mustard", normal="paint_peel_n", roughness=0.45, normal_strength=0.35),
    "PaintRed": dict(tex="paint_red", normal="paint_peel_n", roughness=0.4, normal_strength=0.35),
    "PaintNavy": dict(tex="paint_navy", normal="paint_peel_n", roughness=0.45, normal_strength=0.35),
    "PaintGraphite": dict(tex="paint_graphite", normal="paint_peel_n", roughness=0.5, normal_strength=0.35),
    "PaintOlive": dict(tex="paint_olive", normal="paint_peel_n", roughness=0.5, normal_strength=0.35),
    "PaintWhite": dict(tex="paint_white", normal="paint_peel_n", roughness=0.4, normal_strength=0.35),
    "PaintGray": dict(tex="paint_gray", normal="paint_peel_n", roughness=0.45, normal_strength=0.35),
    "PaintEngine": dict(tex="paint_engine", normal="paint_peel_n", roughness=0.4, normal_strength=0.4),
    "PaintBattery": dict(tex="paint_battery", normal="paint_peel_n", roughness=0.35, normal_strength=0.3),
    "Lagging": dict(color="#d6d0c0", roughness=0.95),
    "FuelAmber": dict(color="#d98a1a", emission=("#ffa020", 1.2), roughness=0.1),
    "Lead": dict(color="#6e7276", metallic=0.6, roughness=0.5),
    "IVBag": dict(color="#cfe7f2", roughness=0.15, coat=0.8),
    "MattressWhite": dict(color="#eef0f2", roughness=0.85),
    # raw materials
    "Steel": dict(color="#9aa1a7", metallic=1.0, roughness=0.32),
    "DarkSteel": dict(color="#4a4f55", metallic=1.0, roughness=0.42),
    "Chrome": dict(color="#dfe3e6", metallic=1.0, roughness=0.12),
    "Brass": dict(color="#c9963f", metallic=1.0, roughness=0.28),
    "Copper": dict(color="#b8693d", metallic=1.0, roughness=0.3),
    "Stainless": dict(tex="steel_brushed", tile=1.0, metallic=1.0, roughness=0.28),
    "Rubber": dict(color="#1f2123", roughness=0.85),
    "BlackPlastic": dict(color="#1e2022", roughness=0.4),
    "Bakelite": dict(color="#3a2418", roughness=0.25, coat=0.6),
    "WhitePlastic": dict(color="#e8e6e0", roughness=0.35),
    "Glass": dict(color="#1a2a30", roughness=0.05, coat=1.0),
    "Wood": dict(tex="wood_planks", normal="wood_planks_n", tile=1.0, roughness=0.35, coat=0.5),
    "Hazard": dict(tex="hazard_stripes", tile=0.6, roughness=0.5),
    "Leather": dict(tex="leather_brown", tile=0.5, roughness=0.45, coat=0.3),
    "Ticking": dict(tex="fabric_ticking", tile=0.6, roughness=0.9),
    "Blanket": dict(tex="fabric_blanket", tile=1.0, roughness=0.95),
    "Curtain": dict(tex="fabric_curtain", tile=0.8, roughness=0.9),
    "Pillow": dict(color="#f1ede2", roughness=0.9),
    "Ceramic": dict(color="#f3efe6", roughness=0.15, coat=0.8),
    "EnamelBlue": dict(color="#2d5d8a", roughness=0.2, coat=1.0),
    "EnamelRed": dict(color="#c44130", roughness=0.2, coat=1.0),
    "EnamelCream": dict(color="#efe5c9", roughness=0.2, coat=1.0),
    "Coffee": dict(color="#2a160c", roughness=0.05),
    "TrayGreen": dict(color="#3f8a5a", roughness=0.4),
    "TrayBlue": dict(color="#3b6fa0", roughness=0.4),
    "CuttingBoard": dict(color="#e9e0cf", roughness=0.6),
    # food
    "MeatRaw": dict(tex="meat_raw", tile=0.3, roughness=0.35, coat=0.4),
    "MeatFat": dict(color="#f0d9cd", roughness=0.4),
    "MeatCooked": dict(tex="meat_cooked", tile=0.3, roughness=0.5),
    "ChickenSkin": dict(tex="chicken_skin", normal="chicken_skin_n", tile=0.25, roughness=0.35, coat=0.5),
    "Bone": dict(color="#efe6d2", roughness=0.5),
    "Bun": dict(color="#d4913f", roughness=0.5),
    # emissive
    "LightWarm": dict(color="#fff1d6", emission=("#fff1d6", 12.0)),
    "LightCool": dict(color="#e8f3ff", emission=("#e8f3ff", 10.0)),
    "LampRed": dict(color="#ff2a1a", emission=("#ff2a1a", 6.0), roughness=0.2),
    "LampGreen": dict(color="#38ff6a", emission=("#38ff6a", 5.0), roughness=0.2),
    "LampAmber": dict(color="#ffaa1a", emission=("#ffaa1a", 5.0), roughness=0.2),
    "LampBlue": dict(color="#3aa8ff", emission=("#3aa8ff", 5.0), roughness=0.2),
    "LampOff": dict(color="#4a2a28", roughness=0.2),
    "GrillGlow": dict(color="#ff6a1a", emission=("#ff5a10", 2.5), roughness=0.6),
}
SCREENS = ["screen_chart", "screen_nav_scope", "screen_sonar", "screen_fire_control", "screen_ballast",
           "screen_cam_fwd", "screen_cam_aft", "screen_target_id", "screen_periscope", "screen_status"]
DECALS = ["gauge_pressure", "gauge_depth", "gauge_air", "gauge_clock", "poster_dive", "poster_quiet",
          "poster_galley", "poster_crew", "sign_hot", "sign_voltage", "sign_explosive", "sign_pressure"]
MATS = {}


def _image(name, noncolor=False):
    img = bpy.data.images.get(name + ".png")
    if img is None:
        img = bpy.data.images.load(tex.path(name), check_existing=True)
        if noncolor:
            img.colorspace_settings.name = "Non-Color"
    return img


def mat(name):
    """Get (or lazily create) a material by library name.

    Unknown names starting with screen_/label_/gauge_/poster_/sign_ become
    image materials (screens are emissive)."""
    if name in MATS:
        return MATS[name]
    spec = MATLIB.get(name)
    if spec is None:
        if name.startswith("screen_"):
            spec = dict(color="#050505", emission_tex=name, emission_strength=1.6, roughness=0.08, coat=1.0)
        else:
            spec = dict(tex=name, roughness=0.6)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if "tex" in spec:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _image(spec["tex"])
        t.location = (-500, 300)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*tex.hex_rgb(spec.get("color", "#808080")) ** 2.2, 1)
    bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
    bsdf.inputs["Roughness"].default_value = spec.get("roughness", 0.5)
    bsdf.inputs["Coat Weight"].default_value = spec.get("coat", 0.0)
    if "normal" in spec:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _image(spec["normal"], noncolor=True)
        t.location = (-700, -200)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-300, -200)
        nm.inputs["Strength"].default_value = spec.get("normal_strength", 1.0)
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if "emission" in spec:
        c, s = spec["emission"]
        bsdf.inputs["Emission Color"].default_value = (*tex.hex_rgb(c) ** 2.2, 1)
        bsdf.inputs["Emission Strength"].default_value = s
    if "emission_tex" in spec:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _image(spec["emission_tex"])
        t.location = (-500, -500)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = spec["emission_strength"]
    m["tile"] = spec.get("tile", 1.0)
    MATS[name] = m
    return m


# ------------------------------------------------------------ uv mapping

def box_uv(me, tile=1.0):
    """World-scale box projection: consistent texel density for tiling textures."""
    if not len(me.polygons):
        return
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    nv, nl, npoly = len(me.vertices), len(me.loops), len(me.polygons)
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lv = np.empty(nl, np.int32)
    me.loops.foreach_get("vertex_index", lv)
    pn = np.empty(npoly * 3, np.float32)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3)
    lt = np.empty(npoly, np.int32)
    me.polygons.foreach_get("loop_total", lt)
    lp = np.repeat(np.arange(npoly), lt)
    n = pn[lp]
    p = co[lv]
    ax = np.argmax(np.abs(n), 1)
    u = np.where(ax == 0, p[:, 1] * np.sign(n[:, 0] + 1e-9), p[:, 0] * np.where(ax == 1, -np.sign(n[:, 1] + 1e-9), 1))
    v = np.where(ax == 2, p[:, 1], p[:, 2])
    uv.data.foreach_set("uv", (np.stack([u, v], 1) / tile).ravel())


# -------------------------------------------------------- bmesh builders

def bm_box(sx, sy, sz, center=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) + Vector(center)
    return bm


def _orient(bm, axis):
    if axis == "X":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(R(90), 3, "Y"))
    elif axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(R(-90), 3, "X"))


def bm_cyl(r, h, segs=24, r2=None, axis="Z", caps=True, center=(0, 0, 0)):
    """Cylinder/cone centred on origin along axis (length h)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    _orient(bm, axis)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center))
    return bm


def bm_sphere(r, segs=24, rings=12, scale=(1, 1, 1), center=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(center)
    return bm


def bm_lathe(profile, segs=32, axis="Z", closed=False, angle=2 * math.pi, center=(0, 0, 0)):
    """Revolve (radius, height) points around the axis. Radius 0 -> pole."""
    bm = bmesh.new()
    full = abs(angle - 2 * math.pi) < 1e-6
    n_ang = segs if full else segs + 1
    rings = []
    for r, z in profile:
        if r < 1e-7:
            v = bm.verts.new((0, 0, z))
            rings.append([v] * n_ang)
        else:
            rings.append([bm.verts.new((r * math.cos(angle * i / segs), r * math.sin(angle * i / segs), z))
                          for i in range(n_ang)])
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for a, b in pairs:
        for i in range(segs):
            j = (i + 1) % n_ang
            quad = list(dict.fromkeys([a[i], a[j], b[j], b[i]]))
            if len(quad) >= 3:
                try:
                    bm.faces.new(quad)
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _orient(bm, axis)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center))
    return bm


def bm_torus(R_, r, segs=32, rsegs=12, axis="Z", center=(0, 0, 0), angle=2 * math.pi):
    prof = [(R_ + r * math.cos(2 * math.pi * k / rsegs), r * math.sin(2 * math.pi * k / rsegs)) for k in range(rsegs)]
    return bm_lathe(prof, segs, axis, closed=True, angle=angle, center=center)


def circle(r, n=12, phase=0.0):
    return [(r * math.cos(2 * math.pi * k / n + phase), r * math.sin(2 * math.pi * k / n + phase)) for k in range(n)]


def rect(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def rrect(w, h, r, segs=4):
    """Rounded rectangle polygon (CCW) centred on origin."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in [(w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                       (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)]:
        for k in range(segs + 1):
            a = R(a0 + 90 * k / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rounded_path(points, radius, segs=6):
    """Fillet the corners of a polyline (quadratic bezier per corner)."""
    P = [Vector(p) for p in points]
    if len(P) < 3 or radius <= 0:
        return P
    out = [P[0]]
    for i in range(1, len(P) - 1):
        d1 = (P[i] - P[i - 1])
        d2 = (P[i + 1] - P[i])
        l1, l2 = d1.length, d2.length
        d1n, d2n = d1.normalized(), d2.normalized()
        if d1n.dot(d2n) > 0.999:
            out.append(P[i])
            continue
        phi = d1n.angle(d2n)
        t = min(radius * math.tan(phi / 2), l1 * 0.49, l2 * 0.49)
        A, B = P[i] - d1n * t, P[i] + d2n * t
        for k in range(segs + 1):
            s = k / segs
            out.append((1 - s) ** 2 * A + 2 * (1 - s) * s * P[i] + s * s * B)
    out.append(P[-1])
    return out


def sag_path(a, b, sag, n=16):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, k / n) - Vector((0, 0, sag * 4 * (k / n) * (1 - k / n))) for k in range(n + 1)]


def bm_sweep(path, section, caps=True, up=None, closed_path=False):
    """Sweep a closed 2D section along a 3D polyline with rotation-minimising frames."""
    bm = bmesh.new()
    P = [Vector(p) for p in path]
    n = len(P)
    T = []
    for i in range(n):
        if closed_path:
            t = (P[(i + 1) % n] - P[i]).normalized() + (P[i] - P[i - 1]).normalized()
        elif i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = (P[i + 1] - P[i]).normalized() + (P[i] - P[i - 1]).normalized()
        T.append(t.normalized())
    up = Vector(up) if up else (Vector((0, 0, 1)) if abs(T[0].z) < 0.95 else Vector((1, 0, 0)))
    N = (up - T[0] * up.dot(T[0])).normalized()
    rings = []
    for i in range(n):
        if i > 0:
            N = T[i - 1].rotation_difference(T[i]) @ N
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        rings.append([bm.verts.new(P[i] + N * u + B * v) for (u, v) in section])
    m = len(section)
    pairs = list(zip(rings, rings[1:]))
    if closed_path:
        pairs.append((rings[-1], rings[0]))
    for a, b in pairs:
        for j in range(m):
            k = (j + 1) % m
            bm.faces.new((a[j], a[k], b[k], b[j]))
    if caps and not closed_path:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_extrude(poly, depth, center_z=True):
    """2D polygon in XY extruded along Z."""
    bm = bmesh.new()
    z0 = -depth / 2 if center_z else 0.0
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z0 + depth)) for x, y in poly]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_plate_with_holes(outer, holes, depth):
    """Flat plate (XY outline) with polygon holes, extruded along Z (0..depth)."""
    bm = bmesh.new()
    edges = []
    for loop in [outer] + holes:
        vs = [bm.verts.new((x, y, 0)) for x, y in loop]
        edges += [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=True, edges=edges)
    for f in bm.faces:
        f.normal_update()
        if f.normal.z > 0:
            f.normal_flip()
    ret = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    vs = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=vs, vec=(0, 0, depth))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_quad(w, h):
    """Quad in the XZ plane facing -Y, UV 0..1 (for screens, signs, posters)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(c) for c in [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)]]
    f = bm.faces.new(vs)
    for loop, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop[uvl].uv = uv
    return bm


def bm_disc(r, segs=32):
    """Disc in XZ facing -Y with circular 0..1 UVs (gauge faces, clock)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new((r * math.cos(2 * math.pi * k / segs), 0, r * math.sin(2 * math.pi * k / segs))) for k in range(segs)]
    f = bm.faces.new(vs)
    f.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    for loop in f.loops:
        loop[uvl].uv = (loop.vert.co.x / (2 * r) + 0.5, loop.vert.co.z / (2 * r) + 0.5)
    return bm


def merge_bm(*bms):
    """Merge several bmeshes into one (consumes them)."""
    me = bpy.data.meshes.new("tmp")
    out = bmesh.new()
    for b in bms:
        b.to_mesh(me)
        out.from_mesh(me)
        b.free()
    bpy.data.meshes.remove(me)
    return out


# ------------------------------------------------------------- the Prop

def _bake(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def clean_slots(me):
    """Drop empty material slots (bpy join leaves one behind) and remap face indices."""
    mats = list(me.materials)
    keep = [i for i, m in enumerate(mats) if m is not None]
    if len(keep) == len(mats):
        return
    idx = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", idx)
    remap = np.zeros(max(len(mats), 1), np.int32)
    for new, old in enumerate(keep):
        remap[old] = new
    me.materials.clear()
    for i in keep:
        me.materials.append(mats[i])
    me.polygons.foreach_set("material_index", remap[np.clip(idx, 0, len(mats) - 1)])


class Prop:
    """Builds one game asset. Parts are merged per group when finish() is called."""

    def __init__(self, name, col=None, **extras):
        self.name = name
        self.col = col or collection("Library")
        self.root = bpy.data.objects.new(name, None)
        self.root.empty_display_size = 0.25
        for k, v in extras.items():
            self.root[k] = v
        self.col.objects.link(self.root)
        self.groups = []
        self.body = self._group("Body", self.root)

    # -- structure
    def _group(self, name, parent, loc=(0, 0, 0), rot=(0, 0, 0)):
        me = bpy.data.meshes.new(f"{self.name}_{name}")
        me.uv_layers.new(name="UVMap")
        g = bpy.data.objects.new(f"{self.name}_{name}", me)
        self.col.objects.link(g)
        g.parent = parent
        g.location = loc
        g.rotation_euler = [R(a) for a in rot]
        self.groups.append(g)
        return g

    def pivot(self, name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, **extras):
        """A movable part. Geometry added with parent=<pivot> is relative to the pivot point."""
        g = self._group(name, parent or self.root, loc, rot)
        for k, v in extras.items():
            g[k] = v
        return g

    def anchor(self, name, loc, rot=(0, 0, 0), parent=None, **extras):
        e = bpy.data.objects.new(f"{self.name}_INTERACT_{name}", None)
        e.empty_display_type = "SINGLE_ARROW"
        e.empty_display_size = 0.3
        self.col.objects.link(e)
        e.parent = parent or self.root
        e.location = loc
        e.rotation_euler = [R(a) for a in rot]
        e["interaction"] = name
        for k, v in extras.items():
            e[k] = v
        return e

    def use_camera(self, loc, target, lens=28, name="CAM_use", parent=None):
        """Zoomed first-person camera for using this station (exported as a glTF camera)."""
        cd = bpy.data.cameras.new(f"{self.name}_{name}")
        cd.lens = lens
        cd.clip_start = 0.02
        o = bpy.data.objects.new(f"{self.name}_{name}", cd)
        self.col.objects.link(o)
        o.parent = parent or self.root
        o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        o["interaction"] = "station_camera"
        return o

    def hand(self, side, loc, pose="grip", parent=None, control=None):
        """Hand target for first-person IK: where the hand goes and which finger pose it uses."""
        e = bpy.data.objects.new(f"{self.name}_HAND_{side}" + (f"_{control}" if control else ""), None)
        e.empty_display_type = "SPHERE"
        e.empty_display_size = 0.03
        self.col.objects.link(e)
        e.parent = parent or self.root
        e.location = loc
        e["interaction"] = "hand_target"
        e["hand"] = side
        e["hand_pose"] = pose
        if control:
            e["control"] = control
        return e

    def light(self, name, kind="POINT", energy=100, color="#fff1d6", loc=(0, 0, 0), rot=(0, 0, 0),
              radius=0.05, spot=60, parent=None):
        ld = bpy.data.lights.new(f"{self.name}_{name}", kind)
        ld.energy = energy
        ld.color = tuple(tex.hex_rgb(color) ** 2.2)
        ld.shadow_soft_size = radius
        if kind == "SPOT":
            ld.spot_size = R(spot)
            ld.spot_blend = 0.6
        o = bpy.data.objects.new(f"{self.name}_{name}", ld)
        self.col.objects.link(o)
        o.parent = parent or self.root
        o.location = loc
        o.rotation_euler = [R(a) for a in rot]
        return o

    # -- geometry
    def add(self, bm, m=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, bevel=0.0, segs=2,
            smooth=40, uv="box", name="part", scale=None):
        me = bpy.data.meshes.new(f"{self.name}_{name}")
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(f"{self.name}_{name}", me)
        self.col.objects.link(obj)
        obj.parent = parent or self.body
        obj.location = loc
        obj.rotation_euler = [R(a) for a in rot]
        if scale:
            me.transform(Matrix.Diagonal((*scale, 1)))
        mats = m if isinstance(m, (list, tuple)) else [m]
        for mm in mats:
            if mm:
                me.materials.append(mat(mm) if isinstance(mm, str) else mm)
        if smooth:
            me.shade_smooth()
            if smooth < 180:
                me.set_sharp_from_angle(angle=R(smooth))
        else:
            me.shade_flat()
        if bevel > 0:
            mod = obj.modifiers.new("Bevel", "BEVEL")
            mod.width = bevel
            mod.segments = segs
            mod.limit_method = "ANGLE"
            mod.angle_limit = R(35)
            mod.harden_normals = True
            mod.miter_outer = "MITER_ARC"
            _bake(obj)
        if uv == "box":
            ms = obj.data.materials
            tile = ms[0].get("tile", 1.0) if len(ms) and ms[0] else 1.0
            box_uv(obj.data, tile)
        elif not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
        obj["_part"] = True
        return obj

    # shorthand builders (sizes in metres, rotations in degrees)
    def box(self, size, loc, m, rot=(0, 0, 0), bevel=0.01, segs=2, parent=None, name="box"):
        return self.add(bm_box(*size), m, loc, rot, parent, bevel, segs, name=name)

    def cyl(self, r, h, loc, m, rot=(0, 0, 0), segs=24, r2=None, axis="Z", bevel=0.0, parent=None,
            caps=True, name="cyl", smooth=40):
        return self.add(bm_cyl(r, h, segs, r2, axis, caps), m, loc, rot, parent, bevel, name=name, smooth=smooth)

    def sphere(self, r, loc, m, scale=(1, 1, 1), segs=24, rings=12, parent=None, rot=(0, 0, 0), name="sphere"):
        return self.add(bm_sphere(r, segs, rings, scale), m, loc, rot, parent, smooth=180, name=name)

    def lathe(self, profile, loc, m, segs=32, axis="Z", rot=(0, 0, 0), parent=None, smooth=50, name="lathe", closed=False):
        return self.add(bm_lathe(profile, segs, axis, closed), m, loc, rot, parent, smooth=smooth, name=name)

    def torus(self, R_, r, loc, m, axis="Z", segs=32, rsegs=12, rot=(0, 0, 0), parent=None, name="torus"):
        return self.add(bm_torus(R_, r, segs, rsegs, axis), m, loc, rot, parent, smooth=180, name=name)

    def tube(self, path, r, m, segs=12, round_r=0.0, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), caps=True, name="tube"):
        pts = rounded_path(path, round_r) if round_r else path
        return self.add(bm_sweep(pts, circle(r, segs), caps), m, loc, rot, parent, smooth=70, name=name)

    def extrude(self, poly, depth, loc, m, rot=(0, 0, 0), bevel=0.0, segs=2, parent=None, name="extrude", smooth=40):
        return self.add(bm_extrude(poly, depth), m, loc, rot, parent, bevel, segs, name=name, smooth=smooth)

    def decal(self, w, h, loc, m, rot=(0, 0, 0), parent=None, name="decal"):
        """Textured quad facing -Y (rotate to orient)."""
        return self.add(bm_quad(w, h), m, loc, rot, parent, uv="keep", smooth=False, name=name)

    def plate(self, w, h, loc, label, rot=(0, 0, 0), parent=None, frame="PaintGraphite", depth=0.012):
        """A screwed-on label plate: thin bevelled backing + printed face."""
        self.box((w + 0.02, depth, h + 0.02), loc, frame, rot, bevel=0.004, parent=parent, name="plate")
        e = Euler([R(a) for a in rot])
        off = Vector((0, -depth / 2 - 0.0015, 0))
        off.rotate(e)
        self.decal(w, h, Vector(loc) + off, label, rot, parent, name="label")

    def screen(self, w, h, loc, image, rot=(0, 0, 0), parent=None, bezel=0.03, depth=0.04, frame="BlackPlastic"):
        """Recessed emissive screen with a bezel frame (faces -Y before rotation)."""
        e = Euler([R(a) for a in rot])
        outer = rrect(w + bezel * 2, h + bezel * 2, bezel * 1.2, 3)
        inner = rrect(w, h, bezel * 0.6, 3)
        bm = bm_plate_with_holes(outer, [inner], depth)
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
        self.add(bm, frame, loc, rot, parent, smooth=40, name="bezel")
        off = Vector((0, -depth * 0.45, 0))
        off.rotate(e)
        self.decal(w, h, Vector(loc) + off, image, rot, parent, name="screen")

    def bolts(self, positions, m="Steel", r=0.012, h=0.008, axis="Y", parent=None):
        for p in positions:
            self.cyl(r, h, p, m, axis=axis, segs=6, parent=parent, name="bolt")

    # -- done
    def finish(self):
        """Merge parts into their groups, drop empty groups, return the root."""
        for g in self.groups:
            parts = [c for c in g.children if c.get("_part")]
            if not parts:
                continue
            with bpy.context.temp_override(active_object=g, object=g, selected_objects=parts + [g],
                                           selected_editable_objects=parts + [g]):
                bpy.ops.object.join()
            clean_slots(g.data)
        for g in list(self.groups):
            if len(g.data.polygons) == 0 and not g.children:
                bpy.data.objects.remove(g)
        return self.root


# ------------------------------------------------------- placing / export

def hierarchy(root):
    return [root] + list(root.children_recursive)


def instance(root, col, loc=(0, 0, 0), rot=(0, 0, 0), name=None):
    """Copy a library prop (sharing mesh data) into a collection at a transform."""
    def rec(o, parent):
        c = o.copy()
        col.objects.link(c)
        c.parent = parent
        if parent is not None:
            c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        for ch in o.children:
            rec(ch, c)
        return c
    r = rec(root, None)
    r.location = loc
    r.rotation_euler = [R(a) for a in rot]
    if name:
        r.name = name
    return r


def select_only(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        try:
            o.select_set(True)
        except RuntimeError:
            pass


def export_glb(objs, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=filepath, export_format="GLB", use_selection=True, export_apply=True,
        export_extras=True, export_lights=True, export_cameras=True, export_yup=True,
        export_image_format="JPEG", export_image_quality=88)
