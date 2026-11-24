"""Reusable prop builders (continents, glow materials, arrows, rocks, trees...). All in clay-toy style."""
import math
import random

import bmesh
import bpy

from . import kit
from .kit import V, box, capsule, cone, cyl, empty, hexc, ico, mat, sphere, torus, curve

R = math.radians


def glow(color="#ffb347", strength=6.0, alpha=1.0, name="Glow"):
    """Pure emission (optionally see-through) material, for suns, lava, magic and halos."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = hexc(color)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if alpha < 1:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs["Fac"].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def poly_slab(pts, scale=0.1, thick=0.35, m=None, bevel=0.05, name="slab", color="#6bbf59"):
    """Extruded polygon (concave ok) with its origin at the centroid. pts in (lon, lat) degrees."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    bm = bmesh.new()
    vs = [bm.verts.new(((x - cx) * scale, (y - cy) * scale, 0)) for x, y in pts]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    s = o.modifiers.new("solid", "SOLIDIFY")
    s.thickness = thick
    s.offset = 0
    b = o.modifiers.new("bev", "BEVEL")
    b.width = bevel
    b.segments = 3
    b.limit_method = "ANGLE"
    o.data.materials.append(m or mat(color, 0.5))
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    o.location = (cx * scale, cy * scale, thick / 2)
    return o, (cx, cy)


def arrow(start, end, color="#ff3b3b", r=0.07, head=0.22, m=None):
    """3D arrow from start to end (tuples)."""
    s, e = V(start), V(end)
    d = e - s
    L = d.length
    mt = m or mat(color, 0.35)
    root = empty("arrow", s)
    shaft = cyl(r, L - head, (0, 0, (L - head) / 2), mt, seg=16)
    shaft.parent = root
    tip = cone(r * 2.6, 0.0, head, (0, 0, L - head / 2), mt, seg=24)
    tip.parent = root
    root.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return root


def rock(r=0.5, loc=(0, 0, 0), color="#8b8f98", seed=1, squash=0.8, rough=0.7, bump=0.35):
    random.seed(seed)
    o = ico(r, loc, mat(color, rough, sss=0.02, coat=0), sub=3, scale=(1, 1, squash))
    d = o.modifiers.new("disp", "DISPLACE")
    t = bpy.data.textures.new(f"rk{seed}", "CLOUDS")
    t.noise_scale = 0.9
    d.texture = t
    d.strength = bump * r
    d.mid_level = 0.5
    o.rotation_euler = (random.random() * 3, random.random() * 3, random.random() * 3)
    return o


def tree_palm(loc=(0, 0, 0), h=1.6, lean=8, scale=1.0, leaf="#3fae4b"):
    root = empty("palm", loc)
    trunk = mat("#8a5a34", 0.7, coat=0)
    segs = 6
    for i in range(segs):
        t = i / segs
        o = cyl(0.11 * (1 - t * 0.35), h / segs * 1.15, (math.sin(R(lean)) * t * h * 0.6, 0, t * h + h / segs / 2), trunk, seg=16)
        o.rotation_euler = (0, R(lean * t * 0.9), 0)
        o.parent = root
    top = (math.sin(R(lean)) * 0.6 * h, 0, h)
    lm = mat(leaf, 0.6, sss=0.1, coat=0)
    for k in range(7):
        a = k / 7 * math.tau
        l = sphere(0.1, (top[0] + math.cos(a) * 0.35, top[1] + math.sin(a) * 0.35, top[2] - 0.05), lm, scale=(4.5, 1.0, 0.35), seg=20, rings=10)
        l.rotation_euler = (0, R(-18), a)
        l.parent = root
    for k in range(2):
        c = sphere(0.1, (top[0] + (k - 0.5) * 0.12, top[1] - 0.08, top[2] - 0.12), mat("#6b3f1d", 0.6), seg=16, rings=8)
        c.parent = root
    root.scale = (scale,) * 3
    return root


def cloud(loc=(0, 0, 0), s=1.0, color="#ffffff"):
    root = empty("cloud", loc)
    m = mat(color, 0.9, sss=0.2, coat=0)
    for x, z, r in ((-0.5, 0, 0.35), (0, 0.12, 0.45), (0.5, 0, 0.35), (0.15, -0.05, 0.4)):
        sphere(r * s, (x * s, 0, z * s), m, scale=(1, 0.8, 0.8), seg=24, rings=12).parent = root
    return root


