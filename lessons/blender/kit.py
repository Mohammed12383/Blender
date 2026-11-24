"""Shared Blender helpers for the lesson videos: clay-toy materials, lighting, primitives, rendering.

Run through the project's virtualenv:  .venv/bin/python lessons/blender/<script>.py
Everything is built from code so any asset can be regenerated or tweaked.
Characters/props face -Y (the camera sits on the -Y side looking toward +Y).
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

V = Vector
_MATS = {}


# ───────────────────────── scene / render ─────────────────────────
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    return sc


def setup_render(w=640, h=640, samples=32, transparent=True, bounces=4, denoise=True):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG" if transparent else "JPEG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    if not transparent:
        sc.render.image_settings.quality = 90
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = denoise
    sc.cycles.max_bounces = bounces
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 4
    sc.render.threads = os.cpu_count() or 4
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0


def render_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ───────────────────────── materials ─────────────────────────
def hexc(h, a=1.0):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    # sRGB -> linear
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), a)


def _set(node, name, value):
    try:
        node.inputs[name].default_value = value
    except KeyError:
        pass


def mat(color="#cccccc", rough=0.45, metal=0.0, emit=None, emit_strength=2.0, sss=0.12, coat=0.25,
        alpha=1.0, name=None, glass=False, ior=1.45):
    key = (color, rough, metal, emit, emit_strength, sss, coat, alpha, glass)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name or f"M{len(_MATS)}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    _set(bsdf, "Base Color", hexc(color))
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Metallic", metal)
    _set(bsdf, "Subsurface Weight", sss)
    _set(bsdf, "Subsurface Radius", (0.12, 0.06, 0.04))
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Coat Roughness", 0.25)
    if alpha < 1:
        _set(bsdf, "Alpha", alpha)
    if glass:
        _set(bsdf, "Transmission Weight", 1.0)
        _set(bsdf, "IOR", ior)
    if emit:
        _set(bsdf, "Emission Color", hexc(emit))
        _set(bsdf, "Emission Strength", emit_strength)
    _MATS[key] = m
    return m


def tex_mat(kind="noise", c1="#2a6fdb", c2="#3dbb5d", scale=3.0, detail=6.0, rough=0.5, mid=0.5, contrast=0.1, name=None,
            coord="Object", emit=0.0, sss=0.1, coat=0.2, bump=0.0):
    """Procedural two-colour noise material (continents, rock grain, sand, foliage...)."""
    m = bpy.data.materials.new(name or f"T{len(_MATS)}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs[coord], mp.inputs["Vector"])
    if kind == "voronoi":
        t = nt.nodes.new("ShaderNodeTexVoronoi")
        t.inputs["Scale"].default_value = 1.0
        out = t.outputs["Distance"]
    elif kind == "wave":
        t = nt.nodes.new("ShaderNodeTexWave")
        t.inputs["Scale"].default_value = 1.0
        t.inputs["Distortion"].default_value = 6
        out = t.outputs["Fac"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise")
        t.inputs["Scale"].default_value = 1.0
        t.inputs["Detail"].default_value = detail
        out = t.outputs["Fac"]
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = max(0.0, mid - contrast)
    ramp.color_ramp.elements[0].color = hexc(c1)
    ramp.color_ramp.elements[1].position = min(1.0, mid + contrast)
    ramp.color_ramp.elements[1].color = hexc(c2)
    nt.links.new(out, ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Subsurface Weight", sss)
    _set(bsdf, "Coat Weight", coat)
    if emit:
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
        _set(bsdf, "Emission Strength", emit)
    if bump:
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        nt.links.new(out, bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def stripes_mat(c1, c2, scale=8.0, axis="Z", rough=0.6, sharp=0.02, name=None):
    """Hard-edged bands along an axis (clothing trim, strata, rugs)."""
    m = bpy.data.materials.new(name or f"S{len(_MATS)}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = scale
    nt.links.new(sep.outputs[axis], mul.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
    nt.links.new(mul.outputs[0], fr.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hexc(c1)
    e = ramp.color_ramp.elements.new(0.5)
    e.color = hexc(c2)
    nt.links.new(fr.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Subsurface Weight", 0.1)
    return m


# ───────────────────────── primitives ─────────────────────────
def _fin(o, m=None, smooth=True, bevel=0.0, subsurf=0, name=None, parent=None, loc=None, rot=None, scale=None):
    if name:
        o.name = name
    if m is not None:
        if o.data.materials:
            o.data.materials[0] = m
        else:
            o.data.materials.append(m)
    if smooth and o.type == "MESH":
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        o.data.update()
    if bevel:
        b = o.modifiers.new("bev", "BEVEL")
        b.width = bevel
        b.segments = 4
        b.limit_method = "ANGLE"
    if subsurf:
        s = o.modifiers.new("sub", "SUBSURF")
        s.levels = subsurf
        s.render_levels = subsurf
    if parent is not None:
        o.parent = parent
    if loc is not None:
        o.location = loc
    if rot is not None:
        o.rotation_euler = tuple(rot)
    if scale is not None:
        o.scale = scale if hasattr(scale, "__len__") else (scale, scale, scale)
    return o


def sphere(r=1.0, loc=(0, 0, 0), m=None, scale=(1, 1, 1), seg=48, rings=24, **kw):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=rings)
    return _fin(bpy.context.object, m, loc=loc, scale=scale, **kw)


def ico(r=1.0, loc=(0, 0, 0), m=None, sub=3, scale=(1, 1, 1), **kw):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=sub)
    return _fin(bpy.context.object, m, loc=loc, scale=scale, **kw)


def cyl(r=0.5, h=1.0, loc=(0, 0, 0), m=None, rot=(0, 0, 0), seg=32, scale=(1, 1, 1), bevel=0.0, **kw):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=seg)
    return _fin(bpy.context.object, m, loc=loc, rot=rot, scale=scale, bevel=bevel, **kw)


def cone(r1=0.5, r2=0.0, h=1.0, loc=(0, 0, 0), m=None, rot=(0, 0, 0), seg=32, scale=(1, 1, 1), bevel=0.0, **kw):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, vertices=seg)
    return _fin(bpy.context.object, m, loc=loc, rot=rot, scale=scale, bevel=bevel, **kw)


def box(size=(1, 1, 1), loc=(0, 0, 0), m=None, rot=(0, 0, 0), bevel=0.05, **kw):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    return _fin(o, m, loc=loc, rot=rot, scale=size, bevel=bevel, **kw)


def torus(R=1.0, r=0.1, loc=(0, 0, 0), m=None, rot=(0, 0, 0), scale=(1, 1, 1), **kw):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=48, minor_segments=16)
    return _fin(bpy.context.object, m, loc=loc, rot=rot, scale=scale, **kw)


def capsule(r=0.2, h=0.6, loc=(0, 0, 0), m=None, rot=(0, 0, 0), **kw):
    """Cylinder body of length h plus two spherical caps (total length h + 2r), centred at loc."""
    c = cyl(r, h, (0, 0, 0), m, seg=24)
    a = sphere(r, (0, 0, h / 2), m, seg=24, rings=12)
    b = sphere(r, (0, 0, -h / 2), m, seg=24, rings=12)
    for o in (a, b):
        o.select_set(True)
    c.select_set(True)
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.join()
    o = bpy.context.object
    return _fin(o, m, loc=loc, rot=rot, **kw)


def empty(name="E", loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    if parent is not None:
        o.parent = parent
    return o


def curve(points, bevel=0.03, m=None, loc=(0, 0, 0), rot=(0, 0, 0), name="curve", cyclic=False, res=12, taper=None):
    """Poly/smooth curve through 3D points with round-bevel tube."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 4
    cu.fill_mode = "FULL"
    cu.resolution_u = res
    sp = cu.splines.new("POLY" if False else "NURBS")
    sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (c[0], c[1], c[2], 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(points))
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    if m is not None:
        cu.materials.append(m)
    o.location = loc
    o.rotation_euler = rot
    return o


