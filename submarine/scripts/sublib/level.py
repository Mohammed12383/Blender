"""Assemble the full submarine interior from the prop library.

Two decks. Bow at x = 0, stern towards +X; port = +Y, starboard = -Y. Upper deck floor z = 0,
lower deck floor z = -2.9.

    UPPER DECK
    x  -0.3 .. 0.0   bow bulkhead (solid)
    x   0.0 .. 7.0   FORWARD QUARTERS  (bunks, sick bay, stairwell down on the port side)
    x   7.3 .. 16.3  CONTROL ROOM      (navigator, weapons officer, periscope, sonar, ballast)
    x  16.6 .. 22.6  CREW MESS         (table, bunks, lockers, coffee)
    x  22.9 .. 27.4  GALLEY            (cook)
    x  27.7 .. 31.7  PASSAGEWAY        (grated walkway over the pipe pit)
    x  32.0 .. 44.0  ENGINE ROOM       (two diesels in a pit, catwalk, aft control platform)

    LOWER DECK
    x  -0.3 .. 0.0   bow bulkhead with the 4 torpedo tubes
    x   0.0 .. 7.0   TORPEDO ROOM      (loader; the stairs come down here)
    x   7.3 .. 16.3  BATTERY ROOM      (main switchboard, battery banks, stores)

Every room has a hand bilge pump or shares one through a door, a SMOKE EXTRACT panel and a duct fan.
"""

import math

import bpy
from mathutils import Vector

from . import core, shell
from .core import Prop, R, bm_torus, bm_cyl, instance
from . import props_common as pc, props_control as pcx, props_torpedo as pt, props_galley as pg
from . import props_machinery as pm, props_engine as pe, props_systems as ps, props_walkway as pw
from .core import bm_sweep, circle, sag_path

F = shell.LOWER_FLOOR
ROOMS = {                    # name: (x0, x1, deck)
    "FwdQuarters": (0.0, 7.0, "upper"),
    "ControlRoom": (7.3, 16.3, "upper"),
    "CrewMess": (16.6, 22.6, "upper"),
    "Galley": (22.9, 27.4, "upper"),
    "Passageway": (27.7, 31.7, "upper"),
    "EngineRoom": (32.0, 44.0, "upper"),
    "TorpedoRoom": (0.0, 7.0, "lower"),
    "BatteryRoom": (7.3, 16.3, "lower"),
}
WALL = shell.HALF_W - 0.08     # back of wall-standing props (clears the ribs)
WALL_DECAL = shell.HALF_W - 0.002
LOWER_WALL = shell.LOWER_HALF_W - 0.08
LOWER_WALL_DECAL = shell.LOWER_HALF_W - 0.002

