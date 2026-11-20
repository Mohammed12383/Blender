// Video director: a scripted tour that uses every control on the boat. Runs inside the game page.
// The recorder calls __director.frame() once per video frame; it advances the script and the game by 1/FPS.
(() => {
  const g = window.__game, sim = g.sim, inn = g.inn, player = g.player;
  const FPS = window.__FPS || 24, DT = 1 / FPS;
  const V3 = (x, y, z) => new g.camera.position.constructor(x, y, z);

  // ---- overlay: captions, fades
  const css = document.createElement('style');
  css.textContent = `
  #cap { position: fixed; left: 50%; bottom: 7%; transform: translateX(-50%); text-align: center; pointer-events: none; z-index: 50;
    font-family: Inter, 'Segoe UI', sans-serif; color: #fff; text-shadow: 0 2px 6px #000; }
  #cap b { display: inline-block; font: 900 30px Inter, sans-serif; letter-spacing: .06em; color: #ffd34d; background: #000a; padding: 6px 16px; border-radius: 8px; }
  #cap span { display: block; margin-top: 8px; font: 600 19px Inter, sans-serif; background: #0009; padding: 5px 12px; border-radius: 6px; }
  #cap kbd { font: 800 15px monospace; background: #f2ead6; color: #111; border-radius: 4px; padding: 1px 6px; margin: 0 2px; }
  #fade { position: fixed; inset: 0; background: #000; opacity: 0; pointer-events: none; z-index: 60; }
  #title { position: fixed; inset: 0; display: none; flex-direction: column; align-items: center; justify-content: center; z-index: 70;
    background: radial-gradient(circle at 50% 40%, #12303bf2, #05080af7 70%); color: #ffd34d; font: 900 64px Inter, sans-serif; letter-spacing: .08em; }
  #title small { font: 600 22px Inter, sans-serif; color: #f2ead6; margin-top: 14px; letter-spacing: .02em; }
  #station { display: none !important; }`;
  document.head.appendChild(css);
  const cap = document.createElement('div'); cap.id = 'cap'; document.body.appendChild(cap);
  const fade = document.createElement('div'); fade.id = 'fade'; document.body.appendChild(fade);
  const title = document.createElement('div'); title.id = 'title'; document.body.appendChild(title);
  const caption = (head, sub = '') => { cap.innerHTML = head ? `<b>${head}</b>${sub ? `<span>${sub}</span>` : ''}` : ''; };
  const showTitle = (big, small) => { title.style.display = big ? 'flex' : 'none'; title.innerHTML = big ? `${big}<small>${small}</small>` : ''; };

  // ---- input helpers (the game's own handlers do the work)
  const down = (key) => window.dispatchEvent(new KeyboardEvent('keydown', { key }));
  const up = (key) => window.dispatchEvent(new KeyboardEvent('keyup', { key }));
  const press = (key) => { down(key); up(key); };
  const click = (button = 0) => g.camera && document.getElementById('view').dispatchEvent(new MouseEvent('mousedown', { button, buttons: 1 }));
  const lookAt = (p) => {
    const eye = V3(player.pos.x, player.pos.y + 1.65, player.pos.z);
    const d = p.clone().sub(eye);
    player.yaw = Math.atan2(-d.x, -d.z);
    player.pitch = Math.atan2(d.y, Math.hypot(d.x, d.z));
  };
  const place = (x, y, z, yaw = player.yaw, pitch = -0.08) => { player.pos.set(x, y, z); player.yaw = yaw; player.pitch = pitch; player.vy = 0; };
  const find = (kind, test = () => true) => inn.interactables.find((i) => i.kind === kind && test(i));
  const leave = () => { if (player.mode !== 'walk') g.leaveStation(); if (player.mode !== 'walk') g.leaveStation(); };
  // walk along waypoints at walking speed using the real navigation (stairs, doors, furniture)
  function walkTo(x, z, speed = 2.2) {
    const dx = x - player.pos.x, dz = z - player.pos.z, d = Math.hypot(dx, dz);
    if (d < 0.08) return true;
    const s = Math.min(d, speed * DT);
    const want = Math.atan2(-dx, -dz);
    let dy = want - player.yaw; while (dy > Math.PI) dy -= 2 * Math.PI; while (dy < -Math.PI) dy += 2 * Math.PI;
    player.yaw += dy * Math.min(1, DT * 6);
    const f = inn.nav.move(player.pos, dx / d * s, dz / d * s, sim.doors, player.swim);
    if (f !== null && !player.swim) player.pos.y = f;
    return false;
  }

  // keep the tour tidy: enemies don't attack, no new waves, and each scene holds the boat at a chosen depth
  let holdDepth = 0;
  const hold = (d) => { holdDepth = d; };
  // the scripted fire stays one fire (no spreading while the tour shows how to put it out)
  let mainFire = null;
  const oneFire = () => sim.fires.forEach((q) => { if (q !== mainFire && !q.out) { q.out = true; sim.events.push({ type: 'fireOut', fire: q }); } });
  sim.spawnWave = () => {};
  // no random hits during the tour (each scene makes its own leak or fire), and none of the alarms that go with them
  sim.damage = () => {};
  const msg0 = sim.message.bind(sim);
  sim.message = (text, kind) => { if (/hunting us|scent|something huge|DEPTH CHARGES|TORPEDO IN THE WATER|HIT!/.test(text)) return; msg0(text, kind); };
  function calm() {
    for (const e of sim.entities) {
      if (e.kind === 'frigate') { e.state = 'patrol'; e.chargeTimer = 99; e.gunTimer = 99; }
      if (e.kind === 'enemySub') { e.state = 'patrol'; e.fireTimer = 99; }
      if (e.kind === 'shark' || e.kind === 'squid') e.alive = false;
    }
    if (holdDepth !== null) { sim.sub.depth = holdDepth; sim.sub.vy = 0; }
    sim.sub.hull = Math.max(sim.sub.hull, 90);
    player.health = Math.max(player.health, 62);   // smoke and flames sting, but no red hurt overlay in the tour
  }

  // ---- the script: a list of shots. Each has a duration (s), optional start(), and every-frame update(t).
  const shots = [];
  const shot = (dur, start, update) => shots.push({ dur, start, update });
  const at = (t, t0, fn, state) => { if (t >= t0 && !state[t0]) { state[t0] = true; fn(); } };

  // 0. title card
  shot(2.5, () => {
    showTitle('DEEPWATER CREW', 'A tour of every control on the boat');
    place(14.2, 0, 0.6, Math.PI / 2, -0.05);
    sim.entities.forEach((e) => { if (e.kind === 'shark') e.alive = false; });
  }, (t) => { player.yaw = Math.PI / 2 + Math.sin(t * 0.6) * 0.3; });

  // 1. control room walk-through
  shot(4.0, () => { showTitle(null); caption('CONTROL ROOM', 'Helm, ballast panel, periscope, sonar, fire control and the chart table'); place(15.4, 0, -0.6, Math.PI / 2, -0.1); },
    (t) => { walkTo(11.6, 0.9, 1.0); });

  // 2. helm
  shot(9.0, () => { g.keys.clear(); g.enterStation('helm'); caption('HELM', 'Engine telegraph <kbd>W</kbd> <kbd>S</kbd> · rudder <kbd>A</kbd> <kbd>D</kbd> · centre <kbd>X</kbd>'); },
    (t, st) => {
      at(t, 2.0, () => press('w'), st); at(t, 3.0, () => press('w'), st); at(t, 4.0, () => down('a'), st);
      at(t, 5.6, () => up('a'), st); at(t, 6.4, () => down('d'), st); at(t, 7.2, () => up('d'), st); at(t, 8.0, () => press('x'), st);
    });

  // 3. ballast and dive planes
  shot(8.5, () => { leave(); g.enterStation('ballast'); caption('BALLAST & DIVE PLANES', '<kbd>F</kbd> flood tanks (dive) · <kbd>B</kbd> blow · <kbd>H</kbd> hold · <kbd>W</kbd> <kbd>S</kbd> planes · the DIVE PROFILE shows the sea floor ahead'); },
    (t, st) => {
      at(t, 1.8, () => press('f'), st); at(t, 3.6, () => down('s'), st); at(t, 4.6, () => up('s'), st);
      at(t, 5.6, () => press('h'), st); at(t, 6.4, () => down('w'), st); at(t, 7.2, () => { up('w'); press('x'); }, st);
      if (t > 1.8) hold(Math.min(9, holdDepth + DT * 1.4));
    });

  // 4. periscope
  let frig = null;
  shot(19.0, () => {
    leave(); hold(9); sim.sub.ballast = 0.5; sim.setValve('hold');
    const s = sim.sub;
    const ships = sim.entities.filter((e) => e.alive && (e.kind === 'frigate' || e.kind === 'freighter'));
    ships.forEach((e, i) => { const b = s.heading + 0.5 + i * 0.12, r = 260 + i * 70; e.x = s.x + Math.cos(b) * r; e.z = s.z - Math.sin(b) * r; e.heading = b + 1.6; e.speed = 1.5; });
    frig = ships.find((e) => e.kind === 'frigate');
    s.periscopeBearing = 0.15; s.periscopeZoom = 1.2; s.periscopePitch = 0;
    g.enterStation('periscope');
    caption('PERISCOPE', 'Train it with <kbd>A</kbd> <kbd>D</kbd> (you turn with it) · zoom with the ZOOM knob <kbd>Z</kbd>');
  }, (t, st) => {
    at(t, 2.0, () => down('a'), st); at(t, 4.8, () => up('a'), st);
    at(t, 5.2, () => down('z'), st); at(t, 6.2, () => up('z'), st);
    at(t, 6.6, () => caption('TAG A CONTACT', 'Slide the tag selector <kbd>1</kbd>–<kbd>8</kbd> · press <kbd>MARK</kbd> on the ship in the crosshair'), st);
    at(t, 7.0, () => g.periscopeTag(2), st);
    at(t, 7.6, () => g.periscopeTag(3), st);
    if (frig && t > 6.0 && t < 9.5) { const s = sim.sub; const want = Math.atan2(-(frig.z - s.z), frig.x - s.x) - s.heading; s.periscopeBearing += (want - s.periscopeBearing) * Math.min(1, DT * 3); }
    at(t, 9.0, () => g.periscopeMark(), st);
    at(t, 11.5, () => caption('EYE TO THE EYEPIECE', '<kbd>V</kbd> or right-click for the full view · tags float over the ships'), st);
    at(t, 12.0, () => press('v'), st);
    at(t, 13.0, () => down('d'), st); at(t, 13.8, () => up('d'), st);
    at(t, 15.0, () => press('v'), st);
    at(t, 15.6, () => caption('TILT AND CLEAR', 'Tilt with <kbd>W</kbd> <kbd>S</kbd> (TILT knob) · <kbd>C</kbd> CLEAR removes a tag'), st);
    at(t, 16.0, () => down('w'), st); at(t, 16.8, () => up('w'), st); at(t, 17.0, () => down('s'), st); at(t, 17.8, () => up('s'), st);
    at(t, 18.3, () => press('c'), st);
  });

  // 5. sonar: train the hydrophone, listen, lock, ping
  shot(10.0, () => { leave(); g.enterStation('sonar'); caption('SONAR', 'Turn the TRAIN wheel <kbd>A</kbd> <kbd>D</kbd> to aim the hydrophone · the SIGNAL meter rises when a ship is there'); },
    (t, st) => {
      at(t, 0.8, () => down('a'), st); at(t, 3.0, () => { up('a'); down('d'); }, st); at(t, 5.0, () => up('d'), st);
      at(t, 5.6, () => caption('SONAR', '<kbd>L</kbd> LOCK what you hear for fire control · <kbd>P</kbd> active ping (they hear you!)'), st);
      at(t, 6.0, () => press('l'), st); at(t, 7.4, () => press('p'), st); at(t, 9.0, () => press('n'), st);
    });

  // 6. chart table: plan a route
  shot(11.0, () => {
    leave(); g.enterStation('chart'); g.inn.chartZoom = 1; g.inn.chartCursor.x = 0; g.inn.chartCursor.z = 0;
    caption('ROUTE PLANNING', 'Chart table: move the cursor with the CURSOR stick <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> · <kbd>SPACE</kbd> ADD WPT');
  }, (t, st) => {
    const c = g.inn.chartCursor;
    at(t, 1.0, () => down('d'), st); at(t, 2.2, () => { up('d'); down('w'); }, st); at(t, 2.8, () => up('w'), st);
    at(t, 3.2, () => press(' '), st);
    at(t, 3.8, () => down('d'), st); at(t, 4.8, () => { up('d'); down('s'); }, st); at(t, 5.8, () => up('s'), st);
    at(t, 6.2, () => press(' '), st);
    at(t, 6.8, () => down('d'), st); at(t, 7.6, () => up('d'), st);
    at(t, 7.9, () => press(' '), st);
    at(t, 8.4, () => caption('ROUTE PLANNING', '<kbd>BACKSPACE</kbd> DEL WPT removes the last one · <kbd>Z</kbd> <kbd>X</kbd> zoom in and out'), st);
    at(t, 8.8, () => press('backspace'), st); at(t, 9.3, () => press(' '), st);
    at(t, 9.6, () => down('z'), st); at(t, 10.3, () => up('z'), st);
  });
  // 6b. helm: follow the route on the autopilot
  shot(7.0, () => { leave(); g.enterStation('helm'); caption('AUTOPILOT', 'Helm: <kbd>T</kbd> steers along the chart route · the scope shows the next waypoint'); },
    (t, st) => { at(t, 1.2, () => press('t'), st); at(t, 2.4, () => press('w'), st); at(t, 3.2, () => press('w'), st); });
  // 6c. ship status: every system on one console, and the general alarm
  shot(13.0, () => {
    leave();
    // something to report: a leak and a little water in the battery room, a small fire in the galley
    const l = { id: sim.nextId++, room: 7, x: 12.0, y: -1.6, side: 1, z: -1.9, severity: 0.8, fixed: false };
    sim.leaks.push(l); sim.events.push({ type: 'leak', leak: l }); sim.water[7] = 0.35;
    sim.addFire(3); const f = sim.fires[sim.fires.length - 1]; f.intensity = 0.4;
    g.enterStation('status');
    caption('SHIP STATUS', 'Every system on one console: <kbd>1</kbd>–<kbd>8</kbd> pages, from NOISE to HEAT · a key flashes red when that system needs help');
  }, (t, st) => {
    ['1', '2', '3', '4', '5', '6', '7', '8'].forEach((k, i) => at(t, 1.0 + i * 1.1, () => press(k), st));
    at(t, 9.9, () => caption('GENERAL ALARM', 'Flip the guard and press: klaxon and beacons for the whole crew'), st);
    at(t, 10.4, () => press('g'), st);
    at(t, 12.6, () => {
      press('g');
      sim.leaks.forEach((l) => { if (!l.fixed) sim.fixLeak(l.id); }); sim.water[7] = 0; sim.water[6] = 0;
      sim.fires.forEach((f) => { f.out = true; }); sim.smoke.fill(0);
    }, st);
    sim.water[7] = Math.min(sim.water[7], 0.35);
  });

  // 6d. the mission wall and the CCTV console
  shot(8.0, () => { leave(); g.enterStation('mission'); caption('MISSION MAP', 'Islands, contacts, tags and the route · the MISSION board: goal, next action, stealth, crew · bow and stern cameras'); },
    (t, st) => { at(t, 2.5, () => press('x'), st); at(t, 3.3, () => press('x'), st); at(t, 5.5, () => press('z'), st); at(t, 6.3, () => press('z'), st); });
  shot(8.0, () => { leave(); g.enterStation('cameras'); caption('CAMERAS', 'CCTV of every compartment: <kbd>1</kbd>–<kbd>6</kbd> TORPEDO · BATTERY · ENGINES · GALLEY · MESS · QUARTERS'); },
    (t, st) => { ['1', '2', '3', '4', '5', '6'].forEach((k, i) => at(t, 0.8 + i * 1.15, () => press(k), st)); });
  // 7. fire control and a torpedo run
  shot(14.0, () => {
    leave(); sim.setAutopilot(false); sim.setTelegraph(1); sim.weapons.lock = null; sim.setAim(0); g.enterStation('weapons');
    caption('FIRE CONTROL', 'The AIM stick <kbd>A</kbd> <kbd>D</kbd> sets the torpedo course when nothing is locked · <kbd>N</kbd> DECOY');
  }, (t, st) => {
    at(t, 1.0, () => down('a'), st); at(t, 2.2, () => { up('a'); down('d'); }, st); at(t, 3.6, () => up('d'), st);
    at(t, 4.0, () => press('n'), st);
    at(t, 4.6, () => {
      if (frig) { sim.weapons.lock = frig.id; const s = sim.sub; frig.x = s.x + Math.cos(s.heading + 0.1) * 170; frig.z = s.z - Math.sin(s.heading + 0.1) * 170; frig.speed = 0; }
      caption('FIRE CONTROL', 'Locked from sonar · <kbd>1</kbd>–<kbd>4</kbd> tube · <kbd>F</kbd> flood · <kbd>O</kbd> door · <kbd>K</kbd> arm · <kbd>G</kbd> guard · <kbd>SPACE</kbd> FIRE');
    }, st);
    at(t, 5.4, () => press('1'), st); at(t, 6.4, () => press('f'), st); at(t, 7.6, () => press('o'), st);
    at(t, 8.8, () => press('k'), st); at(t, 10.0, () => press('g'), st); at(t, 11.4, () => press(' '), st);
    if (t > 4.6 && frig) { const s = sim.sub; frig.x = s.x + Math.cos(s.heading + 0.1) * 170; frig.z = s.z - Math.sin(s.heading + 0.1) * 170; }
  });
  shot(9.0, () => { player.mode = 'chase'; g.ext.orbit.yaw = 0.35; g.ext.orbit.pitch = 0.18; g.ext.orbit.dist = 70; caption('TORPEDO AWAY', 'The external camera follows the run'); },
    (t) => { g.ext.orbit.yaw = 0.35 + t * 0.06; if (frig && frig.alive) { const s = sim.sub; frig.x = s.x + Math.cos(s.heading + 0.1) * 170; } });

  // 8. down the stairs to the torpedo room
  shot(9.0, () => { leave(); player.mode = 'walk'; place(2.2, 0, -0.6, -Math.PI / 2 - 0.4, -0.25); caption('STAIRS', 'Down from the forward quarters to the torpedo room (lower deck)'); },
    (t, st) => {
      if (!st.a) { if (walkTo(2.9, -1.72, 1.4)) st.a = true; }
      else if (!st.b) { if (walkTo(6.75, -1.72, 1.2)) st.b = true; player.pitch = -0.35; }
      else walkTo(5.4, 0.2, 1.2);
    });

  // 8b. the tool board behind the workbench
  shot(5.5, () => { g.keys.clear(); place(5.95, -2.9, 0.75, Math.PI + 0.25, 0.02); caption('TOOL BOARD', 'Every tool hangs on its painted outline: take the wrench or the extinguisher here'); },
    (t) => { player.yaw = Math.PI + 0.25 - t * 0.09; });
  // 9. reload a tube
  shot(14.0, () => {
    g.keys.clear(); caption('RELOAD', 'Take a torpedo from the rack, open the breech, load, close');
    const rack = find('rack'); place(rack.pos.x, -2.9, 0.15, 0, -0.2); lookAt(rack.pos); g.interact(rack);
  }, (t, st) => {
    at(t, 1.2, () => { place(1.2, -2.9, 0.3, Math.PI / 2, -0.15); }, st);
    at(t, 2.4, () => g.enterStation('tube3'), st);
    at(t, 4.2, () => press('e'), st);       // open the breech
    at(t, 6.8, () => press('e'), st);       // load
    at(t, 9.4, () => press('e'), st);       // close
    at(t, 11.0, () => caption('RELOAD', 'Tube 3 loaded'), st);
  });

  // 10. engine room: start the diesels
  shot(8.0, () => {
    leave(); hold(8);
    place(42.6, 0, -0.2, Math.PI / 2, -0.1); g.enterStation('engines');
    caption('ENGINE CONTROLS', 'Start the diesels <kbd>1</kbd> <kbd>2</kbd> · they need air: snorkel depth (12 m) or surfaced');
  }, (t, st) => { at(t, 1.5, () => press('1'), st); at(t, 3.0, () => press('2'), st); });
  shot(6.0, () => { leave(); place(34.2, 0, 0.0, 0, -0.1); g.enterStation('motor1'); caption('DIESEL PANEL', 'Each diesel has its own panel: POWER, revs, load and warnings · <kbd>T</kbd> TALK reports to the control room'); },
    (t, st) => { at(t, 2.0, () => press('t'), st); sim.sub.depth = 8; });
  shot(6.0, () => { leave(); place(41.6, 0, 0.0, Math.PI / 2, -0.32); caption('TWIN DIESELS', 'Running and charging the battery'); },
    (t) => { player.yaw = Math.PI / 2 + Math.sin(t * 0.5) * 0.25; sim.sub.depth = 8; });

  // 11. fuel: transfer pump strokes and a jerrycan
  shot(8.0, () => { place(43.3, 0, -1.1, Math.PI, -0.1); g.enterStation('fuel'); caption('FUEL TRANSFER PUMP', 'Click to pump the lever up and down: every stroke lifts diesel into the day tank'); sim.fuel.day = 30; },
    (t, st) => { for (let k = 0; k < 14; k++) at(t, 1.2 + k * 0.42, () => g.pumpStroke(0), st); sim.sub.depth = 8; });
  shot(6.5, () => {
    leave(); caption('JERRYCAN', 'Carry it to the filler on top of the day tank and hold <kbd>E</kbd> to pour');
    const can = find('pickup', (i) => i.data.item === 'fuel_can' && i.pos.y > -1); place(can.pos.x - 0.6, 0, can.pos.z, -Math.PI / 2, -0.4); lookAt(can.pos); g.interact(can);
  }, (t, st) => {
    const fil = find('filler');
    at(t, 1.0, () => { place(43.3, 0, -0.9, Math.PI, 0.2); lookAt(fil.pos); }, st);
    at(t, 1.6, () => down('e'), st); at(t, 5.0, () => up('e'), st);
    sim.sub.depth = 8;
  });
  // 12. oil and coolant on a diesel
  shot(7.0, () => {
    caption('OIL', 'Top up a diesel at its oil filler: hold <kbd>E</kbd> with an oil can');
    const can = find('pickup', (i) => i.data.item === 'oil_can' && i.pos.y > -1); place(can.pos.x - 0.6, 0, can.pos.z, 0, -0.4); g.interact(can);
    const oil = find('oil', (i) => i.data === 0); place(oil.pos.x + 0.3, 0, 0.15, 0, -0.3); lookAt(oil.pos);
    sim.engines[0].oil = 30;
  }, (t, st) => { at(t, 1.0, () => down('e'), st); at(t, 4.0, () => up('e'), st); sim.sub.depth = 8; });
  shot(6.0, () => {
    caption('COOLANT VALVE', 'If it shakes shut the engine overheats and steams: open it again');
    const v = find('coolant', (i) => i.data === 0); lookAt(v.pos); sim.engines[0].temp = 108;
  }, (t, st) => {
    const v = find('coolant', (i) => i.data === 0);
    at(t, 0.5, () => g.interact(v), st); at(t, 3.5, () => g.interact(v), st); sim.sub.depth = 8;
  });

  // 13. power failure: the main switchboard
  shot(10.0, () => {
    sim.tripPower(); place(14.2, -2.9, 0, -Math.PI / 2, -0.1); g.enterStation('switchboard');
    caption('POWER FAILURE', 'Main switchboard (battery room): close the tripped breakers <kbd>1</kbd>–<kbd>8</kbd>, then the MAIN BREAKER');
  }, (t, st) => {
    st.open ||= sim.breakers.map((b, k) => (b ? -1 : k)).filter((k) => k >= 0);
    st.open.forEach((k, i) => at(t, 1.6 + i * 1.0, () => press(String(k + 1)), st));
    at(t, 7.0, () => press('m'), st);
  });

  // 14. a leak: the jet, the wrench
  shot(9.0, () => {
    leave(); hold(70); sim.engines.forEach((e, i) => sim.stopEngine(i));
    const l = { id: sim.nextId++, room: 1, x: 11.4, y: 1.35, side: 1, z: -2.03, severity: 1.3, fixed: false };
    sim.leaks.push(l); sim.events.push({ type: 'leak', leak: l });
    place(9.6, 0, -0.1, -1.25, -0.08);
    caption('HULL LEAK', 'Sea water under pressure: the deeper you are, the harder it sprays');
  }, (t) => { sim.sub.depth = 70; player.yaw = -1.25 + Math.sin(t * 0.4) * 0.15; });
  shot(7.0, () => {
    caption('FIX IT', 'Pick up a wrench and hold <kbd>E</kbd> on the leak');
    const w = find('wrench', (i) => Math.abs(i.pos.x - 9.9) < 0.6); place(9.9, 0, -0.9, 0, -0.6); lookAt(w.pos); g.interact(w);
    const l = find('leak'); place(11.4, 0, -1.0, 0, 0.05); lookAt(l.pos);
  }, (t, st) => { at(t, 0.8, () => down('e'), st); at(t, 4.0, () => up('e'), st); sim.sub.depth = 70; });

  // 15. flooding, swimming and the bilge pump
  shot(9.0, () => {
    g.drop(); hold(40); sim.doors[5] = false; sim.water[6] = 2.35;
    const l = { id: sim.nextId++, room: 6, x: 2.6, y: -1.6, side: -1, z: 1.93, severity: 1.1, fixed: false };
    sim.leaks.push(l); sim.events.push({ type: 'leak', leak: l });
    place(1.7, -2.9, -0.2, -Math.PI / 2, 0.0);
    caption('FLOODING', 'Leave a leak too long and the water rises: chest-deep, you swim');
  }, (t) => { sim.sub.depth = 40; g.keys.add('w'); if (t > 4) { g.keys.delete('w'); g.keys.add('c'); } if (t > 6.5) g.keys.delete('c'); player.yaw = -Math.PI / 2 + Math.sin(t * 0.5) * 0.35; });
  shot(10.0, () => {
    g.keys.clear(); sim.leaks.forEach((l) => { if (!l.fixed) sim.fixLeak(l.id); }); sim.water[6] = 1.6;
    place(6.0, -2.9, 1.1, -Math.PI / 2, 0); g.enterStation('bilge6');
    caption('BILGE PUMP', 'Click the handle up and down: every stroke lifts water overboard');
  }, (t, st) => { for (let k = 0; k < 20; k++) at(t, 1.0 + k * 0.42, () => g.pumpStroke(0), st); });

  // 16. fire, smoke and the smoke extract
  shot(7.0, () => {
    leave(); sim.water[6] = 0; hold(30); sim.fires.forEach((f) => { f.out = true; }); sim.smoke.fill(0);
    sim.addFire(2); const f = sim.fires[sim.fires.length - 1]; f.intensity = 1.0; f.x = 19.3; f.z = 0.3; f.y = 0.05; mainFire = f;
    inn.fireViews.forEach((v) => { if (v.fire === f) v.base.set(19.3, 0.05, 0.3); });
    sim.smoke[2] = 0.3; place(22.0, 0, 0.0, Math.PI / 2 + 0.1, -0.05);
    caption('FIRE', 'Flames, sparks and thick smoke: it spreads, burns oxygen and hurts');
  }, () => { sim.sub.depth = 30; oneFire(); });
  shot(8.0, () => {
    const ext = find('extinguisher', (i) => i.pos.x > 16.4 && i.pos.x < 22.7); place(ext.pos.x + 0.6, 0, ext.pos.z, 0, -0.3); lookAt(ext.pos); g.interact(ext);
    place(20.8, 0, 0.3, Math.PI / 2, -0.2);
    caption('EXTINGUISHER', 'Hold <kbd>E</kbd> at the flames');
  }, (t, st) => {
    oneFire();
    const fire = find('fire');
    if (fire) lookAt(fire.pos);
    at(t, 0.6, () => down('e'), st); at(t, 6.5, () => up('e'), st);
  });
  shot(8.0, () => {
    g.drop(); sim.fires.forEach((f) => { if (!f.out) { f.out = true; sim.events.push({ type: 'fireOut', fire: f }); } }); const v = find('vent', (i) => i.data === 2); place(v.pos.x - 1.2, 0, v.pos.z * 0.4, 0, 0); lookAt(v.pos); sim.smoke[2] = 0.75;
    caption('SMOKE EXTRACT', 'Switch on the room\'s fans to suck the smoke out (they need power)');
  }, (t, st) => { const v = find('vent', (i) => i.data === 2); at(t, 1.0, () => { if (sim.vents[2]) sim.setVent(2, false); g.interact(v); }, st); if (t > 2.5) { player.pitch = 0.25; } });

  // 17. galley: cook and eat
  shot(9.0, () => {
    const food = find('food', (i) => i.pos.x > 22.9); place(food.pos.x, 0, 0.5, 0, -0.2); lookAt(food.pos); g.interact(food);
    place(25.35, 0, -0.9, Math.PI, -0.3); g.enterStation('griddle');
    caption('GALLEY', 'Raw steak on the griddle: <kbd>P</kbd> power · <kbd>E</kbd> put on / take off');
  }, (t, st) => { at(t, 1.2, () => press('p'), st); at(t, 2.2, () => press('e'), st); at(t, 3.5, () => caption('GALLEY', 'Sizzling... (8 seconds later)'), st); if (t > 3.5 && t < 6.5) g.griddle.slots.forEach((sl) => { if (sl) sl.t += DT * 2.6; }); at(t, 6.6, () => press('e'), st); });
  shot(4.0, () => { leave(); caption('EAT', 'Press <kbd>F</kbd> to eat: hunger restored'); g.player.hunger = 30; }, (t, st) => { at(t, 1.0, () => press('f'), st); });

  // 18. sick bay
  shot(7.0, () => {
    g.player.health = 35; const bed = find('medbed'); place(1.4, 0, 0.9, Math.PI, -0.2); lookAt(bed.pos); g.interact(bed);
    caption('SICK BAY', 'Lie on the med bed to heal · first-aid kits in the cabinet');
  }, () => {});

  // 19. surface and climb to the bridge
  shot(9.0, () => {
    leave(); hold(0.4); sim.sub.depth = 0.4; sim.sub.vy = 0; sim.sub.ballast = 0.3;
    const lad = find('ladder'); place(lad.pos.x - 1.0, 0, lad.pos.z, -Math.PI / 2, 0); g.interact(lad);
    g.ext.look.yaw = -0.6;
    caption('BRIDGE', 'Surfaced: climb the ladder and look around');
  }, (t) => { g.ext.look.yaw = -0.6 + t * 0.12; });

  // the crew handbook
  shot(6.0, () => { leave(); caption('CREW HANDBOOK', '<kbd>TAB</kbd> explains every station and system on the boat'); press('tab'); },
    (t, st) => { const hb = document.getElementById('handbook'); if (hb) hb.scrollTop = Math.max(0, (t - 2) * 120); at(t, 5.8, () => press('tab'), st); });
  // end card
  shot(3.0, () => { leave(); showTitle('DEEPWATER CREW', 'Run every station together · sink the convoy · keep the boat alive'); caption(''); }, () => {});

  // ---- runner
  let i = -1, t = 0, state = {};
  window.__director = {
    total: shots.reduce((a, s) => a + s.dur, 0),
    durs: shots.map((s) => s.dur),
    frame() {
      if (i < 0 || t >= shots[i].dur) {
        if (i >= 0 && window.__onShotEnd) window.__onShotEnd(i);
        i += 1; t = 0; state = {};
        if (i >= shots.length) return { done: true };
        try { shots[i].start && shots[i].start(); } catch (e) { console.error('shot', i, 'start', e.message); }
        fade.style.opacity = '1';
      }
      try { shots[i].update && shots[i].update(t, state); } catch (e) { console.error('shot', i, 'update', e.message); }
      fade.style.opacity = String(Math.max(0, 1 - t / 0.35, (t - (shots[i].dur - 0.25)) / 0.25));
      calm();
      g.tick(DT);
      t += DT;
      return { done: false, shot: i, t };
    },
  };
})();
