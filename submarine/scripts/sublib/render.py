"""Render helpers: Cycles setup, quick studio previews of single props, room shots."""

import math
import os

import bpy
from mathutils import Vector

from . import core, tex

R = math.radians


def setup_cycles(samples=64, res=(1280, 720), percent=100):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.light_sampling_threshold = 0.01
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = percent
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.render.image_settings.file_format = "PNG"


def world(color="#1b2228", strength=0.4):
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*tex.hex_rgb(color) ** 2.2, 1)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w


def bbox(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for o in objs:
        if o.type != "MESH" or not len(o.data.vertices):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


_rig = {}


def _preview_rig():
    if _rig:
        return _rig
    col = core.collection("PreviewRig")
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    cam.data.lens = 50
    col.objects.link(cam)
    floor = bpy.data.objects.new("PreviewFloor", bpy.data.meshes.new("PreviewFloor"))
    import bmesh
    bm = core.bm_box(40, 40, 0.02, (0, 0, -0.011))
    bm.to_mesh(floor.data)
    bm.free()
    m = bpy.data.materials.new("PreviewFloor")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.36, 0.38, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    floor.data.materials.append(m)
    col.objects.link(floor)
    lights = []
    for name, e, loc in [("Key", 600, (-3, -4, 5)), ("Fill", 200, (4, -3, 2)), ("Rim", 400, (1, 5, 4))]:
        ld = bpy.data.lights.new("Prev" + name, "AREA")
        ld.energy, ld.size = e, 3
        o = bpy.data.objects.new("Prev" + name, ld)
        col.objects.link(o)
        lights.append((o, Vector(loc)))
    _rig.update(col=col, cam=cam, floor=floor, lights=lights)
    return _rig


def preview(root, filepath, samples=24, size=(640, 640), view=(-0.75, -1.0, 0.6), floor=True):
    """Render one library prop alone in a neutral studio."""
    rig = _preview_rig()
    for o in [rig["cam"], rig["floor"]] + [l for l, _ in rig["lights"]]:
        o.hide_render = False
    keep = set(core.hierarchy(root)) | {rig["cam"], rig["floor"]} | {l for l, _ in rig["lights"]}
    hidden = []
    for o in bpy.context.scene.objects:
        if o not in keep and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    rig["floor"].hide_render = not floor
    lo, hi = bbox(core.hierarchy(root))
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.05)
    rig["floor"].location.z = lo.z if floor else -100
    cam = rig["cam"]
    d = Vector(view).normalized()
    fov = 2 * math.atan(18 / cam.data.lens)
    dist = radius / math.sin(fov / 2) * 1.05
    cam.location = center + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_start = dist * 0.01
    cam.data.clip_end = dist * 10
    s = max(radius, 0.3)
    for o, loc in rig["lights"]:
        o.location = center + loc * s
        o.rotation_euler = (center - o.location).to_track_quat("-Z", "Y").to_euler()
        o.data.size = 3 * s
        o.data.energy = {"PrevKey": 600, "PrevFill": 200, "PrevRim": 400}[o.name] * s * s
    sc = bpy.context.scene
    sc.camera = cam
    setup_cycles(samples, size)
    world("#3a4248", 0.6)
    sc.render.filepath = filepath
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False


def shot(name, loc, target, filepath, lens=20, samples=96, res=(1600, 900)):
    """Eye-level camera shot of the assembled level."""
    col = core.collection("Cameras")
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        col.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.05
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc = bpy.context.scene
    sc.camera = cam
    setup_cycles(samples, res)
    sc.render.filepath = filepath
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bpy.ops.render.render(write_still=True)


