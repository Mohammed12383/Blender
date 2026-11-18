"""Compartment shells: hull walls, floor, ribs, pipe runs, cable trays, bulkheads.

The pressure hull runs along +X. Interior cross-section (YZ):
  straight walls at y = ±2.5 up to z = 2.1, rounded into a flat ceiling at z = 2.9.
"""

import math

import bmesh
from mathutils import Matrix, Vector

from .core import Prop, R, bm_box, bm_plate_with_holes, bm_sweep, bm_torus, circle, mat, rrect, rounded_path, box_uv
from . import props_common as pc

HALF_W = 2.5
WALL_TOP = 2.1
CEIL = 2.9
ARC_R = CEIL - WALL_TOP          # 0.8
SKIRT = 0.12
DADO = 1.0
DOOR_HOLE = (1.0, 1.9, 0.45)     # w, h, corner of the bulkhead hole (door frame covers the edge)
DOOR_CZ = 0.12 + 0.9 + 0.0


def profile_points(n_arc=10):
    """(y, z, material) points from the right floor corner over the ceiling to the left floor corner."""
    pts = [(HALF_W, 0.0, "PaintGraphite"), (HALF_W, SKIRT, "WallTeal"), (HALF_W, DADO, "WallCream")]
    cy, cz = HALF_W - ARC_R, WALL_TOP
    pts.append((HALF_W, WALL_TOP, "WallCream"))
    for k in range(1, n_arc + 1):
        a = R(90 * k / n_arc)
        pts.append((cy + ARC_R * math.cos(a), cz + ARC_R * math.sin(a), "WallCream"))
    for k in range(n_arc - 1, -1, -1):
        a = R(90 * k / n_arc)
        pts.append((-(cy + ARC_R * math.cos(a)), cz + ARC_R * math.sin(a), "WallCream"))
    pts += [(-HALF_W, DADO, "WallTeal"), (-HALF_W, SKIRT, "PaintGraphite"), (-HALF_W, 0.0, None)]
    return pts


def section_polygon():
    """Closed YZ outline of the hull interior (for bulkhead plates)."""
    return [(y, z) for y, z, _ in profile_points()]


