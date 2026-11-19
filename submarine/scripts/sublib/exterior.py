"""Exterior models: our submarine's hull, and two surface ships used as targets.

Ships float with the waterline at z = 0 and point their bow towards +X.
"""

import math
import random

import bmesh
from mathutils import Matrix, Vector

from . import core
from .core import Prop, R, bm_box, bm_cyl, bm_extrude, bm_lathe, bm_sweep, bm_torus, circle, rrect, rect, rounded_path

core.MATLIB.update({
    "HullTeal": dict(color="#244f55", roughness=0.55, coat=0.2),
    "AntiFoul": dict(color="#a8402c", roughness=0.7),
    "BootTop": dict(color="#1c1f22", roughness=0.6),
    "NavyGray": dict(color="#7d858c", roughness=0.6),
    "NavyGrayDark": dict(color="#5d656c", roughness=0.6),
    "DeckGreen": dict(color="#4d5a4a", roughness=0.8),
    "WindowDark": dict(color="#0e171d", roughness=0.05, coat=1.0),
    "ContainerRed": dict(color="#b5432f", roughness=0.6), "ContainerBlue": dict(color="#2f5f8f", roughness=0.6),
    "ContainerYellow": dict(color="#d9a531", roughness=0.6), "ContainerGreen": dict(color="#3f7a55", roughness=0.6),
    "HullNavy": dict(color="#2b3a52", roughness=0.55),
})


def _split_waterline(bm, levels):
    """Bisect a hull at given z levels and assign material indices by height band."""
    for z in levels:
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                               plane_co=(0, 0, z), plane_no=(0, 0, 1))
    for f in bm.faces:
        cz = f.calc_center_median().z
        f.material_index = sum(cz > z for z in levels)


# ------------------------------------------------------------- submarine

