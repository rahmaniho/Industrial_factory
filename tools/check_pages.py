#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسیِ سرتاسریِ انتشار در گیت‌هاب پیج.

چرا این ابزار وجود دارد؟
    انتشار در Pages می‌تواند از چند جا شکست بخورد و هیچ‌کدام در ساختِ محلی
    دیده نمی‌شود: مخزن اصلاً Pages را فعال نکرده باشد، workflow روی شاخهٔ
    موردنظر اجرا نشود، artifact بارگذاری نشود، یا گامِ deploy شکست بخورد.
    این اسکریپت همهٔ این‌ها را یکی‌یکی چک می‌کند و دقیقاً می‌گوید کدام حلقه
    از زنجیره سبز است و کدام نه.

    از نسخهٔ جاری، گامِ ۵ روی **هر دو میزبان** سنجیده می‌شود: Pages و
    Vercel (`industrialautomation-seven.vercel.app`). این همان جایی است که
    خطایِ `404 NOT_FOUND` دیده شد؛ چکِ `/` روی میزبانِ دوم فوراً می‌گوید
    build اجرا شده یا ریشهٔ مخزن بی‌واسطه منتشر می‌شود.

پیش‌نیاز:  gh (با ورودِ انجام‌شده) — نیازی به دسترسیِ مدیریتی ندارد.

اجرا:      python3 tools/check_pages.py                # Pages + Vercel
           python3 tools/check_pages.py --pages-only     # فقط Pages
           python3 tools/check_pages.py --local http://127.0.0.1:8080/
                              # سنجشِ بستهٔ ساخته‌شده در محلی (بدونِ gh)
خروجی:     0 = انتشار موفق · 1 = مانعی وجود دارد
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "rahmaniho/Industrial_factory"
PAGES_URL = "https://rahmaniho.github.io/Industrial_factory/"
# میزبانِ دوم: همان بستهٔ _site را با vercel.json می‌سازد. اگر `/` اینجا ۴۰۴ داد،
# یعنی build اجرا نشده (یا vercel.json گم شده) و ریشهٔ مخزن منتشر می‌شود.
VERCEL_URL = "https://industrialautomation-seven.vercel.app/"
WORKFLOW = "pages.yml"
SETTINGS_URL = "https://github.com/%s/settings/pages" % REPO

OK, BAD, WARN = "✓", "✗", "!"
results = []


def record(ok, name, detail, hint=""):
    results.append((ok, name, detail, hint))
    print("  %s %-34s %s" % (OK if ok else BAD, name, detail))
    if hint and not ok:
        print("      %s %s" % (WARN, hint))
    return ok


