"""Assemble the full submarine interior from the prop library.

Layout (bow at x = 0, stern towards +X; port = +Y, starboard = -Y):

    x  -0.3 .. 0.0   bow bulkhead with the 4 torpedo tubes
    x   0.0 .. 7.0   TORPEDO ROOM   (loader)
    x   7.0 .. 7.3   bulkhead + watertight door
    x   7.3 .. 16.3  CONTROL ROOM   (navigator, weapons officer, periscope, sonar, ballast)
    x  16.3 .. 16.6  bulkhead + watertight door
    x  16.6 .. 22.6  CREW MESS      (table, bunks, lockers, coffee)
    x  22.6 .. 22.9  bulkhead + watertight door
    x  22.9 .. 27.4  GALLEY         (cook)
    x  27.4 .. 27.7  aft bulkhead, locked engine-room door
"""

import math

import bpy
from mathutils import Vector

from . import core, shell
from .core import Prop, R, bm_torus, bm_cyl, instance
from . import props_common as pc, props_control as pcx, props_torpedo as pt, props_galley as pg

ROOMS = {
    "TorpedoRoom": (0.0, 7.0),
    "ControlRoom": (7.3, 16.3),
    "CrewMess": (16.6, 22.6),
    "Galley": (22.9, 27.4),
}
WALL = shell.HALF_W - 0.08     # back of wall-standing props (clears the ribs)
WALL_DECAL = shell.HALF_W - 0.002


def ceiling_hatch(name="CeilingHatch"):
    """Escape-trunk hatch on the ceiling (origin at the ceiling surface); the lid hinges down."""
    p = Prop(name, category="door", interact="hatch", note="decorative: the shell ceiling has no opening")
    p.add(bm_torus(0.46, 0.035, 48, 10), "PaintTeal", (0, 0, -0.03), smooth=180)
    p.cyl(0.5, 0.02, (0, 0, -0.01), "PaintGraphite", segs=48, bevel=0.004)
    lid = p.pivot("Lid", (-0.42, 0, -0.06), interact="hatch", rotate_axis="Y", min_deg=0, max_deg=100)
    p.cyl(0.42, 0.05, (0.42, 0, 0), "PaintTeal", segs=48, bevel=0.01, parent=lid)
    p.add(bm_torus(0.4, 0.012, 48, 6), "Rubber", (0.42, 0, 0.026), parent=lid, smooth=180)
    for k in range(4):
        a = k * math.pi / 2
        p.box((0.6, 0.04, 0.03), (0.42, 0, -0.035), "PaintTeal", rot=(0, 0, math.degrees(a) / 2), parent=lid, bevel=0.006)
    pc.handwheel(p, (0.42, 0, -0.12), rot=(90, 0, 0), r=0.13, parent=lid, name="LidWheel", interact="hatch_lock",
                 m="PaintMustard")
    p.cyl(0.03, 0.08, (0.42, 0, -0.07), "Steel", segs=12, parent=lid)
    p.box((0.08, 0.06, 0.06), (-0.42, 0, -0.06), "DarkSteel", bevel=0.008)
    return p.finish()


