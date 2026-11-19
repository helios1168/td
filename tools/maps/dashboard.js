// tools/maps/dashboard.js (issue #153): the dashboard's page.  It reads the data dashboard.py embedded (P), keeps its state in the
// URL hash (S), and computes every number on screen from the cells of the chosen scenario and estimate (compute), so the map, the
// totals and the tables cannot disagree.  A person is an index into P.keys; names, when the run gave any, are shown next to keys.
const $ = (id) => document.getElementById(id);
const P = JSON.parse($('data').textContent);
const C = P.cells, NC = C.m.length, NK = P.classes.length, NZ = P.zips.length, NSHAPE = P.zipGeom.length;
const EVERY = (1 << P.scenarios.length) - 1;
const CLS = P.classes, K = Object.fromEntries(CLS.map((c, i) => [c.id, i]));
const GROUP = (g) => CLS.map((c, i) => c.group === g ? i : -1).filter((i) => i >= 0);
const FILL = GROUP('fill'), BARGAIN = GROUP('bargain');
const CH_SHOW = ['NATIONAL', 'WH', 'REGIONAL', 'OPEN'].filter((c) => P.channels.includes(c));     // the priority chain's order
const CH_LABEL = {ALL: 'All', NATIONAL: 'National', WH: 'WH', REGIONAL: 'Regional', OPEN: 'Open seats'};
const CH_OF_ROLE = Object.fromEntries(Object.entries(P.roleOf).map(([c, r]) => [r, c]));
const VIEWS = {fill: 'Where to fill', gap: 'All classes', terr: 'Territories'};
const SHARED = '#E0E0FB', CONTESTED = '#20113E', NOBODY = '#F2F2F2';                            // Territories: a split not held by one assignee, two or more holders, no holder
const ST = P.states, SIX = new Map(ST.map((s, i) => [s.id, i]));

// ---- the places a focus can be: CONUS, the census regions and divisions, the states
const AREAS = new Map([['CONUS', {label: 'CONUS', kind: 'the 48 states and DC', states: new Set(ST.keys()), up: null}]]);
for (const [reg, divs] of P.regions) {
  AREAS.set(reg, {label: reg, kind: 'region', states: new Set(), up: 'CONUS'});
  for (const [div, codes] of divs) {
    AREAS.set(div, {label: div, kind: 'division', states: new Set(codes.map((s) => SIX.get(s))), up: reg});
    for (const s of codes) { AREAS.get(reg).states.add(SIX.get(s)); AREAS.set(s, {label: ST[SIX.get(s)].name, kind: 'state', states: new Set([SIX.get(s)]), up: div}); }
  }
}
for (const [i, s] of ST.entries()) if (!AREAS.has(s.id)) AREAS.set(s.id, {label: s.name, kind: 'state', states: new Set([i]), up: 'CONUS'});
const boxOf = (states) => [...states].reduce((b, i) => [Math.min(b[0], ST[i].box[0]), Math.min(b[1], ST[i].box[1]), Math.max(b[2], ST[i].box[2]), Math.max(b[3], ST[i].box[3])], [180, 90, -180, -90]);

// ---- state: the URL hash, only what differs from the default
const DEF = {sc: P.scenarios[0], est: P.ests[0], view: 'fill', ch: 'ALL', focus: 'CONUS', sel: '', by: 'assigned', cls: '', diff: ''};
const S = {...DEF};
const VALID = {sc: (v) => P.scenarios.includes(v), est: (v) => P.ests.includes(v), view: (v) => v in VIEWS, ch: (v) => v === 'ALL' || CH_SHOW.includes(v),
  focus: (v) => AREAS.has(v), by: (v) => v === 'assigned' || v === 'held', cls: (v) => v === '' || CLS[+v] !== undefined, diff: (v) => v === '' || v === '1',
  sel: (v) => v === '' || /^\d{5}$/.test(v) || v.split('-').every((k) => P.keys.includes(k)) && v.split('-').length <= 2};
function setState(patch) {
  for (const [k, v] of Object.entries(patch)) if (k in DEF) S[k] = VALID[k](v) ? v : DEF[k];
  if (S.view === 'terr') {                      // a territory map is one channel's: no "All"; no one is assigned to an open seat
    if (S.ch === 'ALL') S.ch = CH_SHOW.includes('REGIONAL') ? 'REGIONAL' : CH_SHOW[0];
    if (S.ch === 'OPEN') S.by = 'held';
  }
}
function readHash() { Object.assign(S, DEF); setState(Object.fromEntries(new URLSearchParams(location.hash.slice(1)))); }
function writeHash() {
  const q = new URLSearchParams(Object.entries(S).filter(([k, v]) => v !== DEF[k]));
  const h = q.toString();
  if (location.hash.slice(1) !== h) history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
}
function go(patch) {                             // one door for every control: change the state, redraw
  const before = {...S};
  for (const k of ['sel', 'cls', 'diff']) if (k in patch && patch[k] === S[k] && Object.keys(patch).length === 1) patch[k] = '';      // a second press lets go
  setState(patch);
  writeHash();
  render(before);
}

// ---- words and numbers
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const usd = (v) => Math.abs(v) >= 1e9 ? '$' + (v / 1e9).toFixed(2) + 'B' : Math.abs(v) >= 5e4 ? '$' + (v / 1e6).toFixed(1) + 'MM' : Math.abs(v) >= 500 ? '$' + (v / 1e3).toFixed(0) + 'K' : '$' + Math.round(v);
const mm = (v) => v ? (v / 1e6).toLocaleString('en-US', {minimumFractionDigits: 1, maximumFractionDigits: 1}) : '–';
const pct = (v, of) => of > 0 ? (100 * v / of).toFixed(1) + '%' : '–';
const int = (v) => Math.round(v).toLocaleString('en-US');
const name = (k) => P.names[P.keys[k]] || '';
const label = (k) => P.keys[k] + (name(k) ? ' ' + name(k) : '');
const who = (k, dot) => `<button class="who" data-go="sel=${P.keys[k]}">${dot ? `<i style="background:${P.colour[k]}"></i>` : ''}${esc(label(k))}</button>`;
const whoAll = (ks, none) => ks.length ? ks.map((k) => who(k)).join(', ') : none;
const chName = () => S.ch === 'ALL' ? 'all channels' : CH_LABEL[S.ch] + (S.ch === 'OPEN' ? '' : ' channel');
const area = () => AREAS.get(S.focus);
const clsColour = (i) => S.view === 'fill' ? CLS[i].fill : CLS[i].color;
const sum = (a) => { let t = 0; for (const v of a) t += v; return t; };
const memo = (fn) => { const m = new Map(); return (...a) => { const k = a.join('|'); if (!m.has(k)) m.set(k, fn(...a)); return m.get(k); }; };

