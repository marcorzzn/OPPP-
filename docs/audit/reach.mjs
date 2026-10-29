// Audit v3 — reachability dei comandi e dei tool
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
function keysOf(start, end) {
  const out = []; let depth = 0, q = null, esc = false, paren = 0;
  for (let i = start; i <= end; i++) {
    const c = src[i];
    if (q) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === q) q = null; continue; }
    if (c === "'" || c === '"') {
      if (!depth && !paren) {
        const eq = src.indexOf(c, i + 1);
        if (eq > i && /^\s*:/.test(src.slice(eq + 1, eq + 40))) out.push({ id: src.slice(i + 1, eq), line: lineOf(i) });
      }
      q = c; continue;
    }
    if (c === '(' || c === '[') paren++;
    else if (c === ')' || c === ']') paren--;
    else if (c === '{') depth++;
    else if (c === '}') depth--;
    else if (!depth && !paren && /[A-Za-z_$]/.test(c) && /[\s,{]/.test(src[i - 1] || '{')) {
      const id = (src.slice(i).match(/^[A-Za-z_$][\w$]*/) || [''])[0];
      if (id && /^\s*:/.test(src.slice(i + id.length, i + id.length + 20))) out.push({ id, line: lineOf(i) });
      i += Math.max(0, id.length - 1);
    }
  }
  return out;
}

const declared = [];
for (const m of src.matchAll(/Object\.assign\(COMMANDS\s*,\s*\{/g)) {
  const o = src.indexOf('{', m.index);
  declared.push(...keysOf(o + 1, matchBrace(o) - 1));
}
const counts = new Map();
for (const d of declared) counts.set(d.id, (counts.get(d.id) || 0) + 1);
const declaredSet = new Set(declared.map(d => d.id));

const grab = re => [...src.matchAll(re)].map(x => x[1]);
const dataCommands = grab(/data-command="([^"]+)"/g);
const exportCmds = grab(/data-export-cmd="([^"]+)"/g);
const runCmds = grab(/runCommand\(\s*'([^']+)'/g);
const ribbonCmds = grab(/ribbonBtn\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'/g);
const ctxCmds = grab(/cmd:\s*'([a-z0-9.\-]+)'/g);
const dataTools = grab(/data-tool="([^"]+)"/g);
const toolCalls = grab(/\bsetTool\(\s*'([^']+)'/g);

// comandi raggiungibili (esclusi placeholder template ${...})
const legit = s => s && !s.includes('${');
const reachable = new Set([...dataCommands, ...exportCmds, ...runCmds, ...ribbonCmds, ...ctxCmds].filter(legit));
// i tool.* sono invocati dinamicamente dalla delega data-tool
[...new Set(dataTools)].forEach(t => reachable.add('tool.' + t));
// comandi esposti solo via scorciatoie/palette: runCommand copre già; aggiungiamo le palette
const orphans = [...declaredSet].filter(id => !reachable.has(id));
const dupes = [...counts.entries()].filter(([, n]) => n > 1).map(([id, n]) => ({ id, n, lines: declared.filter(d => d.id === id).map(d => d.line) }));
const ghost = [...reachable].filter(id => !declaredSet.has(id));

// tool disponibili (unione: data-tool emessi, setTool chiamati, e i nomi in toolNames mappa di stato)
const toolsRegistered = new Set([...dataTools, ...toolCalls]);
const toolNamesMap = (src.match(/const toolNames=\{([^}]*)\}/) || [, ''])[1];
const toolNamesKeys = [...toolNamesMap.matchAll(/([A-Za-z]+):/g)].map(x => x[1]);

console.log(JSON.stringify({
  declared: declaredSet.size,
  reachable: reachable.size,
  ghostCommands: ghost,               // pulsanti che chiamano comandi inesistenti
  orphanCommands: orphans,            // comandi definiti ma senza pulsante/scorciatoia
  duplicates: dupes,
  toolsFromRibbon: [...new Set(dataTools)].sort(),
  toolsFromSetTool: [...new Set(toolCalls)].sort(),
  toolNamesKeys,
  toolsInRibbonNotInSetTool: [...new Set(dataTools)].filter(t => !toolCalls.includes(t)),
  toolsInSetToolNotInRibbon: [...new Set(toolCalls)].filter(t => !dataTools.includes(t)),
}, null, 2));
