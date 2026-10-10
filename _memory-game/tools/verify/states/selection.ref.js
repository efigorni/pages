// The quiz-selection reference: round 2's simulation module (~/Documents/ENG-00-english-words/sim/selection.js),
// copied unchanged below this header. engine.js's pickQuiz/updateStats port it; scenarios.js P2 checks the port
// against it, and selection-fixtures.js prints the arrays P2 also keeps recorded.

// Which words an English-words quiz asks, and what an answer does to a word's score (round 2, F5).
// No dependencies, no DOM, no clock, no Math.random: the caller passes the stats, the session clock
// (`opts.now`) and the random source, so the same inputs give the same questions.
//
// A word's score is `firstTry`, its first-pick-correct quiz answers; its level is that score, capped at
// MASTER. A quiz draws from three groups of the words she has met (`encountered`):
//   NEW       never asked in a quiz yet, taken in teaching order (the longest-waiting first);
//   LEARNING  asked before, still under MASTER, the most overdue first: a level's wait between asks
//             grows by GROWTH per level, so the shakiest words come back soonest;
//   SURE      fully learned, the longest unasked first: the "sure success" questions.
// Every quiz asks at least NEW_MIN new words and SURE_MIN sure ones when there are that many; LEARNING
// gets the rest. A group too small for its share passes the slots on: first to NEW (up to NEW_MAX),
// then to SURE, then to any word left. A sure word opens the quiz and another closes it.

const RECOMMENDED = Object.freeze({
  size: 10, // questions per quiz (fewer when she has met fewer words)
  master: 3, // first-try successes that make a word fully learned
  newMin: 1, // never-asked words every quiz takes while there are any (2+ floods LEARNING)
  newMax: 4, // the most never-asked words a quiz takes while sure ones can fill in
  sureMin: 3, // fully learned words every quiz takes while there are any
  growth: 2, // a LEARNING word's wait (in quizzes) doubles per level before it is overdue
  jitter: 0.5, // random spread on the overdue ranking, so two quizzes in a row differ
  decrement: 'demote', // a 1st-try miss on a fully learned word drops it to master - 1
});

const idOf = (item) => (item !== null && typeof item === 'object' ? item.id : item);

function levelOf(entry, master = RECOMMENDED.master) {
  const n = entry && Number.isFinite(entry.firstTry) ? Math.floor(entry.firstTry) : 0;
  return Math.max(0, Math.min(n, master));
}

// The questions for one quiz, in asking order: ids from `items` (teaching order; ids or {id} objects)
// whose `stats[id].encountered` is set. `opts.now` is the quiz clock: one tick per quiz started.
function pickQuiz(items, stats, opts, rng) {
  const o = { ...RECOMMENDED, ...(opts || {}) };
  if (typeof rng !== 'function') throw new TypeError('pickQuiz needs an rng () => [0, 1)');
  const now = Number.isFinite(o.now) ? o.now : 0;
  const fresh = [];
  const learning = [];
  const sure = [];
  items.forEach((item, order) => {
    const id = idOf(item);
    const entry = stats ? stats[id] : null;
    if (!entry || !entry.encountered) return;
    const level = levelOf(entry, o.master);
    const asked = Number.isFinite(entry.lastAsked);
    // never asked counts as asked one quiz before the first: overdue at any level
    const gap = asked ? Math.max(0, now - entry.lastAsked) : now + 1;
    const spread = 1 + o.jitter * rng();
    if (level >= o.master) sure.push({ id, key: (gap + 1) * spread });
    else if (!asked && level === 0) fresh.push({ id, key: -order });
    else learning.push({ id, key: ((gap + 1) / Math.pow(o.growth, level)) * spread });
  });
  const byKey = (a, b) => b.key - a.key;
  fresh.sort(byKey);
  learning.sort(byKey);
  sure.sort(byKey);

  const n = Math.min(o.size, fresh.length + learning.length + sure.length);
  const count = { fresh: 0, learning: 0, sure: 0 };
  const groups = { fresh, learning, sure };
  let left = n;
  const take = (group, k) => {
    const got = Math.max(0, Math.min(k, groups[group].length - count[group], left));
    count[group] += got;
    left -= got;
  };
  take('sure', o.sureMin);
  take('fresh', o.newMin);
  take('learning', left);
  take('fresh', o.newMax - count.fresh);
  take('sure', left);
  take('fresh', left);

  const sureIds = sure.slice(0, count.sure).map((e) => e.id);
  const middle = shuffle(
    fresh.slice(0, count.fresh).concat(learning.slice(0, count.learning)).map((e) => e.id)
      .concat(sureIds.slice(2)),
    rng,
  );
  if (sureIds.length >= 1) middle.unshift(sureIds[0]);
  if (sureIds.length >= 2) middle.push(sureIds[1]);
  return middle;
}

function shuffle(list, rng) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// One answered question: a first-pick-correct answer adds one to `firstTry` (up to MASTER when a rule
// can take it back down); a miss counts in `misses` and, by `decrement`:
//   'none'    the score stays;
//   'demote'  a fully learned word drops to MASTER - 1, so it is practised again (the recommended rule);
//   'dec'     the score drops by one, whatever the level.
// Updates `stats[id]` in place (creating it as encountered) and returns it.
function updateStats(stats, id, firstTryCorrect, now, opts) {
  const o = { ...RECOMMENDED, ...(opts || {}) };
  const prev = stats[id] || {};
  const entry = {
    encountered: true,
    firstTry: Number.isFinite(prev.firstTry) ? Math.max(0, Math.floor(prev.firstTry)) : 0,
    misses: Number.isFinite(prev.misses) ? prev.misses : 0,
    lastAsked: now,
  };
  if (firstTryCorrect) {
    entry.firstTry += 1;
    if (o.decrement !== 'none') entry.firstTry = Math.min(entry.firstTry, o.master);
  } else {
    entry.misses += 1;
    if (o.decrement === 'dec') entry.firstTry = Math.max(0, Math.min(entry.firstTry, o.master) - 1);
    else if (o.decrement === 'demote' && entry.firstTry >= o.master) entry.firstTry = o.master - 1;
  }
  stats[id] = { ...prev, ...entry };
  return stats[id];
}

// A seeded random source (mulberry32) for callers that want repeatable quizzes, e.g. tests.
function seededRng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const api = { RECOMMENDED, pickQuiz, updateStats, levelOf, seededRng };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
