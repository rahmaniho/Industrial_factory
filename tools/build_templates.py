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


def role_journey_blocks(rows, roles, headers, keys):
    """سفرِ کاریِ هر نقش: به‌ازای هر نقش یک بلوک با جدولِ گام‌ها."""
    by = OrderedDict()
    for r in rows:
        by.setdefault(r["code"], []).append(r)
    out = []
    for code in roles:
        items = by.get(code)
        if not items:
            continue
        name = items[0].get("role_fa", "")
        out.append(f"**{code} — {name}**\n")
        items.sort(key=lambda r: int(r["step"]))
        out.append(simple_table(items, headers, keys))
        out.append("")
    return "\n".join(out).rstrip()


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


    # ── نگاشتِ نقش و سفرِ کاری ──
    roles_by_code = {r["code"]: r for r in read("roles.csv")}
    rmap = read("role_map.csv")
    for r in rmap:
        r["role_fa"] = roles_by_code.get(r["code"], {}).get("role_fa", "")
    p["role_raci_map"] = simple_table(
        rmap, ["کد", "نقش", "بازیگر در ماتریس RACI", "ردیف در ماتریس صفحه‌ها"],
        ["code", "role_fa", "raci_actor", "ui_role"])

    jour = read("role_journey.csv")
    for r in jour:
        r["role_fa"] = roles_by_code.get(r["code"], {}).get("role_fa", "")
    p["role_journey"] = role_journey_blocks(
        jour, [r["code"] for r in read("roles.csv")],
        ["#", "فاز", "آنچه در سامانه انجام می‌دهد", "سامانه", "خروجی/اثرِ قابل‌ردیابی"],
        ["step", "phase", "action", "system", "evidence"])


    # ── ۰۰. خلاصهٔ مدیریتی ──
    p["gaps"] = simple_table(
        read("gaps.csv"), ["گسست", "نشانهٔ میدانی", "هزینهٔ پنهان"],
        ["gap", "symptom", "hidden_cost"])
    p["adr_summary"] = simple_table(
        read("adr_summary.csv"), ["ADR", "تصمیم", "جایگزینِ رد‌شده", "دلیل رد"],
        ["adr", "decision", "rejected", "why"])
    p["exec_targets"] = simple_table(
        read("exec_targets.csv"),
        ["شاخص", "واحد", "Baseline [فرض]", "هدف ۱۸ ماهه", "هدف ۳۰ ماهه", "منبع"],
        ["metric", "unit", "baseline", "target_18m", "target_30m", "source"])
    p["phases"] = phase_table(read("phase_summary.csv"), read("roadmap.csv"))
    p["exec_finance"] = simple_table(
        read("exec_finance.csv"), ["مورد", "مقدار"], ["item", "value"])
    p["governance"] = simple_table(
        read("governance.csv"), ["نقش", "مسئولیت", "تصمیمات اختصاصی"],
        ["role", "responsibility", "decisions"])

    # ── ۰۱. ورودی‌ها و مفروضات ──
    p["input_params"] = simple_table(
        read("input_params.csv"),
        ["پارامتر", "مقدار فرضی", "برچسب", "روش تأیید (فاز ۰)"],
        ["param", "assumed_value", "tag", "verify"])
    p["assumptions"] = simple_table(
        read("assumptions.csv"),
        ["#", "فرض", "ریسک اگر غلط باشد", "نشانهٔ هشدار"],
        ["id", "assumption", "risk_if_wrong", "warning_sign"])
    p["glossary"] = simple_table(
        read("glossary.csv"), ["اختصار", "معادل فارسی", "توضیح کوتاه"],
        ["abbr", "fa", "desc"])
    p["unit_codes"] = simple_table(
        read("unit_codes.csv"), ["کد", "واحد", "کد", "واحد"],
        ["code_a", "name_a", "code_b", "name_b"], default="")

    # ── ۲۲. انتخاب تأمین‌کننده ──
    p["vendor_criteria"] = simple_table(
        read("vendor_criteria.csv"), ["#", "معیار", "وزن", "آنچه واقعاً می‌سنجیم"],
        ["id", "criterion", "weight", "what_it_measures"])
    p["vendor_knockout"] = simple_table(
        read("vendor_knockout.csv"), ["#", "شرط حذف", "دلیل"],
        ["id", "condition", "reason"])
    p["vendor_models"] = simple_table(
        read("vendor_models.csv"), ["مدل", "مزایا", "معایب", "دامنهٔ پیشنهادی"],
        ["model", "pros", "cons", "scope"])
    p["vendor_scores"] = simple_table(
        read("vendor_scores.csv"),
        ["معیار", "وزن", "تأمین‌کنندهٔ الف", "تأمین‌کنندهٔ ب", "تأمین‌کنندهٔ ج"],
        ["criterion", "weight", "v_a", "v_b", "v_c"], default="")
    p["poc_schedule"] = simple_table(
        read("poc_schedule.csv"), ["روز", "فعالیت"], ["day", "activity"])
    p["contract_clauses"] = simple_table(
        read("contract_clauses.csv"), ["#", "بند", "چرا حیاتی است"],
        ["id", "clause", "why_critical"])
    p["vendor_pitfalls"] = simple_table(
        read("vendor_pitfalls.csv"), ["اشتباه", "پیامد", "پیشگیری در این فرآیند"],
        ["mistake", "consequence", "prevention"])

    # ── ۲۳. انتقال و مهاجرت داده ──
    p["cutover_principles"] = simple_table(
        read("cutover_principles.csv"), ["اصل", "تصمیم"], ["principle", "decision"])
    p["migration_domains"] = simple_table(
        read("migration_domains.csv"),
        ["حوزه داده", "حجم [فرض]", "روش", "کیفیتِ هدف", "مسئول"],
        ["domain", "volume", "method", "target_quality", "owner"])
    p["cutover_prep"] = simple_table(
        read("cutover_prep.csv"), ["زمان", "اقدام", "مسئول", "معیار عبور"],
        ["time", "action", "owner", "exit_criteria"])
    p["cutover_day"] = simple_table(
        read("cutover_day.csv"), ["زمان", "اقدام", "مسئول"],
        ["time", "action", "owner"])
    p["post_cutover"] = simple_table(
        read("post_cutover.csv"), ["بازه", "اقدام", "معیار خروج"],
        ["window", "action", "exit_criteria"])
    p["reconciliation"] = simple_table(
        read("reconciliation.csv"), ["مورد", "روش", "آستانه", "فرکانس در ماه نخست"],
        ["item", "method", "threshold", "frequency"])

    return p


