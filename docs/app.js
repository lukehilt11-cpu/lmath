/* lmath website — loads the real Python engine in the browser with Pyodide. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const out = $('#out'), line = $('#line'), form = $('#form'), statusEl = $('#status');

  // ── links back to the GitHub repo (derived from the Pages address, so nothing is hard-coded) ──
  const host = location.hostname, seg = location.pathname.split('/').filter(Boolean);
  const repoUrl = host.endsWith('.github.io') ? `https://github.com/${host.split('.')[0]}/${seg[0] || host}` : null;
  document.querySelectorAll('[data-repo]').forEach((a) => { if (repoUrl) a.href = repoUrl; else a.style.display = 'none'; });
  document.querySelectorAll('[data-releases]').forEach((a) => { a.href = repoUrl ? repoUrl + '/releases/latest' : '#download'; });

  // ── theme toggle: auto → light → dark ──
  const root = document.documentElement;
  const saved = (() => { try { return localStorage.getItem('lmath-theme'); } catch (e) { return null; } })();
  if (saved) root.dataset.theme = saved;
  $('#theme').addEventListener('click', () => {
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
    try { localStorage.setItem('lmath-theme', root.dataset.theme); } catch (e) {}
    if (graphCtl) graphCtl.redraw();
  });

  // ── console ──
  const history = []; let hpos = 0, py = null, webapi = null, graphCtl = null, ready = false;
  const EXAMPLES = ['3/4 + 5/6', 'solve x^2-5x+6=0', 'factor 6x^2+11x-10', 'solve 2x^2+3x-1=0', 'plot x^2-4x+3', 'plot x^2+y^2=25',
    'inequality x^2-5x+6<0', 'deriv sin(x)*x^2', 'integ x^2 from 0 to 3', 'system 2x+3y=6 ; x-y=1', 'trig 135', 'identify 4x^2+9y^2-16x+18y-11=0'];

  function add(cls, text) {
    const pre = document.createElement('pre'); pre.className = cls; pre.textContent = text; out.appendChild(pre);
    out.scrollTop = out.scrollHeight; return pre;
  }
  function setStatus(t) { statusEl.textContent = t; }

  function showGraph(payload) {
    const pane = $('#graphpane'); pane.classList.add('has-graph');
    graphCtl = LmathGraph.mount($('#graph'), payload);
  }

  function run(text) {
    text = text.trim(); if (!text) return;
    if (!ready) { add('msg', 'Still loading — one moment…'); return; }
    history.push(text); hpos = history.length;
    add('cmd', 'lmath> ' + text);
    try {
      const res = JSON.parse(webapi.run(text));
      if (res.out && res.out.trim()) add('', res.out.replace(/\s+$/, ''));
      if (res.graph) showGraph(res.graph);
    } catch (e) {
      add('msg', 'Something went wrong running that. Check what you typed and try again.');
    }
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); const t = line.value; line.value = ''; run(t); });
  line.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowUp' && history.length) { hpos = Math.max(0, hpos - 1); line.value = history[hpos] || ''; e.preventDefault(); }
    if (e.key === 'ArrowDown') { hpos = Math.min(history.length, hpos + 1); line.value = history[hpos] || ''; e.preventDefault(); }
  });
  $('#clear').addEventListener('click', () => { out.innerHTML = ''; });

  function runVisible(text) {
    $('#try').scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (!ready) { line.value = text; return; }
    run(text);
  }
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-run]'); if (t) { e.preventDefault(); runVisible(t.dataset.run); }
  });

  // example chips
  const chipBox = $('#examples');
  EXAMPLES.forEach((ex) => {
    const b = document.createElement('button'); b.className = 'chip'; b.textContent = ex; b.dataset.run = ex; chipBox.appendChild(b);
  });

  // ── command cheat sheet (pre-built at publish time, so it shows instantly) ──
  fetch('assets/catalog.json').then((r) => r.json()).then((cat) => {
    $('#ver').textContent = 'v' + cat.version;
    const box = $('#catalog');
    cat.groups.forEach((g) => {
      const sec = document.createElement('div'); sec.className = 'group';
      sec.innerHTML = `<h3>${g.group}</h3>`;
      g.commands.forEach((c) => {
        const row = document.createElement('div'); row.className = 'cmd-row';
        row.dataset.text = (c.name + ' ' + c.usage + ' ' + c.summary + ' ' + g.group + ' ' + c.examples.join(' ')).toLowerCase();
        const use = document.createElement('div'); use.className = 'use'; use.textContent = c.usage;
        const what = document.createElement('div'); what.className = 'what'; what.textContent = c.summary;
        row.append(use, what);
        if (c.examples.length) {
          const ex = document.createElement('div'); ex.className = 'ex';
          c.examples.forEach((e) => { const b = document.createElement('button'); b.className = 'chip'; b.textContent = e; b.dataset.run = e; ex.appendChild(b); });
          row.appendChild(ex);
        }
        sec.appendChild(row);
      });
      box.appendChild(sec);
    });
    $('#filter').addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      box.querySelectorAll('.cmd-row').forEach((r) => { r.style.display = !q || r.dataset.text.includes(q) ? '' : 'none'; });
      box.querySelectorAll('.group').forEach((g) => { g.style.display = [...g.querySelectorAll('.cmd-row')].some((r) => r.style.display !== 'none') ? '' : 'none'; });
    });
  }).catch(() => { $('#catalog').textContent = 'The command list could not be loaded.'; });

  // ── start the Python engine ──
  async function boot() {
    try {
      if (typeof loadPyodide !== 'function') throw new Error('offline');
      setStatus('Loading Python…'); py = await loadPyodide();
      setStatus('Loading SymPy…'); await py.loadPackage('sympy');
      setStatus('Loading lmath…');
      const buf = await (await fetch('assets/lmath-pkg.zip', { cache: 'no-cache' })).arrayBuffer();
      py.unpackArchive(buf, 'zip');
      py.runPython("import sys\nif '/home/pyodide' not in sys.path: sys.path.insert(0, '/home/pyodide')");
      webapi = py.pyimport('lmath.webapi');
      ready = true; line.disabled = false; form.querySelector('.go').disabled = false;
      setStatus('lmath ' + webapi.version() + ' · ready'); line.focus({ preventScroll: true });
      const q = new URLSearchParams(location.search).get('q');
      if (q) { line.value = ''; run(q); }
      else { run('solve x^2-5x+6=0'); run('plot x^2-4x+3'); if (line.value) { const t = line.value; line.value = ''; run(t); } }
    } catch (e) {
      setStatus('Browser preview unavailable');
      add('msg', 'The in-browser engine needs an internet connection to load Python.\nYou can still browse the commands below, or download the app to use lmath offline.');
    }
  }
  boot();
})();