def gh(*args):
    """اجرای gh و برگرداندنِ (کد، خروجی)."""
    try:
        p = subprocess.run(("gh",) + args, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "gh یافت نشد"
    except subprocess.TimeoutExpired:
        return 124, "", "زمانِ انتظارِ gh تمام شد"


def http_head(url, timeout=20):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def http_get(url, timeout=25):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def main():
    # حالتِ محلی: فقط بسته‌ای که همین حالا ساخته شده را می‌سنجد (بی‌نیاز از gh)
    if "--local" in sys.argv:
        i = sys.argv.index("--local")
        if i + 1 >= len(sys.argv):
            print("✗ بعد از --local باید نشانی بیاید، مثل: --local http://127.0.0.1:8080/",
                  file=sys.stderr)
            return 1
        print("بررسیِ بستهٔ محلی — %s\n" % sys.argv[i + 1])
        check_live(sys.argv[i + 1], "محلی")
        return finish()

    print("بررسیِ انتشار در گیت‌هاب پیج — %s\n" % REPO)

    # ── ۱. Pages روی مخزن فعال است؟ ──
    print("۱. تنظیماتِ مخزن")
    code, out, err = gh("api", "repos/%s/pages" % REPO)
    pages_on = code == 0
    info = {}
    if pages_on:
        try:
            info = json.loads(out)
            PAGES_URL_REAL = info.get("html_url") or PAGES_URL
        except Exception:
            PAGES_URL_REAL = PAGES_URL
    else:
        PAGES_URL_REAL = PAGES_URL
    record(pages_on, "Pages روی مخزن فعال است",
           ("build_type=%s | %s" % (info.get("build_type"), info.get("html_url", "")))
           if pages_on else "فعال نیست (پاسخِ ۴۰۴ از API)",
           "فقط مالکِ مخزن می‌تواند فعال کند: %s" % SETTINGS_URL)

    # ── ۲. آخرین اجرای workflow ──
    print("\n۲. آخرین اجرای workflow")
    code, out, _ = gh("run", "list", "--workflow", WORKFLOW, "--limit", "1",
                      "--json", "databaseId,status,conclusion,displayTitle,headBranch")
    if code != 0 or not out:
        record(False, "یافتنِ آخرین اجرا", "ناموفق", "gh در دسترس و واردشده است؟")
        return finish()
    runs = json.loads(out)
    if not runs:
        record(False, "یافتنِ آخرین اجرا", "هیچ اجرایی ثبت نشده",
               "یک push به main یا arena/** بفرستید")
        return finish()
    run = runs[0]
    rid = str(run["databaseId"])
    record(run["conclusion"] == "success", "نتیجهٔ کل",
           "%s (شاخه: %s · %s)" % (run["conclusion"], run.get("headBranch"), rid[:12]))

    # ── ۳. گام‌ها ──
    print("\n۳. گام‌های اجرا")
    code, out, _ = gh("run", "view", rid, "--json", "jobs")
    jobs = {}
    if code == 0 and out:
        try:
            jobs = {j["name"]: j for j in json.loads(out)["jobs"]}
        except Exception:
            pass
    for want in ("build", "deploy"):
        j = jobs.get(want)
        if not j:
            record(False, "گامِ %s" % want, "اجرا نشده", "")
            continue
        failed = [s["name"] for s in j.get("steps", []) if s.get("conclusion") == "failure"]
        record(j.get("conclusion") == "success", "گامِ %s" % want,
               j.get("conclusion") or "—",
               ("گام‌های شکست‌خورده: %s" % "، ".join(failed)) if failed else "")

    # ── ۴. artifact ──
    print("\n۴. بستهٔ انتشار")
    code, out, _ = gh("api", "repos/%s/actions/runs/%s/artifacts" % (REPO, rid))
    arts = []
    if code == 0 and out:
        try:
            arts = json.loads(out).get("artifacts", [])
        except Exception:
            pass
    if arts:
        a = arts[0]
        size = a.get("size_in_bytes", 0)
        record(not a.get("expired", True), "بستهٔ انتشار بارگذاری شده",
               "%s (%.0f کیلوبایت)" % (a.get("name"), size / 1024.0),
               "بسته منقضی شده است" if a.get("expired") else "")
    else:
        record(False, "بستهٔ انتشار بارگذاری شده", "یافت نشد", "")

    # ── ۵. نشانیِ زنده (هر دو میزبان) ──
    print("\n۵. نشانیِ زنده")
    check_live(PAGES_URL_REAL, "Pages")
    if "--pages-only" not in sys.argv:
        check_live(VERCEL_URL, "Vercel")

    return finish()


def check_live(base, label):
    """صفحه و منابعِ لازم را روی یک میزبانِ واقعی می‌سنجد.

    `/` مهم‌ترین بررسی است: اگر ۴۰۴ بدهد ولی `site/index.html` سالم باشد،
    میزبان ریشهٔ مخزن را بی‌واسطه منتشر می‌کند و build (و در نتیجه
    `tools/build_site.py`) اجرا نشده است.
    """
    base = base if base.endswith("/") else base + "/"
    st = http_head(base)
    if st != 200:
        hint = "اگر Pages تازه فعال شده، یک تا دو دقیقه صبر کنید"
        if label == "Vercel":
            hint = ("build اجرا نشده؟ vercel.json باید outputDirectory=_site را بدهد "
                    "(یا میزبان را روی ریشهٔ مخزن گذاشته‌اید) — وگرنه `/` بدون "
                    "index.html در ریشه ۴۰۴ می‌ماند")
        record(False, "%s: صفحه در دسترس است" % label, "HTTP %s — %s" % (st, base), hint)
        return False
    record(True, "%s: صفحه در دسترس است" % label, "HTTP 200 — %s" % base)

    code, body = http_get(base)
    checks = [
        ("عنوانِ صفحه", "طراحی و پیاده‌سازی اتوماسیون یکپارچه کارخانه" in body),
        ("دکمهٔ «نقش من»", 'data-sec="s-role"' in body),
        ("نشانیِ نسبیِ داشبورد", 'data-src="dashboard/index.html"' in body),
    ]
    if label == "Pages":
        checks.insert(1, ("هیچ وابستگیِ خارجی", "cdn." not in body and "http://" not in body))
    for name, good in checks:
        record(good, "%s: %s" % (label, name), "درست" if good else "یافت نشد")

    for path, want in (("data/kpi_catalog.csv", "OEE"),
                       ("data/role_journey.csv", "اپراتور"),
                       ("docs/00-executive-summary.md", "#"),
                       ("dashboard/index.html", "داشبورد")):
        st, body2 = http_get(base + path)
        record(st == 200 and (want in body2 if want else True),
               "%s: منبع %s" % (label, path), "HTTP %s" % st)

    # صفحهٔ کهنه باید همچنان کار کند (پیوندهای بیرونی به /site/index.html هست)
    st = http_head(base + "site/index.html")
    record(st == 200, "%s: مسیرِ کهنه /site/index.html" % label, "HTTP %s" % st)
    return True


def finish():
    bad = [r for r in results if not r[0]]
    print("\n" + "─" * 62)
    if bad:
        print("✗ %d مورد از %d بررسی ناموفق است." % (len(bad), len(results)))
        print("\nمانعِ اصلی:")
        for _, name, detail, hint in bad:
            print("  • %s — %s" % (name, detail))
            if hint:
                print("    %s" % hint)
        print("\nراهنما: %s" % SETTINGS_URL)
        return 1
    print("✓ همهٔ %d بررسی گذشت — انتشار بدون خطا انجام شده است." % len(results))
    print("  نشانی: %s" % PAGES_URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
