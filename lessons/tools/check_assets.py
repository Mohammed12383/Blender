"""python tools/check_assets.py [lesson...]  -> lists assets referenced by lesson scripts that are not rendered yet"""
import json, os, re, sys, glob
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
man = json.load(open(f'{root}/assets/manifest.json'))
def ok(n):
    e = man.get(n)
    if not e: return False
    p = f"{root}/assets/{e['f']}" if e['t'] == 's' else f"{root}/assets/{e['d']}/{e['n'] - 1:03d}.{e['ext']}"
    return os.path.exists(p)
files = [f'{root}/content/{l}.js' for l in sys.argv[1:]] or sorted(glob.glob(f'{root}/content/*.js'))
for f in files:
    if f.endswith('test.js'): continue
    txt = open(f).read()
    names = set(re.findall(r"(?:img|img2|bg):\s*'([a-z0-9_]+)'", txt))
    missing = sorted(n for n in names if not ok(n))
    print(os.path.basename(f), 'OK' if not missing else 'MISSING: ' + ', '.join(missing))
