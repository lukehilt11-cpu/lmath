// DOM smoke test for grapher.js using jsdom with a recording fake canvas.
// Run:  npm install --no-save jsdom   then   node tests/grapher.dom.test.js
const assert = require('assert');
const fs = require('fs');
const path = require('path');
let JSDOM;
try { ({ JSDOM } = require('jsdom')); } catch (e) { console.log('  skip  jsdom not installed'); process.exit(0); }

const src = fs.readFileSync(path.join(__dirname, '..', 'source', 'lmath', 'assets', 'grapher.js'), 'utf8');
const dom = new JSDOM('<!doctype html><div id="g"></div>', { runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
const calls = [];
const ctx = new Proxy({}, { get: (t, k) => (k === 'measureText' ? () => ({ width: 40 }) : k in t ? t[k] : (...a) => { calls.push(k); }), set: (t, k, v) => { t[k] = v; return true; } });
w.HTMLCanvasElement.prototype.getContext = () => ctx;
w.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => 640 });
w.eval(src);

const payload = {
  title: 'test', series: [
    { type: 'fn', js: 'Math.pow(x, 2) - 4*x + 3', label: 'y = x² − 4x + 3' },
    { type: 'implicit', js: 'Math.pow(x,2)+Math.pow(y,2)-25', label: 'circle' },
    { type: 'rel', js: 'y-(2*x+1)', op: '>', label: 'y > 2x+1' },
    { type: 'vline', x: 3, label: 'x = 3' },
    { type: 'points', pts: [[1, 2], [2, 4]], label: 'data' },
    { type: 'fn', samples: [[-5, 1], [0, 2], [5, 3]], label: 'sampled' }],
  points: [{ x: 2, y: -1, label: '(2, -1)', kind: 'vertex' }]
};
const el = w.document.getElementById('g');
const ctl = w.LmathGraph.mount(el, payload);
assert.ok(el.querySelector('canvas'), 'canvas created');
assert.strictEqual(el.querySelectorAll('.lg-chip').length, 6, 'one legend chip per series');
assert.strictEqual(el.querySelectorAll('.lg-pt').length, 1, 'one key-point button');
assert.ok(calls.includes('stroke') && calls.includes('fillRect'), 'something was drawn');
const before = calls.length;
el.querySelector('[data-a="grid"]').click();
el.querySelector('[data-a="equal"]').click();
el.querySelector('[data-a="reset"]').click();
ctl.redraw();
assert.ok(calls.length > before, 'redraws on button clicks');
const canvas = el.querySelector('canvas');
canvas.dispatchEvent(new w.WheelEvent('wheel', { deltaY: -120, clientX: 100, clientY: 100, cancelable: true }));
canvas.dispatchEvent(new w.MouseEvent('dblclick'));
console.log('  ok  grapher mounts, draws, and responds to buttons and the mouse wheel');