def build_library():
    """Build every prop once (at the origin, in the Library collection). Returns {name: root}."""
    lib = {}

    def add(fn, *a, **k):
        root = fn(*a, **k)
        lib[root.name] = root
        return root

    # shared
    add(pc.bulkhead_lamp)
    add(pc.alarm_beacon)
    add(pc.pendant_lamp)
    add(pc.loudspeaker)
    add(pc.junction_box)
    add(pc.fire_extinguisher)
    add(pc.ship_clock)
    add(pc.intercom)
    add(pc.electrical_cabinet, "ElectricalCabinet", variant="gauges")
    add(pc.electrical_cabinet, "EquipmentRack", variant="racks", m="PaintCream")
    add(pc.watertight_door)
    add(pc.watertight_door, "EngineRoomDoor", frame_m="PaintRed")
    lib["EngineRoomDoor"]["locked"] = True
    add(pc.ladder)
    add(pc.stool)
    add(pc.toolbox)
    add(pc.crate)
    add(pc.crate, "SparePartsCrate", m="PaintNavy", w=0.6, d=0.45, h=0.4)
    add(pc.air_tanks)
    add(ceiling_hatch)
    add(pc.pipe_riser)
    add(pc.pipe_riser, "PipeRiserMustard", m="PaintMustard", r=0.04)
    add(pc.floor_hatch)
    for img in ("poster_dive", "poster_quiet", "poster_galley", "poster_crew"):
        add(pc.poster, img)
    for img in ("sign_hot", "sign_voltage", "sign_explosive", "sign_pressure"):
        add(pc.sign, img)
    for img in ("label_control_room", "label_torpedo_room", "label_crew_mess", "label_galley", "label_engine_room"):
        add(pc.room_sign, img)
    # control room
    add(pcx.nav_table)
    add(pcx.nav_console)
    add(pcx.fire_control)
    add(pcx.periscope)
    add(pcx.sonar_station)
    add(pcx.ballast_panel)
    # torpedo room
    add(pt.torpedo)
    add(pt.tube_bank)
    add(pt.torpedo_rack)
    add(pt.loading_cradle)
    add(pt.chain_hoist)
    add(pt.workbench)
    # galley / mess
    add(pg.griddle)
    add(pg.exhaust_hood)
    add(pg.wire_shelf)
    add(pg.tray, "TrayGreen", "TrayGreen")
    add(pg.tray, "TrayBlue", "TrayBlue")
    add(pg.fridge)
    add(pg.prep_counter)
    add(pg.pot_rail)
    add(pg.steak, "SteakRaw", False, 3)
    add(pg.steak, "SteakCooked", True, 5)
    add(pg.drumstick, "DrumstickCooked", True)
    add(pg.drumstick, "DrumstickRaw", False)
    add(pg.patty, "PattyRaw", False)
    add(pg.patty, "PattyCooked", True)
    add(pg.mess_table)
    add(pg.mug, "MugBlue", "EnamelBlue")
    add(pg.mug, "MugRed", "EnamelRed")
    add(pg.mug, "MugCream", "EnamelCream")
    add(pg.plate)
    add(pg.bunk_bed)
    add(pg.lockers)
    add(pg.coffee_station)
    add(pg.wall_monitor, "WallMonitorFwd", "screen_cam_fwd")
    add(pg.wall_monitor, "WallMonitorAft", "screen_cam_aft")
    add(pg.notice_board)
    add(pg.checkers_board)
    return lib


# ------------------------------------------------------------------ helpers

class Room:
    def __init__(self, name, lib):
        self.name = name
        self.col = core.collection("Room_" + name)
        self.lib = lib
        self.x0, self.x1 = ROOMS[name]

    def put(self, prop, loc, rot_z=0.0, rot=None):
        return instance(self.lib[prop], self.col, loc, rot or (0, 0, rot_z))

    # wall helpers: port wall faces -Y (rot 0), starboard wall faces +Y (rot 180)
    def port(self, prop, x, z=0.0, inset=WALL):
        return self.put(prop, (x, inset, z), 0)

    def stbd(self, prop, x, z=0.0, inset=WALL):
        return self.put(prop, (x, -inset, z), 180)

    def fwd_face(self, prop, y, z, x=None):
        """On the forward bulkhead, facing aft (+X)."""
        return self.put(prop, ((self.x0 if x is None else x) + 0.001, y, z), 90)

    def aft_face(self, prop, y, z, x=None):
        """On the aft bulkhead, facing forward (-X)."""
        return self.put(prop, ((self.x1 if x is None else x) - 0.001, y, z), -90)

    def lamps(self, positions):
        for x, y in positions:
            self.put("CeilingLamp", (x, y, shell.CEIL))

    def spawn(self, name, loc, rot_z=0.0):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        self.col.objects.link(e)
        e.location = loc
        e.rotation_euler = (0, 0, R(rot_z))
        e["spawn"] = True
        return e


# -------------------------------------------------------------------- rooms

def torpedo_room(lib):
    r = Room("TorpedoRoom", lib)
    tube_holes = [[(x + 0.34 * math.cos(2 * math.pi * k / 40), z + 0.34 * math.sin(2 * math.pi * k / 40)) for k in range(40)]
                  for x, z in pt.TUBE_POS]
    shell.compartment(r.col, "TorpedoRoom_Shell", r.x0, r.x1)
    shell.bulkhead(r.col, "Bulkhead_Bow", -0.3, holes=tube_holes, door=False)
    r.put("TorpedoTubes", (0.0, 0, 0), 90)
    r.put("LoadingCradle", (0.55, -0.62, 0), 90)
    r.put("Torpedo", (2.05, -0.62, 0.76), 180)
    r.put("ChainHoist", (0.5, 0.0, shell.CEIL), 90)
    r.port("TorpedoRack", 3.9)
    r.stbd("TorpedoRack", 3.9)
    for z in (0.45, 1.25):
        r.put("Torpedo", (3.9, WALL - 0.42, z), 180)
    r.put("Torpedo", (3.9, -(WALL - 0.42), 0.45), 180)
    r.port("AirTanks", 6.25)
    r.stbd("Workbench", 6.15)
    r.put("Toolbox", (5.75, -(WALL - 0.3), 0.9), 172)
    r.put("SupplyCrate", (1.25, 1.95, 0), 8)
    r.put("SparePartsCrate", (1.3, 1.95, 0.45), -6)
    r.put("SupplyCrate", (2.05, 2.0, 0), -3)
    r.port("Sign_Explosive", 3.9, 1.95, WALL_DECAL)
    r.stbd("Poster_Dive", 1.6, 1.55, WALL_DECAL)
    r.stbd("JunctionBox", 2.0, 2.05, WALL_DECAL)
    r.port("Loudspeaker", 5.3, 2.2, WALL_DECAL)
    r.put("AlarmBeacon", (0.001, 1.65, 2.3), 90)
    r.aft_face("FireExtinguisher", 1.25, 0.35)
    r.aft_face("RoomSign_Control_Room", 0, 2.2)
    r.port("PipeRiser", 0.25, 0, shell.HALF_W - 0.01)
    r.put("FloorHatch", (5.3, 0.55, 0), 0)
    r.lamps([(2.2, -1.15), (4.6, 0.0), (6.2, 0.0)])
    return r