STAIR_HOLE = (3.5, 6.4, 1.15, 2.3)      # stairwell opening in the quarters deck (x0, x1, y0, y1)
STAIR_FOOT = (6.3, 1.72)                # foot of the stairs on the lower deck; they climb towards the bow
STAIR_RUN, STAIR_RISE = 2.7, 2.9
PASSAGE_PIT = 0.6
ENGINE_PIT = (32.6, 44.0, 1.2)          # pit under the engines (the aft platform is grating over it)
ENGINE_Y = 1.45                         # diesels on y = +-1.45
ENGINE_X = 36.1
MOTOR_X = 39.3
CATWALK = (32.6, 41.8)                  # engine room catwalk between the diesels
PLATFORM_X = 41.8                       # aft control platform x 41.8 .. 44.0
DOORS = {                               # watertight doors: x of the bulkhead plate, deck
    "FwdQuarters/ControlRoom": (7.0, "upper"), "ControlRoom/CrewMess": (16.3, "upper"),
    "CrewMess/Galley": (22.6, "upper"), "Galley/Passageway": (27.4, "upper"),
    "Passageway/EngineRoom": (31.7, "upper"), "TorpedoRoom/BatteryRoom": (7.0, "lower"),
}


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
    for img in ("label_control_room", "label_torpedo_room", "label_crew_mess", "label_galley", "label_engine_room",
                "label_quarters", "label_battery_room", "label_passage", "label_medical", "label_down"):
        add(pc.room_sign, img)
    # control room
    add(pcx.nav_table)
    add(pcx.nav_console)
    add(pcx.fire_control)
    add(pcx.periscope)
    add(pcx.sonar_station)
    add(pcx.ballast_panel)
    add(pcx.ship_status)
    add(pcx.mission_wall)
    add(pcx.camera_console)
    add(pc.cable_bundle)
    add(pc.cable_bundle, "CableBundleLong", span=2.6, sag=0.45, n=7)
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
    # wall machinery variants (set dressing)
    for w in RACK_WIDTHS:
        for seed in range(7):
            add(pm.equipment_rack, w, seed, f"Rack_{int(w * 100)}_{seed}")
    for w in (0.5, 0.75, 0.9):
        for seed in range(4):
            add(pm.wall_box, w, seed, f"WallBox_{int(w * 100)}_{seed}")
    add(pm.valve_manifold)
    # engine room
    add(pe.diesel_engine, "DieselEngineP", s=-1, label="label_diesel1", engine_id=1)
    add(pe.diesel_engine, "DieselEngineS", s=1, label="label_diesel2", engine_id=2)
    add(pe.motor_generator, "MotorP", s=-1, engine_id=1)
    add(pe.motor_generator, "MotorS", s=1, engine_id=2)
    add(pe.motor_panel, "MotorPanel1", engine_id=1)
    add(pe.motor_panel, "MotorPanel2", engine_id=2)
    add(pe.shaft_line, "ShaftLine", length=round(44.0 - (MOTOR_X + 2.4), 2))
    add(pe.engine_console)
    add(pe.fuel_station)
    add(pe.jerrycan)
    add(pe.oil_can)
    add(pe.stores_shelf)
    # ship systems
    add(ps.bilge_pump)
    add(ps.vent_panel)
    add(ps.duct_fan)
    add(ps.battery_bank)
    add(ps.main_switchboard)
    add(ps.medical_cabinet)
    add(ps.med_bed)
    add(ps.first_aid_kit)
    # walkways
    add(pw.stairs, "Stairs", rise=STAIR_RISE, run=STAIR_RUN)
    add(pw.catwalk, "PassageCatwalk", length=4.0, legs=PASSAGE_PIT)
    add(pw.catwalk, "EngineCatwalk", length=round(CATWALK[1] - CATWALK[0], 2), rails=(False, False), legs=ENGINE_PIT[2])
    add(pw.platform, "AftPlatform", length=round(44.0 - PLATFORM_X, 2), width=4.9, legs=ENGINE_PIT[2])
    add(pw.pipe_bank, "PipeBankA", length=4.0, seed=1)
    add(pw.pipe_bank, "PipeBankB", length=4.0, seed=2)
    return lib


# ------------------------------------------------------------------ helpers

class Room:
    """One compartment. All heights passed to put/port/stbd/... are relative to this room's floor."""

    def __init__(self, name, lib):
        self.name = name
        self.col = core.collection("Room_" + name)
        self.lib = lib
        self.x0, self.x1, self.deck = ROOMS[name]
        lower = self.deck == "lower"
        self.floor = shell.LOWER_FLOOR if lower else 0.0
        self.ceil = shell.LOWER_CEIL if lower else shell.CEIL
        self.half_w = shell.LOWER_HALF_W if lower else shell.HALF_W
        self.wall = LOWER_WALL if lower else WALL
        self.wall_decal = LOWER_WALL_DECAL if lower else WALL_DECAL
        self.roots = []
        self.keep_clear = {"port": [], "stbd": [], "fwd": [], "aft": []}

    def put(self, prop, loc, rot_z=0.0, rot=None):
        loc = (loc[0], loc[1], loc[2] + self.floor)
        root = instance(self.lib[prop], self.col, loc, rot or (0, 0, rot_z))
        root["room"] = self.name
        self.roots.append(root)
        return root

    def add_root(self, root):
        root["room"] = self.name
        self.roots.append(root)
        return root

    # wall helpers: port wall faces -Y (rot 0), starboard wall faces +Y (rot 180)
    def port(self, prop, x, z=0.0, inset=None):
        return self.put(prop, (x, self.wall if inset is None else inset, z), 0)

    def stbd(self, prop, x, z=0.0, inset=None):
        return self.put(prop, (x, -(self.wall if inset is None else inset), z), 180)

    def port_decal(self, prop, x, z):
        return self.port(prop, x, z, self.wall_decal)

    def stbd_decal(self, prop, x, z):
        return self.stbd(prop, x, z, self.wall_decal)

    def fwd_face(self, prop, y, z, x=None):
        """On the forward bulkhead, facing aft (+X)."""
        return self.put(prop, ((self.x0 if x is None else x) + 0.001, y, z), 90)

    def aft_face(self, prop, y, z, x=None):
        """On the aft bulkhead, facing forward (-X)."""
        return self.put(prop, ((self.x1 if x is None else x) - 0.001, y, z), -90)

    def lamps(self, positions):
        for x, y in positions:
            self.put("CeilingLamp", (x, y, self.ceil - self.floor))

    def fan(self, x):
        """Exhaust fan under this room's ventilation duct."""
        if self.deck == "lower":
            return self.put("DuctFan", (x, shell.LOWER_DUCT_Y, shell.LOWER_DUCT_UNDERSIDE - self.floor))
        return self.put("DuctFan", (x, -1.25, shell.DUCT_UNDERSIDE))

    def spawn(self, name, loc, rot_z=0.0):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        self.col.objects.link(e)
        e.location = (loc[0], loc[1], loc[2] + self.floor)
        e.rotation_euler = (0, 0, R(rot_z))
        e["spawn"] = True
        e["room"] = self.name
        return e


