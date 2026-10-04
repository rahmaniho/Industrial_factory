#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ساختِ بستهٔ انتشار (`_site`) — یکسان برای گیت‌هاب پیج و Vercel.

چرا این ابزار وجود دارد؟
    صفحهٔ سایت در `site/index.html` است، ولی داده‌ها (`data/*.csv`) و مستندات
    (`docs/*.md`) دو پوشهٔ جدا در ریشهٔ مخزن‌اند. هر میزبانی که ریشهٔ مخزن را
    بی‌واسطه منتشر کند (Vercel با تنظیماتِ پیش‌فرضِ بدون build، یا Pages در
    حالت «Deploy from a branch») در نشانیِ `/` هیچ `index.html`ی پیدا نمی‌کند
    و خطای `404 NOT_FOUND` می‌دهد؛ تازه اگر صفحه باز هم بشود، داده‌ها ۴۰۴
    می‌شوند. این اسکریپت چیدمانِ درست را یک بار می‌سازد و همان را به هر
    میزبانی می‌دهد.

قرارداد:
    `/index.html`        صفحهٔ سایت در ریشه (نشانیِ اصلی)
    `/site/index.html`   همان صفحه، برای نشانی‌های کهنه — ریشهٔ نسبی‌اش `../`
    `/data/*.csv`        منبعِ داده (سایت با HEAD چک می‌کند کدام ریشه کار می‌کند)
    `/docs/**.md`        مستنداتی که همان صفحه رندر می‌کند
    `/dashboard/…`       داشبوردِ جاسازی‌شده
    `/.nojekyll`         تا Jekyll در Pages دست به فایل‌ها نزند

اجرا:
    python3 tools/build_site.py            # ساخت در `_site` (بازی: فایل‌ها را نو می‌کند)
    python3 tools/build_site.py --check    # ساخت در پوشهٔ موقت و فقط بررسیِ چیدمان
    python3 tools/build_site.py --out DIR  # ساخت در DIR
    python3 tools/build_site.py --quiet    # بدونِ خطِ پیشرفت

خروجی:  0 = بستهٔ سالم · 1 = مانعی وجود دارد
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
from glob import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── چیدمانِ بسته: (فایلِ مبدأ نسبت به ریشهٔ مخزن، مقصد در بسته) ──
COPIES = [
    ("site/index.html", "index.html"),
    ("site/index.html", "site/index.html"),
    ("dashboard/index.html", "dashboard/index.html"),
    ("README.md", "README.md"),
]

# ── پوشه‌به‌پوشه: (پوشهٔ مبدأ، پوشهٔ مقصد، الگوی فایل) ──
TREES = [
    ("data", "data", "*.csv"),
    ("docs", "docs", "*.md"),
    ("docs/03-units", "docs/03-units", "*.md"),
]

