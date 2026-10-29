// Audit estrattivo di OverPowerPoint.html
// Estrae comandi dichiarati, comandi richiamati dall'interfaccia, scorciatoie, schede.
import fs from 'node:fs';

const FILE = 'C:/Progetti/OPP/OverPowerPoint.html';
const src = fs.readFileSync(FILE, 'utf8');
const lines = src.split(/\r?\n/);

function lineOfIndex(idx) {
  let n = 0;
  for (let i = 0; i < idx; i++) if (src.charCodeAt(i) === 10) n++;
  return n + 1;
}
function uniq(a) { return [...new Set(a)].sort(); }
function collect(re, group = 1, filter) {
  const out = [];
  re.lastIndex = 0;
  let m;
  while ((m = re.exec(src))) {
    const v = m[group];
    if (v != null && (!filter || filter(v))) out.push({ id: v, line: lineOfIndex(m.index) });
  }
  return out;
}

// 1. Comandi dichiarati nella mappa COMMANDS
const cmdsBlockStart = src.indexOf('const COMMANDS');
const cmdsBlockEnd = src.indexOf('\n};', cmdsBlockStart);
const cmdsBlock = src.slice(cmdsBlockStart, cmdsBlockEnd);
const commandLine = lineOfIndex(cmdsBlockStart);
const declared = [];
const cmdKeyRe = /^\s*(?:'([^']+)'|"([^"]+)"|([A-Za-z_$][\w$]*))\s*:\s*(?=[<!(]|\{|function|async)/gm;
let m;
while ((m = cmdKeyRe.exec(cmdsBlock))) {
  const id = m[1] || m[2] || m[3];
  const off = cmdsBlockStart + m.index;
  declared.push({ id, line: lineOfIndex(off) });
}
const declaredSet = new Set(declared.map(d => d.id));

// 2. Richiami dall'interfaccia
const ribbonCmds = collect(/ribbonBtn\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'/g);
const ribbonTools = collect(/ribbonTool\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'/g);
const dataCommands = collect(/data-command="([^"]+)"/g);
const exportCmds = collect(/data-export-cmd="([^"]+)"/g);
const runCommands = collect(/runCommand\(\s*'([^']+)'/g);
const dataActions = collect(/data-action="([^"]+)"/g);

// 3. Scorciatoie: mappa dentro installKeyboard
const kbStart = src.indexOf('function installKeyboard');
const kbEnd = src.indexOf('\n}', src.indexOf('addEventListener(\'keydown\'', kbStart));
const kbBlock = src.slice(kbStart, kbEnd === -1 ? kbStart + 9000 : kbEnd);
const shortcuts = [];
const scRe = /(?:'([^']+)'|"([^"]+)")\s*:\s*'([a-z0-9.\-]+)'/gi;
while ((m = scRe.exec(kbBlock))) {
  shortcuts.push({ key: m[1] || m[2], cmd: m[3] });
}

// 4. Schede renderizzate
const tabsRendered = [...src.matchAll(/if\(T===?'([^']+)'\)/g)].map(x => x[1]);
const tabsInHtml = [...src.matchAll(/data-tab="([^"]+)"/g)].map(x => x[1]);

// 5. Controlli HTML interattivi con id, per censire i binding
const htmlIds = [...src.matchAll(/\sid="([A-Za-z0-9_-]+)"/g)].map(x => x[1]);
const boundIds = uniq([...src.matchAll(/\bon\(\s*'([A-Za-z0-9_-]+)'/g)].map(x => x[1])
  .concat([...src.matchAll(/\$\('([A-Za-z0-9_-]+)'\)\.(?:onclick|oninput|onchange|onkeydown)\s*=/g)].map(x => x[1])));

// 6. Funzioni definite vs chiamate (grezzo: definizioni dichiarate e mai referenziate)
const funcDefs = [...src.matchAll(/function\s+([A-Za-z_$][\w$]*)\s*\(/g)].map(x => x[1]);
const funcNames = uniq(funcDefs);
const unusedFuncs = funcNames.filter(f => {
  const re = new RegExp('[^\\w$.]' + f.replace(/\$/g, '\\$') + '\\s*\\(', 'g');
  const count = (src.match(re) || []).length;
  const refs = (src.match(new RegExp('[^.\\w$]' + f.replace(/\$/g, '\\$') + '(?![\\w$])', 'g')) || []).length;
  return count + refs <= 1;
});

const referenced = uniq([...ribbonCmds, ...dataCommands, ...exportCmds, ...runCommands, ...shortcuts.map(s => s.cmd)]);
const missing = referenced.filter(id => !declaredSet.has(id));
const orphans = [...declaredSet].filter(id => !referenced.includes(id));

const summary = {
  file: { lines: lines.length, chars: src.length, kb: +(src.length / 1024).toFixed(1) },
  commands: { declared: declaredSet.size, referencedFromUi: referenced.length, missing, orphans },
  ribbonButtons: ribbonCmds.length,
  ribbonTools: uniq(ribbonTools.map(t => t.id)),
  tabs: { inHtml: tabsInHtml, rendered: uniq(tabsRendered), missingTabBodies: tabsInHtml.filter(t => !tabsRendered.includes(t)), extraBodies: uniq(tabsRendered).filter(t => !tabsInHtml.includes(t)) },
  shortcuts,
  shortcutsToMissing: shortcuts.filter(s => !declaredSet.has(s.cmd)),
  htmlIds: uniq(htmlIds).length,
  boundIds: boundIds.length,
  possiblyUnboundHtmlIds: uniq(htmlIds).filter(id => !boundIds.includes(id)),
  unusedFunctions: unusedFuncs
};

fs.writeFileSync('C:/Progetti/OPP/.audit/extract.json', JSON.stringify({ summary, declared, ribbonCmds, ribbonTools, dataCommands, exportCmds, runCommands }, null, 2));
console.log(JSON.stringify(summary, null, 2));
