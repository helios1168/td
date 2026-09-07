// Run the page script under a minimal DOM stub to surface runtime errors and count what it draws.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];

const counts = { created: {}, appended: 0 };
function node(tag) {
  const n = { tag, attrs: {}, children: [], style: {}, _classes: new Set(), _text: "",
    setAttribute(k, v) { this.attrs[k] = String(v); }, getAttribute(k) { return this.attrs[k]; },
    removeAttribute(k) { delete this.attrs[k]; },
    appendChild(c) { this.children.push(c); counts.appended++; return c; },
    append(...cs) { cs.forEach(c => this.appendChild(c)); },
    replaceChildren(...cs) { this.children = cs; },
    addEventListener() {}, toggleAttribute() {},
    querySelectorAll() { return []; }, querySelector() { return node("x"); },
    insertAdjacentHTML(_, h) { this._html = (this._html || "") + h; },
    get classList() { const s = this._classes; return { toggle(c, f) { if (f === undefined) f = !s.has(c); f ? s.add(c) : s.delete(c); }, add: c => s.add(c), remove: c => s.delete(c) }; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
    dataset: {}, value: "0", max: "0", checked: false, tabIndex: 0 };
  counts.created[tag] = (counts.created[tag] || 0) + 1;
  return n;
}
const byId = {};
global.document = {
  createElementNS: (_, t) => node(t), createElement: t => node(t),
  getElementById: id => (byId[id] ||= node("#" + id)),
  querySelectorAll: () => [], addEventListener() {},
};
global.window = global;
try {
  new Function(js)();
  const panel = byId["panel"];
  console.log("ran without error; created:", JSON.stringify(counts.created), "appended:", counts.appended);
  console.log("panel html length at step 0:", (panel.innerHTML || "").length);
  console.log("viewBox:", byId["map"].attrs.viewBox);
} catch (e) {
  console.log("RUNTIME ERROR:", e && e.stack ? e.stack.split("\n").slice(0, 6).join("\n") : e);
}
