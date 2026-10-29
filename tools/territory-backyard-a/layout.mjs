// Where everything stands in the demo, in three.js metres (Y up). The work package gives slots as scene (x, z) with the
// house's back wall at z = 2.5 and the yard running to z = 12.5; here that maps to three (x, -z), the same mapping the
// Blender layout sheet uses (Blender (x, y) -> glTF (x, -y)), so the demo and art/previews/territory-backyard-a/backyard agree.
export const SLOT = {
  TY_Field_1: { x: -2.8, z: -6.7 }, TY_Field_2: { x: 2.8, z: -6.7 }, TY_Practice: { x: 0, z: -10.8 },
  TY_Lantern: { x: -5.2, z: -12.0 }, TY_Corner_R: { x: 5.0, z: -11.5 }, TY_Rack: { x: 5.4, z: -4.0 },
};
export const HOUSE_Z = -2.5, BACK_Z = -12.5, HALF_X = 6.0;
export const GATE = { x: 3.5, z: BACK_Z, half: 0.42 };     // the gate sits in the back fence, 1 m wide
export const SPAWN = { x: 0, z: -5.0, heading: Math.PI }; // a few steps out of the back door, facing into the yard
const R = 0.3;                                             // player radius

// axis-aligned blockers (centre x, z, half extents) for the solid props
export const BLOCKERS = [
  { x: SLOT.TY_Field_1.x, z: SLOT.TY_Field_1.z, hx: 1.25, hz: 1.62 },
  { x: SLOT.TY_Field_2.x, z: SLOT.TY_Field_2.z, hx: 1.25, hz: 1.62 },
  { x: SLOT.TY_Lantern.x, z: SLOT.TY_Lantern.z, hx: 0.32, hz: 0.32 },
  { x: SLOT.TY_Rack.x, z: SLOT.TY_Rack.z, hx: 0.36, hz: 0.96 },
  { x: SLOT.TY_Corner_R.x, z: SLOT.TY_Corner_R.z, hx: 0.75, hz: 0.75 },
  { x: 0, z: SLOT.TY_Practice.z, hx: 0.2, hz: 0.2 },        // the practice post
  { x: -3.1, z: -12.0, hx: 0.76, hz: 0.25 },                // stone barbell
  { x: 1.95, z: -10.1, hx: 0.2, hz: 0.12 },                 // stone lock
  { x: -2.4, z: -10.4, hx: 0.38, hz: 0.62 },                // weapon rack
];

/** True when a player centred at (x, z) would overlap a fence, the house wall or a solid prop. */
export function blocked(x, z, { gateOpen }) {
  if (z > HOUSE_Z - R) return true;                         // the house (B's work) is behind the spawn point
  if (Math.abs(x) > HALF_X - R) return true;
  if (z > BACK_Z + R) {                                    // inside the yard
    return BLOCKERS.some(b => Math.abs(x - b.x) < b.hx + R && Math.abs(z - b.z) < b.hz + R);
  }
  if (z > BACK_Z - R) {                                    // crossing the back fence line: only through an open gate
    return !(gateOpen && Math.abs(x - GATE.x) < GATE.half - 0.06);
  }
  return z < BACK_Z - 3.0;                                  // a strip of lane behind the yard, then the demo ends
}

/** Is a player at (x, z) inside the gate leaf's swing area (closing would hit them)? */
export function inGateSwing(x, z) {
  return Math.abs(x - GATE.x) < GATE.half + 0.5 && Math.abs(z - GATE.z) < 1.0;
}

/** Interaction spots: fields from the path side, the gate from inside or outside. */
export function nearestTarget(x, z) {
  const cands = [
    { kind: 'field', i: 0, x: SLOT.TY_Field_1.x + 1.25, z: SLOT.TY_Field_1.z },
    { kind: 'field', i: 1, x: SLOT.TY_Field_2.x - 1.25, z: SLOT.TY_Field_2.z },
    { kind: 'gate', x: GATE.x, z: GATE.z },
  ];
  let best = null, bd = Infinity;
  for (const c of cands) {
    const d = c.kind === 'field' ? Math.hypot((x - c.x) * 1.0, Math.max(0, Math.abs(z - c.z) - 1.4)) : Math.hypot(x - c.x, z - c.z);
    if (d < bd) { bd = d; best = c; }
  }
  return bd < 1.3 ? best : null;
}