def control_room(lib):
    r = Room("ControlRoom", lib)
    shell.compartment(r.col, "ControlRoom_Shell", r.x0, r.x1)
    shell.bulkhead(r.col, "Bulkhead_1", 7.0)
    r.put("WatertightDoor", (7.15, 0, 0), -90)
    # port side: weapons, sonar, ballast
    r.put("ElectricalCabinet", (7.85, WALL, 0), 0)
    r.put("FireControl", (9.05, WALL - 0.3, 0), 0)
    r.put("EquipmentRack", (10.3, WALL, 0), 0)
    r.port("Intercom", 11.25, 1.35, WALL_DECAL)
    r.port("SonarStation", 12.65)
    r.put("Stool", (12.65, 1.45, 0), 15)
    r.port("BallastPanel", 14.8)
    r.port("Loudspeaker", 11.25, 2.25, WALL_DECAL)
    r.port("JunctionBox", 13.75, 2.0, WALL_DECAL)
    # centre: periscope and chart table
    r.put("Periscope", (9.9, 0.0, 0), 0)
    r.put("NavTable", (12.0, -0.55, 0), 0)
    # starboard side: nav console and equipment
    r.put("EquipmentRack", (7.85, -WALL, 0), 180)
    r.put("ElectricalCabinet", (8.85, -WALL, 0), 180)
    r.stbd("Poster_Quiet", 10.9, 1.55, WALL_DECAL)
    r.put("NavConsole", (12.0, -(WALL - 0.31), 0), 180)
    r.stbd("Sign_Voltage", 8.45, 2.15, WALL_DECAL)
    r.stbd("JunctionBox", 13.0, 2.0, WALL_DECAL)
    r.put("EquipmentRack", (14.3, -WALL, 0), 180)
    # escape trunk: ladder on the aft bulkhead up to a ceiling hatch
    r.aft_face("Ladder", -1.35, 0)
    r.put("CeilingHatch", (r.x1 - 0.2 - 0.18, -1.35, shell.CEIL), 0)
    r.aft_face("ShipClock", 1.35, 1.85)
    r.aft_face("RoomSign_Crew_Mess", 0, 2.2)
    r.aft_face("FireExtinguisher", 1.2, 0.35)
    r.fwd_face("RoomSign_Torpedo_Room", 0, 2.2)
    r.fwd_face("AlarmBeacon", 1.6, 2.3)
    r.port("PipeRiserMustard", 16.05, 0, shell.HALF_W - 0.01)
    r.put("FloorHatch", (14.6, 0.55, 0), 90)
    r.lamps([(8.6, 0.0), (11.3, 0.0), (13.9, 0.0)])
    # crew spawn points (one per player)
    for k, (x, y, rz) in enumerate([(9.05, 1.3, 90), (12.0, -1.5, 90), (9.9, -0.9, 90), (13.5, 0.4, 180)]):
        r.spawn(f"SPAWN_Player{k + 1}", (x, y, 0), rz)
    return r


