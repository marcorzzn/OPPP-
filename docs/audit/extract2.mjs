// Audit estrattivo v2 — gestisce i blocchi Object.assign(COMMANDS,{...})
import fs from 'node:fs';

const FILE = 'C:/Progetti/OPP/OverPowerPoint.html';
const src = fs.readFileSync(FILE, 'utf8');
const lines = src.split(/\r?\n/);
const lineOf = idx => { let n = 1; for (let i = 0; i < idx; i++) if (src.charCodeAt(i) === 10) n++; return n; };
const uniq = a => [...new Set(a)].sort();

// --- blocchi Object.assign(COMMANDS,{ ... }) con brace matching
function matchBrace(start) {
  let depth = 0, inS = null, inT = null, inLineC = false, inBlockC = false, esc = false;
  for (let i = start; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (inLineC) { if (c === '\n') inLineC = false; continue; }
    if (inBlockC) { if (c === '*' && n === '/') { inBlockC = false; i++; } continue; }
    if (inS) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === inS) inS = null; continue; }
    if (inT) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === inT) inT = null; continue; }
    if (c === '/' && n === '/') { inLineC = true; i++; continue; }
    if (c === '/' && n === '*') { inBlockC = true; i++; continue; }
    if (c === "'" || c === '"' || c === '`') { inS = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return i; }
  }
  return -1;
}

// estrae le chiavi al livello 1 dentro un blocco { ... }
function keysAtDepth1(blockStart, blockEnd) {
  const out = [];
  let depth = 0, inS = null, esc = false, paren = 0;
  for (let i = blockStart; i <= blockEnd; i++) {
    const c = src[i], n = src[i + 1];
    if (inS) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === inS) inS = null; continue; }
    if (c === "'" || c === '"' || c === '`') { 
      // chiave stringa a depth 0 e paren 0
      if (depth === 0 && paren === 0) {
        const endQ = src.indexOf(c, i + 1);
        const after = src.slice(endQ + 1).match(/^\s*:/);
        if (endQ > i && after) out.push({ id: src.slice(i + 1, endQ), line: lineOf(i) });
      }
      inS = c; continue;
    }
    if (c === '(' || c === '[') paren++;
    else if (c === ')' || c === ']') paren--;
    else if (c === '{') depth++;
    else if (c === '}') depth--;
    else if (depth === 0 && paren === 0 && /[A-Za-z_$]/.test(c) && (i === blockStart + 1 || /[\s,{]/.test(src[i - 1]))) {
      const ident = src.slice(i).match(/^[A-Za-z_$][\w$]*/)[0];
      const rest = src.slice(i + ident.length).match(/^\s*:/);
      if (rest) out.push({ id: ident, line: lineOf(i) });
      i += ident.length - 1;
    }
  }
  return out;
}

const declared = [];
for (const m of src.matchAll(/Object\.assign\(COMMANDS\s*,\s*\{/g)) {
  const braceOpen = src.indexOf('{', m.index);
  const braceClose = matchBrace(braceOpen);
  declared.push(...keysAtDepth1(braceOpen + 1, braceClose - 1));
}
const declaredSet = new Set(declared.map(d => d.id));
const dupes = declared.map(d => d.id).filter((id, i, a) => a.indexOf(id) !== i);

const collect = (re, g = 1) => [...src.matchAll(re)].map(x => ({ id: x[g], line: lineOf(x.index) }));
const ribbonCmds = collect(/ribbonBtn\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'/g);
const ribbonTools = collect(/ribbonTool\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'/g);
const dataCommands = collect(/data-command="([^"]+)"/g);
const exportCmds = collect(/data-export-cmd="([^"]+)"/g);
const runCommands = collect(/runCommand\(\s*'([^']+)'/g);

// scorciatoie
const kbStart = src.indexOf('function installKeyboard');
const kbEnd = matchBrace(src.indexOf('{', kbStart));
const kbBlock = src.slice(kbStart, kbEnd);
const shortcuts = [...kbBlock.matchAll(/'([^']+)'\s*:\s*'([a-z0-9.\-]+)'/g)].map(x => ({ key: x[1], cmd: x[2] }));

const tabsRendered = uniq([...src.matchAll(/if\(T===?'([^']+)'\)/g)].map(x => x[1]));
const tabsInHtml = [...src.matchAll(/data-tab="([^"]+)"/g)].map(x => x[1]);

// controlli DOM: id presenti nell'HTML statico
const staticHtml = src.slice(src.indexOf('<body'), src.indexOf('<script>'));
const htmlIds = uniq([...staticHtml.matchAll(/\sid="([A-Za-z0-9_-]+)"/g)].map(x => x[1]));

const referenced = uniq([...ribbonCmds, ...dataCommands, ...exportCmds, ...runCommands, ...shortcuts.map(s => s.cmd)].map(x => x.id || x));
const missing = referenced.filter(id => !declaredSet.has(id));
const orphans = [...declaredSet].filter(id => !referenced.includes(id));

const out = {
  file: { lines: lines.length, kb: +(src.length / 1024).toFixed(1) },
  commands: { declared: declaredSet.size, referenced: referenced.length, duplicates: dupes, missing, orphans },
  tabs: { inHtml: tabsInHtml, rendered: tabsRendered, missingBodies: tabsInHtml.filter(t => !tabsRendered.includes(t)), extraBodies: tabsRendered.filter(t => !tabsInHtml.includes(t)) },
  shortcuts: { count: shortcuts.length, toMissing: shortcuts.filter(s => !declaredSet.has(s.cmd)) },
  staticHtmlIds: htmlIds.length,
  ribbonButtons: ribbonCmds.length
};
fs.writeFileSync('C:/Progetti/OPP/.audit/commands.json', JSON.stringify({ out, declared, missing, orphans, shortcuts, tabsRendered, tabsInHtml }, null, 2));
console.log(JSON.stringify(out, null, 2));