// ---- the cells of a scenario and estimate, and what is read off them
const rowsOf = memo((sc, est) => { const bit = 1 << P.scenarios.indexOf(sc), e = P.ests.indexOf(est); return Int32Array.from({length: NC}, (_, i) => i).filter((i) => C.m[i] & bit && C.e[i] === e); });
const zipRows = memo((sc, est) => { const m = new Map(); for (const i of rowsOf(sc, est)) (m.get(C.z[i]) || m.set(C.z[i], []).get(C.z[i])).push(i); return m; });
const assignedOf = memo((sc, est) => {            // "channel|state" -> the people assigned there, from each person's role and assigned
  const m = new Map(), bit = 1 << P.scenarios.indexOf(sc), e = P.ests.indexOf(est);   // states (not from the cells: a state can be
  const six = new Map(P.states.map((st, i) => [st.id, i]));                             // assigned in a channel that has no cell there)
  const chOf = new Map(Object.entries(P.roleOf).map(([c, r]) => [r, P.channels.indexOf(c)]));
  for (const r of P.people) {                       // [scenario mask, est, key, source, role, assigned states, ...]
    if (!(r[0] & bit) || r[1] !== e || !chOf.has(r[4])) continue;
    for (const st of String(r[5] || '').split(' ')) {
      if (!six.has(st)) continue;
      const k = chOf.get(r[4]) + '|' + six.get(st);
      (m.get(k) || m.set(k, []).get(k)).push(r[2]);
    }
  }
  for (const v of m.values()) v.sort((a, b) => a - b);
  return m;
});
const pairKey = (c, a, b) => c + '|' + Math.min(a, b) + '|' + Math.max(a, b);
function addPairs(pairs, i) {                    // 07's TD_GAP_PAIR: an OVERLAP cell counts in full for each pair of its holders
  const h = P.sets[C.h[i]];
  for (let x = 0; x < h.length; x++) for (let y = x + 1; y < h.length; y++) {
    const key = pairKey(C.c[i], h[x], h[y]);
    const p = pairs.get(key) || pairs.set(key, {c: C.c[i], a: Math.min(h[x], h[y]), b: Math.max(h[x], h[y]), usd: 0, zips: new Set(), states: new Map()}).get(key);
    p.usd += C.u[i]; p.zips.add(C.z[i]); p.states.set(C.s[i], (p.states.get(C.s[i]) || 0) + C.u[i]);
  }
}

function compute(sc = S.sc, lean = false) {
  const rows = rowsOf(sc, S.est), ch = S.ch === 'ALL' ? -1 : P.channels.indexOf(S.ch), F = area().states;
  const D = {rows, ch, est: 0, noState: 0, focus: 0, cls: new Float64Array(NK), noShape: 0, st: new Map(), stTotal: new Map(), pairs: new Map(),
    zc: lean ? null : new Float64Array(NZ * NK).fill(-1), za: new Int32Array(lean ? 0 : NZ).fill(-1), zu: new Float64Array(lean ? 0 : NZ), zh: new Map()};
  for (const i of rows) {
    const u = C.u[i], s = C.s[i], c = C.c[i], k = C.k[i], z = C.z[i], inCh = ch < 0 || c === ch;
    D.est += u;
    if (s < 0) { D.noState += u; continue; }                       // a cell with no state is in the estimate and on no map
    if (inCh && !lean) {
      D.zc[z * NK + k] = Math.max(D.zc[z * NK + k], 0) + u;
      if (D.za[z] < 0 || u > D.zu[z]) { D.za[z] = C.a[i]; D.zu[z] = u; }
      const h = D.zh.get(z) || D.zh.set(z, new Set()).get(z);
      for (const p of P.sets[C.h[i]]) h.add(p);
    }
    if (!F.has(s)) continue;
    D.focus += u;
    if (!inCh) continue;
    D.cls[k] += u;
    if (z >= NSHAPE) D.noShape += u;
    (D.st.get(s) || D.st.set(s, new Float64Array(NK)).get(s))[k] += u;
    if (k === K.OVERLAP && !lean) addPairs(D.pairs, i);
  }
  D.screen = sum(D.cls);
  D.group = {covered: D.cls[K.COVERED], bargain: sum(BARGAIN.map((i) => D.cls[i])), fill: sum(FILL.map((i) => D.cls[i]))};
  return D;
}

// The run's own totals (07's summary and pairs) against the cells: the tie-out the page shows.
const check = memo((sc, est) => {
  const bit = 1 << P.scenarios.indexOf(sc), e = P.ests.indexOf(est), rows = rowsOf(sc, est);
  const got = new Map(), pairs = new Map();
  let total = 0;
  for (const i of rows) { got.set(C.c[i] + '|' + C.k[i], (got.get(C.c[i] + '|' + C.k[i]) || 0) + C.u[i]); total += C.u[i]; if (C.k[i] === K.OVERLAP) addPairs(pairs, i); }
  const want = P.summary.filter((r) => r[0] & bit && r[1] === e), wantPairs = P.pairs.filter((r) => r[0] & bit && r[1] === e);
  const bad = [];
  if (want.length) {
    const keys = new Set([...got.keys(), ...want.map((r) => r[2] + '|' + r[3])]);
    for (const key of keys) {
      const w = sum(want.filter((r) => r[2] + '|' + r[3] === key).map((r) => r[5])), g = got.get(key) || 0;
      if (Math.abs(w - g) > 1) bad.push(`${P.channels[+key.split('|')[0]]} ${CLS[+key.split('|')[1]].label}: cells ${usd(g)}, summary ${usd(w)}`);
    }
  }
  if (wantPairs.length || pairs.size) {
    const keys = new Set([...pairs.keys(), ...wantPairs.map((r) => pairKey(r[2], r[3], r[4]))]);
    for (const key of keys) {
      const w = wantPairs.find((r) => pairKey(r[2], r[3], r[4]) === key), g = pairs.get(key);
      if (!w || !g || Math.abs(w[6] - g.usd) > 1 || w[5] !== g.zips.size) bad.push(`pair ${key.split('|').slice(1).map((k) => P.keys[+k]).join(' and ')}: cells ${g ? usd(g.usd) : 'none'}, run ${w ? usd(w[6]) : 'none'}`);
    }
  }
  return {total, bad, summary: want.length > 0, pairs: wantPairs.length};
});

// ---- the map's colours: one per ZIP, by the view
function zipColours(D) {
  const col = new Array(NSHAPE).fill(null);
  const who = terrWho(D);
  for (let z = 0; z < NSHAPE; z++) {
    const o = z * NK;
    let best = -1, any = false;
    if (S.view === 'terr') { col[z] = who(z); continue; }
    for (let k = 0; k < NK; k++) if (D.zc[o + k] >= 0) { any = true; if (S.view === 'gap' && (best < 0 || D.zc[o + k] > D.zc[o + best])) best = k; }
    if (!any) continue;
    if (S.view === 'gap') { col[z] = CLS[best].color; continue; }
    for (const k of FILL) if (D.zc[o + k] > 0 && (best < 0 || D.zc[o + k] > D.zc[o + best])) best = k;       // Fill: the unfilled class with most $,
    col[z] = best >= 0 ? CLS[best].fill : BARGAIN.some((k) => D.zc[o + k] > 0) ? CLS[BARGAIN[0]].fill : CLS[K.COVERED].fill;   // else to bargain, else covered
  }
  return col;
}
function terrWho(D) {                             // Territories: the colour of a ZIP, by who is assigned or who holds it today
  return (z) => {
    if (D.za[z] < 0) return null;
    const h = [...(D.zh.get(z) || [])];
    if (S.by === 'held') return h.length === 0 ? NOBODY : h.length === 1 ? P.colour[h[0]] : CONTESTED;
    const a = P.sets[D.za[z]];
    if (a.length === 1) return P.colour[a[0]];
    const mine = h.filter((p) => a.includes(p));
    return mine.length === 1 ? P.colour[mine[0]] : a.length ? SHARED : null;
  };
}
const SEL = () => { const v = S.sel; return /^\d{5}$/.test(v) ? {zip: P.zips.indexOf(v), code: v} : v ? {people: v.split('-').map((k) => P.keys.indexOf(k))} : {}; };
function highlight(D) {                           // the ZIPs kept bright, or null for all: what is selected, the isolated class, the scenario differences
  const sets = [], sel = SEL(), inCh = (i) => C.s[i] >= 0 && (D.ch < 0 || C.c[i] === D.ch);
  if (sel.people) {
    const [a, b] = sel.people, s = new Set();
    for (const i of D.rows) {
      if (!inCh(i)) continue;
      const h = P.sets[C.h[i]];
      if (b === undefined ? h.includes(a) || P.sets[C.a[i]].includes(a) : C.k[i] === K.OVERLAP && h.includes(a) && h.includes(b)) s.add(C.z[i]);
    }
    sets.push(s);
  }
  if (S.cls !== '') { const s = new Set(); for (const i of D.rows) if (inCh(i) && C.k[i] === +S.cls) s.add(C.z[i]); sets.push(s); }
  if (S.diff) { const e = P.ests.indexOf(S.est), s = new Set(); for (let i = 0; i < NC; i++) if (C.e[i] === e && C.m[i] !== EVERY && inCh(i)) s.add(C.z[i]); sets.push(s); }
  if (!sets.length) return null;
  return sets.reduce((a, b) => new Set([...a].filter((z) => b.has(z))));
}

