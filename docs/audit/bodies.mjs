// Audit v4 — corpo di ogni comando: dimensione, prima riga, segnali di stub
import fs from 'node:fs';
const src = fs.readFileSync('C:/Progetti/OPP/OverPowerPoint.html', 'utf8');
const lineOf = idx => { let n = 1; for (let i = 0; i < idx; i++) if (src.charCodeAt(i) === 10) n++; return n; };

function matchBrace(start) {
  let depth = 0, q = null, esc = false, lc = false, bc = false;
  for (let i = start; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (lc) { if (c === '\n') lc = false; continue; }
    if (bc) { if (c === '*' && n === '/') { bc = false; i++; } continue; }
    if (q) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === q) q = null; continue; }
    if (c === '/' && n === '/') { lc = true; i++; continue; }
    if (c === '/' && n === '*') { bc = true; i++; continue; }
    if (c === "'" || c === '"' || c === '`') { q = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return i; }
  }
  return -1;
}
// trova le coppie chiave:valore al livello 1 con posizioni
function entries(start, end) {
  const out = []; let depth = 0, q = null, esc = false, paren = 0, pendingKey = null, segStart = null;
  for (let i = start; i <= end; i++) {
    const c = src[i];
    if (q) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === q) q = null; continue; }
    if (c === "'" || c === '"') {
      if (!depth && !paren) { const eq = src.indexOf(c, i + 1); if (eq > i && /^\s*:/.test(src.slice(eq + 1, eq + 40))) { pendingKey = src.slice(i + 1, eq); segStart = eq + 1; } }
      q = c; continue;
    }
    if (c === '(' || c === '[') paren++;
    else if (c === ')' || c === ']') paren--;
    else if (c === '{') depth++;
    else if (c === '}') depth--;
    else if (!depth && !paren) {
      if (/[A-Za-z_$]/.test(c) && /[\s,{]/.test(src[i - 1] || '{')) {
        const id = (src.slice(i).match(/^[A-Za-z_$][\w$]*/) || [''])[0];
        if (id && /^\s*:/.test(src.slice(i + id.length, i + id.length + 20))) { pendingKey = id; segStart = i + id.length; }
        i += Math.max(0, id.length - 1); continue;
      }
      if (c === ',' && pendingKey) {
        out.push({ id: pendingKey, line: lineOf(segStart), body: src.slice(segStart + 1, i).trim() });
        pendingKey = null;
      }
    }
  }
  return out;
}

const all = [];
for (const m of src.matchAll(/Object\.assign\(COMMANDS\s*,\s*\{/g)) {
  const o = src.indexOf('{', m.index);
  const close = matchBrace(o);
  all.push(...entries(o + 1, close - 1));
}
const dup = {};
all.forEach(e => { dup[e.id] = (dup[e.id] || 0) + 1; });

const rows = all.map(e => {
  const body = e.body.replace(/\s+/g, ' ');
  const stubs = [];
  if (/^\(\)\s*=>\s*toast\(/.test(body)) stubs.push('solo-toast');
  if (/non disponibile|non supportat|non implementat|coming soon|in arrivo/i.test(body)) stubs.push('messaggio-negativo');
  if (/^\(\)\s*=>\s*\{\s*\}/.test(body)) stubs.push('vuoto');
  return { id: e.id, line: e.line, len: e.body.length, stub: stubs.join(','), dup: dup[e.id] > 1, head: body.slice(0, 150) };
});
rows.sort((a, b) => a.id.localeCompare(b.id));
fs.writeFileSync('C:/Progetti/OPP/.audit/command-bodies.txt',
  rows.map(r => `${r.id.padEnd(26)} L${String(r.line).padEnd(5)} ${String(r.len).padStart(4)}b ${r.stub ? '⚠' + r.stub : ''}${r.dup ? ' ⧉dup' : ''}\n    ${r.head}`).join('\n'));
const flagged = rows.filter(r => r.stub || r.len < 40);
console.log('totale comandi:', rows.length, '| doppi:', rows.filter(r => r.dup).length, '| sospetti:', flagged.length);
console.log(flagged.map(r => `${r.id} (L${r.line}, ${r.len}b): ${r.stub || 'corto'} → ${r.head}`).join('\n'));