# -------------------------------------------------------------------- rooms

def fwd_quarters(lib):
    """Upper deck, forward: crew bunks, the sick bay and the stairwell down to the torpedo room."""
    r = Room("FwdQuarters", lib)
    shell.compartment(r.col, "FwdQuarters_Shell", r.x0, r.x1, holes=[STAIR_HOLE])
    shell.bulkhead(r.col, "Bulkhead_Bow", -0.3, door=False)
    xa, xb, ya, yb = STAIR_HOLE
    r.add_root(pw.railing("StairwellRail", [(xa + 0.45, ya - 0.05, 0), (xb + 0.05, ya - 0.05, 0), (xb + 0.05, yb + 0.12, 0)],
                          col=r.col))
    r.port_decal("RoomSign_Down", (xa + xb) / 2, 2.05)
    r.keep_clear["port"].append((xa - 0.6, xb + 0.1))
    # port: bunks forward of the stairwell
    r.port("BunkBed", 1.15)
    r.port("Poster_Crew", 2.75, 1.55, WALL_DECAL)
    r.port("Intercom", 2.75, 1.0, WALL_DECAL)
    # starboard: sick bay
    r.put("MedBed", (1.35, -(WALL - 0.45), 0), 180)
    r.stbd("MedicalCabinet", 2.95, 0.78)
    r.stbd_decal("RoomSign_Medical", 2.95, 2.25)
    r.stbd("WireShelf", 4.05)
    for k, z in enumerate((0.6, 1.1)):
        r.put("FirstAidKit", (3.85 + 0.4 * k, -(WALL - 0.225), z + 0.012), 180)
    r.put("FirstAidKit", (4.2, -(WALL - 0.225), 0.6 + 0.012), 176)
    r.stbd("Lockers", 5.25)
    r.stbd("Lockers", 6.3)
    # bow bulkhead
    r.fwd_face("VentPanel", -1.45, 1.35)
    r.fwd_face("ShipClock", 0.0, 1.95)
    r.fwd_face("FireExtinguisher", 1.15, 0.35)
    r.fwd_face("RoomSign_Quarters", 0, 2.35)
    r.aft_face("RoomSign_Control_Room", 0, 2.2)
    r.aft_face("FireExtinguisher", -1.2, 0.35)
    r.lamps([(1.4, 0.0), (3.4, -0.45), (5.6, -0.3)])
    r.fan(4.6)
    r.spawn("SPAWN_Medical", (1.35, -0.55, 0), 90)
    return r


