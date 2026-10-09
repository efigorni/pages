// The arrays scenarios.js P2 keeps recorded: what the simulation's reference module (selection.ref.js) picks for
// P2's pools and seeds. After a deliberate change to the selection (the module and engine.js together), run
//   node _memory-game/tools/verify/states/selection-fixtures.js
// and paste its output over P2's wantA, wantB, wantSeq and wantTries.
const { RECOMMENDED: SIM, pickQuiz, updateStats, seededRng } = require('./selection.ref.js');
const { snap, poolA, poolB, poolC } = require('./selection-pools.js');

const A = snap(poolA.groups, poolA.extra);
const wantA = Object.fromEntries([1, 2, 3].map((seed) => [seed, pickQuiz(A.items, A.stats, { ...SIM, now: 100 }, seededRng(seed))]));
const B = snap(poolB.groups, poolB.extra);
const wantB = pickQuiz(B.items, B.stats, { ...SIM, now: 0 }, seededRng(9)).join(' ');
const C = snap(poolC.groups);
const rng = seededRng(42);
const wantSeq = [];
for (let now = 0; now < 6; now++) {
  const ids = pickQuiz(C.items, C.stats, { ...SIM, now }, rng);
  ids.forEach((id, j) => updateStats(C.stats, id, (j + now) % 3 !== 0, now, SIM));
  wantSeq.push(ids.join(' '));
}
const wantTries = C.items.map((id) => C.stats[id].firstTry);
console.log(`const wantA = ${JSON.stringify(wantA)};`);
console.log(`const wantB = ${JSON.stringify(wantB)};`);
console.log(`const wantSeq = ${JSON.stringify(wantSeq)};`);
console.log(`const wantTries = ${JSON.stringify(wantTries)};`);
