// tools/maps/dashboard.js (issue #153): the dashboard's page.  It reads the data dashboard.py embedded (P), keeps its state in the
// URL hash (S), and computes every number on screen from the cells of the chosen view, scenario and estimate (compute), so the map,
// the totals and the tables cannot disagree.  Three views (S.of): the preliminary assignment ("new": 07's classes as the page's four,
// P.classes), and each firm's territories today (a ZIP's holder is the holder of firm x ZIP x channel, by status or by person).
// A person is an index into P.keys; names, when the run gave any, are shown next to keys.
const $ = (id) => document.getElementById(id);
const P = JSON.parse($('data').textContent);
const C = P.cells, NC = C.m.length, NZ = P.zips.length, NSHAPE = P.zipGeom.length;
const EVERY = (1 << P.scenarios.length) - 1;
const CLS = P.classes, NK = CLS.length, DET = P.detail, J = Object.fromEntries(DET.map((d, i) => [d, i]));       // the page's four classes over 07's seven
const KOF = [];
CLS.forEach((c, k) => c.of.forEach((j) => { KOF[j] = k; }));
C.k = C.j.map((j) => KOF[j]);
const STATUS = P.status, NOONE = STATUS.length - 1, T = P.today, TC = P.tc, FIRMS = T.firms, TCH = T.chans;
const CH_SHOW = ['NATIONAL', 'WH', 'REGIONAL', 'OPEN'].filter((c) => P.channels.includes(c));     // the priority chain's order
const CH_LABEL = {ALL: 'All', NATIONAL: 'National', WH: 'WH', REGIONAL: 'Regional', OPEN: 'Open seats', FI: 'FI'};
const CH_OF_ROLE = Object.fromEntries(Object.entries(P.roleOf).map(([c, r]) => [r, c]));
const ROLE_WORD = {NATIONAL: 'national', WIFI: 'regional', WH: 'WH', FI: 'FI'};
const VIEWS = {fill: 'What changes', gap: 'Largest class', terr: 'Person'};
const TBY = {status: 'Status', person: 'Person'};
const TABS = {people: 'Wholesalers', pairs: 'Contested pairs', states: 'By state'};
const SHARED = '#E0E0FB', CONTESTED = '#20113E', NOBODY = '#F2F2F2';                            // by person: a split not held by one assignee, two or more holders, no holder
const ST = P.states, SIX = new Map(ST.map((s, i) => [s.id, i]));
const HAS_SALES = P.sales.k.length > 0;

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

// ---- state: the URL hash, only what differs from the default (the estimate's default is the view's own firm)
const DEF = {of: 'new', sc: P.scenarios[0], est: P.ests[0], view: 'fill', ch: 'ALL', tch: TCH[0] || '', tby: 'status', focus: 'CONUS', sel: '', by: 'assigned', cls: '', diff: '', sold: '', tab: 'people'};
const S = {...DEF};
const defEst = (of) => P.ests.includes(of) ? of : P.ests[0];
const VALID = {of: (v) => v === 'new' || FIRMS.includes(v), sc: (v) => P.scenarios.includes(v), est: (v) => P.ests.includes(v), view: (v) => v in VIEWS,
  ch: (v) => v === 'ALL' || CH_SHOW.includes(v), tch: (v) => TCH.includes(v), tby: (v) => v in TBY, focus: (v) => AREAS.has(v), by: (v) => v === 'assigned' || v === 'held',
  cls: (v) => v === '' || CLS[+v] !== undefined, diff: (v) => v === '' || v === '1', sold: (v) => v === '' || v === '1' && HAS_SALES, tab: (v) => v in TABS,
  sel: (v) => v === '' || /^\d{5}$/.test(v) || v.split('-').every((k) => P.keys.includes(k)) && v.split('-').length <= 2};
