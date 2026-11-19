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


LOWER_FLOOR = -2.9      # lower deck floor
LOWER_CEIL = -0.12      # lower deck ceiling (just under the upper deck plating)
LOWER_HALF_W = 2.4


def profile_points(n_arc=10, floor_z=0.0):
    """(y, z, material) points from the right floor corner over the ceiling to the left floor corner.

    floor_z < 0 extends the walls down into a pit."""
    pts = []
    if floor_z < -0.01:
        pts.append((HALF_W, floor_z, "WallTeal"))
    pts += [(HALF_W, 0.0, "PaintGraphite"), (HALF_W, SKIRT, "WallTeal"), (HALF_W, DADO, "WallCream")]
    cy, cz = HALF_W - ARC_R, WALL_TOP
    pts.append((HALF_W, WALL_TOP, "WallCream"))
    for k in range(1, n_arc + 1):
        a = R(90 * k / n_arc)
        pts.append((cy + ARC_R * math.cos(a), cz + ARC_R * math.sin(a), "WallCream"))
    for k in range(n_arc - 1, -1, -1):
        a = R(90 * k / n_arc)
        pts.append((-(cy + ARC_R * math.cos(a)), cz + ARC_R * math.sin(a), "WallCream"))
    pts += [(-HALF_W, DADO, "WallTeal"), (-HALF_W, SKIRT, "PaintGraphite")]
    if floor_z < -0.01:
        pts += [(-HALF_W, 0.0, "WallTeal"), (-HALF_W, floor_z, None)]
    else:
        pts += [(-HALF_W, 0.0, None)]
    return pts


def lower_profile_points():
    """Lower deck: straight walls, flat ceiling under the upper deck."""
    W, f, c = LOWER_HALF_W, LOWER_FLOOR, LOWER_CEIL
    return [(W, f, "PaintGraphite"), (W, f + SKIRT, "WallTeal"), (W, f + DADO + 0.2, "WallCream"), (W, c, "WallCream"),
            (-W, c, "WallCream"), (-W, f + DADO + 0.2, "WallTeal"), (-W, f + SKIRT, "PaintGraphite"), (-W, f, None)]


def section_polygon(kind="upper", floor_z=0.0):
    """Closed YZ outline of the hull interior (for bulkhead plates). floor_z < 0: upper plate reaching into a pit."""
    if kind == "lower":
        W, f = LOWER_HALF_W + 0.1, LOWER_FLOOR
        return [(W, f), (W, 0.0), (-W, 0.0), (-W, f)]
    return [(y, z) for y, z, _ in profile_points(floor_z=floor_z)]


def _walls(p, x0, x1, parent, pts=None, center_z=1.45, rails=True):
    pts = pts or profile_points()
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
        inward = Vector((0, -mid.y, center_z - mid.z))
        if f.normal.dot(inward) < 0:
            f.normal_flip()
        f.material_index = mats.index(pts[i][2])
        tile = mat(pts[i][2]).get("tile", 1.0)
        for loop in f.loops:
            idx = ring0.index(loop.vert) if loop.vert in ring0 else ring1.index(loop.vert)
            loop[uvl].uv = (loop.vert.co.x / tile, s[idx] / tile)
    p.add(bm, mats, parent=parent, uv="keep", smooth=False, name="walls")
    if not rails:
        return
    # dado rail and skirting lip along both walls
    for side in (-1, 1):
        p.box((x1 - x0, 0.035, 0.05), ((x0 + x1) / 2, side * (HALF_W - 0.0175), DADO), "PaintGraphite", bevel=0.008, parent=parent)
        p.box((x1 - x0, 0.02, 0.02), ((x0 + x1) / 2, side * (HALF_W - 0.01), SKIRT), "PaintGraphite", bevel=0.004, parent=parent)


