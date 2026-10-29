// Sonda rapida: carica la suite e valuta un'espressione JS passata da riga di comando.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import { launch, sleep } from './cdp.mjs';

const URL = 'http://127.0.0.1:8765/OverPowerPoint.html';
const expr = process.argv[2] || 'document.title';
const width = Number(process.argv[3] || 1440);
const height = Number(process.argv[4] || 900);
const mobile = process.argv[5] === 'mobile';
const shotPath = process.argv[6] || null;

const server = spawn(process.execPath, ['C:/Progetti/OPP/.audit/server.mjs'], { stdio: 'ignore' });
await sleep(500);
let browser;
try {
  browser = await launch({ url: URL, port: 9335, width, height, mobile });
  await sleep(1200);
  const out = await browser.evaluate(`(async()=>{ try { return ${expr}; } catch(e){ return { error:String(e && e.message || e) }; } })()`);
  console.log(JSON.stringify(out, null, 2));
  if (browser.events.exceptions.length) console.log('ECCEZIONI:', browser.events.exceptions.map(e => e.text).join('\n'));
  if (shotPath) {
    const shot = await browser.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(shotPath, Buffer.from(shot.data, 'base64'));
    console.log('screenshot:', shotPath);
  }
} catch (e) {
  console.error('ERRORE:', e);
} finally {
  if (browser) await browser.close();
  server.kill();
}