def torpedo_room(lib):
    """Lower deck, forward: the four tubes, the loading cradle and reload racks. The stairs come down here."""
    r = Room("TorpedoRoom", lib)
    tube_holes = [[(x + 0.34 * math.cos(2 * math.pi * k / 40), F + z + 0.34 * math.sin(2 * math.pi * k / 40)) for k in range(40)]
                  for x, z in pt.TUBE_POS]
    shell.lower_compartment(r.col, "TorpedoRoom_Shell", r.x0, r.x1, holes=[STAIR_HOLE])
    shell.bulkhead(r.col, "Bulkhead_Bow_Lower", -0.3, holes=tube_holes, door=False, kind="lower")
    sx, sy = STAIR_FOOT
    r.put("Stairs", (sx, sy, 0), 180)
    r.put("TorpedoTubes", (0.0, 0, 0), 90)
    r.put("LoadingCradle", (0.55, -0.62, 0), 90)
    r.put("Torpedo", (2.8, -0.62, 0.76), 180)                # on the cradle, run back clear of the tube-3 loader
    r.put("ChainHoist", (0.5, 0.0, r.ceil - r.floor), 90)
    w = r.wall
    r.port("TorpedoRack", 2.1)
    for z in (0.45, 1.25):
        r.put("Torpedo", (2.1, w - 0.42, z), 180)
    r.stbd("TorpedoRack", 3.9)
    r.put("Torpedo", (3.9, -(w - 0.42), 0.45), 180)
    r.port("AirTanks", 3.75)
    r.put("SupplyCrate", (5.05, 1.85, 0), 5)
    r.put("SparePartsCrate", (5.0, 1.85, 0.45), -4)
    r.stbd("Workbench", 6.15)
    r.stbd("FireExtinguisher", 6.15 - 0.7, 0.9 + 0.2, inset=r.wall - 0.03)   # on its outline on the tool board
    r.put("Toolbox", (5.75, -(w - 0.3), 0.9), 172)
    r.aft_face("BilgePump", -1.25, 0)
    r.stbd("VentPanel", 2.35, 1.35)
    r.stbd_decal("Sign_Explosive", 3.9, 1.95)
    r.stbd_decal("JunctionBox", 1.6, 2.1)
    r.port_decal("Loudspeaker", 1.45, 2.25)
    r.put("AlarmBeacon", (0.001, 1.65, 2.3), 90)
    r.aft_face("FireExtinguisher", -1.25, 0.35)
    r.aft_face("RoomSign_Battery_Room", 0, 2.25)
    r.fwd_face("RoomSign_Torpedo_Room", 0, 2.45, x=0.0)
    r.keep_clear["port"].append((STAIR_HOLE[0] - 0.4, STAIR_HOLE[1] + 0.4))
    r.put("SupplyCrate", (0.75, 1.9, 0), 3)
    r.put("SupplyCrate", (0.75, 1.9, 0.45), -4)
    r.lamps([(1.5, 0.0), (3.6, -0.55), (5.6, -0.6)])
    r.fan(3.2)
    return r


def battery_room(lib):
    """Lower deck, under the control room: battery banks, the MAIN SWITCHBOARD and ship's stores."""
    r = Room("BatteryRoom", lib)
    shell.lower_compartment(r.col, "BatteryRoom_Shell", r.x0, r.x1)
    shell.bulkhead(r.col, "Bulkhead_1_Lower", 7.0, kind="lower")
    shell.bulkhead(r.col, "Bulkhead_2_Lower", 16.3, door=False, kind="lower")
    r.put("WatertightDoor", (7.15, 0, 0), -90)
    w = r.wall
    # port: stores and batteries
    r.port("StoresShelf", 8.35)
    for k in range(3):
        r.put("Jerrycan", (8.35 - 0.5 + k * 0.5, w - 0.25, 0.135), 90 + k * 4)
    r.put("OilCan", (9.35, w - 0.3, 0), 10)
    r.put("OilCan", (9.6, w - 0.25, 0), -25)
    r.port("BatteryBank", 10.95)
    r.port("BatteryBank", 13.55)
    r.port_decal("Sign_Voltage", 12.25, 1.95)
    # starboard: bilge pump and batteries
    r.stbd("BilgePump", 7.95)
    r.stbd("BatteryBank", 10.0)
    r.stbd("BatteryBank", 12.6)
    r.stbd("VentPanel", 14.4, 1.35)
    r.stbd_decal("Sign_Voltage", 11.3, 1.95)
    # aft bulkhead: the main switchboard (power reset)
    r.aft_face("MainSwitchboard", 0.0, 0)
    r.aft_face("FireExtinguisher", -2.0, 0.35)
    r.fwd_face("RoomSign_Torpedo_Room", 0, 2.25)
    r.fwd_face("Intercom", -1.3, 1.35)
    r.lamps([(8.7, 0.0), (11.3, 0.0), (13.9, 0.0)])
    r.fan(11.3)
    return r


