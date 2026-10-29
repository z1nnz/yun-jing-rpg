import test from 'node:test';
import assert from 'node:assert/strict';
import { Yard, stageOf, lanternLevel, GROW_SECONDS, STAGE_T } from './yard.mjs';
import { blocked, GATE } from './layout.mjs';

test('stage thresholds follow the work package exactly', () => {
  assert.equal(stageOf(0), 0);
  assert.equal(stageOf(0.2499), 0);
  assert.equal(stageOf(0.25), 1);
  assert.equal(stageOf(0.5999), 1);
  assert.equal(stageOf(0.6), 2);
  assert.equal(stageOf(0.9999), 2);
  assert.equal(stageOf(1), 3);
  assert.deepEqual(STAGE_T, [0.25, 0.6, 1.0]);
});

test('both crops grow through the same four stages', () => {
  for (const crop of ['qingling', 'lotus']) {
    const y = new Yard();
    y.plant(0, crop);
    const seen = new Set();
    for (let s = 0; s <= GROW_SECONDS + 1; s += 0.5) { y.tick(0.5); seen.add(y.stage(0)); }
    assert.deepEqual([...seen].sort(), [0, 1, 2, 3]);
  }
});

test('fast-forward reaches maturity sooner; speed is clamped', () => {
  const y = new Yard();
  y.plant(0, 'qingling');
  y.setSpeed(30);
  y.tick(GROW_SECONDS / 30);
  assert.equal(y.stage(0), 3);
  y.setSpeed(1000);
  assert.equal(y.speed, 60);
  y.setSpeed(0);
  assert.equal(y.speed, 1);
});

test('cannot plant into a busy field or an unknown crop', () => {
  const y = new Yard();
  assert.ok(y.plant(0, 'qingling'));
  assert.equal(y.plant(0, 'lotus'), null);
  assert.equal(y.plant(1, 'rice'), null);
  assert.equal(y.plant(5, 'lotus'), null);
});

test('harvest only when mature', () => {
  const y = new Yard();
  y.plant(0, 'lotus');
  y.tick(GROW_SECONDS * 0.9);
  assert.equal(y.harvest(0), false);
  y.tick(GROW_SECONDS);
  assert.equal(y.harvest(0), true);
  assert.equal(y.fields[0].crop, null);
});

test('repeated harvest of the same planting does not brighten the lantern twice', () => {
  const y = new Yard();
  const id = y.plant(0, 'qingling');
  y.tick(GROW_SECONDS);
  assert.equal(y.harvest(0, id), true);
  assert.equal(y.harvest(0, id), false);          // double click / replayed event
  y.plant(0, 'qingling');
  y.tick(GROW_SECONDS);
  assert.equal(y.harvest(0, id), false);          // stale id against the new planting
  assert.equal(y.harvests, 1);
  assert.equal(y.level, 1);
});

test('lantern brightens one step per harvest and stops at 4', () => {
  const y = new Yard();
  const levels = [y.level];
  for (let k = 0; k < 6; k++) {
    y.plant(k % 2, k % 2 ? 'lotus' : 'qingling');
    y.tick(GROW_SECONDS);
    y.harvest(k % 2);
    levels.push(y.level);
  }
  assert.deepEqual(levels, [0, 1, 2, 3, 4, 4, 4]);
  assert.equal(lanternLevel(-3), 0);
  assert.equal(lanternLevel(99), 4);
});

test('the drying rack fills after the first harvest', () => {
  const y = new Yard();
  assert.equal(y.rackFull, false);
  y.plant(1, 'lotus');
  y.tick(GROW_SECONDS);
  y.harvest(1);
  assert.equal(y.rackFull, true);
});

test('the gate never closes on the player', () => {
  const y = new Yard();
  assert.equal(y.toggleGate(false), true);
  assert.equal(y.toggleGate(true), true);         // standing in the swing area: stays open
  assert.equal(y.toggleGate(false), false);
});

test('a closed gate blocks the gateway, an open one lets the player through', () => {
  const p = { x: GATE.x, z: GATE.z };
  assert.equal(blocked(p.x, p.z, { gateOpen: false }), true);
  assert.equal(blocked(p.x, p.z, { gateOpen: true }), false);
});

test('the yard fence keeps the player inside except through the gate', () => {
  assert.equal(blocked(0, -7.5, { gateOpen: true }), false);    // middle of the yard
  assert.equal(blocked(-6.0, -7.0, { gateOpen: true }), true);  // left fence
  assert.equal(blocked(6.0, -7.0, { gateOpen: true }), true);   // right fence
  assert.equal(blocked(-3.0, -12.5, { gateOpen: true }), true); // back fence away from the gate
});
