// Smoke test for the website: loads docs/index.html + app.js in jsdom with a fake Pyodide.
// Run:  npm install --no-save jsdom   then   node tests/site.dom.test.js
const assert = require('assert');
const fs = require('fs');
const path = require('path');
let JSDOM;
try { ({ JSDOM } = require('jsdom')); } catch (e) { console.log('  skip  jsdom not installed'); process.exit(0); }

const docs = path.join(__dirname, '..', 'docs');
const html = fs.readFileSync(path.join(docs, 'index.html'), 'utf8').replace(/<script[^>]*src=[^>]*><\/script>/g, '');
const dom = new JSDOM(html, { url: 'https://someone.github.io/lmath/', runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
w.matchMedia = () => ({ matches: false });
const ran = [];
w.loadPyodide = async () => ({
  loadPackage: async () => {}, unpackArchive: () => {}, runPython: () => {},
  pyimport: () => ({ version: () => '4.0.0', run: (l) => { ran.push(l); return JSON.stringify({ out: 'ANSWER for ' + l, graph: l.startsWith('plot') ? { title: 't', series: [{ type: 'fn', js: 'x', label: 'y = x' }], points: [] } : null }); } }),
});
w.fetch = async (u) => {
  const p = path.join(docs, u.split('?')[0]);
  const buf = fs.readFileSync(p);
  return { json: async () => JSON.parse(buf.toString('utf8')), arrayBuffer: async () => buf.buffer };
};
w.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, k) => (k === 'measureText' ? () => ({ width: 10 }) : () => {}), set: () => true });
Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', { get: () => 600 });
w.HTMLElement.prototype.scrollIntoView = () => {};
w.eval(fs.readFileSync(path.join(docs, 'assets', 'grapher.js'), 'utf8'));
w.eval(fs.readFileSync(path.join(docs, 'app.js'), 'utf8'));

(async () => {
  await new Promise((r) => setTimeout(r, 300));
  const d = w.document;
  assert.ok(d.querySelectorAll('#examples .chip').length >= 8, 'example chips');
  assert.ok(d.querySelectorAll('#catalog .cmd-row').length > 80, 'cheat sheet rendered');
  assert.strictEqual(d.querySelector('#line').disabled, false, 'input enabled once ready');
  assert.ok(d.querySelector('#status').textContent.includes('ready'), 'status says ready');
  assert.deepStrictEqual(ran.slice(0, 2), ['solve x^2-5x+6=0', 'plot x^2-4x+3'], 'demo runs on load');
  assert.ok(d.querySelector('#graphpane').classList.contains('has-graph'), 'graph shown');
  assert.strictEqual(d.querySelector('a.gh').href, 'https://github.com/someone/lmath', 'repo link derived from Pages URL');
  d.querySelector('#line').value = '3/4+5/6'; d.querySelector('#form').dispatchEvent(new w.Event('submit', { cancelable: true }));
  assert.ok(d.querySelector('#out').textContent.includes('ANSWER for 3/4+5/6'), 'typed command runs');
  d.querySelector('#filter').value = 'factor'; d.querySelector('#filter').dispatchEvent(new w.Event('input'));
  const visible = [...d.querySelectorAll('#catalog .cmd-row')].filter((r) => r.style.display !== 'none').length;
  assert.ok(visible > 0 && visible < 20, 'search filters the commands (' + visible + ' match)');
  console.log('  ok  website boots, renders the cheat sheet, runs commands and shows graphs');
})().catch((e) => { console.error(e); process.exit(1); });