def control_room(lib):
    r = Room("ControlRoom", lib)
    shell.compartment(r.col, "ControlRoom_Shell", r.x0, r.x1, duct_x1=r.x1 - 1.0)
    shell.bulkhead(r.col, "Bulkhead_1", 7.0)
    r.put("WatertightDoor", (7.15, 0, 0), -90)
    # port side: weapons, sonar, ballast
    r.put("ElectricalCabinet", (7.85, WALL, 0), 0)
    r.put("FireControl", (9.05, WALL - 0.3, 0), 0)
    r.put("CameraConsole", (10.3, WALL - 0.27, 0), 0)               # CCTV of every compartment
    r.port("Intercom", 11.25, 1.35, WALL_DECAL)
    r.port("SonarStation", 12.65)
    r.put("Stool", (12.65, 1.45, 0), 15)
    r.port("BallastPanel", 14.8)
    r.port("Loudspeaker", 11.25, 2.25, WALL_DECAL)
    r.port("JunctionBox", 13.75, 2.0, WALL_DECAL)
    # centre: periscope and chart table
    r.put("Periscope", (9.9, 0.0, 0), 0)
    r.put("NavTable", (12.0, -0.55, 0), 0)
    # starboard side: mission centre (map, mission board, outside cameras), nav console and equipment
    r.stbd("MissionWall", 8.4)
    r.stbd("Poster_Quiet", 10.9, 1.55, WALL_DECAL)
    r.put("NavConsole", (12.0, -(WALL - 0.31), 0), 180)
    r.stbd("Sign_Voltage", 9.75, 2.15, WALL_DECAL)
    r.stbd("JunctionBox", 13.0, 2.0, WALL_DECAL)
    r.put("ShipStatus", (14.3, -(WALL - 0.27), 0), 180)          # diagnostics: system pages + general alarm
    # escape trunk: ladder on the aft bulkhead up to a ceiling hatch
    r.aft_face("Ladder", -1.35, 0)
    r.put("CeilingHatch", (r.x1 - 0.2 - 0.18, -1.35, shell.CEIL), 0)
    r.aft_face("ShipClock", 1.35, 1.85)
    r.aft_face("RoomSign_Crew_Mess", 0, 2.2)
    r.aft_face("FireExtinguisher", 1.2, 0.35)
    r.fwd_face("RoomSign_Quarters", 0, 2.2)
    r.fwd_face("AlarmBeacon", 1.6, 2.3)
    r.fwd_face("VentPanel", -1.5, 1.35)
    r.port("PipeRiserMustard", 16.05, 0, shell.HALF_W - 0.01)
    r.put("FloorHatch", (14.6, 0.55, 0), 90)
    r.lamps([(8.6, 0.0), (11.3, 0.0), (13.9, 0.0)])
    r.fan(10.5)
    r.put("CableBundleLong", (12.4, -1.55, shell.CEIL - 0.02), 0)        # cable looms slung under the deckhead
    r.put("CableBundle", (8.6, 1.55, shell.CEIL - 0.02), 0)
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
    r.aft_face("VentPanel", -1.25, 1.95 + 0.05)
    r.fwd_face("RoomSign_Control_Room", 0, 2.2)
    r.stbd("PipeRiser", 22.4, 0, shell.HALF_W - 0.01)
    r.lamps([(17.5, 0.2), (21.6, 0.2)])
    r.fan(19.6)
    return r


def galley(lib):
    r = Room("Galley", lib)
    shell.compartment(r.col, "Galley_Shell", r.x0, r.x1, floor="FloorTiles")
    shell.bulkhead(r.col, "Bulkhead_3", 22.6)
    r.put("WatertightDoor", (22.75, 0, 0), -90)
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
    r.aft_face("RoomSign_Passage", 0, 2.2)
    r.aft_face("Sign_Pressure", 1.45, 1.5)
    r.fwd_face("RoomSign_Crew_Mess", 0, 2.2)
    r.fwd_face("FireExtinguisher", 1.2, 0.35)
    r.fwd_face("VentPanel", -1.6, 1.35)
    r.stbd("PipeRiserMustard", 27.15, 0, shell.HALF_W - 0.01)
    r.lamps([(24.0, 0.2), (26.3, 0.2)])
    r.fan(24.6)
    return r


