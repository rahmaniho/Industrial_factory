#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسیِ سرتاسریِ انتشار در گیت‌هاب پیج.

چرا این ابزار وجود دارد؟
    انتشار در Pages می‌تواند از چند جا شکست بخورد و هیچ‌کدام در ساختِ محلی
    دیده نمی‌شود: مخزن اصلاً Pages را فعال نکرده باشد، workflow روی شاخهٔ
    موردنظر اجرا نشود، artifact بارگذاری نشود، یا گامِ deploy شکست بخورد.
    این اسکریپت همهٔ این‌ها را یکی‌یکی چک می‌کند و دقیقاً می‌گوید کدام حلقه
    از زنجیره سبز است و کدام نه.

پیش‌نیاز:  gh (با ورودِ انجام‌شده) — نیازی به دسترسیِ مدیریتی ندارد.

اجرا:      python3 tools/check_pages.py
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

    # ── ۵. نشانیِ زنده ──
    print("\n۵. نشانیِ زنده")
    st = http_head(PAGES_URL_REAL)
    if st != 200:
        record(False, "صفحه در دسترس است", "HTTP %s — %s" % (st, PAGES_URL_REAL),
               "اگر Pages تازه فعال شده، یک تا دو دقیقه صبر کنید")
        return finish()
    record(True, "صفحه در دسترس است", "HTTP 200 — %s" % PAGES_URL_REAL)

    code, body = http_get(PAGES_URL_REAL)
    checks = [
        ("عنوانِ صفحه", "طراحی و پیاده‌سازی اتوماسیون یکپارچه کارخانه" in body),
        ("هیچ وابستگیِ خارجی", "cdn." not in body and "http://" not in body),
        ("دکمهٔ «نقش من»", 'data-sec="s-role"' in body),
        ("نشانیِ نسبیِ داشبورد", 'data-src="dashboard/index.html"' in body),
    ]
    for name, good in checks:
        record(good, name, "درست" if good else "یافت نشد")

    for path, want in (("data/kpi_catalog.csv", "OEE"),
                       ("data/role_journey.csv", "اپراتور"),
                       ("dashboard/index.html", "داشبورد")):
        st, body2 = http_get(PAGES_URL_REAL + path)
        record(st == 200 and (want in body2 if want else True),
               "منبع: %s" % path, "HTTP %s" % st)

    return finish()


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
