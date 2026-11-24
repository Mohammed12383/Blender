"""python tools/make_all.py  -> videos/all_lessons.mp4: an index card (chapter times on frame 0) + all 11 videos, with chapter markers."""
import json, os, subprocess, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = f'{root}/videos'
INTRO = 20.0
LESSONS = [
    ('u1l1', 1, 'الوحدة 1 · الدرس 1', 'نشأة الأرض'), ('u1l2', 1, 'الوحدة 1 · الدرس 2', 'العوامل الداخلية'), ('u1l3', 1, 'الوحدة 1 · الدرس 3', 'الصخور'),
    ('u2l1', 2, 'الوحدة 2 · الدرس 1', 'التجوية'), ('u2l2', 2, 'الوحدة 2 · الدرس 2', 'التعرية الريحية'), ('u2l3', 2, 'الوحدة 2 · الدرس 3', 'التعرية المائية'), ('u2l4', 2, 'الوحدة 2 · الدرس 4', 'التعرية البحرية'),
    ('u3l1', 3, 'الوحدة 3 · الدرس 1', 'ظهور الإسلام وبناء الدولة'), ('u3l2', 3, 'الوحدة 3 · الدرس 2', 'المدارس الفكرية'), ('u3l3', 3, 'الوحدة 3 · الدرس 3', 'المذاهب الإسلامية'),
    ('review', 0, 'مراجعة أخيرة', 'الأرقام والتواريخ'),
]
def dur(path):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of', 'csv=p=0', path]).decode().strip()
    return float(out)
def hms(s):
    s = int(round(s)); return f'{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}'
def ms(s):
    s = int(round(s)); return f'{s // 60}:{s % 60:02d}'
durs = [dur(f'{V}/{l[0]}.mp4') for l in LESSONS]
t = INTRO; items = []; starts = []
for (lid, unit, tag, name), d in zip(LESSONS, durs):
    starts.append(t); items.append(dict(time=hms(t), len=ms(d), unit=unit, tag=tag, name=name)); t += d
total = t
js = 'window.LESSON = ' + json.dumps(dict(id='index', theme='review', music='review', label='الفهرس الزمني',
     scenes=[dict(t='toc', len=INTRO, title='مراجعة الدراسات الاجتماعية – الصف العاشر', sub='الفهرس الزمني · الفصل الأول · المدة الكلية ' + hms(total), terra='terra_wave_open', items=items)]), ensure_ascii=False) + ';\n'
open(f'{root}/content/index.js', 'w').write(js)
subprocess.run([sys.executable, f'{root}/tools/produce.py', 'index'], check=True)
idur = dur(f'{V}/index.mp4'); print('intro', idur, 'expected', INTRO)
lst = [f'{V}/index.mp4'] + [f'{V}/{l[0]}.mp4' for l in LESSONS]
open('/tmp/concat.txt', 'w').write(''.join(f"file '{p}'\n" for p in lst))
meta = ';FFMETADATA1\ntitle=مراجعة الدراسات الاجتماعية – الصف العاشر\n'
chap = [('الفهرس الزمني', 0, idur)] + [(f'{l[2]}: {l[3]}', s, s + d) for l, s, d in zip(LESSONS, [idur + (s - INTRO) for s in starts], durs)]
for title, a, b in chap:
    meta += f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(a * 1000)}\nEND={int(b * 1000)}\ntitle={title}\n'
open('/tmp/meta.txt', 'w').write(meta)
out = f'{V}/all_lessons.mp4'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', '/tmp/concat.txt', '-i', '/tmp/meta.txt', '-map', '0', '-map_metadata', '1', '-map_chapters', '1', '-c', 'copy', '-movflags', '+faststart', out], check=True)
print(out, hms(dur(out)), round(os.path.getsize(out) / 1e6), 'MB')
for it in items: print(it['time'], it['tag'], it['name'])
