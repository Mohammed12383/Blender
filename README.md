# Blender models

3D models built with Python scripts that drive Blender's API (`bpy`). Each
model is a script, so it can be regenerated, tweaked and version-controlled.

## Projects

### Submarine: 4-player co-op crew game

A complete, game-ready submarine interior on two decks: eight compartments (control room, torpedo room,
engine room with two detailed diesels, battery room, crew mess, galley, sick bay, grated engine passage),
about 100 props with moving parts, four rigged crew characters and exterior ships.
See **[submarine/README.md](submarine/README.md)**.

![Engine room](submarine/renders/engine_room.png)

### Deepwater Crew: the playable game

A browser game that uses these models: 1–4 players crew the submarine, drive and dive it, hunt
convoys through the periscope, plan a route on the chart table, aim and fire torpedoes, reload them by hand, and
fight enemy subs, sharks and a giant squid. A ship-status console shows every system at a glance. Keep the boat alive: fix hull leaks with a wrench, pump out rising flood water (and swim when it
gets deep), fight fires and clear the smoke, run and repair the diesels, and reset the switchboard.
See **[game/README.md](game/README.md)**.

```bash
cd game && npm install && npm start      # then open http://localhost:8080/game/
```

### Small models

| Model | Script | Files |
|-------|--------|-------|
| Toy rocket on a launch pad | [`scripts/rocket.py`](scripts/rocket.py) | [`rocket.blend`](models/rocket.blend), [`rocket.glb`](models/rocket.glb), [`rocket.png`](renders/rocket.png) |

- **`.blend`** opens in Blender with the full scene: model, lights, camera and render settings.
- **`.glb`** is the model on its own, for game engines (Unity, Godot, Unreal), three.js or online viewers.

## Running the scripts

Blender is installed as a Python module from PyPI, so no Blender app or screen is needed. It needs Python 3.13.

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/rocket.py            # full render (a few minutes on CPU)
.venv/bin/python scripts/rocket.py --preview  # quick low-quality render
```

If you have the Blender app installed, the same script runs with `blender --background --python scripts/rocket.py`.