const today = () => S.of !== 'new';
function setState(patch) {
  for (const [k, v] of Object.entries(patch)) if (k in DEF) S[k] = VALID[k](v) ? v : DEF[k];
  if (today()) {                                // a firm's territories today: no pairs, no scenario differences
    if (S.tab === 'pairs') S.tab = 'people';
    if (S.sel.includes('-')) S.sel = '';
    S.diff = '';
  } else if (S.view === 'terr') {               // a territory map is one channel's: no "All"; no one is assigned to an open seat
    if (S.ch === 'ALL') S.ch = CH_SHOW.includes('REGIONAL') ? 'REGIONAL' : CH_SHOW[0];
    if (S.ch === 'OPEN') S.by = 'held';
  }
}
function readHash() {
  const q = Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
  Object.assign(S, DEF);
  setState(q);
  if (!('est' in q)) S.est = defEst(S.of);
}
function writeHash() {
  const q = new URLSearchParams(Object.entries(S).filter(([k, v]) => v !== (k === 'est' ? defEst(S.of) : DEF[k])));
  const h = q.toString();
  if (location.hash.slice(1) !== h) history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
}
function go(patch) {                             // one door for every control: change the state, redraw
  const before = {...S};
  for (const k of ['sel', 'cls', 'diff', 'sold']) if (k in patch && patch[k] === S[k] && Object.keys(patch).length === 1) patch[k] = '';      // a second press lets go
  if ('of' in patch && patch.of !== S.of) patch = {est: defEst(patch.of), cls: '', ...patch};       // another view: its own firm's estimate, no class kept
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
const dots = () => today() ? S.tby === 'person' : S.view === 'terr';          // the map is coloured by person: a person's colour goes with their name
const dot = (k) => dots() ? `<i class="dot" style="background:${(today() ? P.tcolour : P.colour)[k]}"></i>` : '';
const who = (k) => `<button class="who" data-go="sel=${esc(P.keys[k])}">${dot(k)}${esc(label(k))}</button>`;
const whoAll = (ks, none) => ks.length ? ks.map((k) => who(k)).join(', ') : none;
const chName = () => today() ? `${S.of} ${S.tch} territories today` : S.ch === 'ALL' ? 'all channels' : CH_LABEL[S.ch] + (S.ch === 'OPEN' ? '' : ' channel');
const scName = (sc = S.sc) => P.labels[sc] || sc;
const area = () => AREAS.get(S.focus);
const sum = (a) => { let t = 0; for (const v of a) t += v; return t; };
const add = (m, k, v) => m.set(k, (m.get(k) || 0) + v);
const list = (m, k) => m.get(k) || m.set(k, []).get(k);
const memo = (fn) => { const m = new Map(); return (...a) => { const k = a.join('|'); if (!m.has(k)) m.set(k, fn(...a)); return m.get(k); }; };
const bitOf = (sc) => 1 << P.scenarios.indexOf(sc);

// ---- the roster and seat plan 1 of a scenario, and a person's status against them
const rosterOf = memo((sc) => {                   // key -> {src, on (kept, with a role), role}: today's holders, then the people on the sheet with no WH or FI territory
  const bit = bitOf(sc), m = new Map();
  for (const r of P.roster) if (r[0] & bit) m.set(r[1], {src: r[2], on: r[3] === 'Y' && r[4] !== '', role: r[4]});
  for (const r of P.people) if (r[0] & bit && !m.has(r[2])) m.set(r[2], {src: r[3], on: true, role: r[4]});
  return m;
});
const planOf = memo((sc, est) => {                // seat plan 1: who is brought back (readd) or extended (ext) into which seats, and the seats left vacant
  const bit = bitOf(sc), e = P.ests.indexOf(est), out = {readd: new Map(), ext: new Map(), vacant: [], seat: new Map()};
  for (const r of P.plan) {
    if (!(r[0] & bit) || r[1] !== e) continue;
    out.seat.set(r[2], r);
    if (r[4] < 0) out.vacant.push(r[2]); else list(r[3] === 'READD' ? out.readd : out.ext, r[4]).push(r[2]);
  }
  return out;
});
const seatsOf = (k) => { const pl = planOf(S.sc, S.est); return pl.readd.get(k) || pl.ext.get(k) || []; };
function statusOf(k) {                            // 0 on the roster (that wins: an extending neighbour is on it), 1 proposed by seat plan 1, 2 not on the roster
  const r = rosterOf(S.sc).get(k);
  return r && r.on ? 0 : seatsOf(k).length ? 1 : 2;
}
function statusWord(k, long) {
  const r = rosterOf(S.sc).get(k), st = statusOf(k), seats = seatsOf(k).join(', ');
  if (st === 0) return `on the roster, ${ROLE_WORD[r.role] || r.role}` + (long && seats ? `; seat plan 1 extends them into ${seats}` : '');
  return st === 1 ? 'proposed' + (long ? `: seat plan 1 brings them back for ${seats}` : '') : 'not on the roster';
}

// ---- today's territories (a firm's holders of each ZIP in a channel) and the 2025 sales (seller -> ZIP -> $)
const holders = (H, z) => H && H[z] >= 0 ? P.sets[H[z]] : [];
const byState = memo((firm, ch) => {              // state -> person -> the ZIPs they hold there
  const m = new Map(), H = T.h[firm + '|' + ch];
  for (let z = 0; z < NZ; z++) for (const k of holders(H, z)) add(m.get(P.zst[z]) || m.set(P.zst[z], new Map()).get(P.zst[z]), k, 1);
  return m;
});
const SALES = new Map();
for (let i = 0; i < P.sales.k.length; i++) (SALES.get(P.sales.k[i]) || SALES.set(P.sales.k[i], new Map()).get(P.sales.k[i])).set(P.sales.z[i], P.sales.v[i]);
const sold = (k, z) => (SALES.get(k)?.get(z) || 0) > 0;          // "sells there": any sale above $0
const soldIn = memo(() => { const m = new Map(); for (const [k, zs] of SALES) for (const [z, v] of zs) if (v > 0) list(m, z).push([k, v]); return m; });
function salesOf(k, mine, F) {                    // a person's sales in the focus: all, in their own territory (mine(z)), outside it, and the ZIPs where they sold
  const out = {sales: 0, inside: 0, outside: 0, nsold: 0};
  for (const [z, v] of SALES.get(k) || []) {
    if (!F.has(P.zst[z])) continue;
    out.sales += v;
    if (mine(z)) out.inside += v; else out.outside += v;
    if (v > 0) out.nsold++;
  }
  return out;
}

// ---- the cells of a scenario and estimate, and what is read off them
const rowsOf = memo((sc, est) => { const bit = bitOf(sc), e = P.ests.indexOf(est); return Int32Array.from({length: NC}, (_, i) => i).filter((i) => C.m[i] & bit && C.e[i] === e); });
const zipRows = memo((sc, est) => { const m = new Map(); for (const i of rowsOf(sc, est)) list(m, C.z[i]).push(i); return m; });
const tcRows = memo((sc, est) => { const bit = bitOf(sc), e = P.ests.indexOf(est), m = new Map(); for (let i = 0; i < TC.m.length; i++) if (TC.m[i] & bit && TC.e[i] === e) list(m, TC.z[i]).push(i); return m; });
const assignedOf = memo((sc, est) => {            // "channel|state" -> the people assigned there, from each person's role and assigned
  const m = new Map(), bit = bitOf(sc), e = P.ests.indexOf(est);                        // states (not from the cells: a state can be
  const chOf = new Map(Object.entries(P.roleOf).map(([c, r]) => [r, P.channels.indexOf(c)]));   // assigned in a channel that has no cell there)
  for (const r of P.people) {                       // [scenario mask, est, key, source, role, assigned states, held elsewhere]
    if (!(r[0] & bit) || r[1] !== e || !chOf.has(r[4])) continue;
    for (const st of String(r[5] || '').split(' ')) if (SIX.has(st)) list(m, chOf.get(r[4]) + '|' + SIX.get(st)).push(r[2]);
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
    p.usd += C.u[i]; p.zips.add(C.z[i]); add(p.states, C.s[i], C.u[i]);
  }
}

function compute(sc = S.sc, lean = false) {      // the preliminary assignment: D.cls is the four classes' $ on screen
  const rows = rowsOf(sc, S.est), ch = S.ch === 'ALL' ? -1 : P.channels.indexOf(S.ch), F = area().states;
  const D = {rows, ch, est: 0, noState: 0, focus: 0, cls: new Float64Array(NK), noShape: 0, st: new Map(), pairs: new Map(), opp: new Map(), seat: new Map(),
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
    if (!lean) {                                   // whose opportunity it is, every channel (gap_load's rule, so the people add up to the assigned $): all of
      const a = P.sets[C.a[i]], h = P.sets[C.h[i]];    // a cell to the one assignee who covers it alone, else shared equally; an open seat's to its state
      if (!a.length) add(D.seat, s, u);
      else if (C.j[i] === J.COVERED && h.length === 1 && a.includes(h[0])) add(D.opp, h[0], u);
      else for (const p of a) add(D.opp, p, u / a.length);
    }
    if (!inCh) continue;
    D.cls[k] += u;
    if (z >= NSHAPE) D.noShape += u;
    (D.st.get(s) || D.st.set(s, new Float64Array(NK)).get(s))[k] += u;
    if (C.j[i] === J.OVERLAP && !lean) addPairs(D.pairs, i);
  }
  D.screen = sum(D.cls);
  return D;
}
function computeToday() {                         // a firm's territories today: D.cls is the $ on screen by the status of the ZIP's holder
  const H = T.h[S.of + '|' + S.tch], tci = TCH.indexOf(S.tch), bit = bitOf(S.sc), e = P.ests.indexOf(S.est), F = area().states;
  const D = {today: true, H, est: 0, noState: 0, focus: 0, cls: new Float64Array(STATUS.length), noShape: 0, st: new Map(), opp: new Map(),
    zs: new Int8Array(NZ).fill(-1), nz: new Int32Array(STATUS.length)};
  const status = new Map(), of = (k) => status.has(k) ? status.get(k) : status.set(k, statusOf(k)).get(k);
  for (let z = 0; z < NZ; z++) {                  // a ZIP's status: its holder's (the strongest of two holders'); a ZIP on the map with no territory: no one
    const h = holders(H, z);
    if (!h.length && z >= NSHAPE) continue;
    D.zs[z] = h.length ? Math.min(...h.map(of)) : NOONE;
    if (F.has(P.zst[z])) D.nz[D.zs[z]]++;
  }
  for (let i = 0; i < TC.m.length; i++) {
    if (!(TC.m[i] & bit) || TC.e[i] !== e) continue;
    const u = TC.u[i], s = TC.s[i], z = TC.z[i];
    D.est += u;
    if (s < 0) { D.noState += u; continue; }
    if (!F.has(s)) continue;
    D.focus += u;
    if (TC.c[i] !== tci) continue;                // a cell's holder today is the holder of its firm x ZIP x channel today (04)
    const k = D.zs[z] < 0 ? NOONE : D.zs[z];
    D.cls[k] += u;
    if (z >= NSHAPE) D.noShape += u;
    (D.st.get(s) || D.st.set(s, new Float64Array(STATUS.length)).get(s))[k] += u;
    for (const p of holders(H, z)) add(D.opp, p, u);
  }
  D.screen = sum(D.cls);
  return D;
}

// The run's own totals (07's summary and pairs) against the cells, and today's cells against the same estimate: the tie-out the page shows.
const check = memo((sc, est) => {
  const bit = bitOf(sc), e = P.ests.indexOf(est), rows = rowsOf(sc, est);
  const got = new Map(), pairs = new Map();
  let total = 0, todayTotal = 0;
  for (const i of rows) { add(got, C.c[i] + '|' + C.j[i], C.u[i]); total += C.u[i]; if (C.j[i] === J.OVERLAP) addPairs(pairs, i); }
  for (let i = 0; i < TC.m.length; i++) if (TC.m[i] & bit && TC.e[i] === e) todayTotal += TC.u[i];
  const want = P.summary.filter((r) => r[0] & bit && r[1] === e), wantPairs = P.pairs.filter((r) => r[0] & bit && r[1] === e);
  const bad = [];
  if (want.length) {
    const keys = new Set([...got.keys(), ...want.map((r) => r[2] + '|' + r[3])]);
    for (const key of keys) {
      const w = sum(want.filter((r) => r[2] + '|' + r[3] === key).map((r) => r[5])), g = got.get(key) || 0;
      if (Math.abs(w - g) > 1) bad.push(`${P.channels[+key.split('|')[0]]} ${DET[+key.split('|')[1]]}: cells ${usd(g)}, summary ${usd(w)}`);
    }
  }
  if (P.has.pair && (wantPairs.length || pairs.size)) {
    const keys = new Set([...pairs.keys(), ...wantPairs.map((r) => pairKey(r[2], r[3], r[4]))]);
    for (const key of keys) {
      const w = wantPairs.find((r) => pairKey(r[2], r[3], r[4]) === key), g = pairs.get(key);
      if (!w || !g || Math.abs(w[6] - g.usd) > 1 || w[5] !== g.zips.size) bad.push(`pair ${key.split('|').slice(1).map((k) => P.keys[+k]).join(' and ')}: cells ${g ? usd(g.usd) : 'none'}, run ${w ? usd(w[6]) : 'none'}`);
    }
  }
  if (TC.m.length && Math.abs(todayTotal - total) > 1) bad.push(`today's cells ${usd(todayTotal)}, the assignment's ${usd(total)}`);
  return {total, bad, summary: want.length > 0, pairs: P.has.pair ? wantPairs.length : 0};
});

// ---- the map's colours: one per ZIP, by the view
function zipColours(D) {
  const col = new Array(NSHAPE).fill(null);
  if (D.today) {                                  // every ZIP on the map: its holder's status, or its holder
    for (let z = 0; z < NSHAPE; z++) { const k = D.zs[z], h = holders(D.H, z); col[z] = k < 0 ? null : S.tby === 'status' || k === NOONE ? STATUS[k].color : h.length > 1 ? CONTESTED : P.tcolour[h[0]]; }
    return col;
  }
  const who = terrWho(D);
  for (let z = 0; z < NSHAPE; z++) {
    const o = z * NK;
    let best = -1;
    if (S.view === 'terr') { col[z] = who(z); continue; }
    if (S.view === 'fill') for (let k = NK - 1; k >= 0 && best < 0; k--) if (D.zc[o + k] > 0) best = k;       // what changes: the loudest class with any $ in the ZIP
    if (best < 0) for (let k = 0; k < NK; k++) if (D.zc[o + k] >= 0 && (best < 0 || D.zc[o + k] > D.zc[o + best])) best = k;   // largest class: the one with the most $
    col[z] = best < 0 ? null : CLS[best].color;
  }
  return col;
}
function terrWho(D) {                             // by person: the colour of a ZIP, by who is assigned or who covers it today
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
function highlight(D) {                           // the ZIPs kept bright, or null for all: the selection, the isolated class, the scenario differences, the ZIPs with sales
  const sets = [], sel = SEL(), inCh = (i) => C.s[i] >= 0 && (D.ch < 0 || C.c[i] === D.ch), one = sel.people && sel.people.length === 1 ? sel.people[0] : -1;
  if (sel.people) {
    const [a, b] = sel.people, s = new Set();
    if (D.today) { for (let z = 0; z < NZ; z++) if (holders(D.H, z).includes(a)) s.add(z); }
    else for (const i of D.rows) {
      if (!inCh(i)) continue;
      const h = P.sets[C.h[i]];
      if (b === undefined ? h.includes(a) || P.sets[C.a[i]].includes(a) : C.j[i] === J.OVERLAP && h.includes(a) && h.includes(b)) s.add(C.z[i]);
    }
    sets.push(s);
  }
  if (S.cls !== '') {
    const s = new Set();
    if (D.today) { for (let z = 0; z < NZ; z++) if (D.zs[z] === +S.cls) s.add(z); }
    else for (const i of D.rows) if (inCh(i) && C.k[i] === +S.cls) s.add(C.z[i]);
    sets.push(s);
  }
  if (S.diff) { const e = P.ests.indexOf(S.est), s = new Set(); for (let i = 0; i < NC; i++) if (C.e[i] === e && C.m[i] !== EVERY && inCh(i)) s.add(C.z[i]); sets.push(s); }
  if (S.sold) {                                   // ZIPs with sales: where the selected person sold, else where the ZIP's covering person (its holder today, its assignee) sold
    const s = new Set();
    if (one >= 0) { for (const [z, v] of SALES.get(one) || []) if (v > 0) s.add(z); }
    else if (D.today) { for (let z = 0; z < NZ; z++) if (holders(D.H, z).some((k) => sold(k, z))) s.add(z); }
    else for (const i of D.rows) if (inCh(i) && P.sets[C.a[i]].some((k) => sold(k, C.z[i]))) s.add(C.z[i]);
    sets.push(s);
  }
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
      {id: 'lines-case', type: 'line', source: 'states', paint: {'line-color': '#FFFFFF', 'line-opacity': 0.6, 'line-width': ['interpolate', ['linear'], ['zoom'], 3, 2.2, 8, 4]}},      // so a state line reads on a dark fill too
      {id: 'lines', type: 'line', source: 'states', paint: {'line-color': '#20113E', 'line-opacity': 0.6, 'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.6, 8, 1.6]}},
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
  document.body.dataset.zips = col.reduce((n, c) => n + (c ? 1 : 0), 0);          // for whoever checks: the ZIPs that wear a colour, and of them the ones kept bright
  document.body.dataset.lit = keep ? col.reduce((n, c, z) => n + (c && keep.has(z) ? 1 : 0), 0) : '';
  const zsel = sel.zip !== undefined && sel.zip < NSHAPE ? sel.zip : -1;
  if (zsel !== painted.sel) {
    if (painted.sel >= 0) map.setFeatureState({source: 'zips', id: painted.sel}, {sel: false});
    if (zsel >= 0) map.setFeatureState({source: 'zips', id: zsel}, {sel: true});
    painted.sel = zsel;
  }
  const asg = assignedOf(S.sc, S.est), terr = !D.today && S.view === 'terr', F = area().states;
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
const inFocus = (z, F) => F.has(P.zst[z]);
const pad = (b, d) => [b[0] - d, b[1] - d, b[2] + d, b[3] + d];
const boxOfZips = (zs) => zs.length ? pad(zs.reduce((b, z) => [Math.min(b[0], ZBOX[z][0]), Math.min(b[1], ZBOX[z][1]), Math.max(b[2], ZBOX[z][2]), Math.max(b[3], ZBOX[z][3])], [180, 90, -180, -90]), 0.3) : null;

// ---- what a ZIP holds: its cells in the chosen scenario and estimate, one line per channel, class and people, saying what changes
const todayOthers = (z, ch, not) => [...new Set(FIRMS.flatMap((f) => (ch === 'WH' ? ['WH'] : TCH).flatMap((c) => holders(T.h[f + '|' + c], z))))].filter((k) => !not.includes(k));
function story(l, z, card) {                      // the detail inside a class (07's seven), in plain words
  const ppl = (ks) => card ? whoAll(ks, 'no one') : ks.length ? esc(ks.map(label).join(', ')) : 'no one';
  const from = (ks) => ks.map((k) => `${card ? who(k) : esc(label(k))} (${statusWord(k)})`).join(', ');
  const d = DET[l.j];
  if (d === 'COVERED') return `${ppl(l.h)} covers it today, alone, and keeps it.`;
  if (d === 'OVERLAP') return `${ppl(l.h)} cover it today; one keeps it.`;
  if (d === 'HELD BY ANOTHER') return `Moves to ${ppl(l.a)} from ${from(l.h)}.`;
  if (d === 'GAP (HELD TODAY)') { const t = todayOthers(z, P.channels[l.c], l.a); return `Moves to ${ppl(l.a)} from ${t.length ? from(t) : 'someone who is not on the roster for this channel'}.`; }
  if (d === 'GAP (UNHELD)') return `Assigned to ${ppl(l.a)}; no one covers it today.`;
  if (d === 'OPEN SEAT HELD') return `No one is assigned in this state; ${ppl(l.h)} cover${l.h.length === 1 ? 's' : ''} it today.`;
  return 'No one is assigned in this state, and no one on the roster covers it today.';
}
const sw = (colour) => `<i class="sw" style="background:${colour}"></i>`;
const closeBtn = '<button class="close" data-go="sel=">Close</button>';
function soldHere(z, card) {
  const s = (soldIn().get(z) || []).slice().sort((a, b) => b[1] - a[1]);
  if (!HAS_SALES) return '';
  return `<p class="small">${s.length ? `Sold here in 2025: ${s.slice(0, 4).map(([k, v]) => `${card ? who(k) : esc(label(k))} ${usd(v)}`).join(', ')}${s.length > 4 ? `, and ${s.length - 4} more` : ''}.` : 'No one with a key sold here in 2025.'}</p>`;
}
function zipDetail(z, card) {
  if (today()) return zipToday(z, card);
  const rows = (zipRows(S.sc, S.est).get(z) || []).filter((i) => C.s[i] >= 0), lines = new Map();
  for (const i of rows) {
    const key = [C.c[i], C.j[i], C.a[i], C.h[i]].join('|');
    const l = lines.get(key) || lines.set(key, {c: C.c[i], j: C.j[i], k: C.k[i], a: P.sets[C.a[i]], h: P.sets[C.h[i]], usd: 0}).get(key);
    l.usd += C.u[i];
  }
  const all = [...lines.values()].sort((a, b) => CH_SHOW.indexOf(P.channels[a.c]) - CH_SHOW.indexOf(P.channels[b.c]) || b.usd - a.usd);
  const shown = all.filter((l) => S.ch === 'ALL' || P.channels[l.c] === S.ch), total = sum(all.map((l) => l.usd)), part = sum(shown.map((l) => l.usd));
  const st = P.zst[z] >= 0 ? ST[P.zst[z]] : null;
  const body = card ? shown.map((l) => `<div class="cell"><p><b>${sw(CLS[l.k].color)}${CH_LABEL[P.channels[l.c]]}: ${CLS[l.k].label.toLowerCase()}</b><span>${usd(l.usd)}</span></p><p class="sub">${story(l, z, true)}</p></div>`).join('')
    : shown.map((l) => `<tr><td class="l">${CH_LABEL[P.channels[l.c]]}</td><td class="l">${sw(CLS[l.k].color)}${CLS[l.k].label}</td><td class="l wrap">${story(l, z, false)}</td><td>${mm(l.usd)}</td></tr>`).join('');
  const rest = total - part > 0.5 ? `<p class="small">Plus ${usd(total - part)} in other channels: ${usd(total)} in this ZIP in all.</p>` : '';
  const head = `ZIP ${P.zips[z]}${st ? ', ' + esc(st.name) : ''}`;
  const table = !shown.length ? `<p class="small">No opportunity in ${chName()} here.</p>` : card ? body : `<table class="mini"><thead><tr><th class="l">Channel</th><th class="l">Class</th><th class="l">What changes</th><th>$MM</th></tr></thead><tbody>${body}</tbody></table>`;
  if (!card) return `<h3>${head} <span class="sub">${usd(part)}, ${S.est} estimate, ${chName()}</span></h3>${table}${rest}`;
  return `<header><div><h2>${head}</h2><p class="sub">${usd(part)} of opportunity in ${chName()}, ${S.est} estimate</p></div>${closeBtn}</header>
    ${table}${rest}${soldHere(z, true)}${st ? `<p class="small"><button class="link" data-go="focus=${st.id}&sel=">Focus on ${esc(st.name)}</button></p>` : ''}`;
}
function zipToday(z, card) {                      // today: who holds the ZIP in each firm and channel, and the opportunity by the cell's channel today
  const st = P.zst[z] >= 0 ? ST[P.zst[z]] : null, by = new Map();
  for (const i of tcRows(S.sc, S.est).get(z) || []) add(by, TC.c[i], TC.u[i]);
  const part = by.get(TCH.indexOf(S.tch)) || 0, total = sum(by.values());
  const ppl = (h) => h.length ? h.map((k) => `${card ? who(k) : esc(label(k))} (${statusWord(k)})`).join(', ') : 'no one';
  const body = FIRMS.flatMap((f) => TCH.map((c) => { const h = holders(T.h[f + '|' + c], z), mine = f === S.of && c === S.tch;
    return `<tr${mine ? ' class="mine"' : ''}><td class="l">${f} ${c}</td><td class="l wrap">${mine ? sw(STATUS[h.length ? Math.min(...h.map(statusOf)) : NOONE].color) : ''}${ppl(h)}</td><td>${f === S.of ? mm(by.get(TCH.indexOf(c)) || 0) : ''}</td></tr>`; })).join('');
  const table = `<table class="mini"><thead><tr><th class="l">Territory</th><th class="l">Holder today</th><th>$MM</th></tr></thead><tbody>${body}</tbody></table>`;
  const rest = total - part > 0.5 ? `<p class="small">${usd(total)} in this ZIP in every channel today.</p>` : '';
  const head = `ZIP ${P.zips[z]}${st ? ', ' + esc(st.name) : ''}`;
  if (!card) return `<h3>${head} <span class="sub">${usd(part)} in ${S.tch} today, ${S.est} estimate</span></h3>${table}`;
  return `<header><div><h2>${head}</h2><p class="sub">${usd(part)} of opportunity in ${S.tch} today, ${S.est} estimate</p></div>${closeBtn}</header>
    ${table}${rest}${soldHere(z, true)}${st ? `<p class="small"><button class="link" data-go="focus=${st.id}&sel=">Focus on ${esc(st.name)}</button></p>` : ''}`;
}
function stateTip(s) {
  if (today()) {
    const per = [...(byState(S.of, S.tch).get(s) || [])].sort((a, b) => b[1] - a[1]);
    return `<h3>${esc(ST[s].name)} <span class="sub">${S.of} ${S.tch} today</span></h3><table class="mini"><tbody>${per.slice(0, 6).map(([k, n]) => `<tr><td class="l">${esc(label(k))}</td><td class="l">${statusWord(k)}</td><td>${int(n)} ZIPs</td></tr>`).join('') || '<tr><td class="l">No territory here</td></tr>'}</tbody></table>`;
  }
  const asg = assignedOf(S.sc, S.est);
  const lines = CH_SHOW.filter((c) => c !== 'OPEN').map((c) => { const a = asg.get(P.channels.indexOf(c) + '|' + s) || []; return `<tr><td class="l">${CH_LABEL[c]}</td><td class="l">${a.length ? esc(a.map(label).join(', ')) : 'no one assigned'}</td></tr>`; }).join('');
  return `<h3>${esc(ST[s].name)}</h3><table class="mini"><tbody>${lines}</tbody></table>`;
}

// ---- the bar: whose territories (the view, its scenario, the estimate), then how to look at them
function seg(id, key, options, disabled = () => false) {
  $(id).innerHTML = options.map(([v, text, title]) => `<button type="button" data-go="${key}=${esc(v)}" aria-pressed="${S[key] === v}"${disabled(v) ? ' disabled' : ''}${title ? ` title="${esc(title)}"` : ''}>${esc(text)}</button>`).join('');
}
function renderBar() {
  $('runline').textContent = P.run ? 'Run ' + P.run : 'The roster against today’s territories';
  $('made').hidden = !P.madeUp.length;
  $('made').textContent = P.madeUp.length ? `Made-up, not the run’s: ${P.madeUp.join(', ')}` : '';
  $('c-products').textContent = P.products;
  seg('c-of', 'of', [['new', 'NewCo: preliminary assignment', 'Who is assigned where, against who covers it today'], ...FIRMS.map((f) => [f, `${f} today`, `${f}’s territories as they are today`])]);
  $('l-sc').textContent = today() ? 'Roster and seat plan of' : 'Scenario';
  $('sc-id').textContent = S.sc;
  $('c-sc').innerHTML = P.scenarios.map((s) => `<option value="${esc(s)}"${S.sc === s ? ' selected' : ''}>${esc(scName(s))}</option>`).join('');
  $('c-sc').title = scName();
  seg('c-est', 'est', P.ests.map((e) => [e, e, `The ${e} estimate of the same market. The estimates are never added.`]));
  $('l-ch').textContent = today() ? 'Territory channel' : 'Channel';
  if (today()) { seg('c-view', 'tby', Object.entries(TBY)); seg('c-ch', 'tch', TCH.map((c) => [c, c])); }
  else { seg('c-view', 'view', Object.entries(VIEWS)); seg('c-ch', 'ch', [['ALL', CH_LABEL.ALL], ...CH_SHOW.map((c) => [c, CH_LABEL[c]])], (v) => S.view === 'terr' && v === 'ALL'); }
  const opt = (v, text) => `<option value="${esc(v)}"${S.focus === v ? ' selected' : ''}>${esc(text)}</option>`;
  const inDiv = new Set(P.regions.flatMap(([, divs]) => divs.flatMap(([, codes]) => codes)));
  $('c-focus').innerHTML = opt('CONUS', 'CONUS (48 states and DC)')
    + (P.regions.length ? `<optgroup label="Census regions">${P.regions.map(([r]) => opt(r, r)).join('')}</optgroup><optgroup label="Census divisions">${P.regions.flatMap(([, divs]) => divs.map(([d]) => opt(d, d))).join('')}</optgroup>` : '')
    + `<optgroup label="States">${ST.map((s) => opt(s.id, inDiv.has(s.id) || s.name !== s.id ? `${s.name} (${s.id})` : s.id)).join('')}</optgroup>`;
}

// ---- the totals: what is on screen, what it is a share of, the legend with each class's $, the scenarios side by side
function renderTotals(D) {
  const a = area(), chain = [], defs = D.today ? STATUS : CLS;
  for (let f = S.focus; f; f = AREAS.get(f).up) chain.unshift(f);
  const crumbs = chain.map((f, i) => i === chain.length - 1 ? `<span>${esc(AREAS.get(f).label)}</span>` : `<button class="link" data-go="focus=${esc(f)}">${esc(AREAS.get(f).label)}</button><span aria-hidden="true">›</span>`).join('');
  const shown = defs.map((_, i) => i).filter((i) => D.cls[i] > 0.5 || D.today && D.nz[i] > 0 || S.cls === String(i));       // a class with $0 on screen is not listed
  const row = (i) => `<button class="cl" data-go="cls=${i}" aria-pressed="${S.cls === String(i)}" title="Press to show only these ZIPs.">
    <i style="background:${defs[i].color}"></i><span>${defs[i].label}<small>${esc(defs[i].help)}${D.today ? ` ${int(D.nz[i])} ZIPs.` : ''}</small></span><b>${usd(D.cls[i])}</b><em>${pct(D.cls[i], D.screen)}</em></button>`;
  const stack = `<div class="stack" role="img" aria-label="Shares of the $ on screen">${shown.map((i) => `<i style="width:${100 * D.cls[i] / (D.screen || 1)}%;background:${defs[i].color}"></i>`).join('')}</div>`;
  const ck = check(S.sc, S.est);
  const tie = ck.bad.length ? `<p class="check bad">Does not tie to the run’s summary. ${esc(ck.bad.slice(0, 3).join('; '))}${ck.bad.length > 3 ? `; and ${ck.bad.length - 3} more` : ''}</p>`
    : D.today ? `<p class="check"><span aria-hidden="true">✓</span><span>Ties to the preliminary assignment: the same ${usd(ck.total)} of the ${S.est} estimate, here by the cell’s channel today.</span></p>`
    : ck.summary ? `<p class="check"><span aria-hidden="true">✓</span><span>Ties to the run’s ${S.est} summary: ${usd(ck.total)}, class by class${ck.pairs ? ', and pair by pair' : ''}.</span></p>`
    : `<p class="check">The run has no summary rows for ${S.est} to tie to; the cells add up to ${usd(ck.total)}.</p>`;
  const what = D.today ? `of opportunity in ${S.of}’s ${S.tch} territories today, ${S.est} estimate` : `of opportunity, ${S.est} estimate`;
  $('totals').innerHTML = `<nav class="crumbs" aria-label="Focus">${crumbs}</nav>
    <p class="where">On screen: ${esc(a.label)}, ${chName()}</p>
    <p class="big"><span class="capsule">${usd(D.screen)}</span><span class="of">${what}</span></p>
    ${D.today ? '' : `<p class="scn">${esc(scName())}${scName() === S.sc ? '' : ` <small>${esc(S.sc)}</small>`}</p>`}
    ${!D.today && S.ch === 'ALL' ? '' : `<div class="rung"><p><span><b>${pct(D.screen, D.focus)}</b> of ${esc(a.label)}, ${D.today ? 'every channel today' : 'all channels'}</span><span>${usd(D.focus)}</span></p><div class="track"><i class="on" style="width:${100 * D.screen / (D.focus || 1)}%"></i></div></div>`}
    <div class="rung"><p><span><b>${pct(D.screen, D.est)}</b> of the ${S.est} estimate</span><span>${usd(D.est)}</span></p>
      <div class="track"><i style="width:${100 * D.focus / (D.est || 1)}%"></i><i class="on" style="width:${100 * D.screen / (D.est || 1)}%"></i></div></div>
    ${D.noState > 0.5 || D.noShape > 0.5 ? `<p class="small">${D.noState > 0.5 ? `${usd(D.noState)} of the estimate sits on cells with no state: in no focus, on no map. ` : ''}${D.noShape > 0.5 ? `${usd(D.noShape)} on screen is in ZIPs with no map shape.` : ''}</p>` : ''}
    <div class="classes"><h3>${D.today ? `Who holds each ZIP in ${S.of}’s ${S.tch} territories today` : 'What changes for each ZIP under the preliminary assignment'}</h3>
      ${D.today ? `<p class="small">A holder’s status is against the roster and seat plan 1 of the chosen scenario${scName() === S.sc ? '' : ` (${esc(S.sc)})`}.</p>` : ''}${stack}
      <div class="head"><span>${D.today ? 'Holder' : 'Class'}</span><span>$</span><span>of screen</span></div>
      ${shown.map(row).join('')}
      <div class="cl total"><span>On screen</span><b>${usd(D.screen)}</b><em>${pct(D.screen, D.screen)}</em></div>
    </div>${tie}${D.today ? '' : renderScenarios(D)}`;
}
function renderScenarios(D) {
  if (P.scenarios.length < 2) return '';
  const per = P.scenarios.map((sc) => sc === S.sc ? D.cls : compute(sc, true).cls), now = per[P.scenarios.indexOf(S.sc)];
  const cols = CLS.map((_, k) => k).filter((k) => per.some((c) => c[k] > 0.5));
  const cell = (c, k) => `<td${Math.abs(c[k] - now[k]) > 0.5 ? ' class="chg"' : ''}>${usd(c[k])}</td>`;
  return `<div class="scen"><h3>Scenarios side by side <span class="note">violet: differs from the chosen one</span></h3>
    <table><thead><tr>${cols.map((k) => `<th>${CLS[k].label}</th>`).join('')}</tr></thead>
    ${P.scenarios.map((sc, i) => `<tbody tabindex="0" data-go="sc=${sc}" aria-selected="${sc === S.sc}"><tr><th class="l" colspan="${cols.length}">${esc(scName(sc))}${scName(sc) === sc ? '' : ` <small>${esc(sc)}</small>`}</th></tr><tr>${cols.map((k) => cell(per[i], k)).join('')}</tr></tbody>`).join('')}</table>
    <label class="tick"><input type="checkbox" id="c-diff"${S.diff ? ' checked' : ''}>Show only the ZIPs where the scenarios differ</label></div>`;
}

// ---- the wholesalers of the view and focus: territory, opportunity, 2025 sales in and outside it, where they sold
const rowOf = (table, sc, k) => { const bit = bitOf(sc), e = P.ests.indexOf(S.est); return table.find((r) => r[0] & bit && r[1] === e && r[2] === k); };
function wholesalers(D) {
  const F = area().states, out = [];
  if (D.today) {                                  // a firm's holders with a WH or FI territory in the focus; the row's numbers are the chosen channel's
    const per = new Map(), tci = TCH.indexOf(S.tch);
    TCH.forEach((c, ci) => { for (const [s, ks] of byState(S.of, c)) if (F.has(s)) for (const [k, n] of ks) { const p = per.get(k) || per.set(k, {n: TCH.map(() => 0), states: []}).get(k); p.n[ci] += n; if (ci === tci) p.states.push(ST[s].id); } });
    for (const [k, p] of per) out.push({k, who: label(k), status: statusOf(k), stw: statusWord(k), chn: TCH.filter((_, i) => p.n[i]).join(' and '), part: p.n.every((n) => n) ? 'both' : TCH[p.n.findIndex((n) => n)] + ' only',
      shown: p.n[tci] > 0, nzip: p.n[tci], terr: p.states.sort().join(' '), opp: D.opp.get(k) || 0, load: null, ...salesOf(k, (z) => holders(D.H, z).includes(k), F)});
    return out;
  }
  const bit = bitOf(S.sc), e = P.ests.indexOf(S.est), pl = planOf(S.sc, S.est);
  for (const r of P.people) {                     // the roster: each person's assigned states in the focus
    if (!(r[0] & bit) || r[1] !== e) continue;
    const ch = CH_OF_ROLE[r[4]] || '', states = r[5] ? r[5].split(' ') : [], own = new Set(states.map((s) => SIX.get(s))), inF = states.filter((s) => F.has(SIX.get(s)));
    if (!inF.length && !(S.focus === 'CONUS' && !states.length)) continue;
    const ld = rowOf(P.load, S.sc, r[2]), ext = (pl.ext.get(r[2]) || []).filter((s) => F.has(SIX.get(s)));
    out.push({k: r[2], who: label(r[2]), status: 0, stw: 'on the roster' + (ext.length ? `; plan 1 adds ${ext.join(', ')}` : ''), ch, chn: CH_LABEL[ch] || r[4], part: ch, firm: r[3],
      shown: S.ch === 'ALL' || ch === S.ch || S.ch === 'OPEN' && ext.length > 0, terr: inF.join(' '), opp: D.opp.get(r[2]) || 0, load: ld ? ld[9] : null, ...salesOf(r[2], (z) => own.has(P.zst[z]), F)});
  }
  for (const [k, seats] of pl.readd) {            // seat plan 1's re-adds: not on the roster, proposed for the open seats they would take
    const inF = seats.filter((s) => F.has(SIX.get(s))), own = new Set(seats.map((s) => SIX.get(s)));
    if (inF.length && statusOf(k) === 1) out.push({k, who: label(k), status: 1, stw: 'proposed: re-added by plan 1', ch: 'OPEN', chn: 'Open seat', part: 'OPEN', firm: rosterOf(S.sc).get(k)?.src || '',
      shown: S.ch === 'ALL' || S.ch === 'OPEN', terr: inF.join(' '), opp: sum(inF.map((s) => D.seat.get(SIX.get(s)) || 0)), load: null, ...salesOf(k, (z) => own.has(P.zst[z]), F)});
  }
  return out;
}
function renderStrip(all) {                       // the counts: the wholesalers of the view and focus, by channel and by status; each line adds up to the total
  const a = area(), n = (key, v, text) => `<span><b data-n="${key}">${int(v)}</b> ${text}</span>`, count = (f) => all.filter(f).length;
  const parts = today() ? [...TCH.map((c) => [c + ' only', `${c} only`]), ['both', TCH.join(' and ')]] : [['NATIONAL', 'national'], ['WH', 'WH'], ['REGIONAL', 'regional'], ['OPEN', 'for an open seat'], ['', 'no channel']];
  const tabs = Object.entries(TABS).filter(([v]) => !(today() && v === 'pairs'));
  $('strip').innerHTML = `<p class="counts"><span class="lead"><b data-n="total">${int(all.length)}</b> ${today() ? `${S.of} wholesalers with a ${TCH.join(' or ')} territory` : 'wholesalers'} in ${esc(a.label)}</span>
    <span class="grp">${parts.map(([v, text]) => [v, text, count((p) => p.part === v)]).filter(([v, , c]) => c || v).map(([v, text, c]) => n('ch', c, text)).join('')}</span>
    <span class="grp">${STATUS.slice(0, NOONE).map((s, i) => n('st', count((p) => p.status === i), s.label.toLowerCase() + (i === 1 ? ' (seat plan 1)' : ''))).join('')}</span></p>
    <div class="seg light" role="group" aria-label="Table">${tabs.map(([v, t]) => `<button type="button" data-go="tab=${v}" aria-pressed="${S.tab === v}">${t}</button>`).join('')}</div>`;
}

// ---- tables: sortable, a row drives the map
const SORT = {pairs: ['usd', -1], states: ['chg', -1], people: ['opp', -1]};
function sorted(id, rows) { const [key, dir] = SORT[id]; return rows.sort((a, b) => (typeof a[key] === 'string' ? a[key].localeCompare(b[key], 'en', {numeric: true}) : (a[key] ?? -Infinity) - (b[key] ?? -Infinity)) * dir); }
function th(id, key, text, left, title) { const [k, dir] = SORT[id]; return `<th${left ? ' class="l"' : ''}${k === key ? ` aria-sort="${dir < 0 ? 'descending' : 'ascending'}"` : ''}><button type="button" data-sort="${id}:${key}"${title ? ` title="${esc(title)}"` : ''}>${text}</button></th>`; }
const gauge = (ratio) => `<span class="gauge" aria-hidden="true"><i style="left:${Math.max(0, Math.min(100, 50 + 50 * Math.log2(ratio) / 3))}%"></i></span>`;   // a ratio: log scale, 1/8 to 8, 1 in the middle
const loadWord = (r) => r > 1.25 ? 'heavy for its area' : r < 0.8 ? 'light for its area' : 'right-sized for its area';

function renderPeople(D, all) {
  const a = area(), sel = SEL().people || [], t = D.today, tot = (k) => sum(rows.map((r) => r[k]));
  const rows = sorted('people', all.filter((p) => p.shown).map((p) => ({...p, pin: p.sales > 0 ? p.inside / p.sales : null})));
  const sales = (p) => HAS_SALES ? `<td>${mm(p.sales)}</td><td>${mm(p.inside)}</td><td>${mm(p.outside)}</td><td>${pct(p.inside, p.sales)}</td><td>${int(p.nsold)}</td>` : '';
  const body = rows.map((p) => `<tr tabindex="0" data-go="sel=${esc(P.keys[p.k])}" aria-selected="${sel.includes(p.k)}"><td class="l nm" title="${esc(p.who)}">${dot(p.k)}${esc(p.who)}</td>
    ${t ? '' : `<td class="l">${esc(p.firm)}</td>`}<td class="l">${esc(p.chn)}</td><td class="l">${t && S.tby === 'status' ? sw(STATUS[p.status].color) : ''}${esc(p.stw)}</td>
    <td class="l wrap">${t ? `${int(p.nzip)} ZIPs in ` : ''}${esc(p.terr) || 'no state'}</td><td>${mm(p.opp)}</td>${t ? '' : `<td>${p.load === null ? '–' : p.load.toFixed(2) + gauge(p.load)}</td>`}${sales(p)}</tr>`).join('');
  const head = `<tr>${th('people', 'who', 'Wholesaler', 1)}${t ? '' : th('people', 'firm', 'Firm', 1)}${th('people', 'chn', t ? 'Holds' : 'Channel', 1)}${th('people', 'stw', 'Status', 1)}${th('people', 'terr', `Territory in ${esc(a.label)}`, 1)}
    ${th('people', 'opp', 'Opportunity $MM', 0, t ? `The ${S.est} opportunity of the ZIPs they hold in ${S.tch}, by the cell's channel today` : `Their share of the ${S.est} opportunity assigned to them here; a split state is shared`)}${t ? '' : th('people', 'load', 'Load', 0, 'Assigned $ over the $ expected for the area they cover: 1 is right-sized, the band is 0.8 to 1.25')}
    ${HAS_SALES ? `${th('people', 'sales', '2025 sales $MM', 0, `Their 2025 sales in ${a.label}, main-map channels`)}${th('people', 'inside', 'in territory')}${th('people', 'outside', 'outside it')}${th('people', 'pin', 'in territory %')}${th('people', 'nsold', 'ZIPs sold in', 0, 'ZIPs with any sale above $0')}` : ''}</tr>`;
  const foot = `<tr><td class="l" colspan="${t ? 4 : 5}">${int(rows.length)} wholesalers${t ? ` holding ${S.tch} territory` : S.ch === 'ALL' ? '' : ', ' + chName()}</td><td>${mm(tot('opp'))}</td>${t ? '' : '<td></td>'}
    ${HAS_SALES ? `<td>${mm(tot('sales'))}</td><td>${mm(tot('inside'))}</td><td>${mm(tot('outside'))}</td><td>${pct(tot('inside'), tot('sales'))}</td><td></td>` : ''}</tr>`;
  const note = t ? `A ZIP held by two people counts for both.` : `Opportunity adds up to the $ assigned in ${esc(a.label)}; an open seat’s $ shows with the person plan 1 brings back for it.`;
  $('t-main').innerHTML = `<header><h2>Opportunity and sales</h2><p class="note">${esc(a.label)}, ${chName()}, ${S.est} estimate. ${note}
    ${HAS_SALES ? `Sales: 2025 actual, credited to the seller, ${esc(P.products)}; in territory means in ${t ? `a ZIP they hold in ${S.tch}` : 'their assigned states'}.${P.salesNoKey ? ` ${usd(P.salesNoKey)} of sales has a seller with no key and is in no row.` : ''}` : 'This run has no sales.'}</p></header>
    <div class="scroll">${rows.length ? `<table class="people"><thead>${head}</thead><tbody>${body}</tbody><tfoot>${foot}</tfoot></table>` : `<p class="empty">No wholesaler ${t ? `holds ${S.of} ${S.tch} territory` : 'is assigned'} in ${esc(a.label)}${t || S.ch === 'ALL' ? '' : ', ' + chName()}.</p>`}</div>`;
}
function renderPairs(D) {
  const sel = SEL().people || [], a = area();
  const rows = sorted('pairs', [...D.pairs.values()].map((p) => ({...p, ch: CH_LABEL[P.channels[p.c]], an: label(p.a), bn: label(p.b), n: p.zips.size, share: p.usd})));
  const one = S.ch !== 'ALL', k = CLS.findIndex((c) => c.of.includes(J.OVERLAP));
  const body = rows.map((p) => `<tr tabindex="0" data-go="sel=${P.keys[p.a]}-${P.keys[p.b]}" aria-selected="${sel.length === 2 && sel[0] === p.a && sel[1] === p.b}">
    ${one ? '' : `<td class="l">${p.ch}</td>`}<td class="l nm" title="${esc(p.an)}">${esc(p.an)}</td><td class="l nm" title="${esc(p.bn)}">${esc(p.bn)}</td><td>${int(p.n)}</td><td>${mm(p.usd)}</td><td>${pct(p.usd, D.focus)}</td></tr>`).join('');
  $('t-main').innerHTML = `<header><h2>Contested: who covers the same ZIPs</h2><p class="note">${esc(a.label)}, ${chName()}, ${S.est} estimate. Two people on the roster cover the same ZIPs today; one keeps each. Pairs do not add up: a cell with three people is in three pairs. Shares are of ${esc(a.label)}, all channels.</p></header>
    <div class="scroll">${rows.length ? `<table><thead><tr>${one ? '' : th('pairs', 'ch', 'Channel', 1)}${th('pairs', 'an', 'Person', 1)}${th('pairs', 'bn', 'and person', 1)}${th('pairs', 'n', 'ZIPs')}${th('pairs', 'usd', '$MM')}${th('pairs', 'share', `of ${esc(a.label)}`, 0, `The pair’s $ as a share of ${a.label}, all channels`)}</tr></thead>
    <tbody>${body}</tbody><tfoot><tr><td class="l" colspan="${one ? 3 : 4}">Contested on screen (each cell once)</td><td>${mm(D.cls[k])}</td><td>${pct(D.cls[k], D.focus)}</td></tr></tfoot></table>`
    : `<p class="empty">No two people on the roster cover the same ZIP in ${esc(a.label)}, ${chName()}, in this scenario.</p>`}</div>`;
}
function renderStates(D) {                        // the classes (or, today, the holders' statuses) by state
  const a = area(), defs = D.today ? STATUS : CLS, cols = defs.map((_, i) => i).filter((i) => D.cls[i] > 0.5), quiet = D.today ? -1 : 0;
  const rows = sorted('states', [...D.st.entries()].map(([s, c]) => ({s, id: ST[s].id, c, all: sum(c), chg: sum(c) - (quiet < 0 ? 0 : c[quiet]), ...Object.fromEntries(cols.map((i) => ['c' + i, c[i]]))}))
    .map((r) => ({...r, share: r.all ? r.chg / r.all : 0})));
  const max = Math.max(1, ...rows.map((r) => r.all));
  const bar = (r) => `<div class="stack" style="width:${Math.max(2, 100 * r.all / max)}%">${cols.map((i) => `<i style="width:${100 * r.c[i] / (r.all || 1)}%;background:${defs[i].color}"></i>`).join('')}</div>`;
  const body = rows.map((r) => `<tr tabindex="0" data-go="focus=${r.id}&sel=" aria-selected="${S.focus === r.id}"><td class="l">${esc(ST[r.s].name)}</td><td>${mm(r.all)}</td><td class="bar-cell">${bar(r)}</td>
    ${cols.map((i) => `<td>${mm(r.c[i])}</td>`).join('')}${quiet < 0 ? '' : `<td>${pct(r.chg, r.all)}</td>`}</tr>`).join('');
  $('t-main').innerHTML = `<header><h2>${D.today ? 'Who holds it today, by state' : 'What changes, by state'}</h2><p class="note">${esc(a.label)}, ${chName()}, ${S.est} estimate, $MM. Pick a state to focus on it.</p></header>
    <div class="scroll">${rows.length ? `<table><thead><tr>${th('states', 'id', 'State', 1)}${th('states', 'all', 'On screen')}<th></th>${cols.map((i) => th('states', 'c' + i, defs[i].label)).join('')}${quiet < 0 ? '' : th('states', 'share', 'changes', 0, 'Everything but uncontested, as a share of the state’s $ on screen')}</tr></thead>
    <tbody>${body}</tbody><tfoot><tr><td class="l">${esc(a.label)}</td><td>${mm(D.screen)}</td><td></td>${cols.map((i) => `<td>${mm(D.cls[i])}</td>`).join('')}${quiet < 0 ? '' : `<td>${pct(D.screen - D.cls[quiet], D.screen)}</td>`}</tr></tfoot></table>`
    : `<p class="empty">No opportunity on screen in ${esc(a.label)}, ${chName()}.</p>`}</div>`;
}

// ---- the card: the selected ZIP, person or pair; under the totals, the focused state
function salesBlock(k, mine, where) {
  if (!HAS_SALES) return '';
  const a = area(), s = salesOf(k, mine, a.states), on = S.sold === '1';
  return `<h3>2025 sales in ${esc(a.label)}: ${usd(s.sales)}</h3>${s.sales || s.nsold ? `<div class="kv"><span>In ${where}</span><span>${usd(s.inside)}</span><span>${pct(s.inside, s.sales)}</span>
    <span>Outside it</span><span>${usd(s.outside)}</span><span>${pct(s.outside, s.sales)}</span></div>
    <p class="small">Sold in ${int(s.nsold)} ZIPs. <button class="link" data-go="sold=${on ? '' : '1'}">${on ? 'Show all their ZIPs again' : 'Show only the ZIPs where they sold'}</button></p>` : '<p class="sub">No sale here in 2025.</p>'}`;
}
function renderPerson(k, D) {
  const head = `<header><div><h2>${dot(k)}${esc(label(k))}</h2>`, close = `</div>${closeBtn}</header>`, ro = rosterOf(S.sc).get(k), a = area();
  const sub = `<p class="sub">${ro && ro.src ? esc(ro.src) + ': ' : ''}${statusWord(k, true)}.</p>`;
  const r = rowOf(P.people, S.sc, k), states = r && r[5] ? r[5].split(' ') : [], own = new Set(states.map((s) => SIX.get(s))), ch = r ? CH_OF_ROLE[r[4]] : '';
  if (D.today) {
    const n = TCH.map((c) => sum([...byState(S.of, c)].filter(([s]) => a.states.has(s)).map(([, ks]) => ks.get(k) || 0)));
    return `${head}${sub}${close}<h3>${S.of} territory today in ${esc(a.label)}</h3>
      <div class="kv">${TCH.map((c, i) => `<span>${c}</span><span>${int(n[i])} ZIPs</span><span>${c === S.tch ? usd(D.opp.get(k) || 0) : ''}</span>`).join('')}</div>
      ${n.some((v) => v) ? '' : `<p class="sub">They hold no ${S.of} ${TCH.join(' or ')} territory here.</p>`}
      ${salesBlock(k, (z) => holders(D.H, z).includes(k), `the ZIPs they hold in ${S.tch}`)}
      ${r ? `<h3>Under the preliminary assignment</h3><p>${CH_LABEL[ch] || esc(r[4])}: ${states.length ? esc(states.join(', ')) : 'no state'}. <button class="link" data-go="of=new">See it</button></p>` : ''}`;
  }
  if (!r) return `${head}${sub}${close}<p class="sub">Not assigned in this scenario. The ZIPs they cover today stay bright on the map.</p>${salesBlock(k, (z) => seatsOf(k).some((s) => SIX.get(s) === P.zst[z]), seatsOf(k).length ? 'the seats plan 1 gives them' : 'their territory')}`;
  const mine = new Float64Array(NK), ld = rowOf(P.load, S.sc, k), chTotal = sum([...D.rows].filter((i) => P.channels[C.c[i]] === ch).map((i) => C.u[i]));
  for (const i of D.rows) if (P.channels[C.c[i]] === ch && P.sets[C.a[i]].includes(k)) mine[C.k[i]] += C.u[i];
  const asg = sum(mine), pairs = new Map();
  for (const i of D.rows) if (C.s[i] >= 0 && C.j[i] === J.OVERLAP && P.sets[C.h[i]].includes(k)) addPairs(pairs, i);
  const with_ = [...pairs.values()].filter((p) => p.a === k || p.b === k).sort((x, y) => y.usd - x.usd);
  return `${head}${sub}<p class="sub">${CH_LABEL[ch] || esc(r[4])}. Assigned ${states.length ? esc(states.join(', ')) : 'no state'}.</p>${close}
    <h3>What changes in their states <span class="note">${S.est} estimate; a split state’s cells count for each assignee</span></h3>
    <p>Assigned to them: <b>${usd(asg)}</b>, ${pct(asg, chTotal)} of the ${CH_LABEL[ch]} channel. Of that:</p>
    <div class="kv">${CLS.map((c, i) => mine[i] > 0.5 ? `<span>${sw(c.color)}${c.label}</span><span>${usd(mine[i])}</span><span>${pct(mine[i], asg)}</span>` : '').join('')}</div>
    ${r[6] ? `<p>Covers today outside their states: <b>${usd(r[6])}</b>.</p>` : ''}
    ${ld && ld[9] !== null ? `<h3>Load for the area: ${ld[9].toFixed(2)}, ${loadWord(ld[9])}</h3>
    <div class="scale">${gauge(ld[9])}<div aria-hidden="true">${[0.25, 0.5, 1, 2, 4].map((v) => `<span style="left:${50 + 50 * Math.log2(v) / 3}%">${v}</span>`).join('')}</div></div>
    <p class="small">${usd(ld[5])} assigned (a split state shared) over ${usd(ld[8])} expected for ${int(ld[4])} km²: ${usd(ld[6])} × (area ÷ the channel’s median ${int(ld[7])} km²)^${P.beta}. 1 is right-sized; the band is 0.8 to 1.25.</p>` : ''}
    ${salesBlock(k, (z) => own.has(P.zst[z]), 'their assigned states')}
    <h3>Contested with <span class="note">every state and channel</span></h3>${with_.length ? `<div class="kv">${with_.map((p) => `<span>${who(p.a === k ? p.b : p.a)}</span><span>${usd(p.usd)}</span><span><button class="link" data-go="sel=${P.keys[p.a]}-${P.keys[p.b]}&tab=pairs">${p.zips.size} ZIPs</button></span>`).join('')}</div>` : `<p class="sub">No one.</p>`}`;
}
function renderPair(a, b, D) {
  const p = [...D.pairs.values()].filter((p) => p.a === Math.min(a, b) && p.b === Math.max(a, b)).sort((x, y) => y.usd - x.usd)[0];
  const head = `<header><div><h2>${esc(P.keys[a])} and ${esc(P.keys[b])}</h2>`, close = `</div>${closeBtn}</header>`;
  if (!p) return `${head}<p class="sub">They do not cover the same ZIP in ${esc(area().label)}, ${chName()}, in this scenario.</p>${close}<p>${who(a)} and ${who(b)}</p>`;
  return `${head}<p class="sub">Both cover ${int(p.zips.size)} ZIPs holding ${usd(p.usd)} in ${esc(area().label)}, ${CH_LABEL[P.channels[p.c]]}, ${S.est} estimate: contested, one keeps each.</p>${close}
    <p>${who(a)} and ${who(b)}</p><h3>By state</h3><div class="kv">${[...p.states.entries()].sort((x, y) => y[1] - x[1]).map(([s, v]) => `<span><button class="link" data-go="focus=${ST[s].id}">${esc(ST[s].name)}</button></span><span>${usd(v)}</span><span>${pct(v, p.usd)}</span>`).join('')}</div>`;
}
function renderState(s, D) {
  const asg = assignedOf(S.sc, S.est), bit = bitOf(S.sc), e = P.ests.indexOf(S.est), open = P.channels.indexOf('OPEN'), up = AREAS.get(ST[s].id).up;
  const lines = CH_SHOW.filter((c) => c !== 'OPEN').map((c) => `<span>${CH_LABEL[c]}</span><span>${whoAll(asg.get(P.channels.indexOf(c) + '|' + s) || [], 'no one assigned')}</span><span></span>`).join('');
  const held = new Map(); let seat = 0;
  for (const i of D.rows) if (C.s[i] === s && C.c[i] === open) { seat += C.u[i]; for (const k of P.sets[C.h[i]]) add(held, k, C.u[i]); }
  const fit = P.seat.filter((r) => r[0] & bit && r[1] === e && r[2] === ST[s].id).sort((x, y) => x[5] - y[5]), pl = planOf(S.sc, S.est).seat.get(ST[s].id);
  const cand = (kind) => fit.filter((r) => r[3] === kind).slice(0, 3).map((r) => `<span>${r[5]}. ${who(r[4])}</span><span>${kind === 'NEIGHBOUR' ? (r[6] ? 'borders it' : '') : ''}</span><span>${r[8] ? 'load ' + esc(r[8]) : ''}</span>`).join('');
  return `<header><div><h2>${esc(ST[s].name)}</h2><p class="sub">${esc(up)}${AREAS.get(up).up ? ', ' + esc(AREAS.get(up).up) : ''}. Who is assigned:</p></div></header>
    <div class="kv">${lines}</div>
    ${seat > 0.5 ? `<h3>Open seat: ${usd(seat)} with no one assigned <span class="note">${S.est} estimate</span></h3>
      ${pl ? `<p>Seat plan 1: ${pl[4] < 0 ? 'left vacant' : `${pl[3] === 'READD' ? 'bring back' : 'extend'} ${who(pl[4])}`}.</p>` : ''}
      <p class="sub">Covered today by people on the roster (a ZIP with two counts for both):</p><div class="kv">${[...held.entries()].sort((x, y) => y[1] - x[1]).slice(0, 6).map(([k, v]) => `<span>${who(k)}</span><span>${usd(v)}</span><span>${pct(v, seat)}</span>`).join('') || '<span>No one</span><span></span><span></span>'}</div>
      ${fit.length ? `<h3>Who fits the seat <span class="note">the run’s ranking; ranks only, no sales figures</span></h3><p class="sub">Neighbours, by what they would gain against their book; load if they took it:</p><div class="kv">${cand('NEIGHBOUR') || '<span>None</span><span></span><span></span>'}</div>
      <p class="sub" style="margin-top:6px">People with a territory in it today:</p><div class="kv">${cand('HOLDER') || '<span>None</span><span></span><span></span>'}</div>` : ''}` : ''}`;
}
function renderCard(D) {                         // the selection's card floats on the map, so the totals beside it never scroll away
  const sel = SEL();
  const html = sel.zip !== undefined ? (sel.zip >= 0 ? zipDetail(sel.zip, true) : `<header><div><h2>ZIP ${esc(sel.code)}</h2><p class="sub">Not in this run: no opportunity, territory or sale.</p></div>${closeBtn}</header>`)
    : sel.people ? (sel.people.length === 2 ? renderPair(sel.people[0], sel.people[1], D) : renderPerson(sel.people[0], D)) : '';
  $('card').hidden = !html;
  $('card').innerHTML = html;
  $('detail').innerHTML = (!D.today && area().kind === 'state' ? renderState([...area().states][0], D) : '')
    + `<p class="about">Map drawn with MapLibre GL JS 6.19.0, embedded. <button class="link" id="licence-open">Its licence</button></p>`;
}
function renderChips(D) {
  const sel = SEL(), chips = [], one = sel.people && sel.people.length === 1;
  if (sel.people) chips.push([`sel=`, sel.people.length === 2 ? `Where ${P.keys[sel.people[0]]} and ${P.keys[sel.people[1]]} are contested` : D.today ? `ZIPs ${label(sel.people[0])} holds in ${S.tch}` : `ZIPs ${label(sel.people[0])} is assigned or covers today`]);
  if (sel.zip >= 0) chips.push(['sel=', `ZIP ${sel.code}`]);
  if (S.cls !== '') chips.push(['cls=', `Only ${(D.today ? STATUS : CLS)[+S.cls].label.toLowerCase()}`]);
  if (S.diff) chips.push(['diff=', 'Only ZIPs where the scenarios differ']);
  const by = !D.today && S.view === 'terr' ? `<div class="seg light" role="group" aria-label="Colour by">${[['assigned', 'Who is assigned'], ['held', 'Who covers it today']].map(([v, t]) => `<button type="button" data-go="by=${v}" aria-pressed="${S.by === v}"${v === 'assigned' && S.ch === 'OPEN' ? ' disabled' : ''}>${t}</button>`).join('')}</div>` : '';
  const sales = HAS_SALES ? `<button type="button" class="toggle" data-go="sold=${S.sold ? '' : '1'}" aria-pressed="${S.sold === '1'}" title="${one ? 'Only the ZIPs where the selected person sold in 2025' : 'Only the ZIPs where the person who covers them sold in 2025'}">ZIPs with sales${S.sold ? (one ? `: ${esc(P.keys[sel.people[0]])}` : ': everyone') : ''}</button>` : '';
  $('chips').innerHTML = by + sales + chips.map(([goTo, text]) => `<button class="chip" data-go="${goTo}" title="Clear">${esc(text)}<span aria-hidden="true">×</span></button>`).join('');
  const soldNote = S.sold ? (one ? ' Bright: only where the selected person sold in 2025.' : ` Bright: only where ${D.today ? 'the ZIP’s holder' : 'a person assigned to the ZIP'} sold there in 2025.`) : '';
  $('caption').textContent = (D.today ? (S.tby === 'status' ? `${S.of}’s ${S.tch} territories today: each ZIP by whether its holder is on the roster, proposed by seat plan 1, or not on the roster. Grey: no ${S.of} ${S.tch} territory.`
      : `${S.of}’s ${S.tch} territories today: each ZIP in its holder’s colour (colours repeat across the map; point at a ZIP for the person). Dark: two holders. Grey: no one.`)
    : S.view === 'fill' ? `A ZIP takes the colour of the biggest change in it (${chName()}): open if any of it is open, else transition, else contested, else uncontested. White: no opportunity there.`
    : S.view === 'gap' ? `A ZIP takes the colour of its class with the most $ (${chName()}). White: no opportunity in ${chName()}.`
    : S.by === 'assigned' ? `${CH_LABEL[S.ch]}: each ZIP in the colour of the person assigned to its state; a state with one assignee is tinted whole. Pale violet: a split state’s ZIP that not exactly one of its assignees covers today.`
    : `${CH_LABEL[S.ch]}: each ZIP in the colour of the person on the roster who covers it today. Dark: two or more do. Grey: none does.`) + soldNote;
}

// ---- drawing it all
let NOW = null;
function render(before) {
  const at = document.activeElement, home = at && at.closest('[id]'), mark = at && (at.dataset.go !== undefined ? `[data-go="${CSS.escape(at.dataset.go)}"]` : at.dataset.sort ? `[data-sort="${at.dataset.sort}"]` : null);
  NOW = today() ? computeToday() : compute();
  const all = wholesalers(NOW);
  renderBar(); renderTotals(NOW); renderStrip(all);
  if (S.tab === 'pairs') renderPairs(NOW); else if (S.tab === 'states') renderStates(NOW); else renderPeople(NOW, all);
  renderCard(NOW); renderChips(NOW);
  if (mark && home && home.id && !at.isConnected) $(home.id)?.querySelector(mark)?.focus();       // the panels were redrawn: keep the keyboard's place
  paint(before || null);
  document.title = `Territory coverage: ${area().label}, ${today() ? S.of + ' today' : S.sc}`;
}
function find(q) {
  q = q.trim();
  const say = (t) => { $('found').textContent = t; clearTimeout(find.t); find.t = setTimeout(() => { $('found').textContent = ''; }, 5000); };
  if (!q) return;
  const key = P.keys.find((k) => k.toLowerCase() === q.toLowerCase().split(' ')[0]) || P.keys.find((k) => (P.names[k] || '').toLowerCase().includes(q.toLowerCase()));
  const st = ST.find((s) => s.id.toLowerCase() === q.toLowerCase() || s.name.toLowerCase() === q.toLowerCase());
  if (/^\d{5}$/.test(q)) { if (P.zips.includes(q)) go({sel: q}); else return say(`ZIP ${q} is not in this run.`); }
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
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[tabindex][data-go]')) { e.preventDefault(); e.target.click(); }
  if (e.key === 'Escape' && (S.sel || S.cls || S.diff || S.sold) && !$('licence-box').open) go({sel: '', cls: '', diff: '', sold: ''});
});
document.addEventListener('change', (e) => {
  if (e.target.id === 'c-focus') go({focus: e.target.value, sel: ''});
  if (e.target.id === 'c-sc') go({sc: e.target.value});
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
