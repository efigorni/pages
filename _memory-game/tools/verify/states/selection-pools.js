// The word pools scenarios.js P2/P3 and selection-fixtures.js pick quizzes from: ids w0.. in teaching order,
// in groups of [count, firstTry, lastAsked (a value, k => value, or none: never asked)], then `extra` words not
// met yet. The shapes are the selection simulation's own (its selection.test.js).
function snap(groups, extra = 0) {
  const items = [];
  const stats = {};
  let i = 0;
  for (const [count, firstTry, lastAsked] of groups) {
    for (let k = 0; k < count; k++, i++) {
      items.push(`w${i}`);
      stats[`w${i}`] = { encountered: true, firstTry };
      if (lastAsked !== undefined) stats[`w${i}`].lastAsked = typeof lastAsked === 'function' ? lastAsked(k) : lastAsked;
    }
  }
  for (let k = 0; k < extra; k++, i++) items.push(`w${i}`);
  return { items, stats };
}

// P2's exact picks: a mixed pool, a small one, and one asked six times in a row with its answers scored.
const poolA = { groups: [[30, 0], [20, 1, (k) => 90 - k], [20, 2, (k) => 80 - 2 * k], [40, 3, (k) => 50 + k]], extra: 10 };
const poolB = { groups: [[6, 0]], extra: 5 };
const poolC = { groups: [[12, 0]] };

module.exports = { snap, poolA, poolB, poolC };