def crew_mess(lib):
    r = Room("CrewMess", lib)
    shell.compartment(r.col, "CrewMess_Shell", r.x0, r.x1, floor="FloorTiles")
    shell.bulkhead(r.col, "Bulkhead_2", 16.3)
    r.put("WatertightDoor", (16.45, 0, 0), -90)
    # table setting
    tx, ty, th = 19.6, -0.95, 0.76
    r.put("MessTable", (tx, ty, 0), 0)
    for dx in (-0.55, 0.55):
        for dy in (-0.78, 0.78):
            r.put("Stool", (tx + dx, ty + dy, 0), 20 * dx)
    r.put("PendantLamp", (tx, ty, shell.CEIL))
    r.put("CheckersBoard", (tx - 0.35, ty + 0.05, th), 7)
    r.put("MugBlue", (tx + 0.25, ty - 0.25, th), 40)
    r.put("MugRed", (tx + 0.55, ty + 0.2, th), 200)
    r.put("MugCream", (tx - 0.75, ty - 0.2, th), 120)
    r.put("Plate", (tx + 0.6, ty - 0.2, th), 0)
    r.put("DrumstickCooked", (tx + 0.55, ty - 0.22, th + 0.012), 30)
    # port: bunks and lockers
    r.port("BunkBed", 18.0)
    r.port("Lockers", 20.85)
    r.port("Poster_Crew", 22.15, 1.55, WALL_DECAL)
    # starboard: monitors, notice board, coffee
    r.stbd("WallMonitorFwd", 17.1, 1.8, WALL_DECAL)
    r.stbd("WallMonitorAft", 18.15, 1.8, WALL_DECAL)
    r.stbd("NoticeBoard", 20.55, 1.5, WALL_DECAL)
    r.stbd("CoffeeStation", 21.75)
    r.put("MugRed", (21.5, -1.95, 0.9), 20)
    r.aft_face("Intercom", -1.25, 1.35)
    r.aft_face("RoomSign_Galley", 0, 2.2)
    r.aft_face("FireExtinguisher", 1.2, 0.35)
    r.fwd_face("RoomSign_Control_Room", 0, 2.2)
    r.stbd("PipeRiser", 22.4, 0, shell.HALF_W - 0.01)
    r.lamps([(17.5, 0.2), (21.6, 0.2)])
    return r


def galley(lib):
    r = Room("Galley", lib)
    shell.compartment(r.col, "Galley_Shell", r.x0, r.x1, floor="FloorTiles")
    shell.bulkhead(r.col, "Bulkhead_3", 22.6)
    shell.bulkhead(r.col, "Bulkhead_Aft", 27.4)
    r.put("WatertightDoor", (22.75, 0, 0), -90)
    r.put("EngineRoomDoor", (27.55, 0, 0), -90)
    # starboard: prep counter, griddle under the hood
    r.stbd("PrepCounter", 23.7)
    r.stbd("PotRail", 23.7, 1.7, WALL_DECAL)
    gx = 25.35
    r.stbd("Griddle", gx)
    r.stbd("ExhaustHood", gx, 0, WALL)
    r.stbd("Sign_Hot", 26.45, 1.45, WALL_DECAL)
    # food on the grill (griddle front faces +Y here, so local -Y maps to +Y)
    gy = -(WALL - 0.395)
    r.put("DrumstickCooked", (gx + 0.42, gy + 0.1, 0.915), 160)
    r.put("DrumstickCooked", (gx + 0.38, gy - 0.12, 0.915), 200)
    r.put("SteakCooked", (gx - 0.05, gy, 0.915), 75)
    r.put("PattyCooked", (gx - 0.33, gy + 0.12, 0.915), 0)
    r.put("SteakRaw", (24.0, -(WALL - 0.38), 0.926), 20)
    # port: shelves, fridge, crates
    r.port("WireShelf", 23.55)
    r.port("Fridge", 24.75)
    r.port("WireShelf", 25.85)
    for sx, shelf_z, tray, items in [(23.55, 0.6, "TrayGreen", ["SteakRaw", "SteakRaw"]),
                                     (23.55, 1.1, "TrayBlue", ["DrumstickRaw", "DrumstickRaw", "DrumstickRaw"]),
                                     (25.85, 0.6, "TrayBlue", ["PattyRaw", "PattyRaw", "PattyRaw", "PattyRaw"]),
                                     (25.85, 1.1, "TrayGreen", ["SteakRaw"])]:
        y = WALL - 0.225
        r.put(tray, (sx, y, shelf_z + 0.006), 0)
        for k, it in enumerate(items):
            r.put(it, (sx - 0.15 + k * 0.3 / max(1, len(items) - 1) if len(items) > 1 else sx, y, shelf_z + 0.015), 90 + k * 25)
    r.put("SupplyCrate", (26.85, 1.9, 0), 4)
    r.put("SupplyCrate", (26.85, 1.9, 0.45), -5)
    r.aft_face("Poster_Galley", -1.45, 1.5)
    r.aft_face("RoomSign_Engine_Room", 0, 2.2)
    r.aft_face("Sign_Pressure", 1.45, 1.5)
    r.fwd_face("RoomSign_Crew_Mess", 0, 2.2)
    r.fwd_face("FireExtinguisher", 1.2, 0.35)
    r.stbd("PipeRiserMustard", 27.15, 0, shell.HALF_W - 0.01)
    r.lamps([(24.0, 0.2), (26.3, 0.2)])
    return r


def build_level(lib):
    rooms = [torpedo_room(lib), control_room(lib), crew_mess(lib), galley(lib)]
    return rooms
