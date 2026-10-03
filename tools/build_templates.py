#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تولید مستنداتی که «متنِ ثابت + جدولِ داده‌محور» دارند.

چرا این روش؟
    برخی مستندات (۷، ۱۰، ۱۳) شامل تحلیل و نثرِ دست‌نویس‌اند که نباید از دست برود،
    اما جدول‌هایشان دادهٔ ساختاریافته است. راه‌حل: متن در قالب (template) می‌ماند و
    جدول‌ها با نشانهٔ {{name}} از روی فایل‌های CSV ساخته می‌شوند.

اجرا:  python3 tools/build_templates.py
ویرایش ایمن:
    - برای تغییرِ یک جدول  → فایل CSV متناظر در data/ را ویرایش کنید
    - برای تغییرِ متن       → قالب متناظر در tools/templates/ را ویرایش کنید
    - خروجی در docs/ را هرگز دستی ویرایش نکنید
"""
import csv
import os
import re
import sys
from collections import OrderedDict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TPL = os.path.join(BASE, "tools", "templates")
DOCS = os.path.join(BASE, "docs")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name, text):
    path = os.path.join(DOCS, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
    print(f"✓ {name} ({len(text.splitlines())} خط)")


# ───────────────────────────────────────────── رندرکننده‌ها
def _row(cells):
    """یک سطرِ جدول؛ خانهٔ خالی دقیقاً مانند متنِ اصلی رندر می‌شود."""
    return "|" + "".join(" " + c + (" |" if c else "|") for c in cells)


def simple_table(rows, headers, keys, default="—"):
    """جدولِ ساده: هر ردیف یک سطر."""
    out = [_row(headers), "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        cells = []
        for k in keys:
            v = (r.get(k) or "").strip()
            cells.append(v if v else default)
        out.append(_row(cells))
    return "\n".join(out)


def wide_table(rows, row_key, col_key, val_key, row_header, default="—",
               col_order=None, row_prefix=None):
    """جدولِ پهن (ماتریس): از قالبِ طویلِ CSV به نمایشِ ماتریسی باز می‌گردد.

    col_order: ترتیبِ قطعیِ ستون‌ها (اگر داده نشود، از ترتیبِ رؤیت استخراج می‌شود)
    row_prefix: نامِ ستونی که پیش از عنوانِ ردیف می‌آید (مانند شمارهٔ فعالیت)
    """
    row_order, seen_r = [], set()
    for r in rows:
        a = r[row_key]
        if a not in seen_r:
            seen_r.add(a); row_order.append(a)
    if col_order is None:
        col_order, seen_c = [], set()
        for r in rows:
            b = r[col_key]
            if b not in seen_c:
                seen_c.add(b); col_order.append(b)
    else:
        present = {r[col_key] for r in rows}
        col_order = [c for c in col_order if c in present]
        col_order += sorted(present - set(col_order))
    grid = {(r[row_key], r[col_key]): (r[val_key] or "").strip() for r in rows}

    n_lead = 2 if row_prefix else 1
    lead = [row_header] if not row_prefix else ["#", row_header]
    out = [_row(lead + col_order),
           "|" + "|".join(["---"] * (len(col_order) + n_lead)) + "|"]
    prefix_of = {r[row_key]: (r.get(row_prefix) or "").strip() for r in rows} if row_prefix else {}
    for a in row_order:
        cells = [grid.get((a, b)) or default for b in col_order]
        head = [prefix_of[a]] if row_prefix else []
        out.append(_row(head + [a] + cells))
    return "\n".join(out)


# ───────────────────────────────────────────── تعریفِ نشانه‌ها
def build_placeholders():
    """نگاشتِ نامِ نشانه → متنِ جدول."""
    p = OrderedDict()

    p["roles"] = simple_table(
        read("roles.csv"),
        ["کد نقش", "نام نقش", "محیط کار", "سطح دسترسی پیش‌فرض", "ابزار"],
        ["code", "role_fa", "workplace", "access_level", "devices"])

    role_order = [r["code"] for r in read("roles.csv")]
    p["ui_matrix"] = wide_table(
        read("ui_matrix.csv"), "page", "role", "access", "صفحه / فرم",
        col_order=role_order)

    p["raci"] = wide_table(
        read("raci.csv"), "activity", "actor", "value", "فعالیت/تصمیم",
        row_prefix="activity_id")

    p["rbac"] = wide_table(
        read("rbac.csv"), "role", "module", "access", "نقش")

    p["sod_rules"] = simple_table(
        read("sod_rules.csv"), ["#", "قاعده SoD", "کنترل سیستمی"],
        ["id", "rule", "control"])

    p["uat_scenarios"] = simple_table(
        read("uat_scenarios.csv"), ["#", "سناریو", "مسیر", "معیار عبور دقیق"],
        ["id", "scenario", "flow", "pass_criteria"])

    p["uat_criteria"] = simple_table(
        read("uat_criteria.csv"), ["حوزه", "معیار", "آستانه", "روش اندازه‌گیری"],
        ["area", "criterion", "threshold", "measurement"])

    # ── ۰۶. سخت‌افزار و سنسورها ──
    p["sensors"] = simple_table(
        read("sensors.csv"),
        ["واحد", "گروه‌های اصلی تجهیزات", "شمار تقریبی نقطه/دستگاه [فرض]", "سهم از بودجهٔ سخت‌افزار"],
        ["unit", "groups", "count", "budget_share"])
    p["hw_principles"] = simple_table(
        read("hw_principles.csv"), ["اصل", "الزام", "دلیل"],
        ["principle", "requirement", "reason"])
    p["hw_standards"] = simple_table(
        read("hw_standards.csv"), ["حوزه", "مرجع"], ["area", "reference"])
    p["hw_cost_items"] = simple_table(
        read("hw_cost_items.csv"), ["ردیف", "چرا مهم است"], ["item", "why"])

    # ── ۱۵. الزامات غیرکارکردی، امنیت و انطباق ──
    p["nfr"] = simple_table(
        read("nfr.csv"),
        ["دسته", "نیازمندی", "مقدار هدف", "روش اندازه‌گیری", "اولویت"],
        ["category", "requirement", "target", "measurement", "priority"])
    p["sl_targets"] = simple_table(
        read("sl_targets.csv"), ["زون", "SL هدف", "توضیح"],
        ["zone", "sl_target", "description"], default="")
    p["ot_controls"] = simple_table(
        read("ot_controls.csv"), ["حوزه", "کنترل", "وضعیت الزام"],
        ["area", "control", "status"])
    p["compliance"] = simple_table(
        read("compliance.csv"),
        ["استاندارد/الزام", "دامنه", "الزامات سیستمیِ مرتبط", "مدرک/شاهد"],
        ["standard", "scope", "requirements", "evidence"])
    p["audit_reports"] = simple_table(
        read("audit_reports.csv"), ["گزارش ممیزی", "محتوا", "منبع"],
        ["report", "content", "source"])

    # ── ۱۸. مدل داده ──
    p["entities"] = simple_table(
        read("entities.csv"),
        ["موجودیت", "سرویس مالک", "کلید", "ارجاع‌های اصلی", "کلاس نگه‌داری"],
        ["entity", "service", "key", "refs", "retention_class"])
    p["id_conventions"] = simple_table(
        read("id_conventions.csv"), ["نوع", "قالب", "مثال", "توضیح"],
        ["type", "fmt", "example", "note"])
    p["retention_classes"] = simple_table(
        read("retention_classes.csv"),
        ["کلاس", "دامنه", "مدت", "رسانه", "قابل حذف؟"],
        ["cls", "scope", "duration", "media", "deletable"])
    p["integrity_rules"] = simple_table(
        read("integrity_rules.csv"), ["رابطه", "سیاست", "مکانیزم کنترل"],
        ["relation", "policy", "mechanism"])
    p["scd_policies"] = simple_table(
        read("scd_policies.csv"), ["نوع تغییر", "سیاست", "مثال"],
        ["change_type", "policy", "example"])
    p["conformed_dims"] = simple_table(
        read("conformed_dims.csv"), ["بُعد", "منبع", "کلید", "ویژگی‌های کلیدی"],
        ["dimension", "source", "key", "features"])

    return p


def strip_template_notice(text):
    """بلوکِ توضیحیِ بالای قالب را از خروجی حذف می‌کند (فقط مخصوصِ قالب است)."""
    lines = text.split("\n")
    out, skipping = [], False
    for ln in lines:
        if ln.startswith("> این قالب، منبعِ متنِ"):
            skipping = True
            continue
        if skipping:
            if ln.startswith(">"):
                continue
            if ln.strip() == "":
                skipping = False
            continue
        out.append(ln)
    # حذفِ خطوط خالیِ اضافیِ پس از عنوان
    cleaned, i = [], 0
    while i < len(out):
        if out[i].strip() == "" and cleaned and cleaned[-1].strip() == "":
            i += 1
            continue
        cleaned.append(out[i]); i += 1
    return "\n".join(cleaned)


# ───────────────────────────────────────────── اجرا
def main():
    ph = build_placeholders()
    files = sorted(f for f in os.listdir(TPL) if f.endswith(".md"))
    if not files:
        print("هیچ قالبی در tools/templates/ یافت نشد", file=sys.stderr)
        return 1

    for name in files:
        with open(os.path.join(TPL, name), encoding="utf-8") as f:
            text = f.read()
        missing = [m for m in re.findall(r"\{\{(\w+)\}\}", text) if m not in ph]
        if missing:
            print(f"✗ {name}: نشانهٔ تعریف‌نشده: {missing}", file=sys.stderr)
            return 1
        for key, table in ph.items():
            text = text.replace("{{%s}}" % key, table)
        text = strip_template_notice(text)
        write(name, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
