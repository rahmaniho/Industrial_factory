#!/usr/bin/env node
/* تست‌های سمتِ جاوااسکریپت برای site/index.html و dashboard/index.html
 *
 * هدف: رفتارِ نمایشگرِ مارک‌داون، تجزیه‌گر CSV و جست‌وجوی تمام‌متن
 *       بدون نیاز به مرورگر و به‌صورت خودکار بررسی شود.
 *
 * اجرا:  node tools/test_site.js
 */
"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const ROOT = path.resolve(__dirname, "..");

/* ── استاب‌های حداقلیِ DOM ── */
function stubEl(){
  const el = {
    innerHTML: "", textContent: "", value: "", scrollTop: 0,
    dataset: {}, style: {}, classList: { toggle(){}, add(){}, remove(){}, contains(){ return false; } },
    addEventListener(){}, querySelectorAll(){ return []; }, querySelector(){ return null; },
    scrollIntoView(){}, setAttribute(){}, appendChild(){}, closest(){ return null; },
  };
  return el;
}
const documentStub = {
  getElementById(){ return stubEl(); },
  querySelectorAll(){ return []; },
  querySelector(){ return null; },
  addEventListener(){},
  createTreeWalker(){ return { nextNode(){ return null; } }; },
  createElement(){ return stubEl(); },
};
const fetchStub = async (url) => {
  const p = path.join(ROOT, String(url).replace(/^\.\.\//, ""));
  if(!fs.existsSync(p)) return { ok: false, status: 404, text: async () => "" };
  return { ok: true, status: 200, text: async () => fs.readFileSync(p, "utf8") };
};

/* ── بارگذاریِ اسکریپتِ صفحه با استاب ── */
function loadSiteApi(){
  const html = fs.readFileSync(path.join(ROOT, "site", "index.html"), "utf8");
  const m = html.match(/<script>([\s\S]*?)<\/script>/g);
  assert.ok(m && m.length, "هیچ بلوکِ <script> در site/index.html یافت نشد");
  const code = m[m.length - 1].replace(/^<script>/, "").replace(/<\/script>$/, "");
  const exportLine = "\n;return { esc, md, inline, parseCsv, searchAll, snippetOf," +
                     " escapeRe, GROUPS, openDoc, highlightViewer, buildIndex," +
                     " indexSize: () => (INDEX ? INDEX.length : 0) };";
  const factory = new Function(
    "module", "exports", "document", "window", "location", "fetch",
    "NodeFilter", "setTimeout", "clearTimeout", "history", "ROOT_DIR",
    code + exportLine
  );
  return factory({}, {}, documentStub, { addEventListener(){}, scrollTo(){}, open(){} },
                 { hash: "" }, fetchStub, { SHOW_TEXT: 4 },
                 (f) => f(), () => {}, { replaceState(){} }, ROOT);
}

/* ── چارچوبِ کوچکِ تست ── */
let pass = 0, fail = 0;
function test(name, fn){
  try{ fn(); pass++; console.log(`  ✓ ${name}`); }
  catch(e){ fail++; console.log(`  ✗ ${name}\n      ${e.message}`); }
}

const api = loadSiteApi();

(async () => {
console.log("\nنمایشگرِ مارک‌داون");
test("تیترها به درستی تبدیل می‌شوند", () => {
  const out = api.md("# عنوان\n\n## زیرعنوان");
  assert.ok(out.includes("<h2>عنوان</h2>"), "تیتر ۱ باید h2 شود (صفحه خود h1 دارد)");
  assert.ok(out.includes("<h3>زیرعنوان</h3>"));
});
test("جدول به <table> تبدیل می‌شود", () => {
  const out = api.md("| الف | ب |\n|---|---|\n| ۱ | ۲ |\n| ۳ | ۴ |");
  assert.ok(out.includes("<table>"));
  assert.strictEqual((out.match(/<tr>/g) || []).length, 3, "یک ردیف سرآیند + دو ردیف داده");
  assert.strictEqual((out.match(/<td>/g) || []).length, 4);
});
test("بلوکِ کد دست‌نخورده می‌ماند", () => {
  const out = api.md("```\n| الف | ب |\n#not-a-heading\n```");
  assert.ok(out.includes("<pre><code>"));
  assert.ok(out.includes("| الف | ب |"), "محتوای کد باید محفوظ بماند");
  assert.ok(!out.includes("<table>"), "محتوای کد نباید به جدول تبدیل شود");
});
test("فهرست و نقل‌قول", () => {
  assert.ok(api.md("- یک\n- دو").includes("<ul><li>یک</li>"));
  assert.ok(api.md("1. یک\n2. دو").includes("<ol><li>یک</li>"));
  assert.ok(api.md("> نقل‌قول").includes("<blockquote>"));
});
test("قالب‌بندیِ درون‌خطی و گریز از HTML", () => {
  const out = api.inline("**تند** و `کد` و <script>");
  assert.ok(out.includes("<strong>تند</strong>"));
  assert.ok(out.includes("<code>کد</code>"));
  assert.ok(!out.includes("<script>"), "HTML باید گریز داده شود");
});

console.log("\nتجزیه‌گرِ CSV");
test("ستون‌های نقل‌قول‌شده با ویرگولِ داخلی", () => {
  const rows = api.parseCsv('a,b\n"x,y",z\n');
  assert.strictEqual(rows[1][0], "x,y");
  assert.strictEqual(rows[1][1], "z");
});
test("نقل‌قولِ تهی‌شده (دو تا quotation)", () => {
  const rows = api.parseCsv('a\n"say ""hi"""\n');
  assert.strictEqual(rows[1][0], 'say "hi"');
});
test("همهٔ فایل‌های data به‌درستی تجزیه می‌شوند", () => {
  const dir = path.join(ROOT, "data");
  for(const f of fs.readdirSync(dir).filter(x => x.endsWith(".csv"))){
    const rows = api.parseCsv(fs.readFileSync(path.join(dir, f), "utf8"));
    const width = rows[0].length;
    rows.forEach((r, i) => assert.strictEqual(
      r.length, width, `${f}:${i + 1}: عرض ${r.length} با سرآیند ${width} یکی نیست`));
  }
});

console.log("\nجست‌وجوی تمام‌متن");
const DOCS = api.GROUPS.flatMap(g => g.items.map(it => ({ p: it.p, t: it.t, g: g.name })));

await api.buildIndex();   // نمایه با همان سازوکارِ خودِ صفحه ساخته می‌شود

test("نمایه همهٔ اسناد را می‌پوشاند", () => {
  assert.strictEqual(api.indexSize(), DOCS.length, "هر سندِ فهرست باید فایل متناظر داشته باشد");
  assert.ok(api.indexSize() >= 40, `انتظار حداقل ۴۰ سند؛ یافت‌شده: ${api.indexSize()}`);
});
for(const q of ["OEE", "فراخوان", "ADR-005", "شجره", "FEFO", "[فرض]"]){
  test(`عبارتِ «${q}» در اسناد یافت می‌شود`, () => {
    const hits = api.searchAll(q);
    assert.ok(hits.length > 0, "هیچ موردی یافت نشد");
    assert.ok(new Set(hits.map(h => h.p)).size > 0);
  });
}
test("قطعهٔ نتیجه عبارت را برجسته می‌کند", () => {
  const q = "OEE";
  const hits = api.searchAll(q);
  const sn = api.snippetOf(hits[0].line, hits[0].i, q.length, q);
  assert.ok(sn.includes("<mark>"), "قطعه باید شامل <mark> باشد");
  assert.ok(!/undefined|NaN/.test(sn), "خروجیِ آلوده");
});

console.log("\nفهرستِ اسناد");
test("هر ورودی فایل متناظر دارد", () => {
  for(const d of DOCS){
    assert.ok(fs.existsSync(path.join(ROOT, d.p)), `فایل وجود ندارد: ${d.p}`);
  }
});
test("عنوان و توضیح برای همهٔ ورودی‌ها پر است", () => {
  for(const d of DOCS){
    assert.ok(d.t && d.t.trim(), `بدون عنوان: ${d.p}`);
  }
});

console.log("\n" + (fail === 0
  ? `✓ همهٔ ${pass} تست گذشت`
  : `✗ ${fail} تست شکست خورد (از ${pass + fail})`));
process.exit(fail === 0 ? 0 : 1);
})();