def thermometer(loc=(0, 0, 0), fill=0.8, color="#ff3030"):
    root = empty("thermo", loc)
    glass = mat("#e9f4ff", 0.15, alpha=0.4, glass=False, sss=0, coat=0.6)
    tube = capsule(0.16, 1.5, (0, 0, 0.9), glass)
    tube.parent = root
    bulb = sphere(0.34, (0, 0, 0), glass, seg=32, rings=16)
    bulb.parent = root
    liq = mat(color, 0.25, emit=color, emit_strength=0.5, sss=0, coat=0.4)
    b2 = sphere(0.26, (0, 0, 0), liq, seg=32, rings=16)
    b2.parent = root
    h = 0.3 + 1.4 * fill
    c2 = cyl(0.085, h, (0, 0, h / 2), liq, seg=20)
    c2.parent = root
    top = sphere(0.085, (0, 0, h), liq, seg=20, rings=10)
    top.parent = root
    for i in range(5):
        t = cyl(0.01, 0.12 if i % 2 else 0.2, (0.2, 0, 0.35 + i * 0.28), mat("#444", 0.5), rot=(0, R(90), 0), seg=8)
        t.parent = root
    return root


def flame(loc=(0, 0, 0), s=1.0):
    root = empty("flame", loc)
    sphere(0.28 * s, (0, 0, 0.28 * s), glow("#ff6a1a", 5), scale=(1, 0.8, 1.1)).parent = root
    cone(0.28 * s, 0.0, 0.7 * s, (0, 0, 0.7 * s), glow("#ff9a2a", 5), seg=24).parent = root
    cone(0.16 * s, 0.0, 0.4 * s, (0, 0, 0.45 * s), glow("#ffe14d", 6), seg=24).parent = root
    return root


def hexagon_tiles(center=(0, 0, 0), r=1.0, color="#2f9e57"):
    return None


def prism_xz(pts, depth, m, name="prism", bevel=0.03):
    """Polygon given as (x, z) points, extruded along Y (centred on y=0). Origin stays at world (0,0,0)."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in pts]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    s = o.modifiers.new("solid", "SOLIDIFY")
    s.thickness = depth
    s.offset = 0
    if bevel:
        b = o.modifiers.new("bev", "BEVEL")
        b.width = bevel
        b.segments = 2
        b.limit_method = "ANGLE"
    o.data.materials.append(m)
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    return o


def house(loc=(0, 0, 0), s=1.0, wall="#f4e2c0", roof="#d8573a"):
    root = empty("house", loc)
    box((1.6 * s, 1.3 * s, 1.1 * s), (0, 0, 0.55 * s), mat(wall, 0.7, sss=0.1, coat=0), bevel=0.04).parent = root
    r = cone(1.25 * s, 0.0, 0.8 * s, (0, 0, 1.5 * s), mat(roof, 0.55), seg=4)
    r.rotation_euler = (0, 0, R(45))
    r.scale = (1.0, 0.85, 1.0)
    r.parent = root
    box((0.3 * s, 0.05, 0.55 * s), (-0.45 * s, -0.67 * s, 0.35 * s), mat("#7a4a2d", 0.5), bevel=0.02).parent = root
    for sx in (0.4,):
        box((0.38 * s, 0.05, 0.38 * s), (sx * s, -0.67 * s, 0.65 * s), mat("#9fd8ff", 0.2, coat=0.6), bevel=0.02).parent = root
    cyl(0.1 * s, 0.5 * s, (0.5 * s, 0.2 * s, 1.7 * s), mat("#b5523b", 0.6)).parent = root
    return root


def tower_building(loc=(0, 0, 0), s=1.0, h=2.2, col="#6ec1e4"):
    root = empty("tower", loc)
    box((1.0 * s, 1.0 * s, h * s), (0, 0, h * s / 2), mat(col, 0.45, sss=0.1), bevel=0.05).parent = root
    for r in range(int(h * 2)):
        for c in (-0.25, 0.25):
            box((0.22 * s, 0.04, 0.16 * s), (c * s, -0.52 * s, (0.3 + r * 0.45) * s), mat("#fff6c9", 0.3, emit="#ffe9a0", emit_strength=0.6), bevel=0.01).parent = root
    return root
