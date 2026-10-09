// Test-only init script: logs fetches, decodes, buffer sources, HTMLAudio, speech, fullscreen, wake
// lock, SW registration and flyer geometry into window.__log; Web Audio output goes through a 0.0001
// gain so the run is silent with unchanged timing. URLs are logged relative to the page's directory
// (audio/name/<id>.mp3), whatever the game and the path it is served under.
(() => {
  if (window.__log) return;
  const log = [];
  window.__log = log;
  const push = (type, data) => { log.push(Object.assign({ t: Math.round(performance.now()), type }, data || {})); };
  window.__push = push;
  const short = (u) => {
    try {
      const x = new URL(u, location.href);
      const dir = new URL('.', location.href);
      return x.origin === dir.origin && x.pathname.startsWith(dir.pathname) ? x.pathname.slice(dir.pathname.length) : x.href;
    } catch (e) { return String(u); }
  };
  window.addEventListener('error', (e) => push('error', { msg: String(e.message || (e.target && (e.target.src || e.target.href)) || e), src: e.filename || '' }), true);
  window.addEventListener('unhandledrejection', (e) => push('rejection', { msg: String(e.reason) }));
  const bufUrl = new WeakMap();
  const audioUrl = new WeakMap();
  const realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = short(typeof input === 'string' ? input : input.url);
    return realFetch(input, init).then((res) => {
      push('fetch', { url, status: res.status });
      const ab = res.arrayBuffer.bind(res);
      res.arrayBuffer = () => ab().then((buf) => { bufUrl.set(buf, url); return buf; });
      return res;
    }, (err) => { push('fetch-fail', { url, msg: String(err) }); throw err; });
  };
  const BAC = window.BaseAudioContext || window.AudioContext;
  const destDesc = Object.getOwnPropertyDescriptor(BAC.prototype, 'destination');
  Object.defineProperty(BAC.prototype, 'destination', {
    configurable: true,
    get() {
      const real = destDesc.get.call(this);
      if (!this.__quiet) { const g = this.createGain(); g.gain.value = 0.0001; g.connect(real); this.__quiet = g; }
      return this.__quiet;
    },
  });
  const RealAC = window.AudioContext;
  const WrappedAC = function (...a) {
    const c = new RealAC(...a);
    window.__ctx = c;
    push('ctx-new', { state: c.state });
    c.addEventListener('statechange', () => push('ctx-state', { state: c.state }));
    return c;
  };
  WrappedAC.prototype = RealAC.prototype;
  window.AudioContext = WrappedAC;
  const realDecode = BAC.prototype.decodeAudioData;
  BAC.prototype.decodeAudioData = function (buf, ok, err) {
    const url = bufUrl.get(buf) || '?';
    push('decode', { url });
    const okW = ok && ((b) => { audioUrl.set(b, url); ok(b); });
    const p = realDecode.call(this, buf, okW, err);
    if (p && p.then) p.then((b) => audioUrl.set(b, url), () => {});
    return p;
  };
  const ABSN = AudioBufferSourceNode.prototype;
  const realStart = ABSN.start;
  const realStop = ABSN.stop;
  ABSN.start = function (...a) {
    const url = this.buffer ? (audioUrl.get(this.buffer) || (this.buffer.length <= 1 ? 'blip' : '?')) : 'nobuf';
    this.__url = url;
    if (url !== 'blip') {
      push('buf-start', { url, dur: this.buffer ? Math.round(this.buffer.duration * 1000) : 0, ctx: this.context.state });
      this.addEventListener('ended', () => push('buf-end', { url, cut: !!this.__stopped }));
    }
    return realStart.apply(this, a);
  };
  ABSN.stop = function (...a) {
    if (this.__url && this.__url !== 'blip') { this.__stopped = true; push('buf-stop', { url: this.__url }); }
    return realStop.apply(this, a);
  };
  const OSC = OscillatorNode.prototype;
  const realOscStart = OSC.start;
  OSC.start = function (...a) { push('osc', { f: Math.round(this.frequency.value) }); return realOscStart.apply(this, a); };
  const HME = HTMLMediaElement.prototype;
  const realPlay = HME.play;
  HME.play = function () {
    this.volume = 0.0001;
    const url = short(this.currentSrc || this.src);
    push('html-play', { url });
    if (!this.__hooked) {
      this.__hooked = true;
      this.addEventListener('ended', () => push('html-end', { url: short(this.currentSrc || this.src) }));
      this.addEventListener('pause', () => push('html-pause', { url: short(this.currentSrc || this.src) }));
      this.addEventListener('error', () => push('html-error', { url: short(this.currentSrc || this.src) }));
    }
    return realPlay.apply(this, arguments);
  };
  if (window.speechSynthesis) {
    const realSpeak = window.speechSynthesis.speak.bind(window.speechSynthesis);
    window.speechSynthesis.speak = (u) => { push('speech', { text: u.text }); u.volume = 0; return realSpeak(u); };
  }
  Element.prototype.requestFullscreen = function () { push('fullscreen-request'); return Promise.resolve(); };
  if (navigator.wakeLock) {
    const realReq = navigator.wakeLock.request.bind(navigator.wakeLock);
    navigator.wakeLock.request = (type) => realReq(type).then((lock) => {
      push('wake-granted');
      lock.addEventListener('release', () => push('wake-released'));
      return lock;
    }, (e) => { push('wake-denied', { msg: String(e) }); throw e; });
  }
  if (navigator.serviceWorker) {
    const realReg = navigator.serviceWorker.register.bind(navigator.serviceWorker);
    navigator.serviceWorker.register = (...a) => realReg(...a).then((r) => { push('sw-registered', { scope: r.scope }); return r; }, (e) => { push('sw-reg-fail', { msg: String(e) }); throw e; });
    navigator.serviceWorker.addEventListener('controllerchange', () => push('controllerchange'));
  }
  const realAnimate = Element.prototype.animate;
  Element.prototype.animate = function (frames, opts) {
    if (this.classList && this.classList.contains('flyer')) {
      push('flyer', { left: this.style.left, top: this.style.top, width: this.style.width, height: this.style.height,
        frames: frames.map((f) => f.transform) });
    }
    return realAnimate.call(this, frames, opts);
  };
  window.addEventListener('pagehide', () => push('pagehide'));
  window.addEventListener('beforeinstallprompt', () => push('beforeinstallprompt'));
})();
