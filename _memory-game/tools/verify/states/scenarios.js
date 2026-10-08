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
  // ---------- S1 boot + deal ----------
  {
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
  {
    const served = new Set();
    const tmp = boot({ clips: true, webAudio: true });
    const all = tmp.T.DATA.starters.concat(tmp.T.DATA.bench).map((p) => p.id);
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
  {
    const h = boot();
    await start(h);
    const benchIds = h.T.DATA.bench.map((p) => p.id);
    const starterIds = h.T.DATA.starters.map((p) => p.id);
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
  {
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

  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} pass, ${failed} fail`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error('HARNESS ERROR', e); process.exit(1); });