def _walls(p, x0, x1, parent):
    pts = profile_points()
    mats = ["PaintGraphite", "WallTeal", "WallCream"]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.dist(a[:2], b[:2]))
    ring0 = [bm.verts.new((x0, y, z)) for y, z, _ in pts]
    ring1 = [bm.verts.new((x1, y, z)) for y, z, _ in pts]
    for i in range(len(pts) - 1):
        f = bm.faces.new((ring0[i], ring0[i + 1], ring1[i + 1], ring1[i]))
        mid = Vector(((x0 + x1) / 2, (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2))
        f.normal_update()
        inward = Vector((0, -mid.y, 1.45 - mid.z))
        if f.normal.dot(inward) < 0:
            f.normal_flip()
        f.material_index = mats.index(pts[i][2])
        tile = mat(pts[i][2]).get("tile", 1.0)
        for loop in f.loops:
            idx = ring0.index(loop.vert) if loop.vert in ring0 else ring1.index(loop.vert)
            loop[uvl].uv = (loop.vert.co.x / tile, s[idx] / tile)
    p.add(bm, mats, parent=parent, uv="keep", smooth=False, name="walls")
    # dado rail and skirting lip along both walls
    for side in (-1, 1):
        p.box((x1 - x0, 0.035, 0.05), ((x0 + x1) / 2, side * (HALF_W - 0.0175), DADO), "PaintGraphite", bevel=0.008, parent=parent)
        p.box((x1 - x0, 0.02, 0.02), ((x0 + x1) / 2, side * (HALF_W - 0.01), SKIRT), "PaintGraphite", bevel=0.004, parent=parent)


def _floor(p, x0, x1, m, parent):
    bm = bm_box(x1 - x0, HALF_W * 2, 0.1, ((x0 + x1) / 2, 0, -0.05))
    p.add(bm, m, parent=parent, smooth=False, name="floor")
    if m == "FloorPlate":  # deck plate seams
        x = x0 + 1.2
        while x < x1 - 0.3:
            p.box((0.012, HALF_W * 2 - 0.02, 0.004), (x, 0, 0.0005), "DarkSteel", bevel=0, parent=parent)
            x += 1.2
        p.box((x1 - x0, 0.012, 0.004), ((x0 + x1) / 2, 0, 0.0005), "DarkSteel", bevel=0, parent=parent)


def _rib_path():
    pts = profile_points(12)
    return [Vector((0, y, z)) for y, z, _ in pts[1:-1]]


RIB_SECTION = [(-0.015, 0.01), (0.015, 0.01), (0.015, -0.055), (0.06, -0.055), (0.06, -0.075),
               (-0.06, -0.075), (-0.06, -0.055), (-0.015, -0.055)]


def _ribs(p, x0, x1, step, parent, skip=()):
    n = max(1, int((x1 - x0) / step))
    xs = [x0 + (x1 - x0) * (k + 0.5) / n for k in range(n)]
    for x in xs:
        if any(abs(x - s) < 0.4 for s in skip):
            continue
        bm = bm_sweep(_rib_path(), RIB_SECTION, caps=True, up=(1, 0, 0))
        p.add(bm, "PaintCream", (x, 0, 0), parent=parent, smooth=35, name="rib")
    return xs


PIPES_RIGHT = [(18, 0.065, "PaintRed"), (45, 0.045, "PaintMustard"), (68, 0.04, "DarkSteel"), (84, 0.03, "Copper")]
PIPES_LEFT = [(20, 0.055, "PaintNavy"), (42, 0.07, "DarkSteel"), (64, 0.035, "PaintMustard"), (82, 0.03, "Copper")]


def _arc_pos(side, ang, r):
    cy, cz = HALF_W - ARC_R, WALL_TOP
    d = ARC_R - r - 0.09
    return side * (cy + d * math.cos(R(ang))), cz + d * math.sin(R(ang))


def _pipes(p, x0, x1, rib_xs, parent):
    for side, spec in ((1, PIPES_RIGHT), (-1, PIPES_LEFT)):
        for ang, r, m in spec:
            y, z = _arc_pos(side, ang, r)
            p.cyl(r, x1 - x0, ((x0 + x1) / 2, y, z), m, axis="X", segs=16, parent=parent, name="pipe")
            # flanges with bolts
            fx = x0 + 0.9
            while fx < x1 - 0.5:
                for dx in (-0.018, 0.018):
                    p.cyl(r * 1.55, 0.03, (fx + dx, y, z), m, axis="X", segs=20, bevel=0.004, parent=parent, name="flange")
                for k in range(6):
                    a = k * math.pi / 3
                    p.cyl(0.007, 0.08, (fx, y + math.cos(a) * r * 1.3, z + math.sin(a) * r * 1.3), "Steel",
                          axis="X", segs=6, parent=parent, name="bolt")
                fx += 2.6
            # clamps at the ribs
            for rx in rib_xs:
                cx = rx + 0.09
                if cx > x1 - 0.1:
                    continue
                p.add(bm_torus(r + 0.008, 0.008, 20, 6, "X"), "DarkSteel", (cx, y, z), parent=parent, smooth=180, name="clamp")
                wy, wz = _arc_pos(side, ang, -0.09)
                p.tube([(cx, y + (wy - y) * (r + 0.01) / math.hypot(wy - y, wz - z), z + (wz - z) * (r + 0.01) / math.hypot(wy - y, wz - z)),
                        (cx, wy, wz)], 0.008, "DarkSteel", segs=6, parent=parent, name="hanger")
    # straight conduit bundle on the left ceiling
    for k, (dy, r, m) in enumerate([(0, 0.022, "PaintGraphite"), (0.06, 0.018, "PaintGraphite"), (0.115, 0.015, "Steel")]):
        p.cyl(r, x1 - x0, ((x0 + x1) / 2, -0.75 + dy, CEIL - 0.06), m, axis="X", segs=12, parent=parent, name="conduit")


def _cable_tray(p, x0, x1, parent, y=0.75):
    z = CEIL - 0.2
    w = 0.42
    for side in (-1, 1):
        p.box((x1 - x0, 0.012, 0.06), ((x0 + x1) / 2, y + side * w / 2, z + 0.03), "PaintGray", bevel=0.003, parent=parent)
    x = x0 + 0.15
    while x < x1:
        p.box((0.03, w, 0.012), (x, y, z), "PaintGray", bevel=0.002, parent=parent, name="rung")
        x += 0.3
    for hx in [x0 + 0.5 + k * 1.5 for k in range(int((x1 - x0 - 0.5) / 1.5) + 1)]:
        for side in (-1, 1):
            p.cyl(0.006, 0.2, (hx, y + side * (w / 2 + 0.012), z + 0.1), "Steel", segs=6, parent=parent, name="rod")
    cables = [(-0.15, 0.018, "BlackPlastic"), (-0.1, 0.014, "PaintRed"), (-0.06, 0.02, "BlackPlastic"),
              (-0.015, 0.012, "PaintNavy"), (0.03, 0.016, "Rubber"), (0.07, 0.012, "PaintMustard"),
              (0.11, 0.018, "BlackPlastic"), (0.15, 0.01, "PaintWhite")]
    for k, (dy, r, m) in enumerate(cables):
        pts = []
        n = int((x1 - x0) / 0.5) + 1
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n
            pts.append((xx, y + dy + 0.01 * math.sin(i * 1.3 + k), z + 0.006 + r + 0.004 * math.sin(i * 0.7 + k * 2)))
        p.tube(pts, r, m, segs=8, parent=parent, name="cable")


def _duct(p, x0, x1, parent, y=-1.25):
    """Rectangular ventilation duct under the ceiling with flanges, hangers and outlet grilles."""
    w, h = 0.34, 0.2
    z = CEIL - 0.03 - h / 2
    p.box((x1 - x0, w, h), ((x0 + x1) / 2, y, z), "PaintGray", bevel=0.01, parent=parent, name="duct")
    x = x0 + 0.6
    while x < x1 - 0.2:
        p.box((0.04, w + 0.03, h + 0.03), (x, y, z), "PaintGray", bevel=0.006, parent=parent, name="flange")
        p.box((0.03, 0.03, 0.04), (x, y - w / 2 + 0.02, CEIL - 0.015), "DarkSteel", bevel=0, parent=parent)
        p.box((0.03, 0.03, 0.04), (x, y + w / 2 - 0.02, CEIL - 0.015), "DarkSteel", bevel=0, parent=parent)
        x += 1.2
    x = x0 + 1.2
    while x < x1 - 0.6:
        p.box((0.3, w - 0.06, 0.012), (x, y, z - h / 2 - 0.006), "PaintGraphite", bevel=0.003, parent=parent, name="grille")
        for k in range(6):
            p.box((0.27, 0.012, 0.01), (x, y - (w - 0.1) / 2 + k * (w - 0.1) / 5, z - h / 2 - 0.014), "DarkSteel",
                  bevel=0, rot=(30, 0, 0), parent=parent, name="vane")
        x += 2.4


def compartment(col, name, x0, x1, floor="FloorPlate", rib_step=1.6, rib_skip=(), lamp_xs=None, lib=None,
                tray=True, duct=True, duct_x1=None):
    """Build a room shell between x0 and x1. Returns the shell root."""
    p = Prop(name, col=col, category="room_shell")
    walls = p.body
    floor_g = p.pivot("Floor", category="floor", walkable=True)
    detail = p.pivot("Structure", category="structure")
    _walls(p, x0, x1, walls)
    _floor(p, x0, x1, floor, floor_g)
    rib_xs = _ribs(p, x0, x1, rib_step, detail, rib_skip)
    _pipes(p, x0, x1, rib_xs, detail)
    if tray:
        _cable_tray(p, x0, x1, detail)
    if duct:
        _duct(p, x0, duct_x1 or x1, detail)
    return p.finish()


def bulkhead(col, name, x, holes=(), thickness=0.3, door=True):
    """Transverse bulkhead plate between x and x+thickness with holes (YZ polygons)."""
    p = Prop(name, col=col, category="bulkhead")
    outer = section_polygon()
    hs = list(holes)
    if door:
        w, h, c = DOOR_HOLE
        hs.append([(y, z + DOOR_CZ) for y, z in rrect(w, h, c, 8)])
    bm = bm_plate_with_holes(outer, [list(reversed(hh)) for hh in hs], thickness)
    # plate built in XY (=YZ of the hull) with thickness along Z -> rotate into place
    m = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))  # (a,b,c) -> (c,a,b): plate x->Y, y->Z, z->X
    for v in bm.verts:
        v.co = m @ v.co
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                           plane_co=(0, 0, DADO), plane_no=(0, 0, 1))
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                           plane_co=(0, 0, SKIRT), plane_no=(0, 0, 1))
    for f in bm.faces:
        cz = f.calc_center_median().z
        f.material_index = 2 if cz < SKIRT else (1 if cz < DADO else 0)
    p.add(bm, ["WallCream", "WallTeal", "PaintGraphite"], (x, 0, 0), smooth=False, name="plate")
    return p.finish()
