/* Mode lifecycle tests; actual layout and pointer controls are checked in the browser. */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const source = readFileSync(join(__dirname, '../assets/deck.js'), 'utf8');

function harness({ phone = false, search = '', hash = '', deferred = false } = {}) {
  const listeners = {}, frames = [], instances = [], classes = new Set(), writes = [];
  const location = { search, hash };
  let scroll = 0, decorations = 0, resolveInit;
  const sections = Array.from({ length: 8 }, (_, i) => ({
    getBoundingClientRect: () => ({ top: i * 600 - scroll }),
    scrollIntoView: () => { scroll = i * 600; },
    querySelector: () => null,
  }));
  const media = {
    matches: phone,
    addEventListener: (_, listener) => { media.change = listener; },
  };
  class Reveal {
    constructor() { this.index = Number(location.hash.split('/')[1]) || 0; instances.push(this); }
    initialize(config) {
      this.config = config;
      return deferred ? new Promise(resolve => { resolveInit = resolve; }) : Promise.resolve();
    }
    getCurrentSlide() { return sections[this.index]; }
    getIndices() { return { h: this.index }; }
    slide(index) { this.index = index; }
    destroy() { this.destroyed = true; }
  }
  const context = {
    URLSearchParams, location, innerHeight: 900,
    history: { replaceState: (_, __, hash) => { location.hash = hash; writes.push(hash); } },
    requestAnimationFrame: callback => { frames.push(callback); return frames.length; },
    document: {
      querySelectorAll: () => sections, querySelector: () => ({ removeAttribute() {} }),
      documentElement: { classList: { add: value => classes.add(value), remove: value => classes.delete(value) } },
    },
    Reveal, matchMedia: () => media,
    LessonTheme: { decorate: () => { decorations++; } },
    addEventListener: (name, listener) => { listeners[name] = listener; },
    scrollTo: (_, y) => { scroll = y; },
  };
  context.window = context;
  vm.runInNewContext(source, context);
  return {
    instances, sections, classes, location, writes,
    get scroll() { return scroll; }, get decorations() { return decorations; },
    resize(phone) { media.matches = phone; if (media.change) media.change(); },
    hash(hash) { location.hash = hash; listeners.hashchange(); },
    scrollToSlide(index) { scroll = index * 600; listeners.scroll(); },
    reflow() { sections.forEach(section => { section.getBoundingClientRect = () => ({ top: -1 }); }); },
    flush() { frames.splice(0).forEach(callback => callback()); },
    resolve() { resolveInit(); },
  };
}

test('phone starts in readable flow at a direct slide/fragment link without initializing Reveal', () => {
  const h = harness({ phone: true, hash: '#/5/0/2' });
  assert.ok(h.classes.has('lesson-reading'));
  assert.equal(h.instances.length, 0);
  assert.equal(h.scroll, 3000);
  assert.equal(h.decorations, 1);
  assert.equal(h.location.hash, '#/5/0/2');
  h.hash('#/2');
  assert.equal(h.scroll, 1200);
  h.hash('#/999');
  assert.equal(h.scroll, 4200);
});

test('phone scrolling replaces the current hash only when the visible slide changes', () => {
  const h = harness({ phone: true, hash: '#/2/0/1' });
  h.scrollToSlide(2); h.flush();
  assert.deepEqual(h.writes, []);
  h.scrollToSlide(4); h.flush();
  h.scrollToSlide(4); h.flush();
  assert.deepEqual(h.writes, ['#/4']);
});

test('desktop retains RTL presentation settings and disables competing auto-scroll mode', async () => {
  const h = harness();
  await Promise.resolve();
  const { config } = h.instances[0];
  assert.equal(config.rtl, true);
  assert.equal(config.width, 1440);
  assert.equal(config.height, 810);
  assert.equal(config.controls, true);
  assert.equal(config.hash, true);
  assert.equal(config.scrollActivationWidth, null);
  assert.equal(h.decorations, 1);
  assert.equal(h.classes.has('lesson-reading'), false);
});

for (const search of ['?thumb=1&slide=3', '?print-pdf']) {
  test(`${search} never enters reading mode, including resize`, async () => {
    const h = harness({ phone: true, search });
    await Promise.resolve();
    h.resize(false); h.resize(true);
    assert.equal(h.classes.has('lesson-reading'), false);
    assert.equal(h.instances.length, 1);
    const d = h.instances[0];
    assert.equal(d.config.margin, 0);
    assert.equal(d.config.pdfSeparateFragments, false);
    if (search.includes('thumb')) {
      assert.equal(d.index, 3);
      assert.equal(d.config.hash, false);
      assert.equal(d.config.controls, false);
    }
  });
}

test('breakpoint round trip retains original nodes and current slide, without duplicate initialization', async () => {
  const h = harness({ phone: true, hash: '#/1' });
  const original = h.sections.slice();
  h.scrollToSlide(4); h.flush();
  h.resize(false);
  await Promise.resolve();
  assert.equal(h.instances.length, 1);
  assert.equal(h.instances[0].index, 4);
  h.instances[0].index = 6;
  h.resize(true);
  assert.equal(h.instances[0].destroyed, true);
  assert.equal(h.scroll, 3600);
  assert.equal(h.location.hash, '#/6');
  h.resize(true);
  h.resize(false);
  await Promise.resolve();
  assert.equal(h.instances.length, 2);
  assert.equal(h.instances[1].index, 6);
  assert.deepEqual(h.sections, original);
});

test('resize during asynchronous Reveal initialization waits for ready before destruction', async () => {
  const h = harness({ deferred: true, hash: '#/3' });
  h.resize(true);
  assert.equal(h.instances[0].destroyed, undefined);
  h.resolve();
  await Promise.resolve();
  assert.equal(h.instances[0].destroyed, true);
  assert.ok(h.classes.has('lesson-reading'));
  assert.equal(h.scroll, 1800);
});

test('leaving reading uses the tracked slide rather than geometry after viewport reflow', async () => {
  const h = harness({ phone: true, hash: '#/2' });
  h.scrollToSlide(4); h.flush();
  h.reflow();
  h.resize(false);
  await Promise.resolve();
  assert.equal(h.instances[0].index, 4);
});

test('rapid resize returning to desktop during initialization keeps the existing deck', async () => {
  const h = harness({ deferred: true });
  h.resize(true); h.resize(false);
  h.resolve();
  await Promise.resolve();
  assert.equal(h.instances.length, 1);
  assert.equal(h.instances[0].destroyed, undefined);
  assert.equal(h.classes.has('lesson-reading'), false);
});

test('published assets match the canonical source', () => {
  for (const name of ['deck.js', 'slides.css']) {
    assert.equal(readFileSync(join(__dirname, '../assets', name), 'utf8'),
      readFileSync(join(__dirname, '../../../../lesson-lab/lessons/_assets', name), 'utf8'));
  }
});
