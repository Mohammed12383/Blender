"""Tiny signed-distance-field modeller: capsules, tapered capsules, ellipsoids, boxes with smooth
blending, polygonised with marching cubes (scikit-image) into a Blender mesh.

Used for organic shapes (bodies, hands, faces, hair, clothing) where exact radii and soft,
continuous joins matter.
"""

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from skimage.measure import marching_cubes


def _smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _smax(a, b, k):
    return -_smin(-a, -b, k)


class Shape:
    """A union of primitives (optionally with smooth subtractions)."""

    def __init__(self, blend=0.01):
        self.prims = []  # (kind, params, op, k)
        self.blend = blend

    # -- primitives (op: "add" or "sub"; k overrides the blend radius)
    def capsule(self, a, b, ra, rb=None, op="add", k=None):
        self.prims.append(("cap", (np.array(a, np.float32), np.array(b, np.float32), ra, ra if rb is None else rb), op, k))
        return self

    def sphere(self, c, r, op="add", k=None):
        return self.capsule(c, c, r, r, op, k)

    def ellipsoid(self, c, radii, rot=None, op="add", k=None):
        m = np.array((rot or Quaternion()).to_matrix().inverted(), np.float32)
        self.prims.append(("ell", (np.array(c, np.float32), np.array(radii, np.float32), m), op, k))
        return self

    def box(self, c, half, r=0.0, rot=None, op="add", k=None):
        m = np.array((rot or Quaternion()).to_matrix().inverted(), np.float32)
        self.prims.append(("box", (np.array(c, np.float32), np.array(half, np.float32), r, m), op, k))
        return self

    def chain(self, pts, radii, k=None):
        """Tapered capsule chain through points with per-point radii."""
        for (a, b), (ra, rb) in zip(zip(pts, pts[1:]), zip(radii, radii[1:])):
            self.capsule(a, b, ra, rb, k=k)
        return self

    # -- evaluation
    @staticmethod
    def _eval(kind, prm, P):
        if kind == "cap":
            a, b, ra, rb = prm
            ba = b - a
            denom = float(ba @ ba)
            t = np.clip(((P - a) @ ba) / denom, 0, 1) if denom > 1e-12 else np.zeros(len(P), np.float32)
            q = a + t[:, None] * ba
            return np.linalg.norm(P - q, axis=1) - (ra + (rb - ra) * t)
        if kind == "ell":
            c, r, m = prm
            p = (P - c) @ m.T
            k0 = np.linalg.norm(p / r, axis=1)
            k1 = np.linalg.norm(p / (r * r), axis=1)
            return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
        if kind == "box":
            c, h, rr, m = prm
            p = np.abs((P - c) @ m.T) - (h - rr)
            return np.linalg.norm(np.maximum(p, 0), axis=1) + np.minimum(np.max(p, axis=1), 0) - rr
        raise ValueError(kind)

    def bounds(self, pad):
        lo, hi = np.full(3, 1e9), np.full(3, -1e9)
        for kind, prm, op, _ in self.prims:
            if op != "add":
                continue
            if kind == "cap":
                r = max(prm[2], prm[3])
                lo = np.minimum(lo, np.minimum(prm[0], prm[1]) - r)
                hi = np.maximum(hi, np.maximum(prm[0], prm[1]) + r)
            else:
                r = float(np.max(prm[1]))
                lo = np.minimum(lo, prm[0] - r)
                hi = np.maximum(hi, prm[0] + r)
        return lo - pad, hi + pad

    def field(self, P):
        d = np.full(len(P), 1e3, np.float32)
        for kind, prm, op, k in self.prims:
            v = self._eval(kind, prm, P)
            kk = self.blend if k is None else k
            d = _smin(d, v, kk) if op == "add" else _smax(d, -v, kk)
        return d

    def mesh(self, name, res=0.005, inflate=0.0, smooth=2):
        """Polygonise into a new Blender mesh (world coordinates)."""
        lo, hi = self.bounds(pad=max(4 * res, self.blend + inflate + res))
        n = np.maximum(((hi - lo) / res).astype(int) + 1, 2)
        xs, ys, zs = (np.linspace(lo[i], lo[i] + (n[i] - 1) * res, n[i], dtype=np.float32) for i in range(3))
        vol = np.empty(tuple(n), np.float32)
        Y, Z = np.meshgrid(ys, zs, indexing="ij")
        yz = np.stack([Y.ravel(), Z.ravel()], 1)
        for i, x in enumerate(xs):  # slice by slice keeps memory bounded
            P = np.empty((len(yz), 3), np.float32)
            P[:, 0] = x
            P[:, 1:] = yz
            vol[i] = (self.field(P) - inflate).reshape(n[1], n[2])
        verts, faces, _, _ = marching_cubes(vol, level=0.0, spacing=(res, res, res))
        verts += lo
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts.tolist(), [], faces.tolist())
        me.validate()
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=res * 0.05)
        for _ in range(smooth):
            bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.shade_smooth()
        return me