def submarine(name="SubmarineExterior", L=34.0, Rh=3.0):
    """Teal-and-red cigar hull with sail, deck casing, planes, rudder and a spinning propeller.

    Origin at the waterline (surfaced), bow towards +X."""
    p = Prop(name, category="vehicle", note="surfaced: waterline at z=0; submerge by lowering ~3.5 m")
    zc = 0.4  # hull axis height above the waterline when surfaced
    prof = [(0.0, -L / 2), (0.35, -L / 2 + 0.05), (1.1, -L / 2 + 1.5), (2.1, -L / 2 + 4), (2.8, -L / 2 + 7.5),
            (Rh, -L / 2 + 11), (Rh, L / 2 - 8), (2.9, L / 2 - 5), (2.5, L / 2 - 3), (1.8, L / 2 - 1.3),
            (1.0, L / 2 - 0.4), (0.0, L / 2)]
    hull = bm_lathe(prof, 64, "X")
    bmesh.ops.translate(hull, verts=hull.verts, vec=(0, 0, zc))
    _split_waterline(hull, [-0.45, -0.2])
    p.add(hull, ["AntiFoul", "BootTop", "HullTeal"], smooth=180, name="hull", uv="keep")
    # deck casing
    cl = L * 0.65
    casing = bm_extrude(rrect(cl, 1.9, 0.9, 8), 0.5)
    p.add(casing, "DeckGreen", (1.0, 0, zc + Rh - 0.05), bevel=0.05)
    for k in range(int((cl - 4) / 0.7)):  # limber holes along the casing sides
        x = 1.0 - cl / 2 + 2 + k * 0.7
        for s in (-1, 1):
            p.box((0.35, 0.02, 0.08), (x, s * 0.95, zc + Rh - 0.12), "BootTop", bevel=0)
    for x in (-cl * 0.3, cl * 0.38):
        p.cyl(0.42, 0.12, (x, 0, zc + Rh + 0.26), "HullTeal", segs=32, bevel=0.03)
        p.cyl(0.32, 0.06, (x, 0, zc + Rh + 0.34), "BootTop", segs=32)
    # sail / conning tower
    sail = bm_extrude([(x * 1.0, y) for x, y in rrect(6.0, 1.7, 0.85, 8)], 3.4, center_z=False)
    for v in sail.verts:
        if v.co.z > 1:  # taper the top slightly
            v.co.x *= 0.92
            v.co.y *= 0.9
    p.add(sail, "HullTeal", (3.0, 0, zc + Rh + 0.2), bevel=0.08, segs=2, name="sail")
    p.box((1.6, 1.2, 0.08), (4.6, 0, zc + Rh + 3.62), "DeckGreen", bevel=0.02)
    for k in range(5):  # bridge windows
        p.box((0.25, 0.02, 0.18), (4.1 + k * 0.32, -0.76, zc + Rh + 3.2), "WindowDark", rot=(0, 0, 0), bevel=0.02)
        p.box((0.25, 0.02, 0.18), (4.1 + k * 0.32, 0.76, zc + Rh + 3.2), "WindowDark", bevel=0.02)
    for s in (-1, 1):
        p.decal(1.0, 0.75, (2.4, s * 0.86, zc + Rh + 2.3), "hull_number", rot=(0, 0, 0 if s < 0 else 180))
        fin = bm_extrude([(-0.6, 0.0), (0.6, 0.0), (0.4, 1.4), (-0.5, 1.4)], 0.12)
        bmesh.ops.rotate(fin, verts=fin.verts, matrix=Matrix.Rotation(R(-90 * s), 3, "X"))
        p.add(fin, "HullTeal", (3.6, s * 0.8, zc + Rh + 2.3), bevel=0.03, name="sailplane")
    # masts on the sail
    for x, h, r in [(2.2, 2.4, 0.11), (2.8, 3.0, 0.09), (3.4, 1.8, 0.07)]:
        p.cyl(r, h, (x, 0, zc + Rh + 3.6 + h / 2), "BootTop", segs=16)
    p.cyl(0.18, 0.3, (2.2, 0, zc + Rh + 6.05), "BootTop", segs=16, bevel=0.03)
    p.cyl(0.02, 1.2, (3.4, 0, zc + Rh + 6.0), "Steel", segs=6)
    # railing around the bridge
    rail = [Vector((x + 3.8, y, zc + Rh + 4.25)) for x, y in rrect(2.6, 1.5, 0.6, 6)]
    p.add(bm_sweep(rail, circle(0.025, 6), caps=False, closed_path=True), "Steel", smooth=60, name="rail")
    for v in rail[::3]:
        p.cyl(0.02, 0.6, (v.x, v.y, v.z - 0.3), "Steel", segs=6)
    # bow planes, stern planes, rudder
    for s in (-1, 1):
        bp = bm_extrude([(-0.7, 0.0), (0.7, 0.0), (0.5, 1.6), (-0.6, 1.6)], 0.14)
        bmesh.ops.rotate(bp, verts=bp.verts, matrix=Matrix.Rotation(R(-90 * s), 3, "X"))
        p.add(bp, "HullTeal", (L / 2 - 6.0, s * (Rh - 0.6), zc + 0.6), bevel=0.04, name="bowplane")
        sp = bm_extrude([(-1.2, 0.0), (0.6, 0.0), (0.2, 2.1), (-1.3, 2.1)], 0.16)
        bmesh.ops.rotate(sp, verts=sp.verts, matrix=Matrix.Rotation(R(-90 * s), 3, "X"))
        p.add(sp, "HullTeal", (-L / 2 + 2.6, s * 1.4, zc), bevel=0.04, name="sternplane")
    for s in (-1, 1):
        rd = bm_extrude([(-1.2, 0.0), (0.7, 0.0), (0.3, 2.3), (-1.3, 2.3)], 0.16)
        bmesh.ops.rotate(rd, verts=rd.verts, matrix=Matrix.Rotation(R(90 if s > 0 else -90), 3, "X"))
        bmesh.ops.rotate(rd, verts=rd.verts, matrix=Matrix.Rotation(R(90), 3, "X"))
        p.add(rd, "HullTeal" if s > 0 else "AntiFoul", (-L / 2 + 2.6, 0, zc + s * 1.2), bevel=0.04, name="rudder")
    # torpedo tube shutters on the bow
    for yy, zz in [(-1, 0.75), (1, 0.75), (-1, -0.15), (1, -0.15)]:
        # oval shutters sitting on the bow flank, facing outwards
        p.add(core.bm_disc(0.3, 24), "BootTop", (L / 2 - 2.9, yy * 2.27, zc + zz), (0, 0, 0 if yy < 0 else 180),
              uv="keep", smooth=False, name="shutter", scale=(1.6, 1, 1))
    # propeller
    prop = p.pivot("Propeller", (-L / 2 - 0.25, 0, zc), interact="spin", rotate_axis="X")
    p.add(bm_lathe([(0, -0.6), (0.3, -0.4), (0.35, 0.0), (0.0, 0.3)], 24, "X"), "Brass", parent=prop, smooth=60)
    for b in range(6):
        blade = bm_extrude([(-0.25, 0.2), (0.25, 0.2), (0.4, 1.0), (0.1, 1.45), (-0.3, 1.1)], 0.06)
        bmesh.ops.rotate(blade, verts=blade.verts, matrix=Matrix.Rotation(R(90 + 25), 3, "Z"))
        bmesh.ops.rotate(blade, verts=blade.verts, matrix=Matrix.Rotation(R(90), 3, "Y"))
        bmesh.ops.rotate(blade, verts=blade.verts, matrix=Matrix.Rotation(R(b * 60), 3, "X"))
        p.add(blade, "Brass", parent=prop, bevel=0.02, name="blade")
    p.anchor("interior_origin", (L / 2 - 4.0, 0, zc), rot=(0, 0, 180),
             note="interior level origin (bow bulkhead, upper deck floor); the interior's +X runs aft")
    return p.finish()


