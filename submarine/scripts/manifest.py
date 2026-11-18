"""Write models/manifest.json and ASSETS.md: every prop, its moving parts and interaction points.

Run after build.py:  python submarine/scripts/manifest.py
"""
import json
import os
import sys

import bpy

SUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
blend = os.path.join(SUB, "models", "Submarine_Interior.blend")
out_json, out_md = os.path.join(SUB, "models", "manifest.json"), os.path.join(SUB, "ASSETS.md")
bpy.ops.wm.open_mainfile(filepath=blend)
lib = bpy.data.collections["Library"]
crew = bpy.data.collections.get("Crew")

SKIP = {"interaction", "_part"}


def extras(o):
    return {k: (v if isinstance(v, (int, float, str, bool)) else list(v)) for k, v in o.items() if k not in SKIP and not k.startswith("_")}


props = []
for root in sorted([o for o in lib.objects if o.parent is None and o.type == "EMPTY"], key=lambda o: o.name):
    entry = dict(name=root.name, **extras(root), parts=[], interaction_points=[], lights=[])
    for o in root.children_recursive:
        short = o.name[len(root.name) + 1:] if o.name.startswith(root.name + "_") else o.name
        if o.type == "EMPTY" and "interaction" in o.keys():
            entry["interaction_points"].append(dict(name=o.name, interaction=o["interaction"], **extras(o)))
        elif o.type == "LIGHT":
            entry["lights"].append(o.name)
        elif o.type == "MESH" and short != "Body":
            entry["parts"].append(dict(name=o.name, **extras(o)))
    props.append(entry)
chars = []
if crew:
    for a in sorted([o for o in crew.objects if o.type == "ARMATURE"], key=lambda o: o.name):
        chars.append(dict(name=a.name, role=a.get("role"), bones=[b.name for b in a.data.bones]))
json.dump(dict(props=props, characters=chars), open(out_json, "w"), indent=1)

lines = ["# Asset manifest", "", "Generated from `models/Submarine_Interior.blend`. Every prop is also exported on its own",
         "as `models/props/<Name>.glb`. Moving parts are separate nodes with their origin on the hinge/axis.", "",
         "| Prop | Category | Moving parts (interaction) | Interaction points |", "|---|---|---|---|"]
for e in props:
    parts = ", ".join(f"`{p['name'].split('_', 1)[1]}` ({p.get('interact', '-')})" for p in e["parts"]) or "–"
    pts = ", ".join(f"`{p['interaction']}`" for p in e["interaction_points"]) or "–"
    cat = e.get("category", "")
    if e.get("station"):
        cat += f" · {e['station']}"
    lines.append(f"| {e['name']} | {cat} | {parts} | {pts} |")
lines += ["", "## Characters", "", "| Character | Role | Bones |", "|---|---|---|"]
for c in chars:
    lines.append(f"| {c['name']} | {c['role']} | {len(c['bones'])} ({', '.join(c['bones'][:5])}, …) |")
open(out_md, "w").write("\n".join(lines) + "\n")
print("manifest:", len(props), "props,", len(chars), "characters")