def _floor(p, x0, x1, m, parent, holes=(), z=0.0, half_w=HALF_W):
    """Deck plating (top at z). holes = [(xa, xb, ya, yb)] rectangular openings (stairwells)."""
    if holes:
        outer = [(x0, -half_w), (x1, -half_w), (x1, half_w), (x0, half_w)]
        hs = [[(xa, ya), (xa, yb), (xb, yb), (xb, ya)] for xa, xb, ya, yb in holes]
        bm = bm_plate_with_holes(outer, hs, 0.1)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, z - 0.1))
    else:
        bm = bm_box(x1 - x0, half_w * 2, 0.1, ((x0 + x1) / 2, 0, z - 0.05))
    p.add(bm, m, parent=parent, smooth=False, name="floor")
    for xa, xb, ya, yb in holes:   # hazard edging around openings
        for (cx, cy, sx, sy) in [((xa + xb) / 2, ya, xb - xa, 0.05), ((xa + xb) / 2, yb, xb - xa, 0.05),
                                 (xa, (ya + yb) / 2, 0.05, yb - ya), (xb, (ya + yb) / 2, 0.05, yb - ya)]:
            p.box((sx, sy, 0.012), (cx, cy, z + 0.006), "Hazard", bevel=0, parent=parent, name="edge")
    if holes:
        return
    if m == "FloorPlate":  # deck plate seams
        x = x0 + 1.2
        while x < x1 - 0.3:
            p.box((0.012, half_w * 2 - 0.02, 0.004), (x, 0, z + 0.0005), "DarkSteel", bevel=0, parent=parent)
            x += 1.2
        p.box((x1 - x0, 0.012, 0.004), ((x0 + x1) / 2, 0, z + 0.0005), "DarkSteel", bevel=0, parent=parent)


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


def _duct(p, x0, x1, parent, y=-1.25, ceil=CEIL):
    """Rectangular ventilation duct under the ceiling with flanges, hangers and outlet grilles."""
    w, h = 0.34, 0.2
    CEIL_ = ceil
    z = ceil - 0.03 - h / 2
    p.box((x1 - x0, w, h), ((x0 + x1) / 2, y, z), "PaintGray", bevel=0.01, parent=parent, name="duct")
    x = x0 + 0.6
    while x < x1 - 0.2:
        p.box((0.04, w + 0.03, h + 0.03), (x, y, z), "PaintGray", bevel=0.006, parent=parent, name="flange")
        p.box((0.03, 0.03, 0.04), (x, y - w / 2 + 0.02, CEIL_ - 0.015), "DarkSteel", bevel=0, parent=parent)
        p.box((0.03, 0.03, 0.04), (x, y + w / 2 - 0.02, CEIL_ - 0.015), "DarkSteel", bevel=0, parent=parent)
        x += 1.2
    x = x0 + 1.2
    while x < x1 - 0.6:
        p.box((0.3, w - 0.06, 0.012), (x, y, z - h / 2 - 0.006), "PaintGraphite", bevel=0.003, parent=parent, name="grille")
        for k in range(6):
            p.box((0.27, 0.012, 0.01), (x, y - (w - 0.1) / 2 + k * (w - 0.1) / 5, z - h / 2 - 0.014), "DarkSteel",
                  bevel=0, rot=(30, 0, 0), parent=parent, name="vane")
        x += 2.4


def _pit(p, x0, x1, px0, px1, depth, floor, walls, floor_g, detail):
    """Deck at z=0 outside [px0, px1]; a machinery pit (floor at -depth) inside it."""
    for xa, xb in ((x0, px0), (px1, x1)):
        if xb - xa > 0.01:
            _walls(p, xa, xb, walls)
            _floor(p, xa, xb, floor, floor_g)
    _walls(p, px0, px1, walls, pts=profile_points(floor_z=-depth), center_z=0.9)
    p.add(bm_box(px1 - px0, HALF_W * 2, 0.1, ((px0 + px1) / 2, 0, -depth - 0.05)), "FloorPlate", parent=floor_g, smooth=False,
          name="pitfloor")
    for x, sgn in ((px0, 1), (px1, -1)):
        if (sgn > 0 and px0 > x0 + 0.01) or (sgn < 0 and px1 < x1 - 0.01):
            p.box((0.1, HALF_W * 2, depth), (x - sgn * 0.05, 0, -depth / 2), "WallTeal", bevel=0, parent=walls, name="pitwall")
            p.box((0.06, HALF_W * 2, 0.012), (x + sgn * 0.03, 0, 0.006), "Hazard", bevel=0, parent=floor_g, name="pitedge")