def passageway(lib):
    """Upper deck between the galley and the engine room: a grated walkway over a pit full of pipework."""
    r = Room("Passageway", lib)
    d = PASSAGE_PIT
    shell.compartment(r.col, "Passageway_Shell", r.x0, r.x1, pit=(r.x0, r.x1, d))
    shell.bulkhead(r.col, "Bulkhead_4", 27.4, floor_z=-d)
    r.put("WatertightDoor", (27.55, 0, 0), -90)
    r.put("PassageCatwalk", (r.x0, 0, 0), 0)
    r.put("PipeBankA", (r.x0, shell.HALF_W - 0.04, -d), 0)
    r.put("PipeBankB", (r.x1, -(shell.HALF_W - 0.04), -d), 180)
    r.fwd_face("RoomSign_Galley", 0, 2.2)
    r.fwd_face("VentPanel", -1.6, 1.45)
    r.aft_face("RoomSign_Engine_Room", 0, 2.2)
    r.aft_face("Sign_Hot", 1.45, 1.5)
    r.aft_face("Intercom", -1.45, 1.45)
    r.port_decal("Sign_Pressure", 29.7, 1.65)
    r.lamps([(28.7, 0.0), (30.7, 0.0)])
    r.fan(29.7)
    return r


def engine_room(lib):
    """Upper deck aft: two big diesels in a pit with a catwalk between them and a grated control platform."""
    r = Room("EngineRoom", lib)
    px0, px1, depth = ENGINE_PIT
    shell.compartment(r.col, "EngineRoom_Shell", r.x0, r.x1, pit=ENGINE_PIT, rib_step=1.5)
    shell.bulkhead(r.col, "Bulkhead_5", 31.7, floor_z=-PASSAGE_PIT)
    shell.bulkhead(r.col, "Bulkhead_Stern", r.x1, door=False, floor_z=-depth)
    r.put("EngineRoomDoor", (31.85, 0, 0), -90)
    # machinery in the pit
    for name, y in (("P", ENGINE_Y), ("S", -ENGINE_Y)):
        r.put("DieselEngine" + name, (ENGINE_X, y, -depth), 0)
        r.put("Motor" + name, (MOTOR_X, y, -depth), 0)
        r.put("ShaftLine", (MOTOR_X + 2.4, y, -depth + 0.82), 0)
    r.put("EngineCatwalk", (CATWALK[0], 0, 0), 0)
    r.put("MotorPanel1", (34.2, 0.6, 0), 0)                          # local panels clamped to the catwalk rails
    r.put("MotorPanel2", (34.2, -0.6, 0), 180)
    r.put("AftPlatform", (PLATFORM_X, 0, 0), 0)
    rails = [
        ("Rail_FwdP", [(px0 + 0.03, 0.65, 0), (px0 + 0.03, shell.HALF_W - 0.1, 0)]),
        ("Rail_FwdS", [(px0 + 0.03, -0.65, 0), (px0 + 0.03, -(shell.HALF_W - 0.1), 0)]),
        ("Rail_MotorP", [(MOTOR_X + 0.1, 0.63, 0), (PLATFORM_X - 0.03, 0.63, 0), (PLATFORM_X - 0.03, 1.22, 0)]),
        ("Rail_MotorS", [(MOTOR_X + 0.1, -0.63, 0), (PLATFORM_X - 0.03, -0.63, 0), (PLATFORM_X - 0.03, -(shell.HALF_W - 0.1), 0)]),
    ]
    for name, pts in rails:
        r.add_root(pw.railing(name, pts, col=r.col))
    # aft platform: manoeuvring console, fuel day tank + transfer pump, bilge pump, spare fuel and oil
    r.put("EngineConsole", (r.x1 - 0.4, -0.55, 0), -90)
    r.port("FuelStation", 42.8)
    r.stbd("BilgePump", 42.25)
    r.put("Jerrycan", (42.8, -(WALL - 0.2), 0), 90)
    r.put("Jerrycan", (43.05, -(WALL - 0.2), 0), 84)
    r.put("OilCan", (42.85, -(WALL - 0.55), 0), 30)
    r.put("OilCan", (43.1, -(WALL - 0.5), 0), -40)
    r.stbd("VentPanel", 43.55, 1.4)
    r.stbd_decal("Sign_Hot", 40.2, 1.6)
    r.port_decal("Sign_Hot", 35.0, 1.75)
    r.fwd_face("RoomSign_Passage", 0, 2.2)
    r.fwd_face("FireExtinguisher", 1.3, 0.35)
    r.aft_face("ShipClock", 1.6, 1.9)
    r.aft_face("Loudspeaker", -1.95, 2.0)
    r.lamps([(33.2, 0.0), (35.8, 0.0), (38.4, 0.0), (41.0, 0.0), (43.2, 0.0)])
    r.fan(37.2)
    return r


# --------------------------------------------------------- wall machinery

RACK_WIDTHS = (0.9, 0.75, 0.6, 0.5)