// ---- the map (MapLibre GL JS, vendored and embedded: no tiles, our own state and ZIP shapes)
let map = null, painted = {col: [], dim: [], lit: false, tint: [], hover: -1, sel: -1, fit: ''};
const ring = (a) => { const r = []; let x = 0, y = 0; for (let i = 0; i < a.length; i += 2) { x += a[i]; y += a[i + 1]; r.push([x / P.q, y / P.q]); } r.push(r[0]); return r; };
const shape = (g) => ({type: 'MultiPolygon', coordinates: g.map((poly) => poly.map(ring))});
const ZBOX = [];
// The library is the inline module script before this one (globalThis.maplibregl): nothing is imported, since a dynamic import of a
// blob: URL is refused by sandboxed viewers and some policies.  Its worker still needs a URL: a blob: of the worker as a classic
// script, the URL ending ".cjs" so MapLibre starts it as one (dashboard.py's blob() says why).
async function startMap() {
  const gunzip = async (id) => new Response(new Blob([Uint8Array.from(atob($(id).textContent), (c) => c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
  const gl = globalThis.maplibregl;
  if (!gl) throw new Error('the map library did not run');
  document.head.appendChild(Object.assign(document.createElement('style'), {textContent: await gunzip('v-css')}));
  gl.setWorkerUrl(URL.createObjectURL(new Blob([await gunzip('v-worker')], {type: 'text/javascript'})) + '#.cjs');
  const zips = P.zipGeom.map((g, id) => {
    const geometry = shape(g), b = [180, 90, -180, -90];
    for (const poly of geometry.coordinates) for (const [x, y] of poly[0]) { b[0] = Math.min(b[0], x); b[1] = Math.min(b[1], y); b[2] = Math.max(b[2], x); b[3] = Math.max(b[3], y); }
    ZBOX.push(b);
    return {type: 'Feature', id, properties: {}, geometry};
  });
  const fc = (features) => ({type: 'FeatureCollection', features});
  const state = (name, fallback) => ['to-color', ['coalesce', ['feature-state', name], fallback]];
  const m = new gl.Map({container: 'map', attributionControl: false, dragRotate: false, pitchWithRotate: false, touchPitch: false, renderWorldCopies: false,
    minZoom: 2, maxZoom: 13, bounds: boxOf(area().states), fitBoundsOptions: {padding: 28},
    style: {version: 8, sources: {
      states: {type: 'geojson', data: fc(ST.map((s, id) => ({type: 'Feature', id, properties: {}, geometry: shape(s.g)})))},
      zips: {type: 'geojson', data: fc(zips), maxzoom: 11},
      labels: {type: 'geojson', data: fc([])}},
    layers: [
      {id: 'sea', type: 'background', paint: {'background-color': '#F3F3FD'}},
      {id: 'land', type: 'fill', source: 'states', paint: {'fill-color': '#FFFFFF'}},
      {id: 'tint', type: 'fill', source: 'states', paint: {'fill-color': state('c', 'rgba(0,0,0,0)'), 'fill-opacity': 0.2}},
      {id: 'zips', type: 'fill', source: 'zips', paint: {'fill-color': state('c', 'rgba(0,0,0,0)'), 'fill-opacity': ['case', ['boolean', ['feature-state', 'dim'], false], 0.1, 1]}},
      {id: 'veil', type: 'fill', source: 'states', filter: ['==', ['id'], -1], paint: {'fill-color': '#FFFFFF', 'fill-opacity': 0.75}},
      {id: 'lines', type: 'line', source: 'states', paint: {'line-color': '#20113E', 'line-opacity': 0.5, 'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.6, 8, 1.6]}},
      {id: 'mark', type: 'line', source: 'zips', paint: {'line-color': '#20113E', 'line-width': ['interpolate', ['linear'], ['zoom'],      // the selected ZIP, the one under the pointer and,
        5, ['case', ['boolean', ['feature-state', 'sel'], false], 3, ['boolean', ['feature-state', 'hover'], false], 1.5, 0],                             // zoomed in, the ones kept bright
        7, ['case', ['boolean', ['feature-state', 'sel'], false], 3, ['boolean', ['feature-state', 'hover'], false], 1.5, ['boolean', ['feature-state', 'lit'], false], 0.6, 0]]}},
      {id: 'labels', type: 'symbol', source: 'labels', layout: {'text-field': ['get', 't'], 'text-font': ['Arial'], 'text-size': ['interpolate', ['linear'], ['zoom'], 3, 11, 7, 14],
        'text-max-width': 9, 'text-line-height': 1.15, 'text-padding': 3},
        paint: {'text-color': '#20113E', 'text-halo-color': 'rgba(255,255,255,0.9)', 'text-halo-width': 1.5}}]}});
  m.touchZoomRotate.disableRotation();
  m.keyboard.disableRotation();
  m.addControl(new gl.NavigationControl({showCompass: false}), 'bottom-right');
  m.on('mousemove', (e) => hover(e));
  m.on('mouseout', () => hover(null));
  m.on('idle', () => { document.body.dataset.map = 'idle'; });         // for whoever waits to look: the map has drawn what it was asked
  m.on('click', (e) => { const z = zipAt(e.point); if (z >= 0) go({sel: P.zips[z]}); });
  await new Promise((done, fail) => {            // a worker that cannot start never loads the map: say so instead of waiting for ever
    m.on('load', done);
    m.on('error', (e) => fail(e.error || new Error('the map reported an error')));
    setTimeout(() => fail(new Error('the map did not load in 30 seconds')), 30000);
  });
  map = m;
  paint(null);
}
const zipAt = (pt) => { const f = map.queryRenderedFeatures(pt, {layers: ['zips']}).find((f) => painted.col[f.id]); return f ? f.id : -1; };
const stateAt = (pt) => { const f = map.queryRenderedFeatures(pt, {layers: ['land']})[0]; return f ? f.id : -1; };
function hover(e) {
  const z = e ? zipAt(e.point) : -1, tip = $('tip');
  if (z !== painted.hover) {
    if (painted.hover >= 0) map.setFeatureState({source: 'zips', id: painted.hover}, {hover: false});
    if (z >= 0) map.setFeatureState({source: 'zips', id: z}, {hover: true});
    painted.hover = z;
  }
  const s = e && z < 0 ? stateAt(e.point) : -1;
  map.getCanvas().style.cursor = z >= 0 ? 'pointer' : '';
  tip.hidden = z < 0 && s < 0;
  if (tip.hidden) return;
  tip.innerHTML = z >= 0 ? zipDetail(z, false) : stateTip(s);
  const box = $('map').getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.max(4, Math.min(e.point.x + 14, box.width - w - 4)) + 'px';
  tip.style.top = (e.point.y + 16 + h > box.height ? Math.max(4, e.point.y - h - 10) : e.point.y + 16) + 'px';
}
function paint(before) {
  if (!map) return;
  document.body.dataset.map = 'busy';
  const D = NOW, col = zipColours(D), keep = highlight(D), sel = SEL();
  for (let z = 0; z < NSHAPE; z++) {
    const dim = !!keep && !keep.has(z);
    if (col[z] !== painted.col[z] || dim !== painted.dim[z] || !!keep !== painted.lit) map.setFeatureState({source: 'zips', id: z}, {c: col[z], dim, lit: !!keep && !dim && !!col[z]});
    painted.dim[z] = dim;
  }
  painted.col = col; painted.lit = !!keep;
  const zsel = sel.zip !== undefined && sel.zip < NSHAPE ? sel.zip : -1;
  if (zsel !== painted.sel) {
    if (painted.sel >= 0) map.setFeatureState({source: 'zips', id: painted.sel}, {sel: false});
    if (zsel >= 0) map.setFeatureState({source: 'zips', id: zsel}, {sel: true});
    painted.sel = zsel;
  }
  const asg = assignedOf(S.sc, S.est), terr = S.view === 'terr', F = area().states;
  ST.forEach((s, i) => {                       // Territories: a state with one assignee wears their colour lightly, and every state names its people
    const a = terr ? asg.get(D.ch + '|' + i) || [] : [];
    const tint = terr && S.by === 'assigned' && a.length === 1 ? P.colour[a[0]] : null;
    if (tint !== painted.tint[i]) map.setFeatureState({source: 'states', id: i}, {c: tint});
    painted.tint[i] = tint;
  });
  map.getSource('labels').setData({type: 'FeatureCollection', features: ST.map((s, i) => {
    const a = terr ? asg.get(D.ch + '|' + i) || [] : [];
    return {type: 'Feature', properties: {t: s.id + (a.length ? '\n' + a.map((k) => name(k) || P.keys[k]).join(' / ') : '')}, geometry: {type: 'Point', coordinates: s.pt}};
  })});
  map.setFilter('veil', ['!', ['in', ['id'], ['literal', [...F]]]]);
  const cardW = $('card').hidden ? 0 : $('card').offsetWidth + 12;
  let fit = null;                               // a selected person or pair: their ZIPs (in focus when any are); a ZIP: the ZIP; else the focus
  if (sel.people && keep && keep.size) { const zs = [...keep].filter((z) => z < NSHAPE), inF = zs.filter((z) => inFocus(z, F)); fit = boxOfZips(inF.length ? inF : zs); }
  else if (sel.zip >= 0 && sel.zip < NSHAPE) {    // a ZIP that can be seen where the map is stays put; one too small, out of view or under the card is flown to
    const b = ZBOX[sel.zip], nw = map.project([b[0], b[3]]), se = map.project([b[2], b[1]]), box = $('map').getBoundingClientRect();
    const seen = se.x > 0 && nw.x < box.width - cardW && se.y > 0 && nw.y < box.height && Math.max(se.x - nw.x, se.y - nw.y) >= 12 && (!before || before.focus === S.focus);
    fit = seen ? 'stay' : pad(b, Math.max(0.08, 3 * Math.max(b[2] - b[0], b[3] - b[1])));
  }
  const target = fit === 'stay' ? painted.fit : JSON.stringify([fit || boxOf(F), cardW]);
  if (target !== painted.fit) {
    const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    map.fitBounds(JSON.parse(target)[0], {padding: {top: 36, bottom: 52, left: 28, right: 28 + cardW}, duration: before && !calm ? 600 : 0, maxZoom: 11});
    painted.fit = target;
  }
}
const inFocus = (z, F) => (zipRows(S.sc, S.est).get(z) || []).some((i) => F.has(C.s[i]));
const pad = (b, d) => [b[0] - d, b[1] - d, b[2] + d, b[3] + d];
const boxOfZips = (zs) => zs.length ? pad(zs.reduce((b, z) => [Math.min(b[0], ZBOX[z][0]), Math.min(b[1], ZBOX[z][1]), Math.max(b[2], ZBOX[z][2]), Math.max(b[3], ZBOX[z][3])], [180, 90, -180, -90]), 0.3) : null;

// ---- what a ZIP holds: its cells in the chosen scenario and estimate, one line per channel, class and people
function zipDetail(z, card) {
  const rows = (zipRows(S.sc, S.est).get(z) || []).filter((i) => C.s[i] >= 0), lines = new Map();
  for (const i of rows) {
    const key = [C.c[i], C.k[i], C.a[i], C.h[i]].join('|');
    const l = lines.get(key) || lines.set(key, {c: C.c[i], k: C.k[i], a: P.sets[C.a[i]], h: P.sets[C.h[i]], usd: 0, d: new Set()}).get(key);
    l.usd += C.u[i]; l.d.add(P.dists[C.d[i]]);
  }
  const all = [...lines.values()].sort((a, b) => CH_SHOW.indexOf(P.channels[a.c]) - CH_SHOW.indexOf(P.channels[b.c]) || b.usd - a.usd);
  const shown = all.filter((l) => S.ch === 'ALL' || P.channels[l.c] === S.ch), total = sum(all.map((l) => l.usd)), part = sum(shown.map((l) => l.usd));
  const st = rows.length ? ST[C.s[rows[0]]] : null;
  const people = (ks, none) => card ? whoAll(ks, none) : ks.length ? esc(ks.map(label).join(', ')) : none;
  const body = card ? shown.map((l) => `<div class="cell"><p><b><i class="sw" style="background:${clsColour(l.k)}"></i>${CH_LABEL[P.channels[l.c]]}: ${CLS[l.k].label.toLowerCase()}</b><span>${usd(l.usd)}</span></p>
      <p class="sub">Assigned: ${people(l.a, 'no one')}. Works it today: ${people(l.h, 'no one on the shortlist')}.</p></div>`).join('')
    : shown.map((l) => `<tr><td class="l">${CH_LABEL[P.channels[l.c]]}</td><td class="l"><i class="sw" style="background:${clsColour(l.k)}"></i>${CLS[l.k].label}</td>
    <td class="l">${people(l.a, 'no one')}</td><td class="l">${people(l.h, 'no one on the shortlist')}</td><td>${mm(l.usd)}</td></tr>`).join('');
  const rest = total - part > 0.5 ? `<p class="small">Plus ${usd(total - part)} in other channels: ${usd(total)} in this ZIP in all.</p>` : '';
  const head = `ZIP ${P.zips[z]}${st ? ', ' + esc(st.name) : ''}`;
  const table = !shown.length ? `<p class="small">No cell in ${chName()} here.</p>` : card ? body : `<table class="mini"><thead><tr><th class="l">Channel</th><th class="l">Class</th><th class="l">Assigned</th><th class="l">Works it today</th><th>$MM</th></tr></thead><tbody>${body}</tbody></table>`;
  if (!card) return `<h3>${head} <span class="sub">${usd(part)}, ${S.est} estimate, ${chName()}</span></h3>${table}${rest}`;
  return `<header><div><h2>${head}</h2><p class="sub">${usd(part)} of opportunity in ${chName()}, ${S.est} estimate, ${S.sc}</p></div><button class="close" data-go="sel=">Close</button></header>
    ${table}${rest}${st ? `<p class="small"><button class="link" data-go="focus=${st.id}&sel=">Focus on ${esc(st.name)}</button></p>` : ''}`;
}
function stateTip(s) {
  const asg = assignedOf(S.sc, S.est);
  const lines = CH_SHOW.filter((c) => c !== 'OPEN').map((c) => { const a = asg.get(P.channels.indexOf(c) + '|' + s) || []; return `<tr><td class="l">${CH_LABEL[c]}</td><td class="l">${a.length ? esc(a.map(label).join(', ')) : 'no one assigned'}</td></tr>`; }).join('');
  return `<h3>${esc(ST[s].name)}</h3><table class="mini"><tbody>${lines}</tbody></table>`;
}

// ---- the bar
function seg(id, key, options, disabled = () => false) {
  $(id).innerHTML = options.map(([v, text, title]) => `<button type="button" data-go="${key}=${esc(v)}" aria-pressed="${S[key] === v}"${disabled(v) ? ' disabled' : ''}${title ? ` title="${esc(title)}"` : ''}>${esc(text)}</button>`).join('');
}
function renderBar() {
  $('runline').textContent = P.run ? 'Run ' + P.run : 'Shortlist against today’s territories';
  $('c-products').textContent = P.products;
  seg('c-sc', 'sc', P.scenarios.map((s) => [s, s]));
  seg('c-est', 'est', P.ests.map((e) => [e, e, `The ${e} estimate of the same market. The estimates are never added.`]));
  seg('c-view', 'view', Object.entries(VIEWS));
  seg('c-ch', 'ch', [['ALL', CH_LABEL.ALL], ...CH_SHOW.map((c) => [c, CH_LABEL[c]])], (v) => S.view === 'terr' && v === 'ALL');
  const opt = (v, text) => `<option value="${esc(v)}"${S.focus === v ? ' selected' : ''}>${esc(text)}</option>`;
  const inDiv = new Set(P.regions.flatMap(([, divs]) => divs.flatMap(([, codes]) => codes)));
  $('c-focus').innerHTML = opt('CONUS', 'CONUS (48 states and DC)')
    + (P.regions.length ? `<optgroup label="Census regions">${P.regions.map(([r]) => opt(r, r)).join('')}</optgroup><optgroup label="Census divisions">${P.regions.flatMap(([, divs]) => divs.map(([d]) => opt(d, d))).join('')}</optgroup>` : '')
    + `<optgroup label="States">${ST.map((s) => opt(s.id, inDiv.has(s.id) || s.name !== s.id ? `${s.name} (${s.id})` : s.id)).join('')}</optgroup>`;
}

// ---- the totals: what is on screen, what it is a share of, its classes, the scenarios side by side
function renderTotals(D) {
  const a = area(), chain = [];
  for (let f = S.focus; f; f = AREAS.get(f).up) chain.unshift(f);
  const crumbs = chain.map((f, i) => i === chain.length - 1 ? `<span>${esc(AREAS.get(f).label)}</span>` : `<button class="link" data-go="focus=${esc(f)}">${esc(AREAS.get(f).label)}</button><span aria-hidden="true">›</span>`).join('');
  const row = (i) => `<button class="cl" data-go="cls=${i}" aria-pressed="${S.cls === String(i)}" title="${esc(CLS[i].help)} Press to show only these ZIPs.">
    <i style="background:${clsColour(i)}"></i><span>${CLS[i].label}</span><b>${usd(D.cls[i])}</b><em>${pct(D.cls[i], D.screen)}</em></button>`;
  const group = (text, v) => `<div class="cl group"><span>${text}</span><b>${usd(v)}</b><em>${pct(v, D.screen)}</em></div>`;
  const stack = `<div class="stack" role="img" aria-label="Shares of the classes on screen">${CLS.map((c, i) => `<i style="width:${100 * D.cls[i] / (D.screen || 1)}%;background:${clsColour(i)}"></i>`).join('')}</div>`;
  const ck = check(S.sc, S.est);
  const tie = ck.bad.length ? `<p class="check bad">Does not tie to the run’s summary. ${esc(ck.bad.slice(0, 3).join('; '))}${ck.bad.length > 3 ? `; and ${ck.bad.length - 3} more` : ''}</p>`
    : ck.summary ? `<p class="check"><span aria-hidden="true">✓</span><span>Ties to the run’s ${S.est} summary: ${usd(ck.total)} in ${S.sc}, class by class${ck.pairs ? ', and pair by pair' : ''}.</span></p>`
    : `<p class="check">The run has no summary rows for ${S.est} to tie to; the cells add up to ${usd(ck.total)}.</p>`;
  $('totals').innerHTML = `<nav class="crumbs" aria-label="Focus">${crumbs}</nav>
    <p class="where">On screen: ${esc(a.label)}, ${chName()}</p>
    <p class="big"><span class="capsule">${usd(D.screen)}</span><span class="of">of opportunity, ${S.est} estimate, ${S.sc}</span></p>
    ${S.ch === 'ALL' ? '' : `<div class="rung"><p><span><b>${pct(D.screen, D.focus)}</b> of ${esc(a.label)}, all channels</span><span>${usd(D.focus)}</span></p><div class="track"><i class="on" style="width:${100 * D.screen / (D.focus || 1)}%"></i></div></div>`}
    <div class="rung"><p><span><b>${pct(D.screen, D.est)}</b> of the ${S.est} estimate</span><span>${usd(D.est)}</span></p>
      <div class="track"><i style="width:${100 * D.focus / (D.est || 1)}%"></i><i class="on" style="width:${100 * D.screen / (D.est || 1)}%"></i></div></div>
    ${D.noState > 0.5 || D.noShape > 0.5 ? `<p class="small">${D.noState > 0.5 ? `${usd(D.noState)} of the estimate sits on cells with no state: in no focus, on no map. ` : ''}${D.noShape > 0.5 ? `${usd(D.noShape)} on screen is in ZIPs with no map shape.` : ''}</p>` : ''}
    <div class="classes">${stack}
      <div class="head"><span>Class</span><span>$</span><span>of screen</span></div>
      ${row(K.COVERED)}${group('To bargain', D.group.bargain)}${BARGAIN.map(row).join('')}${group('To fill', D.group.fill)}${FILL.map(row).join('')}
      <div class="cl total"><span>On screen</span><b>${usd(D.screen)}</b><em>${pct(D.screen, D.screen)}</em></div>
    </div>${tie}${renderScenarios(D)}`;
}
function renderScenarios(D) {
  if (P.scenarios.length < 2) return '';
  const per = P.scenarios.map((sc) => sc === S.sc ? D.group : compute(sc, true).group);
  const now = per[P.scenarios.indexOf(S.sc)];
  const cell = (g, k) => `<td${Math.abs(g[k] - now[k]) > 0.5 ? ' class="chg"' : ''}>${usd(g[k])}</td>`;
  return `<div class="scen"><h3>Scenarios side by side <span class="note">violet: differs from ${S.sc}</span></h3>
    <table><thead><tr><th class="l"></th><th>Covered</th><th>To bargain</th><th>To fill</th></tr></thead><tbody>
    ${P.scenarios.map((sc, i) => `<tr tabindex="0" data-go="sc=${sc}" aria-selected="${sc === S.sc}"><td class="l">${sc}</td>${cell(per[i], 'covered')}${cell(per[i], 'bargain')}${cell(per[i], 'fill')}</tr>`).join('')}</tbody></table>
    <label class="tick"><input type="checkbox" id="c-diff"${S.diff ? ' checked' : ''}>Show only the ZIPs where the scenarios differ</label></div>`;
}

// ---- tables: sortable, a row drives the map
const SORT = {pairs: ['usd', -1], fill: ['fill', -1], people: ['load', -1]};
function sorted(id, rows) { const [key, dir] = SORT[id]; return rows.sort((a, b) => (typeof a[key] === 'string' ? a[key].localeCompare(b[key], 'en', {numeric: true}) : (a[key] ?? -Infinity) - (b[key] ?? -Infinity)) * dir); }
function th(id, key, text, left, rows, title) { const [k, dir] = SORT[id]; return `<th${left ? ' class="l"' : ''}${rows ? ` rowspan="${rows}"` : ''}${k === key ? ` aria-sort="${dir < 0 ? 'descending' : 'ascending'}"` : ''}><button type="button" data-sort="${id}:${key}"${title ? ` title="${esc(title)}"` : ''}>${text}</button></th>`; }

function renderPairs(D) {
  const sel = SEL().people || [], a = area();
  const rows = sorted('pairs', [...D.pairs.values()].map((p) => ({...p, ch: CH_LABEL[P.channels[p.c]], an: label(p.a), bn: label(p.b), n: p.zips.size, share: p.usd})));
  const one = S.ch !== 'ALL';
  const body = rows.map((p) => `<tr tabindex="0" data-go="sel=${P.keys[p.a]}-${P.keys[p.b]}" aria-selected="${sel.length === 2 && sel[0] === p.a && sel[1] === p.b}">
    ${one ? '' : `<td class="l">${p.ch}</td>`}<td class="l nm" title="${esc(p.an)}">${esc(p.an)}</td><td class="l nm" title="${esc(p.bn)}">${esc(p.bn)}</td><td>${int(p.n)}</td><td>${mm(p.usd)}</td><td>${pct(p.usd, D.focus)}</td></tr>`).join('');
  $('t-pairs').innerHTML = `<header><h2>Overlaps to bargain</h2><p class="note">${esc(a.label)}, ${chName()}, ${S.est} estimate</p><p class="note more">Two shortlisted people work the same ZIPs. Pairs do not add up: a cell with three holders is in three pairs. Shares are of ${esc(a.label)}, all channels.</p></header>
    <div class="scroll">${rows.length ? `<table><thead><tr>${one ? '' : th('pairs', 'ch', 'Channel', 1)}${th('pairs', 'an', 'Person', 1)}${th('pairs', 'bn', 'and person', 1)}${th('pairs', 'n', 'ZIPs')}${th('pairs', 'usd', '$MM')}${th('pairs', 'share', `of ${esc(a.label)}`, 0, 0, `The pair’s $ as a share of ${a.label}, all channels`)}</tr></thead>
    <tbody>${body}</tbody><tfoot><tr><td class="l" colspan="${one ? 3 : 4}">Overlap class on screen (each cell once)</td><td>${mm(D.cls[K.OVERLAP])}</td><td>${pct(D.cls[K.OVERLAP], D.focus)}</td></tr></tfoot></table>`
    : `<p class="empty">No two shortlisted people work the same ZIP in ${esc(a.label)}, ${chName()}, under ${S.sc}.</p>`}</div>`;
}
function renderFill(D) {
  const a = area(), [gh, gu, oh, ou] = [K['GAP (HELD TODAY)'], K['GAP (UNHELD)'], K['OPEN SEAT HELD'], K['OPEN SEAT UNHELD']];
  const rows = sorted('fill', [...D.st.entries()].map(([s, c]) => ({s, id: ST[s].id, gh: c[gh], gu: c[gu], oh: c[oh], ou: c[ou], fill: c[gh] + c[gu] + c[oh] + c[ou], all: sum(c)})).filter((r) => r.fill > 0.5)
    .map((r) => ({...r, share: r.fill / r.all})));
  const max = Math.max(1, ...rows.map((r) => r.fill)), tot = (k) => sum(rows.map((r) => r[k]));
  const bar = (r) => `<div class="stack" style="width:${Math.max(2, 100 * r.fill / max)}%">${[gu, gh, ou, oh].map((k, j) => `<i style="width:${100 * [r.gu, r.gh, r.ou, r.oh][j] / r.fill}%;background:${CLS[k].color}"></i>`).join('')}</div>`;
  const body = rows.map((r) => `<tr tabindex="0" data-go="focus=${r.id}&sel=" aria-selected="${S.focus === r.id}"><td class="l">${esc(ST[r.s].name)}</td><td>${mm(r.fill)}</td><td class="bar-cell">${bar(r)}</td>
    <td>${mm(r.gh)}</td><td>${mm(r.gu)}</td><td>${mm(r.oh)}</td><td>${mm(r.ou)}</td><td>${pct(r.fill, r.all)}</td></tr>`).join('');
  $('t-fill').innerHTML = `<header><h2>To fill, by state</h2><p class="note">${esc(a.label)}, ${chName()}, ${S.est} estimate, $MM</p><p class="note more">Gaps: assigned, and no shortlisted person works it. Open seats: no one is assigned.</p></header>
    <div class="scroll">${rows.length ? `<table><thead><tr>${th('fill', 'id', 'State', 1, 2)}${th('fill', 'fill', 'To fill', 0, 2)}<th rowspan="2"></th><th colspan="2" class="grp">Gap</th><th colspan="2" class="grp">Open seat</th>${th('fill', 'share', 'of the state', 0, 2, 'To fill as a share of the state’s $ on screen')}</tr>
    <tr>${th('fill', 'gh', 'held today')}${th('fill', 'gu', 'unheld')}${th('fill', 'oh', 'held today')}${th('fill', 'ou', 'unheld')}</tr></thead>
    <tbody>${body}</tbody><tfoot><tr><td class="l">${esc(a.label)}</td><td>${mm(tot('fill'))}</td><td></td><td>${mm(tot('gh'))}</td><td>${mm(tot('gu'))}</td><td>${mm(tot('oh'))}</td><td>${mm(tot('ou'))}</td><td>${pct(tot('fill'), D.screen)}</td></tr></tfoot></table>`
    : `<p class="empty">Nothing to fill in ${esc(a.label)}, ${chName()}, under ${S.sc}: every cell is covered or to bargain.</p>`}</div>`;
}

// ---- the card: the selected ZIP, person or pair; else the focused state; else the people in focus
const rowOf = (table, sc, k) => { const bit = 1 << P.scenarios.indexOf(sc), e = P.ests.indexOf(S.est); return table.find((r) => r[0] & bit && r[1] === e && r[2] === k); };
const gauge = (ratio) => `<span class="gauge" aria-hidden="true"><i style="left:${Math.max(0, Math.min(100, 50 + 50 * Math.log2(ratio) / 3))}%"></i></span>`;   // a ratio: log scale, 1/8 to 8, 1 in the middle
const loadWord = (r) => r > 1.25 ? 'heavy for its area' : r < 0.8 ? 'light for its area' : 'right-sized for its area';
function peopleRows() {
  const bit = 1 << P.scenarios.indexOf(S.sc), e = P.ests.indexOf(S.est), F = area().states;
  return P.people.filter((r) => r[0] & bit && r[1] === e).map((r) => {
    const ch = CH_OF_ROLE[r[4]] || '', states = r[5] ? r[5].split(' ') : [], ld = rowOf(P.load, S.sc, r[2]);
    return {k: r[2], who: label(r[2]), ch, chn: CH_LABEL[ch] || r[4], firm: r[3], states, usd: ld ? ld[5] : null, load: ld ? ld[9] : null};
  }).filter((p) => (S.ch === 'ALL' || S.ch === 'OPEN' || p.ch === S.ch) && (S.focus === 'CONUS' || p.states.some((s) => F.has(SIX.get(s)))));       // no one is assigned to an open seat: everyone
}
function renderPeople(heading = true) {
  const rows = sorted('people', peopleRows()), a = area();
  const sel = SEL().people || [];
  const body = rows.map((p) => `<tr aria-selected="${sel.includes(p.k)}"><td class="l">${who(p.k, S.view === 'terr')}<br><span class="sub">${p.chn}${p.firm ? ', ' + esc(p.firm) : ''}: ${esc(p.states.join(' ')) || 'no state'}</span></td>
    <td>${p.usd === null ? '–' : mm(p.usd)}</td><td>${p.load === null ? '–' : p.load.toFixed(2) + gauge(p.load)}</td></tr>`).join('');
  return `${heading ? `<header><div><h2>People</h2><p class="sub">${rows.length} on the shortlist with states in ${esc(a.label)}${S.ch === 'ALL' || S.ch === 'OPEN' ? '' : ', ' + chName()}.${S.ch === 'OPEN' ? ' No one is assigned to an open seat.' : ''}${rows.length ? ' Pick one to see their territory.' : ''}</p></div></header>` : ''}
    ${rows.length ? `<table><thead><tr>${th('people', 'who', 'Person, channel, firm: states', 1)}${th('people', 'usd', '$MM')}${th('people', 'load', 'Load')}</tr></thead><tbody>${body}</tbody></table>
    <p class="small">$MM: the person’s share of their channel’s ${S.est} opportunity, a split state shared. Load: that $ over the $ expected for the area they cover; 1 is right-sized, the band is 0.8 to 1.25. Reported, never a gate.</p>` : ''}`;
}
function renderPerson(k, D) {
  const r = rowOf(P.people, S.sc, k), ld = rowOf(P.load, S.sc, k), head = `<header><div><h2>${esc(label(k))}</h2>`, close = `</div><button class="close" data-go="sel=">Close</button></header>`;
  if (!r) return `${head}<p class="sub">Not on the shortlist in ${S.sc}: they have no row in this scenario. They may still work ZIPs today; those stay bright on the map.</p>${close}`;
  const ch = CH_OF_ROLE[r[4]], [asg, cov, ovl, gap, hba, away] = r.slice(6, 12), chTotal = sum([...D.rows].filter((i) => P.channels[C.c[i]] === ch).map((i) => C.u[i]));
  const mine = new Map();
  for (const i of D.rows) if (C.s[i] >= 0 && C.k[i] === K.OVERLAP && P.sets[C.h[i]].includes(k)) addPairs(mine, i);
  const pairs = [...mine.values()].filter((p) => p.a === k || p.b === k).sort((a, b) => b.usd - a.usd);
  const gaps = new Map();
  for (const i of D.rows) if (C.s[i] >= 0 && P.channels[C.c[i]] === ch && CLS[C.k[i]].id.startsWith('GAP') && P.sets[C.a[i]].includes(k)) gaps.set(C.s[i], (gaps.get(C.s[i]) || 0) + C.u[i]);
  return `${head}<p class="sub">${CH_LABEL[ch] || esc(r[4])}${r[3] ? ', ' + esc(r[3]) : ''}. Assigned ${r[5] ? esc(r[5].split(' ').join(', ')) : 'no state'} in ${S.sc}.</p>${close}
    ${asg === null ? '' : `<h3>In their assigned states <span class="note">${S.est} estimate; a split state’s cells count for each assignee</span></h3>
    <p>Assigned to them: <b>${usd(asg)}</b>, ${pct(asg, chTotal)} of the ${CH_LABEL[ch]} channel. As shares of that:</p>
    <div class="kv">${[['Covered: they work it', cov], ['Overlap: so does another', ovl], ['Gap: no shortlisted person does', gap], ['Held by another only', hba]].map(([t, v]) => v === null ? '' : `<span class="in">${t}</span><span>${usd(v)}</span><span>${pct(v, asg)}</span>`).join('')}</div>
    ${away ? `<p>Works today outside their states: <b>${usd(away)}</b>.</p>` : ''}`}
    ${ld && ld[9] !== null ? `<h3>Load for the area: ${ld[9].toFixed(2)}, ${loadWord(ld[9])}</h3>
    <div class="scale">${gauge(ld[9])}<div aria-hidden="true">${[0.25, 0.5, 1, 2, 4].map((v) => `<span style="left:${50 + 50 * Math.log2(v) / 3}%">${v}</span>`).join('')}</div></div>
    <p class="small">${usd(ld[5])} assigned (a split state shared) over ${usd(ld[8])} expected for ${int(ld[4])} km²: ${usd(ld[6])} × (area ÷ the channel’s median ${int(ld[7])} km²)^${P.beta}. 1 is right-sized; the band is 0.8 to 1.25.</p>` : ''}
    <h3>Overlaps with <span class="note">every state and channel</span></h3>${pairs.length ? `<div class="kv">${pairs.map((p) => `<span>${who(p.a === k ? p.b : p.a)}</span><span>${usd(p.usd)}</span><span><button class="link" data-go="sel=${P.keys[p.a]}-${P.keys[p.b]}">${p.zips.size} ZIPs</button></span>`).join('')}</div>` : `<p class="sub">No one in ${S.sc}.</p>`}
    <h3>Gaps in their states <span class="note">${CH_LABEL[ch] || ''} cells assigned to them</span></h3>${gaps.size ? `<div class="kv">${[...gaps.entries()].sort((a, b) => b[1] - a[1]).map(([s, v]) => `<span><button class="link" data-go="focus=${ST[s].id}">${esc(ST[s].name)}</button></span><span>${usd(v)}</span><span></span>`).join('')}</div>` : `<p class="sub">None.</p>`}`;
}
function renderPair(a, b, D) {
  const p = [...D.pairs.values()].filter((p) => p.a === Math.min(a, b) && p.b === Math.max(a, b)).sort((x, y) => y.usd - x.usd)[0];
  const head = `<header><div><h2>${esc(P.keys[a])} and ${esc(P.keys[b])}</h2>`, close = `</div><button class="close" data-go="sel=">Close</button></header>`;
  if (!p) return `${head}<p class="sub">They do not work the same ZIP in ${esc(area().label)}, ${chName()}, under ${S.sc}.</p>${close}<p>${who(a)} · ${who(b)}</p>`;
  return `${head}<p class="sub">Both work ${int(p.zips.size)} ZIPs holding ${usd(p.usd)} in ${esc(area().label)}, ${CH_LABEL[P.channels[p.c]]}, ${S.est} estimate: to bargain.</p>${close}
    <p>${who(a)} · ${who(b)}</p><h3>By state</h3><div class="kv">${[...p.states.entries()].sort((x, y) => y[1] - x[1]).map(([s, v]) => `<span><button class="link" data-go="focus=${ST[s].id}">${esc(ST[s].name)}</button></span><span>${usd(v)}</span><span>${pct(v, p.usd)}</span>`).join('')}</div>`;
}
function renderState(s, D) {
  const asg = assignedOf(S.sc, S.est), bit = 1 << P.scenarios.indexOf(S.sc), e = P.ests.indexOf(S.est), open = P.channels.indexOf('OPEN');
  const lines = CH_SHOW.filter((c) => c !== 'OPEN').map((c) => `<span>${CH_LABEL[c]}</span><span>${whoAll(asg.get(P.channels.indexOf(c) + '|' + s) || [], 'no one assigned')}</span><span></span>`).join('');
  const held = new Map(); let seat = 0;
  for (const i of D.rows) if (C.s[i] === s && C.c[i] === open) { seat += C.u[i]; for (const k of P.sets[C.h[i]]) held.set(k, (held.get(k) || 0) + C.u[i]); }
  const fit = P.seat.filter((r) => r[0] & bit && r[1] === e && r[2] === ST[s].id).sort((x, y) => x[5] - y[5]);
  const cand = (kind) => fit.filter((r) => r[3] === kind).slice(0, 3).map((r) => `<span>${r[5]}. ${who(r[4])}</span><span>${kind === 'NEIGHBOUR' ? (r[6] ? 'borders it' : '') : ''}</span><span>${r[8] ? 'load ' + esc(r[8]) : ''}</span>`).join('');
  return `<header><div><h2>${esc(ST[s].name)}</h2><p class="sub">${esc(AREAS.get(ST[s].id).up)}${AREAS.get(AREAS.get(ST[s].id).up).up ? ', ' + esc(AREAS.get(AREAS.get(ST[s].id).up).up) : ''}. Who is assigned in ${S.sc}:</p></div></header>
    <div class="kv">${lines}</div>
    ${seat > 0.5 ? `<h3>Open seat: ${usd(seat)} with no one assigned <span class="note">${S.est} estimate</span></h3>
      <p class="sub">Worked today by shortlisted people (a ZIP with two counts for both):</p><div class="kv">${[...held.entries()].sort((x, y) => y[1] - x[1]).slice(0, 6).map(([k, v]) => `<span>${who(k)}</span><span>${usd(v)}</span><span>${pct(v, seat)}</span>`).join('') || '<span>No one</span><span></span><span></span>'}</div>
      ${fit.length ? `<h3>Who fits the seat <span class="note">the run’s ranking; ranks only, no sales figures</span></h3><p class="sub">Neighbours, by what they would gain against their book; load if they took it:</p><div class="kv">${cand('NEIGHBOUR') || '<span>None</span><span></span><span></span>'}</div>
      <p class="sub" style="margin-top:6px">People with a territory in it today:</p><div class="kv">${cand('HOLDER') || '<span>None</span><span></span><span></span>'}</div>` : ''}` : ''}
    <h3>People with states here</h3>`;
}
function renderCard(D) {                         // the selection's card floats on the map, so the totals beside it never scroll away
  const sel = SEL();
  const html = sel.zip !== undefined ? (sel.zip >= 0 ? zipDetail(sel.zip, true) : `<header><div><h2>ZIP ${esc(sel.code)}</h2><p class="sub">No opportunity cell in this run.</p></div><button class="close" data-go="sel=">Close</button></header>`)
    : sel.people ? (sel.people.length === 2 ? renderPair(sel.people[0], sel.people[1], D) : renderPerson(sel.people[0], D)) : '';
  $('card').hidden = !html;
  $('card').innerHTML = html;
  $('detail').innerHTML = (area().kind === 'state' ? renderState([...area().states][0], D) : '') + renderPeople(area().kind !== 'state')
    + `<p class="about">Map drawn with MapLibre GL JS 6.19.0, embedded. <button class="link" id="licence-open">Its licence</button></p>`;
}
function renderChips(D) {
  const sel = SEL(), chips = [];
  if (sel.people) chips.push([`sel=`, sel.people.length === 2 ? `Where ${P.keys[sel.people[0]]} and ${P.keys[sel.people[1]]} overlap` : `ZIPs ${label(sel.people[0])} is assigned or works today`]);
  if (sel.zip >= 0) chips.push(['sel=', `ZIP ${sel.code}`]);
  if (S.cls !== '') chips.push(['cls=', `Only ${CLS[+S.cls].label.toLowerCase()}`]);
  if (S.diff) chips.push(['diff=', 'Only ZIPs where the scenarios differ']);
  const by = S.view === 'terr' ? `<div class="seg light" role="group" aria-label="Colour by">${[['assigned', 'Who is assigned'], ['held', 'Who works it today']].map(([v, t]) => `<button type="button" data-go="by=${v}" aria-pressed="${S.by === v}"${v === 'assigned' && S.ch === 'OPEN' ? ' disabled' : ''}>${t}</button>`).join('')}</div>` : '';
  $('chips').innerHTML = by + chips.map(([goTo, text]) => `<button class="chip" data-go="${goTo}" title="Clear">${esc(text)}<span aria-hidden="true">×</span></button>`).join('');
  $('caption').textContent = S.view === 'fill' ? `A ZIP takes the colour of its largest class still to fill (${chName()}). With nothing to fill it is light blue if any of it is to bargain, else grey: covered. White: no opportunity cell.`
    : S.view === 'gap' ? `A ZIP takes the colour of its class with the most $ (${chName()}). White: no cell in ${chName()}.`
    : S.by === 'assigned' ? `${CH_LABEL[S.ch]}: each ZIP in the colour of the person assigned to its state; a state with one assignee is tinted whole. Pale violet: a split state’s ZIP that not exactly one of its assignees works today.`
    : `${CH_LABEL[S.ch]}: each ZIP in the colour of the shortlisted person who works it today. Dark: two or more do. Grey: none does.`;
}

// ---- drawing it all
let NOW = null;
function render(before) {
  const at = document.activeElement, home = at && at.closest('[id]'), mark = at && (at.dataset.go !== undefined ? `[data-go="${CSS.escape(at.dataset.go)}"]` : at.dataset.sort ? `[data-sort="${at.dataset.sort}"]` : null);
  NOW = compute();
  renderBar(); renderTotals(NOW); renderPairs(NOW); renderFill(NOW); renderCard(NOW); renderChips(NOW);
  if (mark && home && home.id && !at.isConnected) $(home.id)?.querySelector(mark)?.focus();       // the panels were redrawn: keep the keyboard's place
  paint(before || null);
  document.title = `Territory coverage: ${area().label}, ${S.sc}`;
}
function find(q) {
  q = q.trim();
  const say = (t) => { $('found').textContent = t; clearTimeout(find.t); find.t = setTimeout(() => { $('found').textContent = ''; }, 5000); };
  if (!q) return;
  const key = P.keys.find((k) => k.toLowerCase() === q.toLowerCase().split(' ')[0]) || P.keys.find((k) => (P.names[k] || '').toLowerCase().includes(q.toLowerCase()));
  const st = ST.find((s) => s.id.toLowerCase() === q.toLowerCase() || s.name.toLowerCase() === q.toLowerCase());
  if (/^\d{5}$/.test(q)) { if (P.zips.includes(q)) go({sel: q}); else return say(`ZIP ${q} has no opportunity cell in this run.`); }
  else if (key) go({sel: key});
  else if (st) go({focus: st.id, sel: ''});
  else return say(`Nothing matches “${q}”. Type a 5-digit ZIP, a key such as ${P.keys[0] || 'R1'}${Object.keys(P.names).length ? ', a name' : ''} or a state.`);
  $('c-find').value = '';
  say('');
}
document.addEventListener('click', (e) => {
  const sortBy = e.target.closest('[data-sort]'), el = e.target.closest('[data-go]');
  if (e.target.id === 'licence-open') { $('licence-text').textContent = $('licence').textContent; $('licence-box').showModal(); }
  else if (sortBy) { const [id, key] = sortBy.dataset.sort.split(':'); SORT[id] = [key, SORT[id][0] === key ? -SORT[id][1] : -1]; render(S); }
  else if (el && !el.disabled) go(Object.fromEntries(new URLSearchParams(el.dataset.go)));
});
document.addEventListener('keydown', (e) => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('tr[data-go]')) { e.preventDefault(); e.target.click(); }
  if (e.key === 'Escape' && (S.sel || S.cls || S.diff) && !$('licence-box').open) go({sel: '', cls: '', diff: ''});
});
document.addEventListener('change', (e) => {
  if (e.target.id === 'c-focus') go({focus: e.target.value, sel: ''});
  if (e.target.id === 'c-diff') go({diff: e.target.checked ? '1' : ''});
  if (e.target.id === 'c-find') find(e.target.value);
});
window.addEventListener('hashchange', () => { const before = {...S}; readHash(); render(before); });
$('find-list').innerHTML = P.keys.map((k) => `<option value="${esc(k)}">${esc(P.names[k] || '')}</option>`).join('');
$('c-find').placeholder = Object.keys(P.names).length ? 'ZIP, key, name, state' : 'ZIP, key or state';
readHash();
render(null);
startMap().catch((err) => {
  document.body.dataset.map = 'failed';
  $('map').innerHTML = `<div class="nomap"><p><b>The map could not start here.</b></p><p>Save the file, then open it in Chrome or Edge (not in a Teams or email preview).</p>
    <p class="sub">The totals and tables on this page are complete without it. Reason: ${esc(err.message || err)}.</p></div>`;
});
