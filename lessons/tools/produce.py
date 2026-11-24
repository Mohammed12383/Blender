"""python tools/produce.py <lesson-id> [--workers 4] [--crf 26]  ->  lessons/videos/<id>.mp4
Renders frames with Chromium, synthesises the soundtrack from the cue list, muxes with ffmpeg."""
import json, os, subprocess, sys, shutil
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lid = sys.argv[1]
extra = sys.argv[2:]
out = f'{root}/out/{lid}'
os.makedirs(out, exist_ok=True)
subprocess.run(['node', f'{root}/tools/render.cjs', lid, '--out', out] + extra, check=True)
subprocess.run([sys.executable, f'{root}/audio/synth.py', f'{out}/info.json', f'{out}/audio.wav', lid], check=True)
os.makedirs(f'{root}/videos', exist_ok=True)
dst = f'{root}/videos/{lid}.mp4'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{out}/video_silent.mp4', '-i', f'{out}/audio.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', dst], check=True)
info = json.load(open(f'{out}/info.json'))
print(f'{dst}  {info["total"] / 60:.1f} min  {os.path.getsize(dst) / 1e6:.1f} MB')
