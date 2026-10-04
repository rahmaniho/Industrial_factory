#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد مستند «ماتریس یکپارچگی بین‌واحدی» از روی فایل CSV.

فلسفه: فایل data/integration_matrix.csv تنها منبع حقیقت است؛ این اسکریپت
هم جدول‌های انسانی (Markdown) و هم آمار را از آن تولید می‌کند تا مستند
هیچ‌وقت با داده مغایرت پیدا نکند.

اجرا:  python3 tools/build_integration_matrix.py
خروجی: docs/04-integration-matrix.md
"""
import csv
import os
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, "data", "integration_matrix.csv")
OUT_PATH = os.path.join(BASE, "docs", "04-integration-matrix.md")

NODES = ["SEC", "HSE", "PRD", "QCL", "MRO", "RMW", "FGW", "HRM", "SAL",
         "EXP", "FIN", "MNT", "ELE", "MEC", "UTL", "MDM", "ERP", "BI"]

NODE_FA = {
    "SEC": "حراست", "HSE": "HSE", "PRD": "تولید", "QCL": "QC/LIMS", "MRO": "انبار فنی",
    "RMW": "انبار مواد", "FGW": "انبار محصول", "HRM": "منابع انسانی", "SAL": "بازرگانی داخلی",
    "EXP": "بازرگانی خارجی", "FIN": "مالی", "MNT": "نگهداشت", "ELE": "برق", "MEC": "مکانیک",
    "UTL": "تأسیسات", "MDM": "داده پایه", "ERP": "ERP", "BI": "BI/DWH",
}

MECH_ABBR = {"API": "API", "Event": "EV", "Event+API": "EV", "API+Event": "EV",
             "OPC-UA": "OPC", "OPC-UA+Event": "OPC", "OPC-UA+API": "OPC",
             "API+OPC-UA": "OPC", "API+File": "File", "DB+Event": "DB", "DB": "DB",
             "Event+DB": "DB", None: "—"}

FREQ_ABBR = {"Real-time": "RT", "Minutes": "MIN", "Hourly": "H", "Daily": "D",
             "Weekly": "W", "Monthly": "M", "Per-shift": "SH", "On-event": "OE"}

FREQ_FA = {"Real-time": "بلادرنگ", "Minutes": "دقیقه‌ای", "Hourly": "ساعتی", "Daily": "روزانه",
           "Weekly": "هفتگی", "Monthly": "ماهانه", "Per-shift": "شیفتی", "On-event": "رویدادی"}

DIR_FA = {"one-way": "→", "two-way": "↔"}
CRIT_FA = {"Critical": "بحرانی", "High": "بالا", "Medium": "متوسط", "Low": "پایین"}
COL_GROUP = 6


def fa(n):
    """تبدیل عدد به ارقام فارسی."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def load_rows():
    rows = []
    errors = []
    with open(CSV_PATH, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            s, t = r["source"].strip(), r["target"].strip()
            if s not in NODES or t not in NODES:
                errors.append(f"ردیف {i}: کد نامعتبر {s}→{t}")
                continue
            if s == t:
                continue  # خودِ واحد
            rows.append({
                "source": s, "target": t, "data": r["data"].strip(),
                "direction": r["direction"].strip(), "mechanism": r["mechanism"].strip(),
                "frequency": r["frequency"].strip(), "owner": r["owner"].strip(),
                "criticality": r["criticality"].strip(), "notes": r["notes"].strip(),
            })
    return rows, errors


def build_edges(rows):
    """هر رابطهٔ دوطرفه به دو یال جهت‌دار تبدیل می‌شود."""
    edges = {}
    for r in rows:
        pairs = [(r["source"], r["target"])]
        if r["direction"] == "two-way":
            pairs.append((r["target"], r["source"]))
        for s, t in pairs:
            key = (s, t)
            # اگر چند رابطه بین دو گره وجود داشت، بحرانی‌ترین را نگه می‌داریم
            if key not in edges or rank(r["criticality"]) > rank(edges[key]["criticality"]):
                edges[key] = r
    return edges


def rank(c):
    return {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(c, 0)


def cell(edge):
    if not edge:
        return "—"
    d = DIR_FA.get(edge["direction"], "→")
    m = MECH_ABBR.get(edge["mechanism"], edge["mechanism"])
    fq = FREQ_ABBR.get(edge["frequency"], edge["frequency"])
    star = "*" if edge["criticality"] == "Critical" else ""
    return f"{d}{m}·{fq}{star}"


def grid_tables(edges):
    out = []
    for start in range(0, len(NODES), COL_GROUP):
        cols = NODES[start:start + COL_GROUP]
        out.append("")
        out.append(f"**گروه {start // COL_GROUP + 1} — ستون‌ها: "
                   + "، ".join(f"`{c}` ({NODE_FA[c]})" for c in cols) + "**")
        out.append("")
        out.append("| مبدأ ↓ / مقصد → | " + " | ".join(f"`{c}`" for c in cols) + " |")
        out.append("|---|" + "---|" * len(cols))
        for s in NODES:
            cells = [cell(edges.get((s, c))) for c in cols]
            out.append(f"| **{s}** {NODE_FA[s]} | " + " | ".join(cells) + " |")
    return out


def detail_tables(edges):
    by_src = defaultdict(list)
    for (s, t), e in edges.items():
        by_src[s].append((t, e))
    out = []
    for s in NODES:
        items = sorted(by_src.get(s, []), key=lambda x: (-rank(x[1]["criticality"]), x[0]))
        if not items:
            continue
        out.append("")
        out.append(f"#### {s} — {NODE_FA[s]}")
        out.append("")
        out.append("| مقصد | دادهٔ مبادله‌شده | جهت | مکانیزم | فرکانس | مالک داده | حساسیت | ملاحظه |")
        out.append("|---|---|---|---|---|---|---|---|")
        for t, e in items:
            out.append(
                f"| {t} {NODE_FA[t]} | {e['data']} | {DIR_FA.get(e['direction'],'→')} | "
                f"{e['mechanism']} | {FREQ_FA.get(e['frequency'], e['frequency'])} | "
                f"{e['owner']} | {CRIT_FA.get(e['criticality'], e['criticality'])} | "
                f"{e['notes'] if e['notes'] and e['notes'] != '-' else '—'} |"
            )
    return out


def stats(edges):
    mech = Counter()
    freq = Counter()
    crit = Counter()
    for e in edges.values():
        mech[e["mechanism"]] += 1
        freq[e["frequency"]] += 1
        crit[e["criticality"]] += 1
    return mech, freq, crit


def main():
    rows, errors = load_rows()
    edges = build_edges(rows)
    mech, freq, crit = stats(edges)

    L = []
    A = L.append
    A("# ۴. ماتریس یکپارچگی بین‌واحدی (Integration Matrix)")
    A("")
    A("> این مستند به‌طور خودکار از `data/integration_matrix.csv` تولید می‌شود "
      "(`python3 tools/build_integration_matrix.py`).")
    A("> برای تغییر هر رابطه، **CSV را ویرایش کنید**؛ جدول‌ها و آمار خودکار به‌روز می‌شوند.")
    A("")
    A("## ۴-۱. راهنمای خواندن ماتریس")
    A("")
    A("هر خانهٔ ماتریس شامل سه بخش است: `جهت` + `مکانیزم` · `فرکانس` + نشان حساسیت.")
    A("")
    A("| نماد | معنا |")
    A("|---|---|")
    A("| `→` | جریان یک‌طرفه (از سطر به ستون) |")
    A("| `↔` | جریان دوطرفه |")
    A("| `API` | رابط برنامه‌نویسی (REST/gRPC) — درخواست/پاسخ همزمان |")
    A("| `EV` | رویداد از طریق ستون فقرات پیام (Kafka/MQTT) — ناهمزمان |")
    A("| `OPC` | OPC UA (یا MQTT/Sparkplug از لبه) برای دادهٔ OT |")
    A("| `File` | تبادل فایل/سند (SFTP/EDI) برای اسناد رسمی و گمرکی |")
    A("| `DB` | بارگذاری مستقیم در انبار داده برای تحلیل |")
    for code, fa_label in [("RT", "بلادرنگ (زیر ثانیه تا چند ثانیه)"), ("MIN", "دقیقه‌ای"),
                      ("H", "ساعتی"), ("D", "روزانه"), ("W", "هفتگی"), ("M", "ماهانه"),
                      ("SH", "شیفتی"), ("OE", "رویدادی")]:
        A(f"| `{code}` | فرکانس: {fa_label} |")
    A("| `*` | رابطهٔ **بحرانی**: قطع آن بلافاصله تولید یا انطباق را متوقف می‌کند |")
    A("| `—` | تبادل مستقیم تعریف‌نشده — در صورت نیاز، از مسیر غیرمستقیم (MDM/BI/ERP) استفاده می‌شود |")
    A("")
    A("> **قاعدهٔ طلایی ماتریس:** هیچ خانه‌ای بدون پاسخ نمی‌ماند. خانه‌های `—` به معنای "
      "«نیازی به رابطه نیست» است، نه «نامعلوم». عدم قطعیت در این ماتریس پذیرفته نیست؛ "
      "اگر رابطه‌ای هنوز تعریف نشده، باید به‌عنوان «تعریف‌نشده — نیازمند تصمیم» در "
      "[`16-open-questions.md`](16-open-questions.md) ثبت شود.")
    A("")
    A("## ۴-۲. گره‌های ماتریس")
    A("")
    A("| کد | گره | نقش معماری |")
    A("|---|---|---|")
    roles = {
        "SEC": "واحد عملیاتی (حراست و کنترل تردد)", "HSE": "واحد عملیاتی (ایمنی و محیط‌زیست)",
        "PRD": "واحد عملیاتی (تولید — MES)", "QCL": "واحد عملیاتی (کنترل کیفیت و LIMS)",
        "MRO": "واحد عملیاتی (انبار فنی)", "RMW": "واحد عملیاتی (انبار مواد اولیه)",
        "FGW": "واحد عملیاتی (انبار محصول نهایی)", "HRM": "واحد عملیاتی (منابع انسانی)",
        "SAL": "واحد عملیاتی (بازرگانی داخلی)", "EXP": "واحد عملیاتی (بازرگانی خارجی)",
        "FIN": "واحد عملیاتی (مالی و حسابداری)", "MNT": "واحد عملیاتی (نگهداشت — CMMS)",
        "ELE": "واحد عملیاتی (برق)", "MEC": "واحد عملیاتی (مکانیک)",
        "UTL": "واحد عملیاتی (تأسیسات)",
        "MDM": "**سامانهٔ مشترک** — هاب دادهٔ پایه (Single Source of Truth)",
        "ERP": "**سامانهٔ مشترک** — هستهٔ برنامه‌ریزی منابع سازمانی",
        "BI": "**سامانهٔ مشترک** — انبار داده و هوش تجاری",
    }
    for n in NODES:
        A(f"| `{n}` | {NODE_FA[n]} | {roles[n]} |")
    A("")
    A("## ۴-۳. ماتریس کامل (۱۸×۱۸)")
    A("")
    A(f"تعداد یال‌های جهت‌دارِ تعریف‌شده: **{fa(len(edges))}** "
      f"(از {fa(len(rows))} رابطهٔ تعریف‌شده در CSV، شامل روابط دوطرفه)")
    A("")
    L.extend(grid_tables(edges))
    A("")
    A("## ۴-۴. آمار یکپارچگی")
    A("")
    A("| مکانیزم | تعداد یال | سهم |")
    A("|---|---|---|")
    for m, c in mech.most_common():
        A(f"| {m} | {c} | {c / len(edges) * 100:.0f}٪ |")
    A("")
    A("| فرکانس | تعداد یال | سهم |")
    A("|---|---|---|")
    for m, c in freq.most_common():
        A(f"| {FREQ_FA.get(m, m)} | {c} | {c / len(edges) * 100:.0f}٪ |")
    A("")
    A("| حساسیت | تعداد یال | سهم |")
    A("|---|---|---|")
    for m, c in crit.most_common():
        A(f"| {CRIT_FA.get(m, m)} | {c} | {c / len(edges) * 100:.0f}٪ |")
    A("")
    A("**خوانش مدیریتی:** بخش عمدهٔ جریان داده باید «رویدادی و بلادرنگ» باشد. "
      "اگر سهم روابطِ «روزانه/ماهانه» بالا برود، یعنی سیستم به ثبت دستی و تجمیعِ "
      "دوره‌ای برگشته است — همان چیزی که این پروژه می‌خواهد حذف کند.")
    A("")
    A("## ۴-۵. جزئیات یال‌ها (به تفکیک مبدأ)")
    A("")
    L.extend(detail_tables(edges))
    A("")
    A("## ۴-۶. جریان‌های الزامی (پوشش صریح)")
    A("")
    A("یازده جریانِ زیر باید **بدون ابهام** پیاده‌سازی شوند. ردیف هر کدام در "
    "جدول‌های بالا قابل جست‌وجو است.")
    A("")
    mandatory = [
        ("تولید → انبار مواد", "PRD", "RMW",
         "کسر خودکار مصرف به‌ازای دستور کار: با اسکن بارکد و توزین در ایستگاه خط، "
         "رویداد `material.consumed` صادر و موجودی همان لحظه کسر می‌شود؛ "
         "تلورانس ±۱.۵٪ [فرض] و کنترل FEFO پیش از کسر."),
        ("تولید → انبار محصول", "PRD", "FGW",
         "اعلام بچ آماده و انتقال به انبار: پس از ترخیص QC، رویداد `batch.completed` با "
         "کد بچ، مقدار، SSCC و مشخصات ارسال می‌شود؛ بدون `released` انتقالی انجام نمی‌شود."),
        ("QC → انبارها", "QCL", "RMW / FGW",
         "گیت کیفیت: سه وضعیت `released / rejected / quarantine` به‌صورت قفل سیستمی عمل می‌کند؛ "
         "مادهٔ قرنطینه قابل برداشت نیست و محصول قرنطینه قابل ارسال نیست."),
        ("انبار محصول → حراست", "FGW", "SEC",
         "مجوز خروج کالا: تطبیق چهارگانه (بارنامه/فاکتور/تأیید انبار/QC) پیش از صدور مجوز؛ "
         "هر شرط ناقص ⇒ دروازه باز نمی‌شود."),
        ("انبار محصول → بازرگانی", "FGW", "SAL",
         "تأیید ارسال و بارنامه: SSCCها، پکینگ‌لیست و e-POD به سفارش فروش متصل می‌شوند "
         "و صدور فاکتور را آزاد می‌کنند."),
        ("CMMS → تولید", "MNT", "PRD",
         "درخواست کار و توقف برنامه‌ریزی‌شده: WO پنجرهٔ توقف را در برنامهٔ تولید رزرو می‌کند؛ "
         "توقفِ اضطراری بلافاصله در MES ثبت و در OEE لحاظ می‌شود."),
        ("CMMS → انبار فنی", "MNT", "MRO",
         "مصرف قطعه: صدور فقط با شمارهٔ WO باز؛ رزرو خودکار هنگام برنامه‌ریزی و کسر هنگام ثبت مصرف."),
        ("HR → تولید", "HRM", "PRD",
         "تخصیص اپراتور واجد صلاحیت: بررسی مهارت، گواهی و سلامت در لحظهٔ ثبت روی دستور کار؛ "
         "نقض ⇒ قفل ثبت و پیشنهاد جایگزین."),
        ("HSE → حراست", "HSE", "SEC",
         "هشدار اضطراری و تخلیه: با اعلام وضعیت اضطراری، همهٔ گیت‌ها Fail-safe می‌شوند و "
         "فهرست حاضران در نقاط تجمع نمایش داده می‌شود."),
        ("همه → مالی", "*", "FIN",
         "رویداد مالی خودکار: هر رویداد عملیاتیِ اثرگذار یک رویداد `fin.posting` با "
         "`correlation_id` یکتا تولید می‌کند تا از صورت مالی تا رکورد سنسور قابل ردیابی باشد."),
        ("همه → BI", "*", "BI",
         "دادهٔ تحلیلی برای داشبورد مدیریت: انتشار رویدادها در انبار داده با لایهٔ معنایی "
         "یکسان (تعریف واحد برای هر شاخص) و تأخیر هدف زیر ۵ دقیقه."),
    ]
    A("| # | جریان الزامی | مبدأ | مقصد | شرح اجرا |")
    A("|---|---|---|---|---|")
    for i, (name, s, t, desc) in enumerate(mandatory, 1):
        A(f"| {i} | {name} | {s} | {t} | {desc} |")
    A("")
    A("## ۴-۷. الگوهای یکپارچگی (Integration Patterns)")
    A("")
    A("| الگو | کِی استفاده می‌شود | مثال در این پروژه | دلیل |")
    A("|---|---|---|---|")
    A("| **رویداد (Event/Async)** | تغییر وضعیتی که چند سیستم باید از آن مطلع شوند "
      "و فرستنده نباید منتظر بماند | `material.consumed` → WMS، ERP، مالی، BI | "
      "جداسازی، مقیاس‌پذیری، تحمل خطا |")
    A("| **API همزمان (Request/Reply)** | نیاز به پاسخ قطعی پیش از ادامه (گیت/تأیید) | "
      "استعلام صلاحیت اپراتور از HRM پیش از ثبت کار | قطعیت و سادگی خطا |")
    A("| **OPC UA / MQTT** | دادهٔ OT از لایهٔ ۱/۲ به ۳ | تله‌متری PLC، لرزش، پاورمتر | "
      "استاندارد OT، مدل اطلاعاتی، امنیت |")
    A("| **فایل/EDI** | اسناد رسمی و برون‌سازمانی با قالب قانونی | اظهارنامهٔ گمرکی، "
      "صورت‌حساب مالیاتی | الزام قانونی و قطعیت سند |")
    A("| **بارگذاری در انبار داده** | حجم بالا برای تحلیل (بدون تأثیر بر تراکنش) | "
      "تاریخچهٔ تله‌متری و نتایج آزمون برای BI | کارایی و جداسازی بار |")
    A("| **همگام‌سازی دادهٔ پایه (MDM)** | تغییر در موجودیت‌های پایه | تعریف کالای جدید "
      "→ انتشار به ERP، MES، WMS | یکپارچگی معنایی |")
    A("")
    A("## ۴-۸. ضدالگوهای ممنوع (Anti-Patterns)")
    A("")
    A("| ضدالگو | چرا ممنوع | جایگزین |")
    A("|---|---|---|")
    A("| اتصال نقطه‌به‌نقطهٔ مستقیمِ پایگاه‌داده‌ها | وابستگی پنهان، شکستن با هر تغییر اسکیما | "
      "API یا رویداد با قرارداد نسخه‌دار |")
    A("| فایلِ اکسلِ دستی به‌عنوان رابط | بدون ردیابی، بدون زمان، مستعد خطا | فرم/API |")
    A("| انتشار مستقیم از OT به IT (بدون DMZ) | نقض صریح IEC 62443 | عبور از DMZ با لیست سفید |")
    A("| رویدادِ بدون `idempotency_key` | ثبت مضاعف در تلاش مجدد و حالت آفلاین | کلید یکتای باید |")
    A("| ارسال دادهٔ حساسِ پرسنلی در رویداد عمومی | نقض حریم خصوصی | فقط شناسه؛ جزئیات با API مجاز |")
    A("| «دور زدن موقت» با ثبت دستی در ERP | شکستن زنجیرهٔ ردیابی | ثبت اصلاحیِ مستند با دلیل |")
    A("")
    if errors:
        A("## هشدارهای اعتبارسنجی")
        A("")
        for e in errors:
            A(f"- ⚠ {e}")
        A("")
    A("---")
    A("")
    A("← بعدی: [`05-master-data-ownership.md`](05-master-data-ownership.md)")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"✓ نوشته شد: {OUT_PATH}")
    print(f"  {len(rows)} رابطه در CSV · {len(edges)} یال جهت‌دار · {len(errors)} خطا")


if __name__ == "__main__":
    main()
