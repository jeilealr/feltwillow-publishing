// Feltwillow canonical-json-v1, H1 safe-domain profile: independent JavaScript implementation.
// handoff-contract draft H1, PROPOSED CONTRACT. Node.js >= 18, standard library only, offline.
//
// Usage: node tools/cj1.mjs golden/expected.json  -> prints a JSON report, exit 1 on any mismatch.
//
// Two paths are run for every golden case:
//   strict : own RFC 8259 parser (duplicate keys, numbers kept as text, UTF-8 fatal decoding),
//            H1 domain checks, canonical serializer (keys sorted by UTF-16 code units = JCS rule).
//   naive  : JSON.parse + sorted keys + JSON.stringify, i.e. what a developer would write
//            without the profile. Recorded only to show where the unconstrained v1 diverges.
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";

const MAX_SAFE = 9007199254740991n;
const MAX_DEPTH = 64;

class CJError extends Error { constructor(code, detail = "") { super(code + (detail ? ": " + detail : "")); this.code = code; } }

function parseStrict(bytes) {
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) throw new CJError("CJ_BOM");
  let text;
  try { text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch (e) { throw new CJError("CJ_INVALID_UTF8"); }
  let i = 0;
  const ws = () => { while (i < text.length && " \t\n\r".includes(text[i])) i++; };
  const fail = (m) => { throw new CJError("CJ_SYNTAX", m + " at " + i); };
  function value(depth) {
    if (depth > MAX_DEPTH) throw new CJError("CJ_DEPTH");
    ws();
    const c = text[i];
    if (c === "{") return object(depth);
    if (c === "[") return array(depth);
    if (c === '"') return string();
    if (c === "-" || (c >= "0" && c <= "9")) return number();
    for (const [lit, v] of [["true", true], ["false", false], ["null", null]]) {
      if (text.startsWith(lit, i)) { i += lit.length; return v; }
    }
    fail("unexpected token");
  }
  function object(depth) {
    i++; const out = new Map(); ws();
    if (text[i] === "}") { i++; return out; }
    for (;;) {
      ws(); if (text[i] !== '"') fail("expected key");
      const k = string();
      if (out.has(k)) throw new CJError("CJ_DUPLICATE_KEY", k);
      ws(); if (text[i] !== ":") fail("expected colon"); i++;
      out.set(k, value(depth + 1)); ws();
      if (text[i] === ",") { i++; continue; }
      if (text[i] === "}") { i++; return out; }
      fail("expected , or }");
    }
  }
  function array(depth) {
    i++; const out = []; ws();
    if (text[i] === "]") { i++; return out; }
    for (;;) {
      out.push(value(depth + 1)); ws();
      if (text[i] === ",") { i++; continue; }
      if (text[i] === "]") { i++; return out; }
      fail("expected , or ]");
    }
  }
  function string() {
    i++; let s = "";
    for (;;) {
      if (i >= text.length) fail("unterminated string");
      const c = text[i];
      if (c === '"') { i++; return s; }
      if (c.charCodeAt(0) < 0x20) fail("raw control character");
      if (c === "\\") {
        const e = text[i + 1];
        const map = { '"': '"', "\\": "\\", "/": "/", b: "\b", f: "\f", n: "\n", r: "\r", t: "\t" };
        if (e in map) { s += map[e]; i += 2; continue; }
        if (e === "u") {
          const h = text.slice(i + 2, i + 6);
          if (!/^[0-9a-fA-F]{4}$/.test(h)) fail("bad \\u escape");
          s += String.fromCharCode(parseInt(h, 16)); i += 6; continue;
        }
        fail("bad escape");
      }
      s += c; i++;
    }
  }
  function number() {
    const m = /^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?/.exec(text.slice(i));
    if (!m) fail("bad number");
    i += m[0].length;
    if (m[2] !== undefined || m[3] !== undefined) throw new CJError("CJ_FLOAT", m[0]);
    const b = BigInt(m[0]);
    if (b > MAX_SAFE || b < -MAX_SAFE) throw new CJError("CJ_INT_RANGE", m[0]);
    return Number(b);
  }
  const v = value(0); ws();
  if (i !== text.length) throw new CJError("CJ_SYNTAX", "trailing data");
  return v;
}