def parent_to(objs, parent):
    for o in objs:
        o.parent = parent


def hide(o, flag=True):
    o.hide_render = flag
    o.hide_viewport = flag


# ───────────────────────── lighting / camera ─────────────────────────
def world(top="#cfe6ff", bottom="#ffe9d6", strength=0.9):
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    bpy.context.scene.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hexc(bottom)
    ramp.color_ramp.elements[1].color = hexc(top)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def area_light(loc, target=(0, 0, 0), energy=300, size=3.0, color="#ffffff", name="L"):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ld.color = hexc(color)[:3]
    o = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(o)
    o.location = loc
    d = V(target) - V(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


def sun(rot_deg=(50, 0, 30), energy=3.0, color="#fff4e0"):
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy = energy
    ld.color = hexc(color)[:3]
    ld.angle = math.radians(6)
    o = bpy.data.objects.new("Sun", ld)
    bpy.context.collection.objects.link(o)
    o.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    return o


def studio(key=420, fill=90, rim=260, scale=1.0, top="#d8ecff", bottom="#ffe6cc", warm="#fff1dd", cool="#bfe0ff", amb=0.55):
    """Soft three-point toy-studio rig scaled to subject size."""
    world(top, bottom, amb)
    s = scale
    area_light((-3.2 * s, -4.2 * s, 4.6 * s), (0, 0, 0.8 * s), key * s * s, 4.0 * s, warm, "Key")
    area_light((4.6 * s, -3.2 * s, 1.8 * s), (0, 0, 0.8 * s), fill * s * s, 4.0 * s, cool, "Fill")
    area_light((2.0 * s, 4.4 * s, 4.0 * s), (0, 0, 0.8 * s), rim * s * s, 3.0 * s, "#ffffff", "Rim")


def camera(loc, target=(0, 0, 0), lens=60, ortho=None, name="Cam"):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 500
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    o = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(o)
    o.location = loc
    d = V(target) - V(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o
    return o


def look_at(o, target):
    d = V(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def args():
    """CLI args after `--`."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


# ───────────────────────── faces ─────────────────────────
EYE_WHITE = "#ffffff"
INK = "#1c1230"


def face(parent, y, eye_dx=0.2, eye_z=0.05, eye_r=0.11, expr="smile", brow="up", scale=1.0, mouth_z=-0.17, look=(0, 0),
         lashes=False, blush="#ff8aa1"):
    """Cartoon face placed on the -Y side of `parent` at depth y. expr: smile/open/oh/sad/grin/flat/happy/wink."""
    s = scale
    M_ink = mat(INK, 0.3, coat=0.5, sss=0)
    M_white = mat(EYE_WHITE, 0.2, coat=0.6, sss=0)
    M_mouth = mat("#7a1f35", 0.5, sss=0)
    M_tongue = mat("#ff6f8a", 0.5, sss=0)
    objs = []
    for sx in (-1, 1):
        ex = sx * eye_dx * s
        if expr in ("happy",):
            # ^ ^ eyes: arc curve
            pts = [(ex - 0.08 * s, y, eye_z * s - 0.03 * s), (ex, y, eye_z * s + 0.045 * s), (ex + 0.08 * s, y, eye_z * s - 0.03 * s)]
            c = curve(pts, 0.022 * s, M_ink)
            c.parent = parent
            objs.append(c)
        elif expr == "wink" and sx == 1:
            pts = [(ex - 0.07 * s, y, eye_z * s - 0.02 * s), (ex, y, eye_z * s + 0.03 * s), (ex + 0.07 * s, y, eye_z * s - 0.02 * s)]
            c = curve(pts, 0.02 * s, M_ink)
            c.parent = parent
            objs.append(c)
        else:
            w = sphere(eye_r * s, (ex, y, eye_z * s), M_white, scale=(0.92, 0.5, 1.12), seg=32, rings=16)
            w.parent = parent
            pr = eye_r * 0.62 * s
            lx, lz = look
            p = sphere(pr, (ex + lx * 0.03 * s, y - eye_r * s * 0.28, eye_z * s + lz * 0.03 * s), M_ink, scale=(0.95, 0.5, 1.05), seg=24, rings=12)
            p.parent = parent
            h = sphere(pr * 0.32, (ex + lx * 0.03 * s + pr * 0.32, y - eye_r * s * 0.5, eye_z * s + lz * 0.03 * s + pr * 0.4), M_white, seg=12, rings=8)
            h.parent = parent
            objs += [w, p, h]
        # brows
        bz = eye_z * s + eye_r * s * 2.0
        ang = {"up": 8, "angry": -22, "sad": 22, "flat": 0, "worried": 24, "none": None}.get(brow, 0)
        if ang is not None:
            ba = math.radians(ang * sx)
            bp = capsule(0.02 * s, 0.11 * s, (ex, y + 0.01 * s, bz), M_ink, rot=(0, math.pi / 2 + ba, 0))
            bp.parent = parent
            objs.append(bp)
        if blush:
            ch = cyl(0.055 * s, 0.01, (sx * (eye_dx + 0.13) * s, y + 0.035 * s, eye_z * s - 0.1 * s), mat(blush, 0.6, sss=0, alpha=1.0),
                     rot=(math.pi / 2, 0, 0), seg=20, scale=(1.1, 1, 0.7))
            ch.parent = parent
            objs.append(ch)
    mz = mouth_z * s
    if expr in ("smile", "happy", "wink"):
        pts = [(-0.11 * s, y, mz + 0.03 * s), (0, y - 0.005 * s, mz - 0.015 * s), (0.11 * s, y, mz + 0.03 * s)]
        c = curve(pts, 0.02 * s, M_ink)
        c.parent = parent
        objs.append(c)
    elif expr == "grin":
        m = sphere(0.13 * s, (0, y + 0.01 * s, mz + 0.015 * s), M_mouth, scale=(1.0, 0.35, 0.7), seg=32, rings=16)
        t = sphere(0.075 * s, (0, y - 0.005 * s, mz - 0.03 * s), M_tongue, scale=(1.0, 0.3, 0.55), seg=24, rings=12)
        tp = box((0.2 * s, 0.01, 0.05 * s), (0, y - 0.035 * s, mz + 0.05 * s), mat("#ffffff", 0.3, sss=0), bevel=0.01)
        m.parent = parent; t.parent = parent; tp.parent = parent
        objs += [m, t, tp]
    elif expr == "open":
        m = sphere(0.135 * s, (0, y + 0.01 * s, mz - 0.01 * s), M_mouth, scale=(1.0, 0.4, 1.1), seg=32, rings=16)
        t = sphere(0.085 * s, (0, y - 0.012 * s, mz - 0.07 * s), M_tongue, scale=(1.0, 0.3, 0.55), seg=24, rings=12)
        m.parent = parent; t.parent = parent
        objs += [m, t]
    elif expr == "oh":
        m = sphere(0.055 * s, (0, y, mz), M_mouth, scale=(1.0, 0.4, 1.2), seg=24, rings=12)
        m.parent = parent
        objs.append(m)
    elif expr == "sad":
        pts = [(-0.09 * s, y, mz - 0.02 * s), (0, y, mz + 0.02 * s), (0.09 * s, y, mz - 0.02 * s)]
        c = curve(pts, 0.02 * s, M_ink)
        c.parent = parent
        objs.append(c)
    elif expr == "flat":
        c = curve([(-0.07 * s, y, mz), (0.07 * s, y, mz)], 0.02 * s, M_ink)
        c.parent = parent
        objs.append(c)
    return objs


def strata_mat(colors, period=1.0, axis="Z", coord="Object", rough=0.6, offset=0.0, name=None):
    """Horizontal rock layers: N constant colour bands repeating every `period` along an axis."""
    m = bpy.data.materials.new(name or f"ST{len(_MATS)}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs[coord], sep.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; add.inputs[1].default_value = offset
    nt.links.new(sep.outputs[axis], add.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "DIVIDE"; mul.inputs[1].default_value = period
    nt.links.new(add.outputs[0], mul.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
    nt.links.new(mul.outputs[0], fr.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    n = len(colors)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hexc(colors[0])
    for i in range(1, n):
        e = ramp.color_ramp.elements.new(i / n)
        e.color = hexc(colors[i])
    nt.links.new(fr.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Subsurface Weight", 0.08)
    _set(bsdf, "Coat Weight", 0.0)
    return m
