"""python lessons/render_assets.py <group|name> ... [--force] [--preview] [--list]"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender import assets_lib
import importlib, glob
for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender", "assets_*.py"))):
    n = os.path.basename(f)[:-3]
    if n != "assets_lib":
        importlib.import_module("blender." + n)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
force, prev = "--force" in sys.argv, "--preview" in sys.argv
if "--list" in sys.argv:
    for k, v in assets_lib.REG.items(): print(v["group"], k, v["size"], v["loop"])
    sys.exit()
names = [k for k, v in assets_lib.REG.items() if not args or k in args or v["group"] in args or any(k.startswith(a.rstrip('*')) for a in args if a.endswith('*'))]
t0 = time.time(); n = 0
for i, k in enumerate(names):
    t1 = time.time()
    try:
        did = assets_lib.render(k, force, prev)
    except Exception as e:
        import traceback; traceback.print_exc(); print("FAILED", k, e); continue
    if did:
        n += 1; print(f"[{i + 1}/{len(names)}] {k} {time.time() - t1:.1f}s", flush=True)
print(f"rendered {n} assets in {time.time() - t0:.0f}s")
