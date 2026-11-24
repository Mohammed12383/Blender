"""Cast stills: Terra, Salem, Maryam, Jiddi, the Professor, in many poses x expressions."""
import os, sys
from . import kit, chars
from .assets_lib import register_many

POSES_P = ["idle", "wave", "point", "pointup", "cheer", "think", "present", "hold", "surprise", "explain", "shrug"]
POSES_T = ["idle", "wave", "point", "cheer", "think", "shrug", "present"]
EXTRA = [("idle", "grin"), ("idle", "oh"), ("idle", "sad"), ("idle", "flat"), ("idle", "happy"), ("cheer", "grin"), ("think", "flat"),
         ("surprise", "oh"), ("shrug", "sad"), ("point", "grin"), ("present", "grin")]


def _mk(kind, pose, expr, brow=None):
    def fn(ctx):
        kit.studio(scale=1.2)
        if kind == "terra":
            chars.terra(expr=expr, pose=pose, brow=brow or ("worried" if expr in ("sad",) else "up"))
            kit.camera((0, -7.4, 0.35), (0, 0, 0.12), lens=60)
        else:
            chars.person(kind, expr=expr, pose=pose, brow=brow or ("worried" if expr == "sad" else "up"))
            kit.camera((0, -7.9, 1.45), (0, 0, 1.45), lens=60)
        ctx.still()
    return fn


items = []
for kind in ("terra", "salem", "maryam", "jidd", "prof"):
    poses = POSES_T if kind == "terra" else POSES_P
    combos = [(p, e) for p in poses for e in ("smile", "open")] + EXTRA
    for pose, expr in combos:
        if kind == "terra" and pose in ("pointup", "hold", "surprise", "explain"):
            continue
        name = f"{kind}_{pose}_{expr}"
        size = (480, 600) if kind == "terra" else (420, 600)
        if any(i["name"] == name for i in items):
            continue
        items.append(dict(name=name, fn=_mk(kind, pose, expr), size=size, loop=None, bg=False, samples=40, group="cast"))
register_many(items)


def _mk_drop(pose, expr, brow):
    def fn(ctx):
        kit.studio(scale=1.2)
        chars.droplet(expr=expr, pose=pose, brow=brow)
        kit.camera((0, -7.2, 0.5), (0, 0, 0.45), lens=60)
        ctx.still()
    return fn


register_many([dict(name=f"drop_{p}_{e}", fn=_mk_drop(p, e, b), size=(420, 520), loop=None, bg=False, samples=36, group="cast")
               for p, e, b in (("idle", "smile", "up"), ("idle", "open", "up"), ("run", "open", "up"), ("wave", "open", "up"), ("sleepy", "flat", "flat"))])
register_many([dict(name="drop_sleepy", fn=_mk_drop("sleepy", "flat", "sad"), size=(420, 520), loop=None, bg=False, samples=36, group="cast")])