def _rack(lib, w, seed):
    return f"Rack_{int(w * 100)}_{seed}"


def _bbox(root):
    from .render import bbox
    return bbox(core.hierarchy(root))


def _free(span, taken, margin=0.05):
    lo, hi = span
    out = []
    for a, b in sorted(taken):
        a, b = a - margin, b + margin
        if a > lo:
            out.append((lo, min(a, hi)))
        lo = max(lo, b)
    if lo < hi:
        out.append((lo, hi))
    return [(a, b) for a, b in out if b - a >= 0.5]


def _pack(a, b):
    """Rack widths that fill [a, b], centred."""
    L, ws = b - a, []
    while True:
        for w in RACK_WIDTHS:
            if sum(ws) + w + 0.01 * len(ws) <= L:
                ws.append(w)
                break
        else:
            break
    start = a + (L - sum(ws) - 0.01 * (len(ws) - 1)) / 2
    xs = []
    for w in ws:
        xs.append((start + w / 2, w))
        start += w + 0.01
    return xs


def fill_walls(room, seed=0):
    """Fill every free stretch of wall/bulkhead (below 2 m) with equipment racks + cable looms."""
    lib, x0, x1 = room.lib, room.x0, room.x1
    f0, hw, wall = room.floor, room.half_w, room.wall
    taken = {"port": list(room.keep_clear["port"]), "stbd": list(room.keep_clear["stbd"]),
             "fwd": list(room.keep_clear["fwd"]), "aft": list(room.keep_clear["aft"])}
    for root in list(room.roots):
        lo, hi = _bbox(root)
        if lo.z - f0 > 1.95 or hi.z - f0 < 0.2:
            continue
        if hi.y > hw - 0.75:
            taken["port"].append((lo.x, hi.x))
        if lo.y < -hw + 0.75:
            taken["stbd"].append((lo.x, hi.x))
        if lo.x < x0 + 0.75:
            taken["fwd"].append((lo.y, hi.y))
        if hi.x > x1 - 0.75:
            taken["aft"].append((lo.y, hi.y))
    placed = []
    k = seed
    for side in ("port", "stbd"):
        for a, b in _free((x0 + 0.08, x1 - 0.08), taken[side]):
            for x, w in _pack(a, b):
                k += 1
                key = _rack(lib, w, k % 7)
                if side == "port":
                    placed.append((room.port(key, x), side))
                else:
                    placed.append((room.stbd(key, x), side))
    e = hw - 0.2
    for side, xf, rz in (("fwd", x0 + 0.005, 90), ("aft", x1 - 0.005, -90)):
        for span in ((-e, -0.72), (0.72, e)):
            for a, b in _free(span, taken[side]):
                for y, w in _pack(a, b):
                    k += 1
                    key = _rack(lib, w, k % 7)
                    placed.append((room.put(key, (xf, y, 0), rz), side))
    # upper band (z 1.86..2.1) above consoles and other low furniture
    band = {"port": list(room.keep_clear["port"]), "stbd": list(room.keep_clear["stbd"])}
    for root in list(room.roots):
        lo, hi = _bbox(root)
        if hi.z - f0 < 1.84 or lo.z - f0 > 2.3:
            continue
        if hi.y > hw - 0.75:
            band["port"].append((lo.x, hi.x))
        if lo.y < -hw + 0.75:
            band["stbd"].append((lo.x, hi.x))
    for side in ("port", "stbd"):
        for a, b in _free((x0 + 0.08, x1 - 0.08), band[side], margin=0.03):
            L = b - a
            ws = []
            while True:
                for w in (0.9, 0.75, 0.5):
                    if sum(ws) + w + 0.02 * len(ws) <= L:
                        ws.append(w)
                        break
                else:
                    break
            x = a + (L - sum(ws) - 0.02 * (len(ws) - 1)) / 2
            for w in ws:
                k += 1
                key = f"WallBox_{int(w * 100)}_{k % 4}"
                if side == "port":
                    placed.append((room.port(key, x + w / 2, 1.87, hw - 0.005), side))
                else:
                    placed.append((room.stbd(key, x + w / 2, 1.87, hw - 0.005), side))
                x += w + 0.02
    # cable looms from each rack up into the overhead
    p = Prop(room.name + "_CableLooms", col=room.col, category="decor")
    rnd = __import__("random").Random(seed + 5)
    top = min(room.ceil - 0.3, f0 + 2.6)
    for root, side in placed:
        lo, hi = _bbox(root)
        n = rnd.randint(2, 5)
        for c in range(n):
            t = (c + 1) / (n + 1)
            if side in ("port", "stbd"):
                sgn = 1 if side == "port" else -1
                x = lo.x + (hi.x - lo.x) * t
                a = Vector((x, sgn * (wall - 0.13 - 0.03 * c), hi.z + 0.01))
                b = Vector((x + rnd.uniform(-0.15, 0.15), sgn * (hw - 0.12), min(top, f0 + 2.45 + rnd.uniform(0, 0.15))))
            else:
                y = lo.y + (hi.y - lo.y) * t
                sx = 1 if side == "fwd" else -1
                xf = room.x0 if side == "fwd" else room.x1
                a = Vector((xf + sx * (0.13 + 0.03 * c), y, f0 + pm.RACK_H + 0.03))
                b = Vector((xf + sx * 0.05, y + rnd.uniform(-0.15, 0.15), top))
            if b.z <= a.z + 0.1:
                continue
            mid = (a + b) / 2 + Vector((0, 0, 0.12))
            pts = [a, a + Vector((0, 0, 0.08)), mid, b]
            p.tube(core.rounded_path(pts, 0.08, 4), rnd.uniform(0.006, 0.012),
                   rnd.choice(["BlackPlastic", "BlackPlastic", "PaintRed", "PaintNavy", "Rubber", "PaintMustard"]), segs=6)
    p.finish()
    return placed


