"""Build the whole submarine: textures -> prop library -> exports -> level -> renders.

Run from the repository root with the bpy venv:
    python submarine/scripts/build.py                 # everything
    python submarine/scripts/build.py --no-render     # skip the room renders
    python submarine/scripts/build.py --quick         # low-sample renders
    python submarine/scripts/build.py --retex         # regenerate all textures first
    python submarine/scripts/build.py --sheet         # also render the prop contact sheet
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402  (must load before bmesh/mathutils users)

from sublib import core, exterior, humans, level, render, tex  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SUB = core.SUB_DIR
MODELS = os.path.join(SUB, "models")
RENDERS = os.path.join(SUB, "renders")
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def main():
    tex.FORCE = "--retex" in ARGS
    tex.generate_all()
    log("textures ready")

    core.reset_scene()
    lib = level.build_library()
    log(f"built {len(lib)} props")
    ext = {}
    for fn in (exterior.submarine, exterior.frigate, exterior.freighter):
        root = fn()
        ext[root.name] = root
        core.export_glb(core.hierarchy(root), os.path.join(MODELS, "exterior", root.name + ".glb"))
    log("built + exported exterior models")

    if "--sheet" in ARGS:
        out = os.path.join(SUB, "renders", "props")
        for name, root in lib.items():
            view = (-0.6, -1.0, 0.5)
            if name in ("CeilingLamp", "PendantLamp", "CeilingHatch", "ExhaustHood"):
                view = (-0.6, -1.0, -0.35)
            floor = root.get("category") not in ("light", "decor", "screen") or name.startswith(("Electrical", "Equipment", "Supply", "Spare", "Air"))
            render.preview(root, os.path.join(out, name + ".png"), samples=12, size=(360, 360), view=view, floor=floor)
        log("prop previews rendered")
        for o in render._rig.get("col").objects if render._rig else []:
            o.hide_render = True

    for name, root in lib.items():
        core.export_glb(core.hierarchy(root), os.path.join(MODELS, "props", name + ".glb"))
    log("exported prop GLBs")

    # crew: rigged characters (exported in rest T-pose) + a posed lineup render
    cast = {a["role"]: a for a in humans.build_all(core.collection("Crew"))}
    for a in cast.values():
        core.export_glb(core.hierarchy(a), os.path.join(MODELS, "characters", a.name + ".glb"))
    for spec in humans.CREW:
        fp = humans.build_fp_arms(spec, core.collection("Crew"))
        core.export_glb(core.hierarchy(fp), os.path.join(MODELS, "characters", fp.name + ".glb"))
    log("built + exported crew and first-person arms")
    rc = core.collection("RenderCrew")
    core.layer_collection("Library").exclude = True
    core.layer_collection("Crew").exclude = True
    if "--no-render" not in ARGS:
        line = bpy.data.objects.new("CrewLineup", None)
        rc.objects.link(line)
        for i, (role, pose) in enumerate([("navigator", "wave"), ("weapons_officer", "relaxed"),
                                          ("torpedo_loader", "operate"), ("cook", "relaxed")]):
            humans.place_copy(cast[role], rc, (-1.35 + i * 0.9, 0, 0), 0, pose).parent = line
        render.preview(line, os.path.join(RENDERS, "crew_lineup.png"), samples=48 if "--quick" not in ARGS else 16,
                       size=(1600, 900), view=(0, -1, 0.15))
        for o in core.hierarchy(line):
            bpy.data.objects.remove(o)
        log("rendered crew lineup")
    if render._rig:
        core.layer_collection("PreviewRig").exclude = True
    rooms = level.build_level(lib)
    # crew at their stations (render-only, not part of the room exports)
    for role, loc, rz, pose in [("navigator", (12.0, 0.4, 0), 0, "operate"),
                                ("weapons_officer", (9.05, 1.4, 0), 180, "operate"),
                                ("torpedo_loader", (2.45, 0.15, 0), 20, "operate"),
                                ("cook", (25.35, -1.3, 0), 0, "operate"),
                                ("navigator", (19.75, 0.75, 0), 110, "wave"),
                                ("weapons_officer", (18.35, -0.05, 0), 70, "relaxed")]:
        humans.place_copy(cast[role], rc, loc, rz, pose)
    log("level assembled")

    everything = []
    for r in rooms:
        objs = list(r.col.objects)
        everything += objs
        core.export_glb(objs, os.path.join(MODELS, "rooms", r.name + ".glb"))
    core.export_glb(everything, os.path.join(MODELS, "Submarine_Interior.glb"))
    log("exported room + level GLBs")

    render.world("#0d1216", 0.15)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(MODELS, "Submarine_Interior.blend"), relative_remap=True)
    log("saved .blend")

    if "--no-render" not in ARGS:
        quick = "--quick" in ARGS
        spp = 24 if quick else 56
        res = (960, 540) if quick else (1600, 900)
        shots = [
            ("control_room", (15.6, -0.75, 1.7), (9.2, 0.85, 1.0), 17),
            ("control_room_fwd", (7.75, -0.95, 1.7), (13.5, 1.1, 1.0), 17),
            ("torpedo_room", (6.5, 1.35, 1.65), (0.6, -0.5, 1.15), 17),
            ("crew_mess", (22.2, 1.0, 1.6), (17.6, -0.9, 0.95), 17),
            ("galley", (23.25, 1.35, 1.65), (26.2, -1.75, 1.15), 17),
        ]
        only = [a.split("=")[1] for a in ARGS if a.startswith("--shot=")]
        for name, loc, tgt, lens in shots:
            if only and name not in only:
                continue
            render.shot("Cam_" + name, loc, tgt, os.path.join(RENDERS, name + ".png"), lens=lens, samples=spp, res=res)
            log(f"rendered {name}")
        if not only or "cutaway" in only:
            render.cutaway(rooms, os.path.join(RENDERS, "cutaway.png"), samples=spp, res=res)
            log("rendered cutaway")
        if not only or "exterior" in only:
            render.exterior_shot(rooms, ext, os.path.join(RENDERS, "exterior.png"), samples=spp, res=res)
            log("rendered exterior")
    log("done")


main()
