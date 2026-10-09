// Scenario checks against a game page's scripts (see harness.js). Prints one line per check and
// exits 1 if any fails.
//   node scenarios.js <game>/index.html
process.env.HARNESS_HTML = process.argv[2] || process.env.HARNESS_HTML;
const { boot } = require('./harness');

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  -- ${detail}` : ''}`);
}

async function start(h) {
  await h.click('play');
  await h.advance(700);
}

async function playToLastPair(h) {
  // Match every pair except one, leaving the board in 'idle' with exactly one pair down.
  for (;;) {
    const downs = h.cards().filter((c) => c.state === 'down');
    if (downs.length <= 2) return downs;
    const a = downs[0];
    await h.down(a);
    await h.down(h.pairOf(a));
    await h.advance(1500);
  }
}

(async () => {
  // A squad's game (players with roles) or a word game: each has its own suites.
  const SQUAD = !boot({ noClips: true }).T.DATA.words;
  // The engine's own suites run for every game; a word game's quiz opens with four learned words, so a
  // suite that plays it starts with six.
  const probe = boot({ noClips: true }).T;
  const QUIZ_STORAGE = probe.PLAY.quiz.pool === 'learned'
    ? [[`${probe.DATA.game}:learned`, JSON.stringify(probe.ITEMS.slice(0, 6).map((p) => p.id))]] : [];
  // ---------- S1 boot + deal ----------
  if (SQUAD) {
    const h = boot({ noClips: true });
    await h.click('play');
    const cards = h.cards();
    const ids = cards.map((c) => c.p.id);
    const counts = {};
    ids.forEach((id) => { counts[id] = (counts[id] || 0) + 1; });
    check('S1 30 cards, 15 ids x2', cards.length === 30 && Object.keys(counts).length === 15 && Object.values(counts).every((n) => n === 2));
    check('S1 phase idle after start, fullscreen requested, wake lock taken',
      h.phase() === 'idle' && h.fullscreenRequests.length === 1 && h.sentinels.length === 1);
    // S2 deal guard
    const first = cards[0];
    await h.down(first);
    check('S2 tap during the first 60% of the deal is ignored', first.state === 'down' && h.phase() === 'idle');
    await h.advance(600);
    await h.down(first);
    check('S2 tap after the deal guard flips', first.state === 'up' && h.phase() === 'one');
    // S3 double tap on the same card
    await h.down(first);
    check('S3 second tap on the same card ignored', first.state === 'up' && h.T.game.up.length === 1);
    // S4 mismatch window
    const other = h.firstDown((c) => c.p.id !== first.p.id);
    await h.down(other);
    check('S4 mismatch -> two', h.phase() === 'two');
    await h.down(first);
    check('S4 tap on a face-up card ignored in two', h.T.game.up.length === 2 && h.phase() === 'two');
    await h.advance(2199);
    check('S4 still up at 2199 ms', first.state === 'up' && other.state === 'up');
    await h.advance(1);
    check('S4 flipped back at 2200 ms', first.state === 'down' && other.state === 'down' && h.phase() === 'idle');
    // S5 hurry-up
    await h.down(first);
    await h.down(other);
    await h.advance(1000);
    const third = h.firstDown((c) => c.p.id !== first.p.id && c.p.id !== other.p.id);
    await h.down(third);
    check('S5 hurry-up: old pair down at once, new card up, phase one',
      first.state === 'down' && other.state === 'down' && third.state === 'up' && h.phase() === 'one');
    await h.advance(3000);
    check('S5 stale flip-back timer cleared', third.state === 'up' && h.phase() === 'one');
    // S6 match + matched taps
    const mate = h.pairOf(third);
    await h.down(mate);
    check('S6 match -> matched, found=1, idle', third.state === 'matched' && mate.state === 'matched' && h.T.game.found === 1 && h.phase() === 'idle');
    await h.down(third);
    check('S6 tap on matched ignored', third.state === 'matched' && h.T.game.up.length === 0);
    await h.advance(400);
    check('S6 pip 0 filled after the celebration', h.byId.pips.children[0].classList.contains('full'));
    // speech order for a match: name then match; then a new flip cancels the match line
    h.synth.spoken.length = 0;
    const p = h.firstDown();
    await h.down(p);
    await h.down(h.pairOf(p));
    await h.advance(200);
    const q = h.firstDown();
    await h.down(q);
    await h.advance(3000);
    const texts = h.synth.spoken.map((s) => s.text);
    const said = (x) => x.p.speak_he || x.p.name_he;
    check('S6b match line is cancelled by the next flip', texts.includes(said(p)) && !texts.some((t) => t.startsWith('מספר')) && texts.includes(said(q)), JSON.stringify(texts));
    await h.advance(3000);
    // S7 finish + win timing
    const last = await playToLastPair(h);
    h.synth.spoken.length = 0;
    await h.down(last[0]);
    await h.down(last[1]);
    const t0 = h.clock.now;
    check('S7 last match -> finishing', h.phase() === 'finishing');
    await h.down(h.cards().find((c) => c.state === 'matched'));
    check('S7 taps ignored while finishing', h.phase() === 'finishing');
    let wonAt = null;
    for (let i = 0; i < 200 && wonAt === null; i++) { await h.advance(50); if (h.phase() === 'won') wonAt = h.clock.now - t0; }
    check('S7 win screen reached', wonAt !== null && h.byId.win.classList.contains('show'), `after ${wonAt} ms (speech fake: 60 ms/char)`);
    // S8 wake lock after the win
    await h.advance(10 * 60 * 1000);
    const held = h.sentinels.filter((s) => !s.released).length;
    check('S8 wake lock released on win (ruling)', held === 0, `${held} sentinel(s) still held 10 min after the win`);
    // S16 visibility during won re-acquires
    await h.setVisibility('hidden');
    await h.setVisibility('visible');
    check('S16 no re-acquire when visible on the win screen', h.sentinels.filter((s) => !s.released).length === 0,
      `${h.sentinels.filter((s) => !s.released).length} held after hide/show on the win screen`);
    // S13 replay re-picks bench
    const before = new Set(h.cards().map((c) => c.p.id));
    let differs = false;
    for (let i = 0; i < 20 && !differs; i++) {
      await h.click('replay');
      await h.advance(10);
      const now = new Set(h.cards().map((c) => c.p.id));
      differs = [...now].some((id) => !before.has(id));
      if (!differs) { h.T.game.phase = 'won'; }
    }
    check('S13 replay re-picks bench players', differs);
  }

  // ---------- S10 mute during finishing ----------
  {
    const h = boot();
    await start(h);
    const last = await playToLastPair(h);
    await h.advance(5000);
    await h.down(last[0]);
    await h.down(last[1]);
    const t0 = h.clock.now;
    await h.click('mute');
    let wonAt = null;
    for (let i = 0; i < 400 && wonAt === null; i++) { await h.advance(50); if (h.phase() === 'won') wonAt = h.clock.now - t0; }
    check('S10 mute pressed right after the last match: win screen delay', wonAt !== null && wonAt <= 1600, `won after ${wonAt} ms`);
  }

  // ---------- S14 restart mid-mismatch ----------
  {
    const h = boot();
    await start(h);
    const a = h.cards()[0];
    await h.down(a);
    await h.down(h.firstDown((c) => c.p.id !== a.p.id));
    await h.click('again');
    await h.click('yes');
    await h.advance(3000);
    check('S14 restart during the mismatch window leaves a clean board',
      h.cards().every((c) => c.state === 'down') && h.phase() === 'idle' && h.T.game.up.length === 0);
  }

  // ---------- S11 clips shipped, AudioContext later suspended ----------
  if (SQUAD) {
    const served = new Set();
    const tmp = boot({ clips: true, webAudio: true });
    const all = tmp.T.DATA.players.map((p) => p.id);
    all.forEach((id) => { served.add(`audio/name/${id}.mp3`); served.add(`audio/match/${id}.mp3`); });
    served.add('audio/ui/start.mp3');
    served.add('audio/ui/win.mp3');

    const h = boot({ clips: true, webAudio: true, served });
    await start(h);
    const ac = h.audioCtxs[0];
    check('S11a AudioContext created by the start tap', !!ac && ac.state === 'running');
    const a = h.firstDown();
    await h.down(a);
    await h.advance(50);
    const startedOk = ac.sources.some((s) => s.buffer && s.buffer.url === `audio/name/${a.p.id}.mp3`);
    check('S11a flip plays the name clip through Web Audio', startedOk && h.synth.spoken.length === 0);
    await h.advance(3000);
    const oscBefore = ac.oscillators;
    // context leaves 'running' (screen lock / audio interruption), page hidden then visible again
    ac.state = 'suspended';
    await h.setVisibility('hidden');
    await h.setVisibility('visible');
    const b = h.firstDown((c) => c.state === 'down');
    await h.down(b);
    await h.advance(3000);
    check('S11b something resumes the AudioContext after visibility/tap', ac.resumes > 0, `resume() calls: ${ac.resumes}, ctx.state: ${ac.state}, sfx oscillators since: ${ac.oscillators - oscBefore}`);
    // play to the end with the context still suspended
    await h.advance(3000);
    const last = await playToLastPair(h);
    await h.down(last[0]);
    await h.down(last[1]);
    const t0 = h.clock.now;
    let wonAt = null;
    for (let i = 0; i < 400 && wonAt === null; i++) { await h.advance(50); if (h.phase() === 'won') wonAt = h.clock.now - t0; }
    check('S11c win screen within ~5 s of the last match with a suspended context', wonAt !== null && wonAt < 5000, `won after ${wonAt} ms`);

    // control: same flow with a running context
    const k = boot({ clips: true, webAudio: true, served });
    await start(k);
    const lastK = await playToLastPair(k);
    await k.advance(4000);
    await k.down(lastK[0]);
    await k.down(lastK[1]);
    const t1 = k.clock.now;
    let wonK = null;
    for (let i = 0; i < 400 && wonK === null; i++) { await k.advance(50); if (k.phase() === 'won') wonK = k.clock.now - t1; }
    check('S11d control: running context, win screen timing', wonK !== null && wonK < 5000, `won after ${wonK} ms (name 1.2 s + match 2.5 s)`);
  }

  // ---------- S12 decode() re-entrancy for a clip that was never prefetched ----------
  {
    const served = new Set(['audio/name/zz.mp3']);
    const h = boot({ webAudio: true, served });
    await start(h);
    const ac = h.audioCtxs[0];
    const before = ac.decodes.length;
    h.T.sound.say([{ url: 'audio/name/zz.mp3', text: 'זז' }]);
    await h.advance(500);
    const decodes = ac.decodes.slice(before).filter((b) => b.url === 'audio/name/zz.mp3').length;
    const played = ac.sources.some((s) => s.buffer && s.buffer.url === 'audio/name/zz.mp3');
    const spoke = h.synth.spoken.some((s) => s.text === 'זז');
    check('S12 un-prefetched clip plays from its buffer (no double decode)', decodes === 1 && played && !spoke,
      `decodeAudioData calls on the same ArrayBuffer: ${decodes}, buffer played: ${played}, fell back to speech: ${spoke}`);
  }

  // ---------- S15 bench pick and deck uniformity ----------
  if (SQUAD) {
    const h = boot();
    await start(h);
    const role = (r) => h.T.DATA.players.filter((p) => p.role === r).map((p) => p.id);
    const benchIds = role('bench');
    const starterIds = role('starter');
    const N = 20000;
    const benchCount = Object.fromEntries(benchIds.map((id) => [id, 0]));
    const posCount = new Array(30).fill(0);
    let bad = 0;
    for (let i = 0; i < N; i++) {
      h.T.newGame();
      const ids = h.cards().map((c) => c.p.id);
      const uniq = new Set(ids);
      const bench = [...uniq].filter((id) => benchIds.includes(id));
      if (ids.length !== 30 || uniq.size !== 15 || bench.length !== 4 || !starterIds.every((id) => uniq.has(id))) bad++;
      bench.forEach((id) => { benchCount[id]++; });
      ids.forEach((id, pos) => { if (id === starterIds[0]) posCount[pos]++; });
    }
    const expectBench = N * 4 / 11;
    const chiBench = benchIds.reduce((s, id) => s + (benchCount[id] - expectBench) ** 2 / expectBench, 0);
    const expectPos = N * 2 / 30;
    const chiPos = posCount.reduce((s, n) => s + (n - expectPos) ** 2 / expectPos, 0);
    check('S15 every game: 30 cards, 15 distinct pairs, all 11 starters, 4 bench', bad === 0, `${bad} bad of ${N}`);
    check('S15 bench picks uniform (chi2, df=10, crit 23.2 @ p=.01)', chiBench < 23.2, `chi2=${chiBench.toFixed(1)}`);
    check('S15 card positions uniform (chi2, df=29, crit 49.6 @ p=.01)', chiPos < 49.6, `chi2=${chiPos.toFixed(1)}`);
  }

  // ---------- S17 no Hebrew voice, no clips: last pair timing ----------
  if (SQUAD) {
    const h = boot({ noHebrewVoice: true, noClips: true });
    await start(h);
    const last = await playToLastPair(h);
    await h.down(last[0]);
    await h.down(last[1]);
    const t0 = h.clock.now;
    let wonAt = null;
    for (let i = 0; i < 400 && wonAt === null; i++) { await h.advance(50); if (h.phase() === 'won') wonAt = h.clock.now - t0; }
    check('S17 silent device: win after ~1.5 s', wonAt !== null && wonAt <= 1600, `won after ${wonAt} ms`);
  }

  // ---------- Q1-Q5 the quiz (speech only: the fake voice takes 60 ms a character) ----------
  if (SQUAD) {
    const h = boot({ noClips: true });
    const { DATA, quiz, game } = h.T;
    const pool = DATA.players.map((p) => p.id);
    await h.click('play-quiz');
    const ids = () => quiz.cards.map((c) => c.p.id);
    check('Q1 the quiz asks: 4 distinct cards with the answer, every pool player a pip',
      h.phase() === 'ask' && new Set(ids()).size === 4 && ids().includes(quiz.answer.p.id) && game.total === pool.length);
    const first = quiz.answer;
    await h.pick(quiz.cards.find((c) => c !== first));
    check('Q2 a pick in the first 450 ms of a question is ignored', quiz.cards.every((c) => c.state === 'down'));
    await h.advance(500);
    // A wrong pick turns over and says that player's match line; a next pick, the replay button or
    // the right pick cuts it off.
    const line = (card) => h.T.clip.match(card.p).text;
    const from = h.synth.spoken.length;
    const heard = () => h.synth.spoken.slice(from).map((s) => s.text);
    const [w1, w2, w3] = quiz.cards.filter((c) => c !== first);
    await h.pick(w1);
    await h.pick(w1);
    await h.advance(100);
    const quiet = heard().length === 0;
    await h.advance(600);
    check('Q2 a wrong pick turns over (named, out of play), stays on the question; a second tap is ignored',
      w1.state === 'out' && w1.el.getAttribute('aria-label') === w1.p.name_he && h.phase() === 'ask'
      && quiz.answer === first && game.found === 0);
    check("Q2 a beat after the wrong pick, that player's match line, once", quiet && heard().join('|') === line(w1),
      JSON.stringify(heard()));
    let cancels = h.synth.cancels;
    await h.pick(w2);
    const cutByPick = h.synth.cancels > cancels && !h.synth.speaking;
    await h.advance(700);
    check('Q2 the next wrong pick cuts it off and says its own', cutByPick && heard().join('|') === `${line(w1)}|${line(w2)}`,
      JSON.stringify(heard()));
    cancels = h.synth.cancels;
    await h.click('say');
    await h.advance(100);
    check('Q2 the replay button cuts it off and asks the question again', h.synth.cancels > cancels
      && heard().join('|') === `${line(w1)}|${line(w2)}|${line(first)}`, JSON.stringify(heard()));
    await h.pick(w3);
    await h.advance(700);
    const wrongLine = h.synth.speaking && heard().slice(-1)[0] === line(w3);
    cancels = h.synth.cancels;
    h.synth.spoken.length = 0;
    await h.pick(first);
    const name = first.p.speak_he || first.p.name_he;
    await h.advance(100);
    check('Q3 the right pick cuts off the wrong line, reveals and says the name', wrongLine && h.synth.cancels > cancels
      && first.state === 'up' && h.phase() === 'reveal' && game.found === 1
      && h.synth.spoken.map((s) => s.text).join('|') === name, JSON.stringify(h.synth.spoken.map((s) => s.text)));
    await h.advance(60 * name.length + 1300);
    check('Q3 still on the reveal until 1.5 s after the name', h.phase() === 'reveal');
    await h.advance(300);
    const next = quiz.answer.p;
    await h.advance(3000);
    const said = h.synth.spoken.map((s) => s.text);
    check("Q3 then the next question, asked by its player's match line alone", h.phase() === 'ask' && next !== first.p
      && said.slice(1).join('|') === h.T.clip.match(next).text, JSON.stringify(said));
    const asked = [first.p.id];
    for (let i = 0; i < pool.length && h.phase() === 'ask'; i++) {
      asked.push(quiz.answer.p.id);
      await h.advance(500);
      await h.pick(quiz.answer);
      await h.advance(800);
      if (h.phase() === 'reveal') await h.pick(quiz.cards[0]);
      await h.advance(50);
    }
    let wonAt = null;
    for (let i = 0; i < 200 && wonAt === null; i++) { await h.advance(50); if (h.phase() === 'won') wonAt = i; }
    check('Q4 every quiz player asked exactly once, then the win screen', asked.length === pool.length
      && new Set(asked).size === pool.length && wonAt !== null && h.byId.win.classList.contains('show'), `${asked.length}/${pool.length}`);
    const backups = new Set(DATA.players.filter((p) => p.role === 'backup').map((p) => p.id));
    let dealt = 0;
    for (let i = 0; i < 200; i++) { h.T.newGame(); dealt += h.cards().filter((c) => backups.has(c.p.id)).length; }
    check('Q5 memory never deals a backup', dealt === 0, `${backups.size} backup(s), ${dealt} dealt in 200 games`);
  }

  // ---------- QC2, QC3: a quiz reveal waits under the ↻ confirm and on a hidden page ----------
  {
    const h = boot({ noClips: true, storage: QUIZ_STORAGE });
    const { quiz } = h.T;
    await h.click('play-quiz');
    await h.advance(3000);
    let at = quiz.at;
    await h.pick(quiz.answer);
    await h.click('again');
    await h.advance(20000);
    check('QC2 the ↻ confirm holds a reveal: no next question behind it', h.phase() === 'reveal' && quiz.at === at
      && h.byId.confirm.classList.contains('show'));
    await h.click('no');
    await h.advance(1499);
    const held = h.phase() === 'reveal';
    await h.advance(2);
    check('QC2 "no" picks the reveal up again: the next question 1.5 s later', held && h.phase() === 'ask' && quiz.at === at + 1);
    await h.advance(1000);
    at = quiz.at;
    await h.pick(quiz.answer);
    await h.advance(100);
    await h.setVisibility('hidden');
    await h.advance(20000);
    const hidden = h.phase() === 'reveal' && quiz.at === at;
    await h.setVisibility('visible');
    await h.advance(1499);
    const back = h.phase() === 'reveal';
    await h.advance(2);
    check('QC3 no advance while the page is hidden; back on screen, the next question 1.5 s later',
      hidden && back && h.phase() === 'ask' && quiz.at === at + 1);
  }

  const key = (h) => `${h.T.DATA.game}:learned`;
  const ids = (list) => list.map((p) => p.id);
  const subset = (a, b) => a.every((x) => b.includes(x));
  // The clips a step started (the fake Web Audio's log), from `from` on.
  const started = (h, from) => h.log.slice(from).filter((l) => l.startsWith('buffer-start')).map((l) => l.split(': ')[1].split(' ')[0]);
  const withClips = (extra = {}) => {
    const probe = boot({ clips: true });
    const served = new Set(['audio/ui/start.mp3', 'audio/ui/win.mp3']);
    Object.keys(probe.T.DATA.audio).filter((k) => k !== 'ui').forEach((kind) => probe.T.ITEMS.forEach((p) => served.add(`audio/${kind}/${p.id}.mp3`)));
    return boot({ clips: true, webAudio: true, served, ...extra });
  };

  // ---------- F1-F3 a squad's flash cards; its quiz stays the whole roster whatever she has learned ----------
  if (SQUAD) {
    const h = withClips();
    const { ITEMS, shelf, learned } = h.T;
    await h.click('play-cards');
    check('F1 flash cards: the shelf holds every player, none learned yet', h.phase() === 'browse'
      && h.byId.shelf.children.length === ITEMS.length && h.byId.shelf.children.every((t) => t.dataset.learned === 'false'));
    let from = h.log.length;
    await h.tile(5);
    await h.advance(3000);
    check("F1 a tile opens that player's card, turned up; once its line has played it counts as learned and its tile is ticked",
      h.phase() === 'card' && shelf.card.p === ITEMS[5] && shelf.card.el.dataset.state === 'up' && learned.has(ITEMS[5].id)
      && h.byId.shelf.children[5].dataset.learned === 'true' && h.byId['shelf-count'].textContent === `1 / ${ITEMS.length}`);
    check("F1 the card says the player's match clip (PLAY.voice.card)",
      JSON.stringify(started(h, from)) === JSON.stringify([`audio/match/${ITEMS[5].id}.mp3`]), JSON.stringify(started(h, from)));
    await h.click('close');
    check('F1 ✗ goes back to the shelf', h.phase() === 'browse' && !h.byId.flash.classList.contains('show'));
    await h.click('next-new');
    check('F1 the next-new button opens the first player not learned yet', h.phase() === 'card' && shelf.card.p === ITEMS[0]);
    await h.click('next');
    const next = shelf.card.p;
    await h.click('prev');
    await h.click('prev');
    check('F1 ← and → page through the shelf in order and wrap around', next === ITEMS[1] && shelf.card.p === ITEMS[ITEMS.length - 1]);
    const saved = JSON.parse(h.store.get(key(h)));
    check('F2 what she learned is stored under the game\'s own key; a card paged past at once is not learned',
      subset([ITEMS[5].id], saved) && !saved.includes(ITEMS[0].id) && !saved.includes(ITEMS[1].id), JSON.stringify(saved));

    const k = boot({ noClips: true, storage: [[key(h), JSON.stringify(ids(ITEMS.slice(0, 3)))]] });
    await k.click('play-quiz');
    check('F3 the squad quiz asks the whole roster, learned or not', k.phase() === 'ask' && k.T.game.total === k.T.ITEMS.length
      && k.T.quiz.order.length === k.T.ITEMS.length && new Set(ids(k.T.quiz.order)).size === k.T.ITEMS.length);
    const starters = ids(k.T.ITEMS.filter((p) => p.role === 'starter'));
    let squadDeals = 0;
    for (let i = 0; i < 50; i++) { const picks = k.T.dealPicks(); squadDeals += picks.length === 15 && subset(starters, ids(picks)); }
    check('F3 memory still deals the 11 starters and 4 of the bench, learned or not', squadDeals === 50, `${squadDeals}/50`);
  }

  // ---------- W1-W6 a word game: new-first deals, the learned-only quiz, flash cards, the bar ----------
  if (!SQUAD) {
    const h = boot({ noClips: true });
    const { ITEMS, PLAY } = h.T;
    const N = ITEMS.length;
    const learnedOf = (list) => [[`${h.T.DATA.game}:learned`, JSON.stringify(ids(list))]];
    const first15 = ids(ITEMS.slice(0, 15));
    check('W1 nothing learned: memory deals the first 15 words in teaching order', JSON.stringify(ids(h.T.dealPicks())) === JSON.stringify(first15));
    {
      const k = boot({ noClips: true, storage: learnedOf(ITEMS.slice(0, 20)) });
      let ok = 0;
      for (let i = 0; i < 30; i++) {
        const picks = ids(k.T.dealPicks());
        ok += picks.length === 15 && JSON.stringify(picks.slice(0, PLAY.deal.new)) === JSON.stringify(ids(ITEMS.slice(20, 20 + PLAY.deal.new)))
          && subset(picks.slice(PLAY.deal.new), ids(ITEMS.slice(0, 20))) && new Set(picks).size === 15;
      }
      check(`W1 20 learned: the next ${PLAY.deal.new} new words in order, then ${15 - PLAY.deal.new} learned ones for review`, ok === 30, `${ok}/30`);
    }
    {
      const k = boot({ noClips: true, storage: learnedOf(ITEMS.slice(0, 3)) });
      const picks = ids(k.T.dealPicks());
      check('W1 3 learned: those 3 for review and 12 new words in order', picks.length === 15
        && JSON.stringify(picks.slice(0, 12)) === JSON.stringify(ids(ITEMS.slice(3, 15))) && subset(picks.slice(12), ids(ITEMS.slice(0, 3))));
    }
    {
      const k = boot({ noClips: true, storage: learnedOf(ITEMS) });
      const picks = ids(k.T.dealPicks());
      check('W1 everything learned: 15 different learned words', picks.length === 15 && new Set(picks).size === 15);
    }

    // W2 the quiz: locked below PLAY.quiz.unlock, then only learned words, at most PLAY.quiz.size
    {
      const k = boot({ noClips: true, storage: learnedOf(ITEMS.slice(0, PLAY.quiz.unlock - 1)) });
      await k.click('play-quiz');
      check(`W2 ${PLAY.quiz.unlock - 1} learned: the quiz is locked, a tap only points at the other two`, k.phase() === 'start'
        && k.byId['play-quiz'].dataset.locked === 'true' && k.document.body.classList.contains('hint'));
    }
    for (const n of [PLAY.quiz.unlock + 1, 20]) {
      const pool = ids(ITEMS.slice(5, 5 + n));
      const k = boot({ noClips: true, storage: learnedOf(ITEMS.slice(5, 5 + n)) });
      await k.click('play-quiz');
      const { quiz, game } = k.T;
      let cardsOk = true;
      const asked = [];
      for (let i = 0; i < 40 && k.phase() === 'ask'; i++) {
        asked.push(quiz.answer.p.id);
        cardsOk = cardsOk && quiz.cards.length === 4 && subset(ids(quiz.cards.map((c) => c.p)), pool);
        await k.advance(500);
        await k.pick(quiz.answer);
        await k.advance(800);
        if (k.phase() === 'reveal') await k.pick(quiz.cards[0]);
        await k.advance(50);
      }
      const size = Math.min(n, PLAY.quiz.size);
      check(`W2 ${n} learned: ${size} questions, each a learned word once, its four cards all learned words`,
        game.total === size && asked.length === size && new Set(asked).size === size && subset(asked, pool) && cardsOk, `${asked.length} asked`);
    }

    // W3 the voice script: flip en; match en then he; the question en alone; a wrong or right pick en then he
    {
      const k = withClips();
      await k.click('play');
      await k.advance(700);
      const a = k.firstDown();
      let from = k.log.length;
      await k.down(a);
      await k.advance(100);
      const flip = started(k, from);
      from = k.log.length;
      await k.down(k.pairOf(a));
      await k.advance(4000);
      const match = started(k, from);
      const clips = (p, kinds) => kinds.map((kind) => `audio/${kind}/${p.id}.mp3`);
      check('W3 memory: a flip says the English word, a match the English then the Hebrew',
        JSON.stringify(flip) === JSON.stringify(clips(a.p, ['en'])) && JSON.stringify(match) === JSON.stringify(clips(a.p, ['en', 'he'])),
        JSON.stringify({ flip, match }));
    }
    {
      const k = withClips({ storage: learnedOf(ITEMS.slice(0, 6)) });
      let from = k.log.length;
      await k.click('play-quiz');
      await k.advance(3000);
      const { quiz } = k.T;
      const ask = started(k, from).filter((u) => !u.includes('/ui/'));
      const wrong = quiz.cards.find((c) => c !== quiz.answer);
      await k.advance(500);
      from = k.log.length;
      await k.pick(wrong);
      await k.advance(3000);
      const said = started(k, from);
      from = k.log.length;
      await k.pick(quiz.answer);
      await k.advance(3000);
      const right = started(k, from);
      const clips = (p, kinds) => kinds.map((kind) => `audio/${kind}/${p.id}.mp3`);
      check('W3 quiz: the question is the English word alone, in text and out loud',
        JSON.stringify(ask) === JSON.stringify(clips(quiz.answer.p, ['en'])) && k.byId.question.textContent === quiz.answer.p.en, JSON.stringify(ask));
      check('W3 quiz: a wrong pick says that word in English then Hebrew, a right pick the answer\'s',
        JSON.stringify(said) === JSON.stringify(clips(wrong.p, ['en', 'he'])) && JSON.stringify(right) === JSON.stringify(clips(quiz.answer.p, ['en', 'he'])),
        JSON.stringify({ said, right }));
    }

    // W4 a flash card counts as learned and moves the bar; W5 it is still learned after a reload
    {
      const k = withClips();
      check('W4 the bar starts at "0 / N"', k.byId['progress-count'].textContent === `0 / ${N}`);
      await k.click('play-cards');
      const from = k.log.length;
      await k.click('next-new');
      await k.advance(4000);
      check('W4 the next-new button opens the first word; its card says English then Hebrew',
        k.T.shelf.card.p.id === ITEMS[0].id && JSON.stringify(started(k, from)) === JSON.stringify([`audio/en/${ITEMS[0].id}.mp3`, `audio/he/${ITEMS[0].id}.mp3`]),
        JSON.stringify(started(k, from)));
      check('W4 seeing it counts as learned: its tile is ticked and the bar says "1 / N"', k.T.learned.has(ITEMS[0].id)
        && k.byId.shelf.children[0].dataset.learned === 'true' && k.byId['progress-count'].textContent === `1 / ${N}`
        && Number(k.byId.progress.style.props['--done']) === 1 / N);
      await k.click('close');
      await k.click('next-new');
      check('W4 then the next-new button opens the second word', k.T.shelf.card.p.id === ITEMS[1].id);
      await k.advance(4000);
      await k.click('next');
      await k.advance(300);
      const paged = !k.T.learned.has(ITEMS[2].id);
      await k.click('next');
      await k.advance(4000);
      check('W4 a card paged past before its line ends is not learned; one left to speak is', paged
        && !k.T.learned.has(ITEMS[2].id) && k.T.learned.has(ITEMS[3].id));
      const again = boot({ noClips: true, storage: [...k.store] });
      check('W5 after a reload they are still learned, and the bar says "3 / N"', again.T.learned.has(ITEMS[0].id)
        && again.T.learned.has(ITEMS[1].id) && again.T.learned.has(ITEMS[3].id) && again.byId['progress-count'].textContent === `3 / ${N}`);
    }
    {
      const k = boot({ noClips: true });
      await k.click('play');
      await k.advance(700);
      const a = k.firstDown();
      await k.down(a);
      await k.down(k.pairOf(a));
      const again = boot({ noClips: true, storage: [...k.store] });
      check('W5 a match in memory is learned, and still is after a reload', again.T.learned.has(a.p.id)
        && again.byId['progress-count'].textContent === `1 / ${N}`);
      k.g.localStorage.setItem = () => { throw new Error('QuotaExceededError'); };
      const b = k.firstDown();
      await k.down(b);
      await k.down(k.pairOf(b));
      check('W6 storage that refuses a write keeps the game going, learned for this visit', k.T.learned.has(b.p.id)
        && k.byId['progress-count'].textContent === `2 / ${N}`);
    }
    // W8 two pictures that look alike (PLAY.quiz.apart) are never offered against each other
    for (const [a, b] of PLAY.quiz.apart || []) {
      const others = ITEMS.filter((p) => p.id !== a && p.id !== b).slice(0, 3);
      const k = boot({ noClips: true, storage: learnedOf(ITEMS.filter((p) => p.id === a || p.id === b).concat(others)) });
      let together = 0;
      let asked = 0;
      for (let round = 0; round < 12; round++) {
        await k.click('yes-quiz');
        for (let i = 0; i < 6 && k.phase() === 'ask'; i++) {
          const cards = k.T.quiz.cards.map((c) => c.p.id);
          if ([a, b].includes(k.T.quiz.answer.p.id)) { asked += 1; together += cards.includes(a) && cards.includes(b); }
          await k.advance(500);
          await k.pick(k.T.quiz.answer);
          await k.advance(800);
          if (k.phase() === 'reveal') await k.pick(k.T.quiz.cards[0]);
          await k.advance(50);
        }
      }
      check(`W8 "${a}" and "${b}" never share a question, and it still has four cards`, asked > 0 && together === 0
        && k.T.quiz.cards.length === 4, `${asked} questions asked ${a} or ${b}`);
    }
    // W7 the win in the game's own words (club.json lines), when it has them
    if (h.T.DATA.lines && h.T.DATA.lines.win) {
      const k = boot({ noClips: true });
      await start(k);
      const last = await playToLastPair(k);
      await k.advance(4000);
      k.synth.spoken.length = 0;
      await k.down(last[0]);
      await k.down(last[1]);
      for (let i = 0; i < 300 && k.phase() !== 'won'; i++) await k.advance(50);
      check('W7 the win says the game\'s own line', k.phase() === 'won' && k.synth.spoken.some((s) => s.text === k.T.DATA.lines.win),
        JSON.stringify(k.synth.spoken.map((s) => s.text)));
    }
  }

  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} pass, ${failed} fail`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error('HARNESS ERROR', e); process.exit(1); });