def build_level(lib):
    rooms = [fwd_quarters(lib), control_room(lib), crew_mess(lib), galley(lib), passageway(lib), engine_room(lib),
             torpedo_room(lib), battery_room(lib)]
    by = {r.name: r for r in rooms}
    # keep the swing area of each door leaf clear (leaves open into the forward room, hinge on +Y)
    for name in ("FwdQuarters", "ControlRoom", "CrewMess", "TorpedoRoom"):
        by[name].keep_clear["aft"].append((0.55, 1.8))
    by["Galley"].keep_clear["aft"].append((-0.7, 0.7))
    for i, r in enumerate(rooms):
        if r.name in ("Passageway", "EngineRoom"):
            continue
        fill_walls(r, seed=i * 10)
    return rooms


def nav_data():
    """Walkable areas for the game (Blender coordinates): floors, stairs, catwalks, platform, doors, pits."""
    sx, sy = STAIR_FOOT
    xa, xb, ya, yb = STAIR_HOLE
    return {
        "decks": {"upper": 0.0, "lower": shell.LOWER_FLOOR},
        "rooms": {k: {"x0": v[0], "x1": v[1], "deck": v[2]} for k, v in ROOMS.items()},
        "doors": [{"between": k.split("/"), "x": v[0], "deck": v[1], "w": shell.DOOR_HOLE[0]} for k, v in DOORS.items()],
        "stairs": [{"name": "Stairs", "bottom": [sx, sy, shell.LOWER_FLOOR], "top": [sx - STAIR_RUN, sy, 0.0], "width": 1.0,
                    "upper": "FwdQuarters", "lower": "TorpedoRoom"}],
        "holes": [{"room": "FwdQuarters", "x0": xa, "x1": xb, "y0": ya, "y1": yb}],
        "pits": [
            {"room": "Passageway", "x0": ROOMS["Passageway"][0], "x1": ROOMS["Passageway"][1], "depth": PASSAGE_PIT,
             "walk": [{"x0": ROOMS["Passageway"][0], "x1": ROOMS["Passageway"][1], "y0": -0.6, "y1": 0.6}]},
            {"room": "EngineRoom", "x0": ENGINE_PIT[0], "x1": ENGINE_PIT[1], "depth": ENGINE_PIT[2],
             "walk": [{"x0": CATWALK[0], "x1": CATWALK[1], "y0": -0.6, "y1": 0.6},
                      {"x0": PLATFORM_X, "x1": ROOMS["EngineRoom"][1], "y0": -2.45, "y1": 2.45}]},
        ],
        "half_w": {"upper": shell.HALF_W, "lower": shell.LOWER_HALF_W},
        "ceil": {"upper": shell.CEIL, "lower": shell.LOWER_CEIL},
        "engines": [{"id": 1, "x": ENGINE_X, "y": ENGINE_Y, "base": -ENGINE_PIT[2]}, {"id": 2, "x": ENGINE_X, "y": -ENGINE_Y, "base": -ENGINE_PIT[2]}],
    }
