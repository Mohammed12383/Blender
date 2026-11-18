# Asset manifest

Generated from `models/Submarine_Interior.blend`. Every prop is also exported on its own
as `models/props/<Name>.glb`. Moving parts are separate nodes with their origin on the hinge/axis.

| Prop | Category | Moving parts (interaction) | Interaction points |
|---|---|---|---|
| AirTanks | decor | `GaugeNeedle` (gauge_needle), `Valve1` (valve_wheel), `Valve2` (valve_wheel), `Valve3` (valve_wheel) | – |
| AlarmBeacon | light | `Reflector` (spin) | – |
| BallastPanel | station · ballast | `AirGaugeNeedle` (gauge_needle), `BlowValve` (ballast_blow), `DepthGaugeNeedle` (gauge_needle), `FloodValve` (ballast_flood), `PressureGaugeNeedle` (gauge_needle), `TrimLever1` (lever), `TrimLever2` (lever), `VentValve` (ballast_vent) | `hand_target`, `hand_target`, `operate` |
| BunkBed | furniture | `Curtain_lower` (curtain), `Curtain_upper` (curtain) | `berth_lower`, `berth_upper` |
| CargoFreighter | vehicle | `Crane_17` (crane), `Crane_30` (crane) | `hit_center` |
| CeilingHatch | door | `Lid` (hatch), `LidWheel` (hatch_lock) | – |
| CeilingLamp | light | – | – |
| ChainHoist | station · hoist | `Trolley` (slide), `Hook` (hook) | – |
| CheckersBoard | pickup | – | – |
| CoffeeStation | station · coffee | `Tap` (pour) | `hand_target`, `use` |
| DrumstickCooked | pickup | – | – |
| DrumstickRaw | pickup | – | – |
| ElectricalCabinet | decor | `Door` (door), `GaugeANeedle` (gauge_needle), `GaugeBNeedle` (gauge_needle), `Switch1` (toggle), `Switch2` (toggle), `Switch3` (toggle), `Switch4` (toggle), `Switch5` (toggle) | – |
| EnemyFrigate | vehicle | `Radar` (spin), `Turret` (turret), `Gun` (gun) | `hit_center` |
| EnemySubmarine | vehicle | `Propeller` (spin) | `interior_origin` |
| EngineRoomDoor | door | `Leaf` (door), `WheelBack` (door_lock), `WheelFront` (door_lock) | `open_back`, `open_front`, `hand_target`, `hand_target` |
| EquipmentRack | decor | `Door` (door) | – |
| ExhaustHood | decor | – | – |
| FireControl | station · weapons | `ArmKey` (key_switch), `FireButton` (fire), `FireGuard` (guard), `Handset` (pickup), `TubeSelect1` (toggle), `TubeSelect2` (toggle), `TubeSelect3` (toggle), `TubeSelect4` (toggle) | `hand_target`, `hand_target`, `operate` |
| FireExtinguisher | pickup | – | – |
| FloorHatch | door | `Lid` (hatch) | – |
| Fridge | storage | `FreezerDoor` (door), `FridgeDoor` (door) | `use` |
| Griddle | station · cooking | `Door1` (door), `Door2` (door), `LeftHeatKnob` (dial), `PowerButton` (power), `RightHeatKnob` (dial), `TimerKnob` (dial) | `hand_target`, `hand_target`, `cook_slot1`, `cook_slot2`, `cook_slot3`, `cook_slot4`, `operate` |
| HullCrack | decor | – | `spray` |
| HullPatch | decor | – | – |
| Intercom | station | `TalkButton` (intercom_talk) | – |
| JunctionBox | decor | – | – |
| Ladder | ladder | – | `climb` |
| LoadingCradle | station · loader | `Carriage` (push), `LiftCrank` (lift_crank), `LiftTray` (lift) | `hand_target`, `operate` |
| Lockers | storage | `Door1` (door), `Door2` (door), `Door3` (door) | – |
| Loudspeaker | decor | – | – |
| MessTable | furniture | – | – |
| MugBlue | pickup | – | – |
| MugCream | pickup | – | – |
| MugRed | pickup | – | – |
| NavConsole | station · navigation | `Button1` (button), `Button2` (button), `Button3` (button), `Button4` (button), `Joystick` (joystick), `StickTrigger` (button), `ZoomDial` (dial) | `hand_target`, `hand_target`, `operate` |
| NavTable | station · navigation | `Dividers` (pickup), `Marker1` (map_marker), `Marker2` (map_marker), `Marker3` (map_marker), `Marker4` (map_marker), `ParallelRuler` (pickup) | `hand_target`, `hand_target`, `use_back`, `use_front` |
| NoticeBoard | decor | – | – |
| PattyCooked | pickup | – | – |
| PattyRaw | pickup | – | – |
| PendantLamp | light | – | – |
| Periscope | station · periscope | `Head` (periscope_train), `HandleL` (periscope_handle), `Zoom` (zoom), `HandleR` (periscope_handle), `Mark` (mark_target) | `hand_target`, `hand_target`, `operate` |
| PipeRiser | station · valve | `GaugeNeedle` (gauge_needle), `Valve` (valve_wheel) | `operate` |
| PipeRiserMustard | station · valve | `GaugeNeedle` (gauge_needle), `Valve` (valve_wheel) | `operate` |
| Plate | pickup | – | – |
| Poster_Crew | decor | – | – |
| Poster_Dive | decor | – | – |
| Poster_Galley | decor | – | – |
| Poster_Quiet | decor | – | – |
| PotRail | decor | `Ladle_35` (pickup), `Pan_-50` (pickup), `Pan_12` (pickup), `Pot_-20` (pickup), `Whisk_52` (pickup) | – |
| PrepCounter | station · prep | `ColdTap` (tap), `HotTap` (tap), `Knife` (pickup) | `operate` |
| Rack_50_0 | decor | – | `cable_in` |
| Rack_50_1 | decor | – | `cable_in` |
| Rack_50_2 | decor | – | `cable_in` |
| Rack_50_3 | decor | – | `cable_in` |
| Rack_50_4 | decor | – | `cable_in` |
| Rack_50_5 | decor | – | `cable_in` |
| Rack_50_6 | decor | – | `cable_in` |
| Rack_60_0 | decor | – | `cable_in` |
| Rack_60_1 | decor | – | `cable_in` |
| Rack_60_2 | decor | – | `cable_in` |
| Rack_60_3 | decor | – | `cable_in` |
| Rack_60_4 | decor | – | `cable_in` |
| Rack_60_5 | decor | – | `cable_in` |
| Rack_60_6 | decor | – | `cable_in` |
| Rack_75_0 | decor | – | `cable_in` |
| Rack_75_1 | decor | – | `cable_in` |
| Rack_75_2 | decor | – | `cable_in` |
| Rack_75_3 | decor | – | `cable_in` |
| Rack_75_4 | decor | – | `cable_in` |
| Rack_75_5 | decor | – | `cable_in` |
| Rack_75_6 | decor | – | `cable_in` |
| Rack_90_0 | decor | – | `cable_in` |
| Rack_90_1 | decor | – | `cable_in` |
| Rack_90_2 | decor | – | `cable_in` |
| Rack_90_3 | decor | – | `cable_in` |
| Rack_90_4 | decor | – | `cable_in` |
| Rack_90_5 | decor | – | `cable_in` |
| Rack_90_6 | decor | – | `cable_in` |
| RoomSign_Control_Room | decor | – | – |
| RoomSign_Crew_Mess | decor | – | – |
| RoomSign_Engine_Room | decor | – | – |
| RoomSign_Galley | decor | – | – |
| RoomSign_Torpedo_Room | decor | – | – |
| ShipClock | decor | `HourHand` (clock_hand), `MinuteHand` (clock_hand), `SecondHand` (clock_hand) | – |
| Sign_Explosive | decor | – | – |
| Sign_Hot | decor | – | – |
| Sign_Pressure | decor | – | – |
| Sign_Voltage | decor | – | – |
| SonarStation | station · sonar | `BearingKnob` (dial), `FilterKnob` (dial), `GainKnob` (dial), `Headphones` (pickup), `RangeKnob` (dial), `Switch1` (toggle), `Switch2` (toggle), `Switch3` (toggle), `Switch4` (toggle), `Switch5` (toggle) | `hand_target`, `hand_target`, `operate` |
| SparePartsCrate | decor | – | – |
| SteakCooked | pickup | – | – |
| SteakRaw | pickup | – | – |
| Stool | seat | – | – |
| SubmarineExterior | vehicle | `Propeller` (spin) | `interior_origin` |
| SupplyCrate | decor | – | – |
| Toolbox | pickup | `Lid` (lid) | – |
| Torpedo | pickup | `Propeller1` (spin), `Propeller2` (spin) | – |
| TorpedoRack | storage | – | `slot_lower`, `slot_upper`, `use` |
| TorpedoTubes | station · torpedo_tubes | `Door1` (tube_door), `Door1Latch` (latch), `Door1Wheel` (tube_lock), `Door2` (tube_door), `Door2Latch` (latch), `Door2Wheel` (tube_lock), `Door3` (tube_door), `Door3Latch` (latch), `Door3Wheel` (tube_lock), `Door4` (tube_door), `Door4Latch` (latch), `Door4Wheel` (tube_lock), `Interlock1` (toggle), `Interlock2` (toggle), `Interlock3` (toggle), `Interlock4` (toggle), `ManualFire` (manual_fire), `Tube1Flood` (tube_flood), `Tube1GaugeNeedle` (gauge_needle), `Tube2Flood` (tube_flood), `Tube2GaugeNeedle` (gauge_needle), `Tube3Flood` (tube_flood), `Tube3GaugeNeedle` (gauge_needle), `Tube4Flood` (tube_flood), `Tube4GaugeNeedle` (gauge_needle) | `hand_target`, `hand_target`, `hand_target`, `hand_target`, `hand_target`, `hand_target`, `hand_target`, `hand_target`, `tube1`, `tube2`, `tube3`, `tube4` |
| TrayBlue | pickup | – | – |
| TrayGreen | pickup | – | – |
| ValveManifold | decor | `Gauge1Needle` (gauge_needle), `Gauge3Needle` (gauge_needle), `Valve1` (valve_wheel), `Valve2` (valve_wheel), `Valve3` (valve_wheel), `Valve4` (valve_wheel) | – |
| WallBox_50_0 | decor | – | – |
| WallBox_50_1 | decor | – | – |
| WallBox_50_2 | decor | – | – |
| WallBox_50_3 | decor | – | – |
| WallBox_75_0 | decor | – | – |
| WallBox_75_1 | decor | – | – |
| WallBox_75_2 | decor | – | – |
| WallBox_75_3 | decor | – | – |
| WallBox_90_0 | decor | – | – |
| WallBox_90_1 | decor | – | – |
| WallBox_90_2 | decor | – | – |
| WallBox_90_3 | decor | – | – |
| WallMonitorAft | screen | `Knob1` (knob), `Knob2` (knob) | – |
| WallMonitorFwd | screen | `Knob1` (knob), `Knob2` (knob) | – |
| WatertightDoor | door | `Leaf` (door), `WheelBack` (door_lock), `WheelFront` (door_lock) | `open_back`, `open_front`, `hand_target`, `hand_target` |
| WireShelf | storage | – | `shelf1`, `shelf2`, `shelf3`, `shelf4` |
| Workbench | decor | `ViseJaw` (crank) | – |
| Wrench | pickup | `Jaw` (adjust) | `grip` |

## Characters

| Character | Role | Bones |
|---|---|---|
| Crew_Cook | cook | 51 (Hips, Spine, Chest, Neck, Head, …) |
| Crew_Gunner | weapons_officer | 51 (Hips, Spine, Chest, Neck, Head, …) |
| Crew_Loader | torpedo_loader | 51 (Hips, Spine, Chest, Neck, Head, …) |
| Crew_Navigator | navigator | 51 (Hips, Spine, Chest, Neck, Head, …) |
| FPArms_Cook | cook | 51 (Hips, Spine, Chest, Neck, Head, …) |
| FPArms_Gunner | weapons_officer | 51 (Hips, Spine, Chest, Neck, Head, …) |
| FPArms_Loader | torpedo_loader | 51 (Hips, Spine, Chest, Neck, Head, …) |
| FPArms_Navigator | navigator | 51 (Hips, Spine, Chest, Neck, Head, …) |