# --------------------------------------------------------- surface ships

def ship_hull(L, B, keel=2.0, deck=2.6, bow_len=8.0, sheer=0.8, stern_frac=0.85, n=40, sec=10):
    """Lofted ship hull from x=0 (transom) to x=L (bow), waterline at z=0. Returns (bmesh, deck_outline)."""
    bm = bmesh.new()
    rings = []
    outline = []
    for i in range(n + 1):
        x = L * i / n
        if x > L - bow_len:
            t = (x - (L - bow_len)) / bow_len
            hb = B / 2 * max(1 - t ** 1.7, 0.02)
        else:
            t = x / (L - bow_len)
            hb = B / 2 * (stern_frac + (1 - stern_frac) * min(1, t * 3))
        dz = deck + sheer * max(0, (x - L * 0.6) / (L * 0.4)) ** 2
        kz = -keel * (1 - 0.7 * max(0, (x - (L - bow_len)) / bow_len) ** 2) * (0.6 + 0.4 * min(1, x / 3))
        pts = []
        for j in range(sec + 1):
            u = j / sec  # 0 keel centre .. 1 deck edge
            zz = kz + (dz - kz) * u
            w = hb * min(1, math.sin(u * math.pi / 2) ** 0.35 + 0.02)
            pts.append((x, w, zz))
        right = [bm.verts.new(p_) for p_ in pts]
        left = [bm.verts.new((p_[0], -p_[1], p_[2])) for p_ in pts]
        rings.append((right, left))
        outline.append((x, hb, dz))
    for (r0, l0), (r1, l1) in zip(rings, rings[1:]):
        for j in range(sec):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
            bm.faces.new((l0[j + 1], l1[j + 1], l1[j], l0[j]))
        bm.faces.new((r0[sec], r1[sec], l1[sec], l0[sec]))  # deck
        bm.faces.new((l0[0], l1[0], r1[0], r0[0]))  # keel line strip
    r0, l0 = rings[0]
    bm.faces.new(list(reversed(r0)) + l0[1:])  # transom
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, outline


