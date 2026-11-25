// Tests for the pure parts of grapher.js. Run:  node tests/grapher.test.js
const assert = require('assert');
const path = require('path');
const G = require(path.join(__dirname, '..', 'source', 'lmath', 'assets', 'grapher.js'));

let n = 0;
function t(name, fn) { fn(); n++; console.log('  ok  ' + name); }

t('niceStep picks 1/2/5 × 10^k', () => {
  assert.strictEqual(G.niceStep(10, 5), 2);
  assert.strictEqual(G.niceStep(100, 10), 10);
  assert.strictEqual(G.niceStep(0.7, 7), 0.1);
});
t('ticks cover the range and include 0', () => {
  const k = G.ticks(-10, 10, 8);
  assert.ok(k.values.includes(0));
  assert.ok(k.values[0] >= -10 && k.values[k.values.length - 1] <= 10);
});
t('fmtTick avoids float noise', () => {
  assert.strictEqual(G.fmtTick(0.30000000000000004, 0.1), '0.3');
  assert.strictEqual(G.fmtTick(2, 1), '2');
  assert.strictEqual(G.fmtTick(-5, 5), '-5');
});
t('compile1 + sample', () => {
  const f = G.compile1('Math.pow(x, 2) - 4*x + 3');
  const s = G.sample(f, 0, 4, 4);
  assert.deepStrictEqual(s.map(p => p[1]), [3, 0, -1, 0, 3]);
});
t('runs break at NaN and at asymptote jumps', () => {
  const f = G.compile1('1/x');
  const r = G.runs(G.sample(f, -1, 1, 200), -10, 10);
  assert.strictEqual(r.length, 2);                       // left branch and right branch, no line across x=0
  const tanRuns = G.runs(G.sample(G.compile1('Math.tan(x)'), -6, 6, 600), -10, 10);
  assert.ok(tanRuns.length >= 4);
});
t('autoView: parabola near origin keeps honest 1:1 axes', () => {
  const f = G.compile1('x*x');
  const v = G.autoView({ series: [] }, [{ f }], 600 / 440);
  assert.strictEqual(v.equal, true);
  assert.strictEqual(v.xmin, -10);
});
t('autoView: tiny curve far from the window switches to fitted y', () => {
  const f = G.compile1('1000*x + 5000');
  const v = G.autoView({ series: [] }, [{ f }], 1.3);
  assert.strictEqual(v.equal, false);
  assert.ok(v.ymax - v.ymin > 100);
});
t('autoView honours an explicit window', () => {
  const v = G.autoView({ xmin: -2, xmax: 2, ymin: -1, ymax: 5 }, [], 1.3);
  assert.deepStrictEqual([v.xmin, v.xmax, v.ymin, v.ymax], [-2, 2, -1, 5]);
});
t('contour traces a circle', () => {
  const g = G.compile1.length ? new Function('x', 'y', 'return x*x + y*y - 25;') : null;
  const segs = G.contour(g, -10, 10, -10, 10, 80, 80);
  assert.ok(segs.length > 60);
  segs.forEach(s => {
    const r1 = Math.hypot(s[0], s[1]), r2 = Math.hypot(s[2], s[3]);
    assert.ok(Math.abs(r1 - 5) < 0.2 && Math.abs(r2 - 5) < 0.2);
  });
});
t('quantile', () => { assert.strictEqual(G.quantile([1, 2, 3, 4, 5], 0.5), 3); });

console.log(`\n${n} grapher tests passed`);
