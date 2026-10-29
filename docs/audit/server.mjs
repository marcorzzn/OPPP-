// Server statico minimale per servire la suite in locale
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'C:/Progetti/OPP';
const PORT = Number(process.env.PORT || 8765);
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.ttf': 'font/ttf' };

http.createServer((req, res) => {
  const url = decodeURIComponent((req.url || '/').split('?')[0]);
  const rel = url === '/' ? '/OverPowerPoint.html' : url;
  const file = path.resolve(ROOT, '.' + rel);
  if (!path.resolve(file).toLowerCase().startsWith(path.resolve(ROOT).toLowerCase())) { res.writeHead(403).end('fuori radice'); return; }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404).end('not found'); return; }
    res.writeHead(200, { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-store' });
    res.end(data);
  });
}).listen(PORT, '127.0.0.1', () => console.log('server su http://127.0.0.1:' + PORT));