def frigate(name="EnemyFrigate", L=38.0, B=5.0):
    """Grey warship target: gun turret (yaw/pitch pivots), bridge, funnel, mast with spinning radar."""
    p = Prop(name, category="vehicle", team="enemy", target_type="frigate", hit_points=3)
    hull, outline = ship_hull(L, B, keel=2.2, deck=2.4, bow_len=10, sheer=1.0)
    for f in hull.faces:
        f.material_index = 0
    _split_waterline(hull, [-0.3, 0.15])
    for f in hull.faces:
        f.normal_update()
        if f.normal.z > 0.9 and f.calc_center_median().z > 2.0:
            f.material_index = 3
    p.add(hull, ["AntiFoul", "BootTop", "NavyGray", "NavyGrayDark"], smooth=30, uv="keep", name="hull")
    for s in (-1, 1):
        p.decal(3.2, 1.05, (L - 7.5, s * (B / 2 - 0.05) * 0.86, 1.4), "frigate_number", rot=(0, 0, 0 if s < 0 else 180))
    # superstructure
    p.box((9.0, 3.8, 2.4), (L * 0.5, 0, 2.4 + 1.2), "NavyGray", bevel=0.08)
    p.box((5.0, 3.4, 1.8), (L * 0.55, 0, 2.4 + 2.4 + 0.9), "NavyGray", bevel=0.08)
    p.box((3.0, 3.6, 1.2), (L * 0.6, 0, 2.4 + 4.2 + 0.6), "NavyGray", bevel=0.06)
    for k in range(6):
        p.box((0.35, 3.65, 0.35), (L * 0.6 - 1.0 + k * 0.45, 0, 7.05), "WindowDark", bevel=0.03)
    for k in range(8):
        for s in (-1, 1):
            p.cyl(0.14, 0.06, (L * 0.5 - 3.8 + k * 1.0, s * 1.91, 4.1), "WindowDark", axis="Y", segs=12)
    # funnel
    fun = bm_extrude(rrect(2.6, 1.8, 0.6, 6), 3.0, center_z=False)
    for v in fun.verts:
        if v.co.z > 1:
            v.co.x -= 0.5
    p.add(fun, "NavyGrayDark", (L * 0.4, 0, 4.7), bevel=0.06, name="funnel")
    p.box((2.0, 1.6, 0.3), (L * 0.4 - 0.5, 0, 7.75), "BootTop", bevel=0.04)
    # mast + radar
    p.cyl(0.18, 6.0, (L * 0.58, 0, 10.0), "NavyGrayDark", segs=12)
    p.box((0.15, 3.0, 0.15), (L * 0.58, 0, 11.5), "NavyGrayDark", bevel=0.02)
    radar = p.pivot("Radar", (L * 0.58, 0, 13.2), interact="spin", rotate_axis="Z")
    p.box((0.3, 2.6, 0.5), (0, 0, 0.3), "NavyGray", parent=radar, bevel=0.04)
    p.cyl(0.12, 0.3, (0, 0, 0.0), "BootTop", parent=radar, segs=12)
    # gun turret
    tur = p.pivot("Turret", (L - 9.5, 0, 2.5 + 0.2), interact="turret", rotate_axis="Z")
    p.add(bm_lathe([(0, 0), (1.3, 0), (1.25, 0.6), (0.9, 1.1), (0.0, 1.15)], 32), "NavyGray", parent=tur, smooth=40)
    gun = p.pivot("Gun", (0.8, 0, 0.6), parent=tur, interact="gun", rotate_axis="Y", min_deg=-35, max_deg=5)
    p.cyl(0.12, 3.6, (1.8, 0, 0), "NavyGrayDark", axis="X", segs=16, parent=gun)
    p.cyl(0.18, 0.5, (0.2, 0, 0), "NavyGrayDark", axis="X", segs=16, parent=gun)
    # lifeboats and railings
    for s in (-1, 1):
        lb = bm_lathe([(0.0, -1.6), (0.35, -1.4), (0.5, -0.6), (0.5, 0.6), (0.35, 1.3), (0.0, 1.6)], 16, "X")
        p.add(lb, "ContainerRed", (L * 0.47, s * 2.2, 4.4), scale=(1, 1, 0.7), smooth=60, name="lifeboat")
        rail = [Vector((x, s * (hb - 0.12), dz + 0.9)) for x, hb, dz in outline[2:-3]]
        p.add(bm_sweep(rail, circle(0.03, 6)), "Steel", smooth=60, name="rail")
        for x, hb, dz in outline[2:-3:2]:
            p.cyl(0.025, 0.9, (x, s * (hb - 0.12), dz + 0.45), "Steel", segs=6)
    p.anchor("hit_center", (L * 0.5, 0, 0.5))
    return p.finish()