def compartment(col, name, x0, x1, floor="FloorPlate", rib_step=1.6, rib_skip=(), lamp_xs=None, lib=None,
                tray=True, duct=True, duct_x1=None, holes=(), pit=None):
    """Build a room shell between x0 and x1. holes: stairwell openings; pit: (px0, px1, depth). Returns the shell root."""
    p = Prop(name, col=col, category="room_shell")
    walls = p.body
    floor_g = p.pivot("Floor", category="floor", walkable=True)
    detail = p.pivot("Structure", category="structure")
    if pit:
        _pit(p, x0, x1, *pit, floor, walls, floor_g, detail)
    else:
        _walls(p, x0, x1, walls)
        _floor(p, x0, x1, floor, floor_g, holes=holes)
    rib_xs = _ribs(p, x0, x1, rib_step, detail, rib_skip)
    _pipes(p, x0, x1, rib_xs, detail)
    if tray:
        _cable_tray(p, x0, x1, detail)
    if duct:
        _duct(p, x0, duct_x1 or x1, detail)
    return p.finish()


DUCT_UNDERSIDE = CEIL - 0.03 - 0.2           # z of the upper-deck duct underside (duct fans hang here)
LOWER_DUCT_UNDERSIDE = LOWER_CEIL - 0.03 - 0.2
LOWER_DUCT_Y = -1.1


def _in_holes(x, holes, pad=0.12):
    return [h for h in holes if h[0] - pad <= x <= h[1] + pad]


def _pipe_run(p, xa, xb, y, z, r, m, parent, top, up_a=False, up_b=False):
    """Horizontal pipe from xa to xb; up_a/up_b turn the ends up through the deckhead with a flange."""
    if xb - xa > 0.05:
        p.cyl(r, xb - xa, ((xa + xb) / 2, y, z), m, axis="X", segs=16, parent=parent, name="pipe")
    for x, up in ((xa, up_a), (xb, up_b)):
        if up:
            p.sphere(r * 1.05, (x, y, z), m, segs=16, parent=parent, name="elbow")
            p.cyl(r, top - z, (x, y, (z + top) / 2), m, segs=16, parent=parent, name="riser")
            p.cyl(r * 1.5, 0.03, (x, y, top - 0.015), m, segs=16, bevel=0.004, parent=parent, name="flange")


