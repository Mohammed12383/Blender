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

from sublib import core, level, render, tex  # noqa: E402

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

    core.layer_collection("Library").exclude = True
    if render._rig:
        core.layer_collection("PreviewRig").exclude = True
    rooms = level.build_level(lib)
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
        spp = 24 if quick else 128
        res = (960, 540) if quick else (1600, 900)
        shots = [
            ("control_room", (15.6, -0.75, 1.7), (9.2, 0.85, 1.0), 17),
            ("control_room_fwd", (7.85, 1.75, 1.7), (13.5, -1.2, 1.0), 17),
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
    log("done")


main()