def freighter(name="CargoFreighter", L=46.0, B=8.0):
    """Merchant target: stacked containers, aft bridge, funnel and two deck cranes."""
    p = Prop(name, category="vehicle", team="neutral", target_type="freighter", hit_points=2)
    hull, outline = ship_hull(L, B, keel=3.0, deck=3.2, bow_len=9, sheer=1.2, stern_frac=0.92)
    _split_waterline(hull, [-0.4, 0.2])
    p.add(hull, ["AntiFoul", "BootTop", "HullNavy"], smooth=30, uv="keep", name="hull")
    for s in (-1, 1):
        p.decal(6.0, 0.94, (L - 8.0, s * (B / 2 - 0.08) * 0.88, 2.0), "freighter_name", rot=(0, 0, 0 if s < 0 else 180))
    p.box((L - 12, B - 0.6, 0.2), (L / 2 + 0.5, 0, 3.25), "DeckGreen", bevel=0.05)
    rnd = random.Random(11)
    cols = ["ContainerRed", "ContainerBlue", "ContainerYellow", "ContainerGreen"]
    for bay in range(6):
        x = 13 + bay * 4.2
        for row in range(3):
            for tier in range(rnd.randint(1, 3)):
                p.box((4.0, 2.3, 2.3), (x, -2.4 + row * 2.4, 3.35 + 1.15 + tier * 2.35), rnd.choice(cols), bevel=0.04)
    # aft accommodation block
    p.box((6.0, B - 1.0, 6.0), (4.5, 0, 3.2 + 3.0), "PaintWhite", bevel=0.08)
    p.box((4.0, B + 0.6, 1.4), (4.8, 0, 9.9), "PaintWhite", bevel=0.06)
    for k in range(7):
        p.box((0.45, B + 0.65, 0.5), (3.3 + k * 0.5, 0, 10.0), "WindowDark", bevel=0.03)
    for lvl in range(3):
        for k in range(6):
            for s in (-1, 1):
                p.cyl(0.18, 0.06, (2.2 + k * 0.9, s * (B / 2 - 0.47), 4.5 + lvl * 1.6), "WindowDark", axis="Y", segs=12)
    p.add(bm_extrude(rrect(2.2, 1.8, 0.5, 6), 3.0, center_z=False), "ContainerRed", (3.0, 0, 10.6), bevel=0.05)
    p.box((2.3, 1.9, 0.6), (3.0, 0, 13.3), "BootTop", bevel=0.05)
    for cx in (17, 30):
        p.cyl(0.35, 5.0, (cx - 2.1, 0, 3.3 + 2.5), "ContainerYellow", segs=16)
        crane = p.pivot(f"Crane_{cx}", (cx - 2.1, 0, 8.3), interact="crane", rotate_axis="Z")
        p.box((7.0, 0.35, 0.35), (2.8, 0, 0.6), "ContainerYellow", rot=(0, -15, 0), parent=crane, bevel=0.04)
        p.cyl(0.02, 4.0, (5.9, 0, -0.9), "Steel", segs=6, parent=crane)
    p.anchor("hit_center", (L * 0.5, 0, 0.5))
    return p.finish()
