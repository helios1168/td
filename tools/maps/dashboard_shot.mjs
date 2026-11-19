// tools/maps/dashboard_shot.mjs (issue #153): look at a built dashboard in headless Chromium, for the render-and-look loop and the
// smoke test.  Node 22+ (its own WebSocket and fetch), no package; the browser is $TD_CHROME or Playwright's cached headless shell.
//
//   node tools/maps/dashboard_shot.mjs <dashboard.html[#hash]> <out.png | -> [--size=1920x1080] [steps, run in order ...]
//     --hash=view=gap&focus=West   go to that state of the page        --mouse=x,y[,click]   move (and click) at a point of the window
//     --eval=<js>                  run it in the page                  --key=Tab,Tab,Enter   press keys
//     --dump=<js expression>       print `dump: <its JSON>`            --sleep=<ms>
//
// It drives the browser over the DevTools protocol in real time and waits for the page's own "the map has drawn" mark
// (body[data-map=idle]) after every step: `chrome --screenshot --virtual-time-budget` cannot be used, the map's worker never answers
// under virtual time and the map comes out blank.  --no-sandbox: the GPU process does not start inside an agent sandbox; the page
// is a local file and the last line printed lists every request that was not file:, blob: or data: (there must be none).
import {spawn} from 'node:child_process';
import {existsSync, mkdtempSync, readdirSync, writeFileSync} from 'node:fs';
import {homedir, tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

function browser() {
  if (process.env.TD_CHROME) return process.env.TD_CHROME;
  for (const root of [join(homedir(), 'Library', 'Caches', 'ms-playwright'), join(homedir(), '.cache', 'ms-playwright'), join(process.env.LOCALAPPDATA || '', 'ms-playwright')]) {
    if (!existsSync(root)) continue;
    for (const d of readdirSync(root).filter((d) => d.startsWith('chromium_headless_shell-')).sort().reverse())
      for (const sub of readdirSync(join(root, d))) for (const exe of ['chrome-headless-shell', 'chrome-headless-shell.exe', 'headless_shell']) if (existsSync(join(root, d, sub, exe))) return join(root, d, sub, exe);
  }
  return null;
}
if (process.argv.includes('--which')) { console.log(browser() || ''); process.exit(browser() ? 0 : 2); }
const [page, png, ...steps] = process.argv.slice(2);
const exe = browser();
if (!page || !png) { console.error('usage: node tools/maps/dashboard_shot.mjs <dashboard.html[#hash]> <out.png | -> [--size=WxH] [--hash= --eval= --mouse= --key= --dump= --sleep= ...]'); process.exit(1); }
if (!exe) { console.error('no headless Chromium: set TD_CHROME to a chrome or chrome-headless-shell binary'); process.exit(2); }
const [file, hash = ''] = page.split('#');
const url = (/^[a-z]+:\/\//.test(file) ? file : pathToFileURL(resolve(file)).href) + (hash ? '#' + hash : '');
const [W, H] = (steps.find((a) => a.startsWith('--size=')) || '--size=1920x1080').slice(7).split('x').map(Number);
const port = 9300 + Math.floor(Math.random() * 600);
const proc = spawn(exe, ['--headless', '--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), 'td-shot-'))}`, `--window-size=${W},${H}`, '--hide-scrollbars', 'about:blank'], {stdio: 'ignore'});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, code = 0;
try {
  let info;
  for (let i = 0; i < 60 && !info; i++) { await sleep(200); try { info = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); } catch {} }
  ws = new WebSocket(info.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r));
  let id = 0;
  const pending = new Map(), requests = [];
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    else if (m.method === 'Runtime.consoleAPICalled') console.log('console.' + m.params.type + ':', m.params.args.map((a) => a.value ?? a.description ?? '').join(' '));
    else if (m.method === 'Runtime.exceptionThrown') { code = 1; console.log('EXCEPTION:', m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text); }
    else if (m.method === 'Network.requestWillBeSent') requests.push(m.params.request.url);
  });
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => { pending.set(++id, (m) => m.error ? rej(new Error(method + ': ' + m.error.message)) : res(m.result)); ws.send(JSON.stringify({id, method, params, sessionId})); });
  const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
  const S = (m, p) => send(m, p, sessionId);
  for (const d of ['Runtime', 'Page', 'Network']) await S(d + '.enable');
  await S('Emulation.setDeviceMetricsOverride', {width: W, height: H, deviceScaleFactor: 1, mobile: false});
  await S('Page.navigate', {url});
  const run = async (expression) => { const r = await S('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true}); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
  const drawn = async () => { for (let t = 0; t < 240; t++) { await sleep(250); try { if (await run('document.body.dataset.map === "idle"')) return; } catch {} } code = 1; console.log('TIMED OUT waiting for the map to draw'); };
  const press = async (key) => { const p = {key, code: key, windowsVirtualKeyCode: {Tab: 9, Enter: 13, Escape: 27}[key] || 0}; await S('Input.dispatchKeyEvent', {type: 'keyDown', ...p}); await S('Input.dispatchKeyEvent', {type: 'keyUp', ...p}); };
  await drawn();
  for (const a of steps) {
    const v = a.slice(a.indexOf('=') + 1);
    if (a.startsWith('--hash=')) await run(`location.hash = ${JSON.stringify(v)}`);
    else if (a.startsWith('--eval=')) await run(v);
    else if (a.startsWith('--dump=')) console.log('dump:', JSON.stringify(await run(v)));
    else if (a.startsWith('--sleep=')) await sleep(+v);
    else if (a.startsWith('--key=')) for (const k of v.split(',')) await press(k);
    else if (a.startsWith('--mouse=')) {
      const [x, y, click] = v.split(',');
      await S('Input.dispatchMouseEvent', {type: 'mouseMoved', x: +x, y: +y});
      if (click) for (const type of ['mousePressed', 'mouseReleased']) await S('Input.dispatchMouseEvent', {type, x: +x, y: +y, button: 'left', clickCount: 1});
    } else continue;
    await sleep(400);
    await drawn();
  }
  await sleep(400);
  if (png !== '-') { writeFileSync(png, Buffer.from((await S('Page.captureScreenshot', {format: 'png'})).data, 'base64')); console.log('wrote', resolve(png)); }
  const outside = requests.filter((u) => !/^(file|blob|data|about):/.test(u));
  if (outside.length) code = 1;
  console.log('requests not local:', JSON.stringify(outside));
} catch (err) {
  code = 1;
  console.log('ERROR:', err.message);
} finally {
  try { ws?.close(); } catch {}
  proc.kill('SIGKILL');
}
process.exit(code);
