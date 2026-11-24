import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blender import kit, chars
SP = '/tmp/claude-0/-home-user-Blender/02b4fa82-242b-5f8f-94d2-1d7c45ca5b57/scratchpad/t'
who = sys.argv[sys.argv.index('--')+1]
t = time.time()
kit.reset(); kit.setup_render(480, 640, samples=32)
kit.studio(scale=1.2)
if who == 'terra':
    chars.terra(expr='open', pose='wave'); kit.camera((0, -7.2, 0.35), (0, 0, 0.05), lens=60)
else:
    chars.person(who, expr='open', pose='wave'); kit.camera((0, -7.6, 1.45), (0, 0, 1.45), lens=60)
kit.render_to(f'{SP}/cast_{who}.png')
print('time', round(time.time() - t, 1))
