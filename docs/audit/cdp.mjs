// Driver CDP senza dipendenze: avvia Chrome headless, apre la suite, espone evaluate.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

export async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

export async function launch({ url, port = 9333, width = 1440, height = 900, mobile = false }) {
  const base = 'C:/Progetti/OPP/.audit/chrome-profile';
  fs.rmSync(base, { recursive: true, force: true });
  fs.mkdirSync(base, { recursive: true });
  const profile = base;
  const args = [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--disable-background-networking', '--disable-sync',
    '--disable-dev-shm-usage', '--disable-crash-reporter', '--no-sandbox',
    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + port,
    '--user-data-dir=' + profile, '--disk-cache-dir=' + profile + '/cache',
    '--crash-dumps-dir=' + profile + '/crash',
    `--window-size=${width},${height}`, 'about:blank'
  ];
  const proc = spawn(CHROME, args, { stdio: 'ignore', detached: false });

  // attesa endpoint
  let version = null;
  for (let i = 0; i < 100; i++) {
    try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; } catch { await sleep(100); }
  }
  if (!version) throw new Error('Chrome non raggiungibile');

  const target = await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws')); });

  let id = 0;
  const pending = new Map();
  const events = { console: [], exceptions: [], log: [] };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id) { const p = pending.get(msg.id); if (p) { pending.delete(msg.id); msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result); } return; }
    if (msg.method === 'Runtime.consoleAPICalled') {
      events.console.push({ type: msg.params.type, text: msg.params.args.map(a => a.value ?? a.description ?? a.type).join(' '), line: msg.params.stackTrace?.callFrames?.[0]?.lineNumber });
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails;
      events.exceptions.push({ text: d.exception?.description || d.text, line: d.lineNumber, col: d.columnNumber, url: d.url });
    }
    if (msg.method === 'Log.entryAdded') events.log.push({ level: msg.params.entry.level, text: msg.params.entry.text });
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const mid = ++id; pending.set(mid, { resolve, reject });
    ws.send(JSON.stringify({ id: mid, method, params }));
    setTimeout(() => { if (pending.has(mid)) { pending.delete(mid); reject(new Error('timeout ' + method)); } }, 30000);
  });

  await send('Runtime.enable');
  await send('Log.enable');
  await send('Page.enable');
  if (mobile) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 2, mobile: true });
    await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  }
  await send('Page.navigate', { url });
  await sleep(1200);

  const evaluate = async (expression, { awaitPromise = true } = {}) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, allowUnsafeEvalBlockedByCSP: true });
    if (r.exceptionDetails) throw new Error('eval: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  };

  const close = async () => {
    try { ws.close(); } catch {}
    try { proc.kill(); } catch {}
    await sleep(200);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
  };

  return { send, evaluate, events, close, port };
}
