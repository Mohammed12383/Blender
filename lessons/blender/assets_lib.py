"""Asset registry + render context. Each asset is a function taking a Ctx; it builds the scene and calls
ctx.still() or ctx.loop(update). Output goes to lessons/assets/{png,seq}/ and assets/manifest.json."""
import json
import os
import fcntl

from . import kit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
REG = {}


def asset(name, size=(640, 640), loop=None, bg=False, samples=32, group="misc"):
    def deco(fn):
        REG[name] = dict(fn=fn, size=size, loop=loop, bg=bg, samples=samples, group=group)
        return fn
    return deco


def register_many(items):
    for it in items:
        REG[it["name"]] = it


class Ctx:
    def __init__(self, name, spec, preview=False):
        self.name, self.spec, self.preview = name, spec, preview
        self.w, self.h = spec["size"]
        if preview:
            self.w, self.h = self.w // 2, self.h // 2
        self.rendered = None

    @property
    def n(self):
        return self.spec["loop"][0] if self.spec["loop"] else 1

    def _manifest(self, entry):
        os.makedirs(ASSETS, exist_ok=True)
        path = os.path.join(ASSETS, "manifest.json")
        with open(path + ".lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            m = json.load(open(path)) if os.path.exists(path) else {}
            m[self.name] = entry
            json.dump(m, open(path, "w"), indent=0, sort_keys=True)

    def still(self):
        ext = "jpg" if self.spec["bg"] else "png"
        rel = f"png/{self.name}.{ext}"
        kit.render_to(os.path.join(ASSETS, rel))
        self._manifest({"t": "s", "f": rel, "w": self.w, "h": self.h})

    def loop(self, update):
        n, fps = self.spec["loop"]
        ext = "jpg" if self.spec["bg"] else "png"
        d = f"seq/{self.name}"
        for i in range(n):
            update(i, i / n)
            kit.render_to(os.path.join(ASSETS, d, f"{i:03d}.{ext}"))
        self._manifest({"t": "l", "d": d, "n": n, "fps": fps, "w": self.w, "h": self.h, "ext": ext})


def done(name, spec):
    m = os.path.join(ASSETS, "manifest.json")
    if not os.path.exists(m):
        return False
    e = json.load(open(m)).get(name)
    if not e:
        return False
    if e["t"] == "s":
        return os.path.exists(os.path.join(ASSETS, e["f"]))
    return os.path.exists(os.path.join(ASSETS, e["d"], f"{e['n'] - 1:03d}.{e['ext']}"))


def render(name, force=False, preview=False):
    spec = REG[name]
    if not force and done(name, spec):
        return False
    kit.reset()
    ctx = Ctx(name, spec, preview)
    kit.setup_render(ctx.w, ctx.h, samples=spec["samples"] if not preview else 12, transparent=not spec["bg"])
    spec["fn"](ctx)
    return True
