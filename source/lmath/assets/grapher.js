/*
 * grapher.js — lmath's interactive graph. One file, no dependencies.
 *
 * Used in two places with identical behaviour:
 *   • the desktop app writes it into data/graph.html and opens it in the browser
 *   • the website preview loads it next to the Pyodide console
 *
 * LmathGraph.mount(element, payload)  →  controller
 *
 * payload = {
 *   title, xmin?, xmax?, ymin?, ymax?, equal?,
 *   series: [
 *     {type:'fn',       js:'Math.pow(x,2)', label:'y = x²', samples?:[[x,y],…]},
 *     {type:'implicit', js:'Math.pow(x,2)+Math.pow(y,2)-25', label:'x² + y² = 25'},
 *     {type:'rel',      js:'y-(2*x+1)', op:'>', label:'y > 2x + 1'},
 *     {type:'vline',    x: 3, label:'x = 3'},
 *     {type:'points',   pts:[[1,2],[2,4]], label:'data'}
 *   ],
 *   points: [{x, y, label, kind}]            // key points (intercepts, extrema, intersections)
 * }
 */
(function (root) {
  'use strict';

  var COLORS = ['#2f6fed', '#e5484d', '#1f9d55', '#f59e0b', '#8b5cf6', '#0891b2', '#db2777', '#64748b'];

  /* ───────────── pure helpers (unit-tested under node) ───────────── */

  function niceStep(range, target) {
    var raw = range / Math.max(1, target);
    var pow = Math.pow(10, Math.floor(Math.log10(raw)));
    var f = raw / pow;
    var nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10;
    return nice * pow;
  }

  function ticks(lo, hi, target) {
    var step = niceStep(hi - lo, target);
    var out = [];
    var start = Math.ceil(lo / step - 1e-9) * step;
    for (var v = start; v <= hi + step * 1e-9; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
    return { step: step, values: out };
  }

  function fmtTick(v, step) {
    if (v === 0) return '0';
    var a = Math.abs(v);
    if (a >= 1e6 || a < 1e-4) return v.toExponential(1).replace('e+', 'e');
    var digits = Math.max(0, -Math.floor(Math.log10(step)) + (step < 1 ? 0 : 0));
    var s = v.toFixed(Math.min(digits, 8));
    return s.indexOf('.') >= 0 ? s.replace(/\.?0+$/, '') : s;
  }

  function compile1(js) {
    try { return new Function('x', '"use strict"; return (' + js + ');'); } catch (e) { return null; }
  }
  function compile2(js) {
    try { return new Function('x', 'y', '"use strict"; return (' + js + ');'); } catch (e) { return null; }
  }

  function safe(f, x) {
    try { var y = f(x); return (typeof y === 'number' && isFinite(y)) ? y : NaN; } catch (e) { return NaN; }
  }

  function sample(f, xmin, xmax, n) {
    var out = [];
    for (var i = 0; i <= n; i++) {
      var x = xmin + (xmax - xmin) * i / n;
      out.push([x, safe(f, x)]);
    }
    return out;
  }

  /* Split a sampled curve into drawable runs: break at NaN and at asymptote-sized jumps. */
  function runs(samples, ymin, ymax) {
    var out = [], cur = [], prev = null, tall = (ymax - ymin) * 3;
    for (var i = 0; i < samples.length; i++) {
      var p = samples[i];
      if (!isFinite(p[1])) { if (cur.length) out.push(cur); cur = []; prev = null; continue; }
      if (prev !== null && Math.abs(p[1] - prev) > tall) { if (cur.length) out.push(cur); cur = []; }
      cur.push(p); prev = p[1];
    }
    if (cur.length) out.push(cur);
    return out;
  }

  function quantile(sorted, q) {
    if (!sorted.length) return 0;
    var i = (sorted.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
  }

  /* Choose a starting window. Honest 1:1 axes by default; fit y only if nothing shows. */
  function autoView(payload, fns, aspect) {
    var xmin = payload.xmin != null ? payload.xmin : -10;
    var xmax = payload.xmax != null ? payload.xmax : 10;
    var haveY = payload.ymin != null && payload.ymax != null;
    var ymin, ymax, equal = payload.equal !== false;
    if (haveY) { ymin = payload.ymin; ymax = payload.ymax; equal = payload.equal === true; }
    else {
      var half = (xmax - xmin) / 2 / aspect;
      var cy = 0;
      ymin = cy - half; ymax = cy + half;
      var ys = [];
      fns.forEach(function (s) {
        var pts = s.samples || sample(s.f, xmin, xmax, 300);
        pts.forEach(function (p) { if (isFinite(p[1])) ys.push(p[1]); });
      });
      (payload.series || []).forEach(function (s) {
        if (s.type === 'points') s.pts.forEach(function (p) { ys.push(p[1]); xmin = Math.min(xmin, p[0]); xmax = Math.max(xmax, p[0]); });
      });
      var inWin = ys.filter(function (y) { return y >= ymin && y <= ymax; }).length;
      if (ys.length && inWin < Math.max(3, ys.length * 0.2)) {
        ys.sort(function (a, b) { return a - b; });
        var lo = quantile(ys, 0.03), hi = quantile(ys, 0.97);
        if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
        var pad = (hi - lo) * 0.15;
        ymin = lo - pad; ymax = hi + pad; equal = false;
      }
    }
    return { xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax, equal: equal };
  }

  /* Marching squares: returns line segments [[x1,y1,x2,y2],…] where f(x,y)=0 in the given window. */
  function contour(f, xmin, xmax, ymin, ymax, nx, ny) {
    var vals = [], dx = (xmax - xmin) / nx, dy = (ymax - ymin) / ny, i, j;
    for (j = 0; j <= ny; j++) {
      var row = [];
      for (i = 0; i <= nx; i++) {
        var v; try { v = f(xmin + i * dx, ymin + j * dy); } catch (e) { v = NaN; }
        row.push(typeof v === 'number' && isFinite(v) ? v : NaN);
      }
      vals.push(row);
    }
    var segs = [];
    function lerp(a, b, va, vb) { var t = va / (va - vb); return a + (b - a) * t; }
    for (j = 0; j < ny; j++) for (i = 0; i < nx; i++) {
      var v0 = vals[j][i], v1 = vals[j][i + 1], v2 = vals[j + 1][i + 1], v3 = vals[j + 1][i];
      if (isNaN(v0) || isNaN(v1) || isNaN(v2) || isNaN(v3)) continue;
      var x0 = xmin + i * dx, x1 = x0 + dx, y0 = ymin + j * dy, y1 = y0 + dy;
      var idx = (v0 > 0 ? 1 : 0) | (v1 > 0 ? 2 : 0) | (v2 > 0 ? 4 : 0) | (v3 > 0 ? 8 : 0);
      if (idx === 0 || idx === 15) continue;
      var pB = [lerp(x0, x1, v0, v1), y0], pR = [x1, lerp(y0, y1, v1, v2)];
      var pT = [lerp(x0, x1, v3, v2), y1], pL = [x0, lerp(y0, y1, v0, v3)];
      var table = {
        1: [[pL, pB]], 2: [[pB, pR]], 3: [[pL, pR]], 4: [[pR, pT]], 5: [[pL, pT], [pB, pR]], 6: [[pB, pT]], 7: [[pL, pT]],
        8: [[pL, pT]], 9: [[pB, pT]], 10: [[pL, pB], [pR, pT]], 11: [[pR, pT]], 12: [[pL, pR]], 13: [[pB, pR]], 14: [[pL, pB]]
      }[idx];
      table.forEach(function (s) { segs.push([s[0][0], s[0][1], s[1][0], s[1][1]]); });
    }
    return segs;
  }

  /* ───────────── the interactive grapher ───────────── */

  function mount(el, payload) {
    el.classList.add('lg-root');
    el.innerHTML =
      '<div class="lg-bar">' +
      '<button data-a="reset" title="Reset view">⟲ Reset</button>' +
      '<button data-a="equal" title="Same scale on both axes">1:1</button>' +
      '<button data-a="grid" title="Show or hide the grid">Grid</button>' +
      '<button data-a="png" title="Save as an image">⬇ PNG</button>' +
      '<span class="lg-hint">drag to pan · scroll to zoom · hover to trace</span></div>' +
      '<div class="lg-stage"><canvas></canvas></div>' +
      '<div class="lg-legend"></div><div class="lg-points"></div>';
    var canvas = el.querySelector('canvas'), stage = el.querySelector('.lg-stage');
    var legend = el.querySelector('.lg-legend'), plist = el.querySelector('.lg-points');
    var ctx = canvas.getContext('2d');

    var series = (payload.series || []).map(function (s, i) {
      var o = Object.assign({}, s, { color: COLORS[i % COLORS.length], on: true });
      if (s.type === 'fn') o.f = s.js ? compile1(s.js) : null;
      if (s.type === 'implicit' || s.type === 'rel') o.g = compile2(s.js);
      if (s.type === 'fn' && !o.f && o.samples) { var pts = o.samples; o.f = function (x) { return interp(pts, x); }; }
      return o;
    });
    var fnSeries = series.filter(function (s) { return s.type === 'fn' && s.f; });

    function interp(pts, x) {
      var lo = 0, hi = pts.length - 1;
      if (x < pts[lo][0] || x > pts[hi][0]) return NaN;
      while (hi - lo > 1) { var m = (lo + hi) >> 1; if (pts[m][0] <= x) lo = m; else hi = m; }
      var a = pts[lo], b = pts[hi];
      if (!isFinite(a[1]) || !isFinite(b[1])) return NaN;
      return a[1] + (b[1] - a[1]) * (x - a[0]) / ((b[0] - a[0]) || 1);
    }

    var W = 600, H = 440, dpr = 1, view = null, home = null, showGrid = true, mouse = null, pinned = [];

    function size() {
      var w = Math.max(260, stage.clientWidth || 600);
      W = w; H = Math.round(Math.min(Math.max(w * 0.72, 300), 620));
      dpr = root.devicePixelRatio || 1;
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function initView() {
      home = autoView(payload, fnSeries, W / H);
      view = Object.assign({}, home);
      fixAspect();
    }
    function fixAspect() {
      if (!view.equal) return;
      var cx = (view.xmin + view.xmax) / 2, cy = (view.ymin + view.ymax) / 2;
      var xr = view.xmax - view.xmin;
      var yr = xr * H / W;
      view.ymin = cy - yr / 2; view.ymax = cy + yr / 2;
      view.xmin = cx - xr / 2; view.xmax = cx + xr / 2;
    }
    function sx(x) { return (x - view.xmin) / (view.xmax - view.xmin) * W; }
    function sy(y) { return H - (y - view.ymin) / (view.ymax - view.ymin) * H; }
    function ux(px) { return view.xmin + px / W * (view.xmax - view.xmin); }
    function uy(py) { return view.ymin + (H - py) / H * (view.ymax - view.ymin); }

    function css(name, fallback) {
      var v = getComputedStyle(el).getPropertyValue(name).trim();
      return v || fallback;
    }

    function draw() {
      var bg = css('--g-bg', '#ffffff'), gridc = css('--g-grid', '#e6e9ef'), axisc = css('--g-axis', '#8791a3'), txt = css('--g-text', '#4b5565');
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
      var tx = ticks(view.xmin, view.xmax, W / 90), ty = ticks(view.ymin, view.ymax, H / 70);
      ctx.font = '11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
      if (showGrid) {
        ctx.lineWidth = 1; ctx.strokeStyle = gridc; ctx.beginPath();
        tx.values.forEach(function (v) { var p = Math.round(sx(v)) + 0.5; ctx.moveTo(p, 0); ctx.lineTo(p, H); });
        ty.values.forEach(function (v) { var p = Math.round(sy(v)) + 0.5; ctx.moveTo(0, p); ctx.lineTo(W, p); });
        ctx.stroke();
      }
      // axes
      var ax = sx(0), ay = sy(0);
      ctx.strokeStyle = axisc; ctx.lineWidth = 1.5; ctx.beginPath();
      if (ay >= 0 && ay <= H) { ctx.moveTo(0, ay); ctx.lineTo(W, ay); }
      if (ax >= 0 && ax <= W) { ctx.moveTo(ax, 0); ctx.lineTo(ax, H); }
      ctx.stroke();
      // tick labels
      ctx.fillStyle = txt; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      var labY = Math.min(Math.max(ay + 4, 2), H - 14);
      tx.values.forEach(function (v) { if (v !== 0 || ax < 0 || ax > W) ctx.fillText(fmtTick(v, tx.step), sx(v), labY); });
      ctx.textAlign = ax < 34 ? 'left' : 'right'; ctx.textBaseline = 'middle';
      var labX = ax < 34 ? Math.max(ax + 5, 3) : Math.min(ax - 5, W - 3);
      ty.values.forEach(function (v) { if (v !== 0) ctx.fillText(fmtTick(v, ty.step), labX, sy(v)); });

      // series
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      series.forEach(function (s) {
        if (!s.on) return;
        ctx.strokeStyle = s.color; ctx.fillStyle = s.color;
        if (s.type === 'fn' && s.f) {
          ctx.lineWidth = 2.4;
          var n = Math.min(2400, Math.ceil(W * 2));
          var rs = runs(sample(s.f, view.xmin, view.xmax, n), view.ymin, view.ymax);
          rs.forEach(function (r) {
            ctx.beginPath();
            r.forEach(function (p, i) { var X = sx(p[0]), Y = sy(p[1]); if (i) ctx.lineTo(X, Y); else ctx.moveTo(X, Y); });
            if (r.length === 1) { ctx.arc(sx(r[0][0]), sy(r[0][1]), 1.5, 0, 6.3); ctx.fill(); } else ctx.stroke();
          });
        } else if (s.type === 'vline') {
          ctx.lineWidth = 2.4; ctx.beginPath(); ctx.moveTo(sx(s.x), 0); ctx.lineTo(sx(s.x), H); ctx.stroke();
        } else if (s.type === 'implicit' && s.g) {
          ctx.lineWidth = 2.4; drawContour(s.g, false);
        } else if (s.type === 'rel' && s.g) {
          shade(s); ctx.lineWidth = 2.2; drawContour(s.g, s.op === '>' || s.op === '<');
        } else if (s.type === 'points') {
          s.pts.forEach(function (p) { ctx.beginPath(); ctx.arc(sx(p[0]), sy(p[1]), 4.5, 0, 6.3); ctx.fill(); });
        }
      });
      ctx.setLineDash([]);

      // key points
      var kp = (payload.points || []);
      ctx.font = '11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'; ctx.textBaseline = 'bottom'; ctx.textAlign = 'left';
      var placed = [];
      kp.forEach(function (p) {
        var X = sx(p.x), Y = sy(p.y);
        if (X < -4 || X > W + 4 || Y < -4 || Y > H + 4) return;
        ctx.fillStyle = bg; ctx.strokeStyle = p.kind === 'intersection' ? '#111827' : css('--g-pt', '#111827'); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(X, Y, 4.2, 0, 6.3); ctx.fill(); ctx.stroke();
        var w = ctx.measureText(p.label).width, lx = X + 7, ly = Y - 6;
        if (lx + w > W - 2) lx = X - 7 - w;
        var clash = placed.some(function (q) { return Math.abs(q[0] - lx) < w + 6 && Math.abs(q[1] - ly) < 14; });
        if (!clash) {
          ctx.fillStyle = css('--g-label-bg', 'rgba(255,255,255,.85)'); ctx.fillRect(lx - 2, ly - 12, w + 4, 15);
          ctx.fillStyle = txt; ctx.fillText(p.label, lx, ly + 1); placed.push([lx, ly]);
        }
      });
      // pinned + hover
      pinned.forEach(function (t) { dot(t); });
      if (mouse) { var h = trace(mouse.x); if (h) dot(h, true); }
    }

    function drawContour(g, dashed) {
      var nx = Math.ceil(W / 4), ny = Math.ceil(H / 4);
      var segs = contour(g, view.xmin, view.xmax, view.ymin, view.ymax, nx, ny);
      ctx.setLineDash(dashed ? [7, 5] : []); ctx.beginPath();
      segs.forEach(function (s) { ctx.moveTo(sx(s[0]), sy(s[1])); ctx.lineTo(sx(s[2]), sy(s[3])); });
      ctx.stroke(); ctx.setLineDash([]);
    }
    function shade(s) {
      var step = 5, strict = s.op === '>' || s.op === '<';
      ctx.save(); ctx.globalAlpha = 0.16; ctx.fillStyle = s.color;
      for (var py = 0; py < H; py += step) for (var px = 0; px < W; px += step) {
        var v; try { v = s.g(ux(px + step / 2), uy(py + step / 2)); } catch (e) { v = NaN; }
        if (!isFinite(v)) continue;
        var ok = (s.op === '>' || s.op === '>=') ? v > 0 : v < 0;
        if (ok) ctx.fillRect(px, py, step, step);
      }
      ctx.restore();
    }

    function trace(px) {
      var x = ux(px), best = null, bd = 1e9;
      fnSeries.forEach(function (s) {
        if (!s.on) return;
        var y = safe(s.f, x); if (!isFinite(y)) return;
        var d = Math.abs(sy(y) - mouse.y);
        if (d < bd && d < 40) { bd = d; best = { x: x, y: y, color: s.color }; }
      });
      return best;
    }
    function dot(t, hover) {
      var X = sx(t.x), Y = sy(t.y);
      ctx.fillStyle = t.color; ctx.beginPath(); ctx.arc(X, Y, 5, 0, 6.3); ctx.fill();
      ctx.strokeStyle = css('--g-bg', '#fff'); ctx.lineWidth = 2; ctx.stroke();
      var txt = '(' + (+t.x.toPrecision(5)) + ', ' + (+t.y.toPrecision(5)) + ')';
      ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
      var w = ctx.measureText(txt).width, lx = X + 10, ly = Y - 12;
      if (lx + w > W - 4) lx = X - 10 - w; if (ly < 16) ly = Y + 24;
      ctx.fillStyle = css('--g-tip', '#111827'); ctx.fillRect(lx - 5, ly - 14, w + 10, 20);
      ctx.fillStyle = '#fff'; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'; ctx.fillText(txt, lx, ly);
    }

    // legend + point list
    function buildLegend() {
      legend.innerHTML = '';
      series.forEach(function (s) {
        var b = document.createElement('label'); b.className = 'lg-chip';
        var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = true;
        cb.onchange = function () { s.on = cb.checked; draw(); };
        var sw = document.createElement('i'); sw.style.background = s.color;
        var t = document.createElement('span'); t.textContent = s.label || '';
        b.appendChild(cb); b.appendChild(sw); b.appendChild(t); legend.appendChild(b);
      });
      var kp = payload.points || [];
      plist.innerHTML = '';
      if (kp.length) {
        var h = document.createElement('div'); h.className = 'lg-ph'; h.textContent = 'Key points'; plist.appendChild(h);
        kp.forEach(function (p) {
          var r = document.createElement('button'); r.className = 'lg-pt';
          r.textContent = p.label + (p.kind ? '  · ' + p.kind : '');
          r.onclick = function () { centerOn(p.x, p.y); };
          plist.appendChild(r);
        });
      }
    }
    function centerOn(x, y) {
      var xr = view.xmax - view.xmin, yr = view.ymax - view.ymin;
      if (x < view.xmin || x > view.xmax) { view.xmin = x - xr / 2; view.xmax = x + xr / 2; }
      if (y < view.ymin || y > view.ymax) { view.ymin = y - yr / 2; view.ymax = y + yr / 2; }
      draw();
    }

    // interaction
    var drag = null, touches = {};
    function pos(e) { var r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }
    function zoomAt(px, py, k) {
      var x = ux(px), y = uy(py);
      view.xmin = x - (x - view.xmin) * k; view.xmax = x + (view.xmax - x) * k;
      if (view.equal) { fixAspectAround(y, py); } else { view.ymin = y - (y - view.ymin) * k; view.ymax = y + (view.ymax - y) * k; }
      draw();
    }
    function fixAspectAround(y, py) {
      var xr = view.xmax - view.xmin, yr = xr * H / W;
      view.ymax = y + (py / H) * yr; view.ymin = view.ymax - yr;
    }
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault(); var p = pos(e); zoomAt(p.x, p.y, Math.exp(e.deltaY * 0.0015));
    }, { passive: false });
    canvas.addEventListener('pointerdown', function (e) {
      canvas.setPointerCapture(e.pointerId); touches[e.pointerId] = pos(e);
      drag = { x: e.clientX, y: e.clientY, moved: false, view: Object.assign({}, view), id: e.pointerId };
    });
    canvas.addEventListener('pointermove', function (e) {
      var p = pos(e); touches[e.pointerId] = p;
      var ids = Object.keys(touches);
      if (ids.length === 2 && e.pointerType === 'touch') {
        var a = touches[ids[0]], b = touches[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (drag && drag.pinch) { zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, drag.pinch / d); }
        if (drag) drag.pinch = d; return;
      }
      if (drag && drag.id === e.pointerId && (e.buttons || e.pointerType === 'touch')) {
        var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
        var xr = drag.view.xmax - drag.view.xmin, yr = drag.view.ymax - drag.view.ymin;
        view.xmin = drag.view.xmin - dx / W * xr; view.xmax = drag.view.xmax - dx / W * xr;
        view.ymin = drag.view.ymin + dy / H * yr; view.ymax = drag.view.ymax + dy / H * yr;
        mouse = p; draw();
      } else { mouse = p; draw(); }
    });
    function up(e) {
      delete touches[e.pointerId];
      if (drag && !drag.moved && e.type === 'pointerup' && mouse) { var t = trace(mouse.x); if (t) pinned.push(t); else pinned = []; draw(); }
      drag = null;
    }
    canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
    canvas.addEventListener('pointerleave', function () { mouse = null; draw(); });
    canvas.addEventListener('dblclick', function () { view = Object.assign({}, home); fixAspect(); pinned = []; draw(); });

    el.querySelector('.lg-bar').addEventListener('click', function (e) {
      var a = e.target.getAttribute && e.target.getAttribute('data-a'); if (!a) return;
      if (a === 'reset') { view = Object.assign({}, home); fixAspect(); pinned = []; }
      if (a === 'equal') { view.equal = !view.equal; if (view.equal) fixAspect(); }
      if (a === 'grid') showGrid = !showGrid;
      if (a === 'png') { var l = document.createElement('a'); l.download = 'lmath-graph.png'; l.href = canvas.toDataURL('image/png'); l.click(); }
      draw();
    });

    function relayout() { size(); if (!view) initView(); else fixAspect(); draw(); }
    if (root.ResizeObserver) new root.ResizeObserver(function () { relayout(); }).observe(stage);
    root.addEventListener('resize', relayout);
    size(); initView(); buildLegend(); draw();
    return { redraw: draw, reset: function () { view = Object.assign({}, home); fixAspect(); draw(); } };
  }

  var api = { mount: mount, niceStep: niceStep, ticks: ticks, fmtTick: fmtTick, sample: sample, runs: runs, autoView: autoView, contour: contour, compile1: compile1, quantile: quantile };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LmathGraph = api;
})(typeof window !== 'undefined' ? window : globalThis);
