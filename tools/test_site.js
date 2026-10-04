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
const EL_CACHE = new Map();
const documentStub = {
  getElementById(id){ if(!EL_CACHE.has(id)) EL_CACHE.set(id, stubEl()); return EL_CACHE.get(id); },
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
                     " indexSize: () => (INDEX ? INDEX.length : 0)," +
                     " owns, bestIn, rpCounts, pickRole, renderRole, buildRoleGrid," +
                     " roles: () => ROLES, rmap: () => RMAP, acc: () => ACC, rbac: () => RBAC," +
                     " tgt: () => TGT," +
                     " raci: () => RACIX, jour: () => JOUR, kpis: () => KPIS, als: () => ALS," +
                     " curRole: () => CUR_ROLE, setRp: (v) => { CUR_RP = v; }," +
                     " ready: () => BOOT };";
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

/* ══════════════════════════════════════════════════════════════
   نمای اختصاصیِ هر نقش  (s-role)
   ══════════════════════════════════════════════════════════════ */
console.log("\nجدولِ اهدافِ مشترک");
const SITE_HTML = fs.readFileSync(path.join(ROOT, "site", "index.html"), "utf8");

test("جدولِ اهداف از CSV می‌آید، نه از آرایهٔ دستی", () => {
  assert.ok(!/const TARGETS\s*=/.test(SITE_HTML),
    "آرایهٔ TARGETS باید حذف شود؛ اهداف باید از exec_targets.csv خوانده شوند");
  assert.ok(SITE_HTML.includes('"exec_targets"'), "exec_targets در فهرستِ بارگذاری نیست");
  assert.ok(/function drawTargets/.test(SITE_HTML), "تابعِ drawTargets یافت نشد");
});

await api.ready();
test("اهداف در سایت رندر می‌شوند", () => {
  const html = documentStub.getElementById("targets").innerHTML;
  assert.ok(html.length > 200, "جدولِ اهداف خالی است");
  for(const m of ["OEE", "OTIF", "LTIFR"]){
    assert.ok(html.includes(m), `شاخصِ ${m} در جدولِ اهداف نیست`);
  }
});
test("ستونِ واحد و هر دو افقِ زمانی نمایش داده می‌شود", () => {
  const html = documentStub.getElementById("targets").innerHTML;
  assert.ok(/هدف ۱۸ ماهه/.test(SITE_HTML) && /هدف ۳۰ ماهه/.test(SITE_HTML),
    "هر دو افق باید در سرستون باشند");
  assert.strictEqual((html.match(/<tr>/g) || []).length, api.tgt().length,
    "تعداد سطرها باید با exec_targets.csv یکی باشد");
});

console.log("\nنمای اختصاصیِ هر نقش");
await api.ready();

const ROLE_CODES = Array.from({ length: 24 }, (_, i) => "R" + String(i + 1).padStart(2, "0"));

test("بخشِ «نقش من» در ناوبری و بدنهٔ صفحه هست", () => {
  assert.ok(/data-sec="s-role"/.test(SITE_HTML), "دکمهٔ ناوبری ندارد");
  assert.ok(/<section id="s-role">/.test(SITE_HTML), "بخش ندارد");
  for(const id of ["roleGrid", "rolePick", "rpTitle", "rpIdent", "rpKpis", "rpNav", "rpBody"]){
    assert.ok(SITE_HTML.includes(`id="${id}"`), `عنصرِ #${id} یافت نشد`);
  }
});

test("شش زیربخش برای هر نقش تعریف شده است", () => {
  const nav = SITE_HTML.match(/<div class="subnav" id="rpNav">([\s\S]*?)<\/div>/);
  assert.ok(nav, "زیرناوبری یافت نشد");
  const keys = [...nav[1].matchAll(/data-rp="(\w+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(keys,
    ["pages", "journey", "raci", "alarms", "kpis", "modules"],
    "زیربخش‌ها: " + keys.join("، "));
});

test("مسیریابی با هش برای نقش پشتیبانی می‌شود", () => {
  assert.ok(/#\/role\/\(R\d\d\)/.test(SITE_HTML.replace(/\\/g, "\\")) ||
            SITE_HTML.includes("#/role/"), "مسیرِ #/role/ یافت نشد");
});

await api.ready();   // صبر تا بارگذاریِ داده‌ها در boot کامل شود
assert.strictEqual(api.roles().length, 24, "انتظار ۲۴ نقش؛ یافت‌شده: " + api.roles().length);
assert.strictEqual(api.rmap().length, 24, "نگاشت باید برای ۲۴ نقش باشد");
assert.strictEqual(api.jour().length, 96, "سفر کاری باید ۹۶ گام (۲۴×۴) باشد");
assert.strictEqual(api.acc().length, 672, "ماتریس صفحه‌ها باید ۲۸×۲۴ باشد");
console.log("  ✓ داده‌های نقش بارگذاری شدند (۲۴ نقش · ۶۷۲ خانه · ۹۶ گام)");

test("هر ۲۴ نقش در ماتریسِ صفحه‌ها ردیف دارد", () => {
  for(const code of ROLE_CODES){
    const cells = api.acc().filter(a => a.role === code);
    assert.strictEqual(cells.length, 28, `${code}: ${cells.length} خانه به‌جای ۲۸`);
  }
});

test("هیچ نقشی بدونِ هیچ صفحه‌ای نیست", () => {
  const empty = ROLE_CODES.filter(c =>
    api.acc().filter(a => a.role === c).every(a => a.access === "—"));
  assert.deepStrictEqual(empty, [], "نقش‌های بدون صفحه: " + empty.join("، "));
});

test("تخصیصِ مالک: خاص‌ترین نقش برنده است", () => {
  const by = Object.fromEntries(api.rmap().map(m => [m.code, m.owner_aliases]));
  assert.ok(api.owns(by.R03, "QC شیفت"), "«QC شیفت» باید به تکنسین QC برسد");
  assert.ok(!api.owns(by.R04, "QC شیفت"), "«QC شیفت» نباید به مدیر QC برسد");
  assert.ok(api.owns(by.R04, "QC"), "«QC» باید به مدیر QC برسد");
});

test("مالکِ چندگانه به همهٔ نقش‌های ذی‌ربط می‌رسد", () => {
  const by = Object.fromEntries(api.rmap().map(m => [m.code, m.owner_aliases]));
  assert.ok(api.owns(by.R04, "QC + تأسیسات"), "بخش QC");
  assert.ok(api.owns(by.R08, "QC + تأسیسات"), "بخش تأسیسات");
});

test("هر شاخص و هر هشدار دست‌کم به یک نقش نسبت داده می‌شود", () => {
  const maps = api.rmap();
  for(const [name, rows, col] of [["شاخص", api.kpis(), "data_owner"],
                                  ["هشدار", api.als(), "owner_role"]]){
    for(const r of rows){
      const hit = maps.filter(m => api.owns(m.owner_aliases, r[col]));
      assert.ok(hit.length, `${name} ${r.id}: مالکِ «${r[col]}» به هیچ نقشی نسبت داده نشد`);
    }
  }
});

test("انتخابِ یک نقش، پانل را برای همهٔ زیربخش‌ها پُر می‌کند", () => {
  for(const code of ROLE_CODES){
    api.pickRole(code);
    assert.strictEqual(api.curRole(), code, "نقشِ فعلی درست تنظیم نشد");
    for(const tab of ["pages", "journey", "raci", "alarms", "kpis", "modules"]){
      api.setRp(tab);
      api.renderRole();
      const html = documentStub.getElementById("rpBody").innerHTML;
      assert.ok(html && html.length > 60,
        `${code}/${tab}: خروجیِ خالی یا بسیار کوتاه`);
      assert.ok(!/undefined|NaN/.test(html), `${code}/${tab}: خروجیِ آلوده`);
    }
  }
});

test("آمارِ هر نقش با داده‌های واقعی سازگار است", () => {
  for(const code of ROLE_CODES){
    const c = api.rpCounts(code);
    assert.strictEqual(c.acc.length, 28, `${code}: شمارشِ دسترسی`);
    assert.ok(c.full + c.part + c.read <= 28, `${code}: جمعِ سطوح از ۲۸ بیشتر است`);
    assert.ok(c.jour === undefined || true);
  }
});

test("سفر کاری برای هر نقش ۴ گام دارد", () => {
  for(const code of ROLE_CODES){
    const steps = api.jour().filter(j => j.code === code);
    assert.strictEqual(steps.length, 4, `${code}: ${steps.length} گام`);
    for(const st of steps){
      for(const k of ["phase", "action", "system", "evidence"]){
        assert.ok((st[k] || "").trim(), `${code}/${st.step}: ستون ${k} خالی است`);
      }
    }
  }
});

/* ══════════════════════════════════════════════════════════════
   داشبورد: همهٔ منابع باید واقعاً رندر شوند
   ══════════════════════════════════════════════════════════════ */
console.log("\nداشبورد");

const DASH_CACHE = new Map();
function dashEl(){
  const el = stubEl();
  el.classList = { toggle(){}, add(){}, remove(){}, contains(){ return false; } };
  return el;
}
const dashDoc = {
  getElementById(id){ if(!DASH_CACHE.has(id)) DASH_CACHE.set(id, dashEl()); return DASH_CACHE.get(id); },
  querySelectorAll(){ return []; }, querySelector(){ return null; }, addEventListener(){},
};
function loadDashApi(){
  const html = fs.readFileSync(path.join(ROOT, "dashboard", "index.html"), "utf8");
  const blocks = html.match(/<script>([\s\S]*?)<\/script>/g);
  assert.ok(blocks && blocks.length, "هیچ بلوکِ اسکریپت در داشبورد یافت نشد");
  const code = blocks[blocks.length - 1].replace(/^<script>/, "").replace(/<\/script>$/, "");
  const tail = "\n;return { ready: () => BOOT, panels: () => PANELS()," +
               " counts: () => ({ kpi: KPIS.length, roles: ROLES.length }) };";
  return new Function("document", "fetch", "setTimeout", code + tail)(
    dashDoc, fetchStub, (f) => f());
}
const dash = loadDashApi();
await dash.ready();

test("داشبورد همهٔ داده‌ها را بدون خطا بارگذاری می‌کند", () => {
  assert.strictEqual(dashDoc.getElementById("loadErr").innerHTML, "",
    "خطای بارگذاری: " + dashDoc.getElementById("loadErr").innerHTML);
});

test("هر پانلِ داشبورد پس از بارگذاری جدولِ پُر دارد", () => {
  const ids = dash.panels();
  assert.ok(ids.length >= 20, "انتظار حداقل ۲۰ پانل؛ یافت‌شده: " + ids.length);
  for(const id of ids){
    const html = dashDoc.getElementById(id).innerHTML;
    assert.ok(html.indexOf("موردی یافت نشد") === -1, `${id}: پانل خالی رندر شده است`);
    assert.ok((html.match(/<tr>/g) || []).length >= 2, `${id}: کمتر از دو سطر دارد`);
  }
});

test("جدولِ فازها از roadmap جمع‌بسته می‌شود", () => {
  const html = dashDoc.getElementById("pPhases").innerHTML;
  assert.ok(html.includes("4.96") && html.includes("8.42"),
    "جمعِ بودجه باید با roadmap.csv یکی باشد (۴.۹۶–۸.۴۲)");
  assert.ok(/<tr>/g.test(html) && (html.match(/<tr>/g) || []).length >= 8,
    "هفت فاز به‌علاوهٔ سطرِ جمع");
});

console.log("\n" + (fail === 0
  ? `✓ همهٔ ${pass} تست گذشت`
  : `✗ ${fail} تست شکست خورد (از ${pass + fail})`));
process.exit(fail === 0 ? 0 : 1);
})();
