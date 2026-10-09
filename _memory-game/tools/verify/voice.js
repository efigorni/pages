// What drive.js and sw_check.js expect a game to say: the clips a moment of its voice script says for an
// item (DATA.play.voice; an older tree has none and says a squad's), and how many words a word game starts
// with learned, so its quiz is open and its deal reaches past the words the worker precaches.
const SQUAD_VOICE = { flip: ['name'], match: ['name', 'match'], ask: ['match'], wrong: ['match'], right: ['name'], card: ['match'] };
const clipsOf = (voice, id, moment) => (voice || SQUAD_VOICE)[moment].map((kind) => `audio/${kind}/${id}.mp3`);
const LEARNED_START = 25;

module.exports = { clipsOf, LEARNED_START };
