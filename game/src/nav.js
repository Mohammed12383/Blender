// Walkable surfaces of the two-deck interior, built from submarine/models/nav.json (exported by Blender).
// three.js coordinates: x along the boat (bow = 0), y up, z = -(Blender y) (port side is -z).
// Every region is for the CENTRE of a crewman of radius R, so it is already shrunk by R.

export class Nav {
  constructor(data, R = 0.28) {
    this.R = R;
    const deckY = (d) => data.decks[d];
    const hw = (d) => data.half_w[d] - 0.3 - R;
    const pitRooms = new Set(data.pits.map((p) => p.room));
    const regions = [];
    for (const [name, rm] of Object.entries(data.rooms)) {
      if (pitRooms.has(name)) continue;
      regions.push({ room: name, x0: rm.x0 + R, x1: rm.x1 - R, z0: -hw(rm.deck), z1: hw(rm.deck), y: deckY(rm.deck), holes: [] });
    }
    for (const pit of data.pits) {
      const rm = data.rooms[pit.room];
      if (pit.x0 > rm.x0 + 0.05) regions.push({ room: pit.room, x0: rm.x0 + R, x1: pit.x0 + 0.06, z0: -hw('upper'), z1: hw('upper'), y: 0, holes: [] });
      for (const w of pit.walk) {
        regions.push({ room: pit.room, x0: Math.max(rm.x0 + R, w.x0 - 0.06), x1: Math.min(rm.x1 - R, w.x1 + 0.06),
          z0: Math.max(-hw('upper'), -w.y1 + R), z1: Math.min(hw('upper'), -w.y0 - R), y: 0, holes: [] });
      }
    }
    for (const h of data.holes) {
      for (const reg of regions.filter((r) => r.room === h.room)) reg.holes.push({ x0: h.x0 - R, x1: h.x1 + R, z0: -h.y1 - R, z1: -h.y0 + R });
    }
    this.stairs = data.stairs.map((s) => {
      const [bx, by, bz] = s.bottom, [tx, , tz] = s.top;
      const zc = -by, half = s.width / 2 - R;
      const yAt = (x) => tz + (bz - tz) * Math.max(0, Math.min(1, (x - tx) / (bx - tx)));
      const reg = { room: s.upper, stairs: true, x0: Math.min(bx, tx) - 0.45, x1: Math.max(bx, tx) + 0.42, z0: zc - half, z1: zc + half, yAt, holes: [] };
      regions.push(reg);
      // you cannot walk underneath the flight on the deck below: you step onto its foot instead
      const lo = Math.min(bx, tx), hi = Math.max(bx, tx);
      const under = bx > tx ? { x0: lo - 0.1, x1: hi - 0.15 } : { x0: lo + 0.15, x1: hi + 0.1 };
      for (const r of regions.filter((q) => q.room === s.lower)) r.holes.push({ ...under, z0: zc - s.width / 2 - R, z1: zc + s.width / 2 + R });
      return { ...s, reg, zc, yAt, tx, bx };
    });
    this.doors = data.doors.map((d, i) => ({ door: i, x0: d.x - R - 0.06, x1: d.x + 0.3 + R + 0.06, z0: -0.42, z1: 0.42, y: deckY(d.deck) }));
    this.regions = regions;
    this.colliders = [];     // {minX, maxX, minY, maxY, minZ, maxZ, name}
    this.ceil = data.ceil;
    this.holes = data.holes.map((h) => ({ x0: h.x0, x1: h.x1, z0: -h.y1, z1: -h.y0 }));
  }

  // Floor height under (x, z) for someone whose feet are at y, or null if they can't stand/swim there.
  floorAt(x, z, y, doors, swim = false) {
    let best = null, bestScore = 1e9;
    const consider = (h) => {
      if (swim ? h > y + 0.5 : Math.abs(h - y) > 0.55) return;
      const score = swim ? -h : Math.abs(h - y);
      if (score < bestScore) { bestScore = score; best = h; }
    };
    for (const r of this.regions) {
      if (x < r.x0 || x > r.x1 || z < r.z0 || z > r.z1) continue;
      if (r.holes.some((h) => x > h.x0 && x < h.x1 && z > h.z0 && z < h.z1)) continue;
      consider(r.yAt ? r.yAt(x) : r.y);
    }
    for (const d of this.doors) if (doors[d.door] && x >= d.x0 && x <= d.x1 && z >= d.z0 && z <= d.z1) consider(d.y);
    return best;
  }

  // Height of the deckhead above (x, z) for someone at y (the stairwell opens the lower deckhead).
  ceilingAt(x, z, y) {
    if (y > -1.0) return this.ceil.upper - 0.1;
    const open = this.holes.some((h) => x > h.x0 && x < h.x1 && z > h.z0 && z < h.z1);
    return open ? this.ceil.upper - 0.1 : this.ceil.lower - 0.05;
  }

  onStairs(x, z) { return this.stairs.find((s) => x >= s.reg.x0 && x <= s.reg.x1 && z >= s.reg.z0 && z <= s.reg.z1); }

  // Move p ({x, y, z}) by (dx, dz) sliding along walls and furniture. Returns the floor height under p.
  move(p, dx, dz, doors, swim = false) {
    const ok = (x, z) => this.floorAt(x, z, p.y, doors, swim) !== null;
    for (const [ax, az] of [[dx, dz], [dx, 0], [0, dz]]) {
      if ((ax || az) && ok(p.x + ax, p.z + az) && !this.hits(p.x + ax, p.z + az, p.y)) { p.x += ax; p.z += az; break; }
    }
    const px = p.x, pz = p.z;
    this.pushOut(p);
    if (!ok(p.x, p.z)) { p.x = px; p.z = pz; }
    return this.floorAt(p.x, p.z, p.y, doors, swim);
  }

  hits(x, z, y) {
    const r = this.R * 0.6;
    return this.colliders.some((c) => c.minY < y + 1.5 && c.maxY > y + 0.25 && x > c.minX - r && x < c.maxX + r && z > c.minZ - r && z < c.maxZ + r);
  }

  pushOut(p) {
    const R = this.R;
    for (const c of this.colliders) {
      if (!(c.minY < p.y + 1.5 && c.maxY > p.y + 0.25)) continue;
      const nx = Math.max(c.minX, Math.min(p.x, c.maxX)), nz = Math.max(c.minZ, Math.min(p.z, c.maxZ));
      const dx = p.x - nx, dz = p.z - nz, d = Math.hypot(dx, dz);
      if (d >= R) continue;
      if (d > 1e-5) { p.x = nx + dx / d * R; p.z = nz + dz / d * R; }
      else {
        // inside the box: leave by the nearest face
        const opts = [[c.minX - R - p.x, 0], [c.maxX + R - p.x, 0], [0, c.minZ - R - p.z], [0, c.maxZ + R - p.z]];
        opts.sort((a, b) => Math.abs(a[0] + a[1]) - Math.abs(b[0] + b[1]));
        p.x += opts[0][0]; p.z += opts[0][1];
      }
    }
  }
}
