"""python tools/sheet.py <lesson> [--frac 0.75] [--from 0 --to 12]: screenshots at scene points -> contact sheets"""
import json, subprocess, sys, os, glob
from PIL import Image
lesson = sys.argv[1]
args = sys.argv[2:]
g = lambda k, d: args[args.index(k) + 1] if k in args else d
frac = float(g('--frac', '0.7')); a = int(g('--from', 0)); b = int(g('--to', 999)); cols = int(g('--cols', 2))
SP = os.environ.get('SHOTS', '/tmp/shots_' + lesson)
os.makedirs(SP, exist_ok=True)
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
info_p = f'{root}/out/{lesson}/info.json'
if not os.path.exists(info_p):
    subprocess.run(['node', f'{root}/tools/render.cjs', lesson, '--shots', '1'], check=True)
info = json.load(open(info_p))
sc = info['scenes'][a:b]
times = [round(s['start'] + min(s['dur'] - 0.9, s['dur'] * frac), 1) for s in sc]
for f in glob.glob(SP + '/shot_*'): os.remove(f)
subprocess.run(['node', f'{root}/tools/render.cjs', lesson, '--out', SP, '--shots', ','.join(map(str, times))], check=True, capture_output=True)
ims = []
for t in times:
    ims.append(Image.open(f'{SP}/shot_{t:.1f}.png').convert('RGB').resize((640, 360)))
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (640 * cols, 360 * rows))
for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
out = f'{SP}/sheet_{a}_{b}.jpg'
sheet.save(out, quality=82); print(out, [(a + i, t) for i, t in enumerate(times)])