def lower_compartment(col, name, x0, x1, floor="FloorPlate", rib_step=1.6, holes=(), duct=True):
    """Lower-deck room: straight walls, flat deckhead under the upper deck with beams, pipes and cables.

    holes = [(xa, xb, ya, yb)] openings in the deckhead (stairwells) - beams and pipes are routed round them."""
    p = Prop(name, col=col, category="room_shell", deck="lower")
    walls = p.body
    floor_g = p.pivot("Floor", category="floor", walkable=True)
    detail = p.pivot("Structure", category="structure")
    W, f, c = LOWER_HALF_W, LOWER_FLOOR, LOWER_CEIL
    _walls(p, x0, x1, walls, pts=[(W, f, "PaintGraphite"), (W, f + SKIRT, "WallTeal"), (W, f + DADO + 0.2, "WallCream"), (W, c, None)],
           center_z=-1.5, rails=False)
    _walls(p, x0, x1, walls, pts=[(-W, c, "WallCream"), (-W, f + DADO + 0.2, "WallTeal"), (-W, f + SKIRT, "PaintGraphite"), (-W, f, None)],
           center_z=-1.5, rails=False)
    outer = [(x0, -W), (x1, -W), (x1, W), (x0, W)]
    hs = [[(xa, ya), (xa, yb), (xb, yb), (xb, ya)] for xa, xb, ya, yb in holes]
    bm = bm_plate_with_holes(outer, hs, 0.02) if hs else bm_box(x1 - x0, W * 2, 0.02, ((x0 + x1) / 2, 0, 0.01))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, c))
    p.add(bm, "WallCream", parent=walls, smooth=False, name="deckhead")
    for xa, xb, ya, yb in holes:       # coaming round the opening
        for (cx, cy, sx, sy) in [((xa + xb) / 2, ya, xb - xa + 0.08, 0.04), ((xa + xb) / 2, yb, xb - xa + 0.08, 0.04),
                                 (xa, (ya + yb) / 2, 0.04, yb - ya), (xb, (ya + yb) / 2, 0.04, yb - ya)]:
            p.box((sx, sy, 0.14), (cx, cy, c - 0.07), "Hazard", bevel=0.004, parent=detail, name="coaming")
    for side in (-1, 1):
        p.box((x1 - x0, 0.035, 0.05), ((x0 + x1) / 2, side * (W - 0.0175), f + DADO + 0.2), "PaintGraphite",
              bevel=0.008, parent=walls)
        p.box((x1 - x0, 0.02, 0.02), ((x0 + x1) / 2, side * (W - 0.01), f + SKIRT), "PaintGraphite", bevel=0.004, parent=walls)
    n = max(1, int((x1 - x0) / rib_step))
    for k in range(n):
        x = x0 + (x1 - x0) * (k + 0.5) / n
        hit = _in_holes(x, holes)
        if hit:   # short beam stopping at the opening (openings are against the port wall)
            ya = min(h[2] for h in hit) - 0.05
            p.box((0.12, ya + W, 0.16), (x, (ya - W) / 2, c - 0.08), "PaintCream", bevel=0.01, parent=detail, name="beam")
        else:
            p.box((0.12, W * 2, 0.16), (x, 0, c - 0.08), "PaintCream", bevel=0.01, parent=detail, name="beam")
        for side in (-1, 1):
            p.box((0.12, 0.075, abs(f - c) - 0.15), (x, side * (W - 0.0375), (f + c) / 2 + 0.05),
                  "PaintCream", bevel=0.01, parent=detail, name="rib")
    for side, specs in ((1, [(0.06, "PaintRed", 0.18), (0.045, "PaintMustard", 0.38)]), (-1, [(0.07, "DarkSteel", 0.2), (0.04, "Copper", 0.4)])):
        for r, m, off in specs:
            y, z = side * (W - off), c - 0.25
            blocked = sorted((h[0] - 0.15, h[1] + 0.15) for h in holes if h[2] - 0.1 <= y <= h[3] + 0.1)
            xa = x0
            for ba, bb in blocked:
                _pipe_run(p, xa, ba, y, z, r, m, detail, c, up_a=xa > x0, up_b=True)
                xa = bb
            _pipe_run(p, xa, x1, y, z, r, m, detail, c, up_a=xa > x0)
    for k, (dy, r, m) in enumerate([(0, 0.022, "PaintGraphite"), (0.06, 0.018, "BlackPlastic"), (0.11, 0.015, "PaintRed")]):
        p.cyl(r, x1 - x0, ((x0 + x1) / 2, -0.6 + dy, c - 0.2), m, axis="X", segs=12, parent=detail, name="conduit")
    if duct:
        _duct(p, x0, x1, detail, y=LOWER_DUCT_Y, ceil=c)
    _floor(p, x0, x1, floor, floor_g, z=f, half_w=W)
    return p.finish()


def bulkhead(col, name, x, holes=(), thickness=0.3, door=True, kind="upper", floor_z=0.0):
    """Transverse bulkhead plate between x and x+thickness with holes (YZ polygons). kind: upper / lower deck.

    floor_z < 0 extends an upper-deck plate down to the floor of an adjoining machinery pit."""
    p = Prop(name, col=col, category="bulkhead", deck=kind)
    outer = section_polygon(kind, floor_z)
    hs = list(holes)
    if door:
        w, h, c = DOOR_HOLE
        base = LOWER_FLOOR if kind == "lower" else 0.0
        hs.append([(y, z + DOOR_CZ + base) for y, z in rrect(w, h, c, 8)])
    bm = bm_plate_with_holes(outer, [list(reversed(hh)) for hh in hs], thickness)
    # plate built in XY (=YZ of the hull) with thickness along Z -> rotate into place
    m = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))  # (a,b,c) -> (c,a,b): plate x->Y, y->Z, z->X
    for v in bm.verts:
        v.co = m @ v.co
    base = LOWER_FLOOR if kind == "lower" else 0.0
    dado = base + DADO + (0.2 if kind == "lower" else 0.0)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                           plane_co=(0, 0, dado), plane_no=(0, 0, 1))
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                           plane_co=(0, 0, base + SKIRT), plane_no=(0, 0, 1))
    if floor_z < -0.01:
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                               plane_co=(0, 0, 0.0), plane_no=(0, 0, 1))
    for f in bm.faces:
        cz = f.calc_center_median().z
        f.material_index = 1 if cz < base - 0.005 else (2 if cz < base + SKIRT else (1 if cz < dado else 0))
    p.add(bm, ["WallCream", "WallTeal", "PaintGraphite"], (x, 0, 0), smooth=False, name="plate")
    return p.finish()