# فایل‌هایی که در ریشهٔ بسته ساخته می‌شوند و مبدأی در مخزن ندارند
NOT_FOUND = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>۴۰۴ — صفحه پیدا نشد</title>
<meta name="robots" content="noindex">
<style>
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f1115;
       color:#e6e9ef;font-family:"Vazirmatn","Tahoma","Segoe UI",system-ui,sans-serif;
       line-height:1.9;text-align:center;padding:24px}
  .box{background:#171a21;border:1px solid #2a2f3a;border-radius:14px;padding:30px 34px;max-width:520px}
  h1{margin:0 0 8px;font-size:20px}
  p{margin:0 0 16px;color:#9aa4b2;font-size:13.5px}
  code{background:#1d212a;border:1px solid #2a2f3a;border-radius:6px;padding:1px 6px;font-size:12.5px}
  a{color:#4f8cff;text-decoration:none}
  a:hover{text-decoration:underline}
  .btn{display:inline-block;background:#4f8cff;color:#fff;border-radius:9px;padding:9px 18px;
        font-size:13.5px;margin-inline-start:8px}
  .btn:hover{text-decoration:none;filter:brightness(1.08)}
</style>
</head>
<body>
  <div class="box">
    <h1>نشانی درخواستی در این بسته وجود ندارد</h1>
    <p>مستندات و داده‌ها در همین بسته‌اند؛ کافی است از صفحهٔ اصلی بازشان کنید.</p>
    <p><code id="path">—</code></p>
    <a class="btn" href="./">بازگشت به صفحهٔ اصلی</a>
    <a class="btn" href="./dashboard/">داشبورد</a>
  </div>
<script>
  document.getElementById("path").textContent = location.pathname + location.search;
</script>
</body>
</html>
"""


def rel(*parts):
    return os.path.join(BASE, *parts)


GENERIC = {".nojekyll": "", "404.html": NOT_FOUND}


def expand(tree):
    """بازگرداندنِ فهرستِ (مبدأ مطلق، مقصد نسبی) برای یک TREES."""
    src, dst, pattern = tree
    out_dir = rel(src)
    if not os.path.isdir(out_dir):
        return []
    found = []
    for path in sorted(glob(os.path.join(out_dir, pattern))):
        found.append((path, os.path.join(dst, os.path.basename(path))))
    return found


def manifest():
    """همهٔ فایل‌هایی که بسته باید داشته باشد: (مبدأ در مخزن، مقصد در بسته)."""
    items = []
    for src, dst in COPIES:
        if os.path.exists(rel(src)):
            items.append((rel(src), dst))
        else:
            items.append((None, dst))
    for tree in TREES:
        items.extend(expand(tree))
    return items


def requests_from_pages():
    """هر چیزی که سایت و داشبورد هنگامِ اجرا درخواست می‌کنند (نسبی به ریشهٔ بسته).

    سه شکلِ ارجاع در دو صفحه جست‌وجو می‌شود:
        {p:"docs/xx.md"}          فهرستِ مستنداتِ صفحهٔ اصلی
        ["a","b"].map(csv)        فهرستِ CSVها در صفحهٔ اصلی  →  data/a.csv
        load("a.csv") / csv("a")  فهرستِ داشبورد و فراخوان‌های تکی
    """
    want = set()
    for page in ("site/index.html", "dashboard/index.html"):
        path = rel(page)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()
        want |= set(re.findall(r'\{p:"([^"]+\.md)"', html))
        m = re.search(r"await Promise\.all\(\[([^\]]+)\]\.map\(csv\)\)", html)
        if m:
            want |= {"data/%s.csv" % x.strip().strip("\"'")
                     for x in m.group(1).split(",") if x.strip()}
        for name in re.findall(r'(?:load|csv)\(\s*"([^"]+)"', html):
            want.add("data/" + (name if name.endswith(".csv") else name + ".csv"))
        want |= set(re.findall(r'["\'](data/[^"\']+\.csv)["\']', html))
    return want


def build(out, quiet=False):
    """ساختنِ بسته در `out`. برمی‌گرداند تعداد فایل‌های نوشته‌شده."""
    out = os.path.abspath(out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    copied = 0
    for src, dst in manifest():
        dst_path = os.path.join(out, dst.replace("\\", "/"))
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        if src is None:
            raise SystemExit("✗ فایلِ لازم برای بستهٔ انتشار وجود ندارد: %s" % dst)
        shutil.copy2(src, dst_path)
        copied += 1
        if not quiet:
            print("  · %-34s ← %s" % (dst, os.path.relpath(src, BASE).replace(os.sep, "/")))
    for name, body in sorted(GENERIC.items()):
        dst_path = os.path.join(out, name)
        os.makedirs(os.path.dirname(dst_path) or out, exist_ok=True)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(body)
        copied += 1
        if not quiet:
            print("  · %-34s (ساخته شد)" % name)
    return copied


def verify(out, quiet=False):
    """بررسیِ اینکه هر آنچه میزبان/سایت لازم دارد، در بسته هست. فهرستِ خطاها را می‌دهد."""
    out = os.path.abspath(out)
    problems = []

    # ۱) ریشهٔ بسته: نبودنِ همین فایل، دقیقاً همان ۴۰۴ی است که میزبان می‌دهد
    root_index = os.path.join(out, "index.html")
    if not os.path.isfile(root_index):
        problems.append("`index.html` در ریشهٔ بسته نیست → `/` روی هر میزبانی ۴۰۴ "
                        "می‌شود (خطایِ Vercel: 404 NOT_FOUND)")

    # ۲) .nojekyll — وگرنه Jekyll در Pages فایل‌های زیرِ `_` و … را می‌سوزاند
    if not os.path.isfile(os.path.join(out, ".nojekyll")):
        problems.append("`.nojekyll` نیست — Jekyll می‌تواند بخشی از بسته را حذف کند")

    # ۳) منابعی که سایت هنگامِ اجرا می‌خواند، باید از هر دوِ مسیرِ ورود قابل‌دسترس باشند
    #    `/index.html`  → ROOT = ""     ⇒  `<بسته>/<منبع>`
    #    `/site/index.html` → ROOT = "../" ⇒  باز هم `<بسته>/<منبع>` (یکی بالا، همان ریشه)
    for req in sorted(requests_from_pages()):
        if not os.path.isfile(os.path.join(out, req)):
            problems.append("منبعِ `%s` که سایت درخواست می‌کند در بسته نیست → ۴۰۴" % req)

    for entry in ("index.html", os.path.join("site", "index.html")):
        if not os.path.isfile(os.path.join(out, entry)):
            problems.append("صفحهٔ `/%s` در بسته نیست" % entry.replace(os.sep, "/"))

    # ۴) داشبوردِ جاسازی‌شده
    if not os.path.isfile(os.path.join(out, "dashboard", "index.html")):
        problems.append("`dashboard/index.html` در بسته نیست → بخشِ «داشبورد زنده» خالی می‌ماند")

    # ۵) صفحهٔ سایت باید همان باشد، نه صفحهٔ جایگزین/خالی
    if os.path.isfile(root_index):
        with open(root_index, encoding="utf-8") as f:
            body = f.read()
        if "اتوماسیون یکپارچه کارخانه" not in body:
            problems.append("ریشهٔ بسته `index.html` است ولی محتوای سایت را ندارد")
    return problems


def report(problems, out, copied, quiet=False):
    if problems:
        print("\n✗ بستهٔ انتشار (%s) ناکامل است — %d مورد:" % (out, len(problems)),
              file=sys.stderr)
        for p in problems:
            print("  • %s" % p, file=sys.stderr)
        print("\n  راهنما: `python3 tools/build_site.py` و سپس "
              "`python3 -m http.server 8080 -d %s`" % out, file=sys.stderr)
        return 1
    if not quiet:
        print("✓ بستهٔ انتشار سالم است — %d فایل در %s" % (copied, out))
        print("  بررسیِ محلی: python3 -m http.server 8080 -d %s" % out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="ساخت و اعتبارسنجیِ بستهٔ انتشار (_site)")
    ap.add_argument("--out", default=os.path.join(BASE, "_site"),
                    help="پوشهٔ مقصد (پیش‌فرض: _site)")
    ap.add_argument("--check", action="store_true",
                    help="بساز در پوشهٔ موقت و فقط بررسی کن (هیچ فایلی در مخزن نمی‌نویسد)")
    ap.add_argument("--quiet", action="store_true", help="بدونِ خطِ پیشرفت")
    args = ap.parse_args(argv)

    if args.check:
        tmp = tempfile.mkdtemp(prefix="build_site_")
        try:
            copied = build(tmp, quiet=True)
            return report(verify(tmp, quiet=True), tmp, copied, quiet=args.quiet)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    copied = build(args.out, quiet=args.quiet)
    return report(verify(args.out, quiet=args.quiet), args.out, copied, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