function checkString(s, isKey) {
  for (let k = 0; k < s.length; k++) {
    const u = s.charCodeAt(k);
    if (u >= 0xd800 && u <= 0xdbff) {
      const n = s.charCodeAt(k + 1);
      if (!(n >= 0xdc00 && n <= 0xdfff)) throw new CJError("CJ_LONE_SURROGATE");
      k++; continue;
    }
    if (u >= 0xdc00 && u <= 0xdfff) throw new CJError("CJ_LONE_SURROGATE");
  }
  if (isKey) { if (!/^[\x20-\x7e]*$/.test(s)) throw new CJError("CJ_KEY_NOT_ASCII", s); return; }
  if (s.normalize("NFC") !== s) throw new CJError("CJ_NOT_NFC");
}

function checkDomain(v) {
  if (v instanceof Map) { for (const [k, x] of v) { checkString(k, true); checkDomain(x); } return; }
  if (Array.isArray(v)) { v.forEach(checkDomain); return; }
  if (typeof v === "string") checkString(v, false);
}

// Canonical serializer: keys sorted by UTF-16 code units (JS default sort, RFC 8785 rule);
// strings and integers via JSON.stringify (ECMAScript rules, as RFC 8785 requires).
function serialize(v) {
  if (v === null || typeof v === "boolean") return JSON.stringify(v);
  if (typeof v === "number") { if (!Number.isSafeInteger(v)) throw new CJError("CJ_FLOAT"); return JSON.stringify(v); }
  if (typeof v === "string") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(serialize).join(",") + "]";
  if (v instanceof Map) {
    const keys = [...v.keys()].sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + serialize(v.get(k))).join(",") + "}";
  }
  throw new CJError("CJ_SYNTAX", "type");
}

function naive(bytes) {
  const v = JSON.parse(new TextDecoder().decode(bytes));
  const ser = (x) => {
    if (x !== null && typeof x === "object" && !Array.isArray(x))
      return "{" + Object.keys(x).sort().map((k) => JSON.stringify(k) + ":" + ser(x[k])).join(",") + "}";
    if (Array.isArray(x)) return "[" + x.map(ser).join(",") + "]";
    return JSON.stringify(x);
  };
  return ser(v);
}

const sha = (buf) => createHash("sha256").update(buf).digest("hex");
if (process.argv[2] === "--digest") {
  // node tools/cj1.mjs --digest file.json ... : strict parse + canonical digest of whole record and of .payload
  const out = {};
  for (const f of process.argv.slice(3)) {
    try {
      const v = parseStrict(readFileSync(f)); checkDomain(v);
      out[f] = { record: sha(Buffer.from(serialize(v), "utf8")),
                 payload: v instanceof Map && v.has("payload") ? sha(Buffer.from(serialize(v.get("payload")), "utf8")) : null };
    } catch (e) { out[f] = { error: e.code || String(e) }; }
  }
  console.log(JSON.stringify({ runtime: "node " + process.version, digests: out }, null, 2));
  process.exit(0);
}
const expectedPath = process.argv[2];
const expected = JSON.parse(readFileSync(expectedPath, "utf8"));
const base = dirname(expectedPath);
const results = [];
let mismatches = 0;
for (const c of expected.cases) {
  const raw = readFileSync(join(base, c.file));
  const r = { id: c.id, expect: c.expect };
  try {
    const v = parseStrict(raw); checkDomain(v);
    const out = Buffer.from(serialize(v), "utf8");
    r.strict = { ok: true, sha256: sha(out), hex: out.toString("hex") };
  } catch (e) { r.strict = { ok: false, code: e.code || String(e) }; }
  try { const n = Buffer.from(naive(raw), "utf8"); r.naive = { ok: true, text: n.toString("utf8"), sha256: sha(n) }; }
  catch (e) { r.naive = { ok: false, error: String(e).slice(0, 100) }; }
  if (c.expect === "ok") r.pass = r.strict.ok && r.strict.hex === c.canonical_utf8_hex && r.strict.sha256 === c.sha256;
  else if (c.authority === "python-only") { r.pass = true; r.informational = "verdict not required of JS consumers"; }
  else r.pass = !r.strict.ok && r.strict.code === c.code;
  const py = c.v2_python_unconstrained;
  r.naive_equals_v2_python = py && py.ok && r.naive.ok ? r.naive.sha256 === py.sha256 : null;
  if (!r.pass) mismatches++;
  results.push(r);
}
const report = { runtime: "node " + process.version, unicode: process.versions.unicode,
  cases: results.length, mismatches, results };
console.log(JSON.stringify(report, null, 2));
process.exit(mismatches ? 1 : 0);
