"""Re-render only the crew lineup image:  python submarine/scripts/lineup.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from sublib import core, humans, render, tex  # noqa: E402

tex.generate_all()
core.reset_scene()
cast = {a["role"]: a for a in humans.build_all(core.collection("Crew"))}
rc = core.collection("RenderCrew")
line = bpy.data.objects.new("CrewLineup", None)
rc.objects.link(line)
for i, (role, pose) in enumerate([("navigator", "wave"), ("weapons_officer", "relaxed"), ("torpedo_loader", "operate"), ("cook", "relaxed")]):
    humans.place_copy(cast[role], rc, (-1.35 + i * 0.9, 0, 0), 0, pose).parent = line
core.layer_collection("Crew").exclude = True
render.preview(line, os.path.join(core.SUB_DIR, "renders", "crew_lineup.png"), samples=64, size=(1600, 900), view=(0, -1, 0.12))