def cutaway(rooms, filepath, samples=96, res=(1600, 900)):
    """Bird's-eye view of the whole level with walls, ceiling and ceiling clutter hidden."""
    hidden = []
    for r in rooms:
        for o in r.col.objects:
            n = o.name
            hide = n.endswith(("_Shell_Body", "_Structure")) or "CeilingLamp" in n or "ChainHoist" in n \
                or "PendantLamp" in n or "CeilingHatch" in n or ("Bulkhead" in n and n.endswith("_Body"))
            if o.parent and ("CeilingLamp" in o.parent.name or "PendantLamp" in o.parent.name
                             or "ChainHoist" in o.parent.name or "CeilingHatch" in o.parent.name):
                hide = True
            if hide and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    col = core.collection("RenderOnly")
    sun = bpy.data.objects.get("CutawaySun")
    if sun is None:
        ld = bpy.data.lights.new("CutawaySun", "SUN")
        ld.energy = 3.0
        ld.angle = R(8)
        sun = bpy.data.objects.new("CutawaySun", ld)
        col.objects.link(sun)
    sun.rotation_euler = (R(40), R(10), R(-150))
    sun.hide_render = False
    cam = bpy.data.objects.get("Cam_cutaway") or bpy.data.objects.new("Cam_cutaway", bpy.data.cameras.new("Cam_cutaway"))
    if cam.name not in col.objects:
        col.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 29.5
    center = Vector((13.7, 0.0, 0.6))
    d = Vector((-0.18, 1.0, 1.05)).normalized()
    cam.location = center + d * 40
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = 200
    sc = bpy.context.scene
    sc.camera = cam
    old = (sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value,)
    world("#9fb4c4", 0.6)
    setup_cycles(samples, res)
    sc.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    sun.hide_render = True
    world("#0d1216", old[0])


def exterior_shot(rooms, ext, filepath, samples=64, res=(1600, 900)):
    """Our sub surfaced at sea, with the two target ships on the horizon (render only)."""
    for r in rooms:
        core.layer_collection(r.col.name).exclude = True
    lc = core.layer_collection("RenderCrew")
    if lc:
        lc.exclude = True
    col = core.collection("ExteriorScene")
    sub = core.instance(ext["SubmarineExterior"], col, (0, 0, -0.2), (0, 0, 0))
    core.instance(ext["EnemyFrigate"], col, (201, 125, 0), (0, 0, 205))
    core.instance(ext["CargoFreighter"], col, (190, 420, 0), (0, 0, -15))
    # ocean
    import bmesh
    me = bpy.data.meshes.new("Ocean")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3000)
    bm.to_mesh(me)
    bm.free()
    ocean = bpy.data.objects.new("Ocean", me)
    col.objects.link(ocean)
    m = bpy.data.materials.new("OceanWater")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*tex.hex_rgb("#1a4a66") ** 2.2, 1)
    bsdf.inputs["Roughness"].default_value = 0.2
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.9, 0.35, 0.9)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.0
    nz.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    me.materials.append(m)
    ld = bpy.data.lights.new("ExtSun", "SUN")
    ld.energy = 4.0
    ld.angle = R(2)
    ld.color = tuple(tex.hex_rgb("#fff1dc") ** 2.2)
    sun = bpy.data.objects.new("ExtSun", ld)
    col.objects.link(sun)
    sun.rotation_euler = (R(58), R(0), R(-35))
    ld.energy = 5.0
    # gradient sky: pale at the horizon, deeper blue overhead
    w = bpy.context.scene.world
    nt = w.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (*tex.hex_rgb("#dfe9ee") ** 2.2, 1)
    ramp.color_ramp.elements[1].position = 0.64
    ramp.color_ramp.elements[1].color = (*tex.hex_rgb("#4a8cc8") ** 2.2, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    math_n = nt.nodes.new("ShaderNodeMath")
    math_n.operation = "MULTIPLY_ADD"
    math_n.inputs[1].default_value = 0.5
    math_n.inputs[2].default_value = 0.5
    nt.links.new(sep.outputs["Z"], math_n.inputs[0])
    nt.links.new(math_n.outputs["Value"], ramp.inputs["Fac"])
    bg = nt.nodes["Background"]
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    cam = bpy.data.objects.new("Cam_exterior", bpy.data.cameras.new("Cam_exterior"))
    col.objects.link(cam)
    cam.data.lens = 30
    cam.data.clip_end = 3000
    cam.location = (-27, -31, 4.6)
    cam.rotation_euler = (Vector((2.0, 0, 2.4)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc = bpy.context.scene
    sc.camera = cam
    setup_cycles(samples, res)
    sc.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    for r in rooms:
        core.layer_collection(r.col.name).exclude = False
    if lc:
        lc.exclude = False
    core.layer_collection("ExteriorScene").exclude = True
    for n in [n for n in nt.nodes if n.type in ("TEX_COORD", "SEPXYZ", "VALTORGB", "MATH")]:
        nt.nodes.remove(n)
    world("#0d1216", 0.15)
