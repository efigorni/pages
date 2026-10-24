// What drive.js and sw_check.js expect a game to say: the clips a moment of its voice script says for an
// item (DATA.play.voice; an older tree has none and says a squad's), and how many words a word game starts
// with learned, so its quiz is open and its deal reaches past the words the worker precaches.
const SQUAD_VOICE = { flip: ['name'], match: ['name', 'match'], ask: ['match'], wrong: ['match'], right: ['name'], card: ['match'] };
const clipsOf = (voice, id, moment) => (voice || SQUAD_VOICE)[moment].map((kind) => `audio/${kind}/${id}.mp3`);
const LEARNED_START = 25;
// The ids the page plays, in teaching order, as a page.evaluate expression: a word game with levels
// (DATA.play.levels) plays the words up to the level kept in `<game>:level` (engine.js savedLevel), every
// other game, or no level kept, every item. The seeds, the bar and the offline cache are counted on it.
const POOL = `(() => {
  const all = DATA.words || DATA.players || [];
  const levels = DATA.play && DATA.play.levels;
  let raw = null;
  try { raw = localStorage.getItem(DATA.game + ':level'); } catch (e) {}
  const n = levels && /^[1-9]\\d*$/.test(raw || '') && Number(raw) <= levels.names.length ? Number(raw) : 0;
  return all.filter((p) => !n || p.level <= n).map((p) => p.id);
})()`;

module.exports = { clipsOf, LEARNED_START, POOL };