def fa(n):
    """تبدیل عدد به ارقام فارسی."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def phase_table(rows, road):
    """جدولِ فازها در خلاصهٔ مدیریتی: بازه و بودجه از roadmap.csv حساب می‌شود،
    نه از دست. با این کار ادعای «این اعداد از CSV محاسبه شده‌اند» واقعی می‌ماند."""
    agg = OrderedDict()
    for r in road:
        agg.setdefault(r["phase"], []).append(r)
    out = [_row(["فاز", "بازه (هفته)", "بودجه (M USD)", "اصلی‌ترین خروجی"]),
           "|---|---|---|---|"]
    tlo = thi = 0.0
    wmin, wmax = None, None
    for r in rows:
        items = agg.get(r["phase"], [])
        if not items:
            continue
        lo = sum(float(i["cost_low_musd"]) for i in items)
        hi = sum(float(i["cost_high_musd"]) for i in items)
        ws = min(int(i["start_week"]) for i in items)
        we = max(int(i["start_week"]) + int(i["duration_weeks"]) for i in items)
        tlo += lo; thi += hi
        wmin = ws if wmin is None else min(wmin, ws)
        wmax = we if wmax is None else max(wmax, we)
        out.append(_row([r["label"], "%s–%s" % (fa(ws), fa(we)),
                         "%s–%s" % (fa("%.2f" % lo), fa("%.2f" % hi)),
                         r["main_output"]]))
    span = "**%s–%s (≈ ۲۴ ماه؛ تا ۳۰ ماه با احتیاط)**" % (fa(wmin), fa(wmax))
    out.append(_row(["**جمع**", span, "**%s–%s**" % (fa("%.2f" % tlo), fa("%.2f" % thi)), "—"]))
    return "\n".join(out)


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
