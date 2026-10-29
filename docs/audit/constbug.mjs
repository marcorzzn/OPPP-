// Cerca riassegnazioni di variabili dichiarate const (bug tipo ai.art)
import fs from 'node:fs';
const src = fs.readFileSync('C:/Progetti/OPP/OverPowerPoint.html', 'utf8');
const lines = src.split(/\r?\n/);
const lineOf = i => src.slice(0, i).split('\n').length;

const declRe = /\blet\s+|\bconst\s+/g;
const findings = [];

// per ogni funzione (semplice: blocchi 'function name(') analizza le dichiarazioni const del corpo
const fnRe = /function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{/g;
let m;
while ((m = fnRe.exec(src))) {
  const start = src.indexOf('{', m.index);
  // trova fine funzione con brace matching grezza
  let depth = 0, end = start, q = null, esc = false, lc = false, bc = false;
  for (let i = start; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (lc) { if (c === '\n') lc = false; continue; }
    if (bc) { if (c === '*' && n === '/') { bc = false; i++; } continue; }
    if (q) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === q) q = null; continue; }
    if (c === '/' && n === '/') { lc = true; i++; continue; }
    if (c === '/' && n === '*') { bc = true; i++; continue; }
    if (c === "'" || c === '"' || c === '`') { q = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) { end = i; break; } }
  }
  const body = src.slice(start, end);
  const constRe = /\bconst\s+([A-Za-z_$][\w$]*)\s*=(?!=)/g;
  const names = new Set();
  let cm;
  while ((cm = constRe.exec(body))) names.add(cm[1]);
  for (const name of names) {
    const esc = name.replace(/\$/g, '\\$');
    const reass = new RegExp('(^|[\\s;{}()])' + esc + '\\s*=(?![=>])', 'g');
    let rm;
    while ((rm = reass.exec(body))) {
      const abs = start + rm.index;
      findings.push(`${m[1]} @ L${lineOf(abs)}: riassegna const ${name} → ${lines[lineOf(abs) - 1].trim().slice(0, 90)}`);
    }
  }
  fnRe.lastIndex = Math.max(fnRe.lastIndex, end);
}
const uniq = [...new Set(findings)];
console.log('riassegnazioni const trovate:', uniq.length);
console.log(uniq.join('\n'));
