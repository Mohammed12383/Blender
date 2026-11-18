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
