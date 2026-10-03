# ابزارهای تولید مستندات

فلسفهٔ این مخزن: **فایل‌های CSV در `data/` تنها منبع حقیقت‌اند**؛
مستنداتِ Markdown «نمای انسانی» همان داده هستند و نباید با دست ویرایش شوند
(وگرنه با دور بعدیِ تولید، تغییرات از بین می‌رود).

```
data/*.csv  ──►  tools/*.py  ──►  docs/*.md
                                      │
                                      └──►  dashboard/index.html (در زمان اجرا، مستقیماً CSV را می‌خواند)
```

## اجرا

از ریشهٔ مخزن:

```bash
python3 tools/build_integration_matrix.py   # => docs/04-integration-matrix.md
python3 tools/build_catalogs.py             # => docs/05 , 08 , 09 , 11
```

یا هر دو با هم:

```bash
python3 tools/build_integration_matrix.py && python3 tools/build_catalogs.py
```

پیش‌نیاز: Python ۳٫۸+ (بدون وابستگی خارجی).

## فایل‌ها

| ابزار | ورودی | خروجی |
|---|---|---|
| `build_integration_matrix.py` | `data/integration_matrix.csv` | `docs/04-integration-matrix.md` (ماتریس ۱۸×۱۸، آمار، جزئیات یال‌ها، الگوها، ضدالگوها) |
| `build_catalogs.py` | `data/master_data.csv` | `docs/05-master-data-ownership.md` |
| `build_catalogs.py` | `data/kpi_catalog.csv` | `docs/08-kpi-catalog.md` |
| `build_catalogs.py` | `data/alarm_catalog.csv` | `docs/09-alarm-map.md` |
| `build_catalogs.py` | `data/roadmap.csv` | `docs/11-roadmap.md` (شامل گانت متنی) |
| `build_catalogs.py` | `data/risk_register.csv` | `docs/12-risk-register.md` (امتیاز، نقشهٔ حرارتی ۵×۵، راهبرد کاهش) |
| `build_catalogs.py` | `data/event_catalog.csv` | `docs/19-event-catalog.md` (قراردادهای عمومی، جدول رویدادها، سیاست‌های ویژه) |
| `build_catalogs.py` | `data/open_questions.csv` | `docs/16-open-questions.md` + `docs/24-customer-questionnaire.md` |

## ویرایش ایمن

1. فایل CSV مربوطه را ویرایش کنید (ستون‌ها را تغییر ندهید؛ مقادیر را اصلاح کنید).
2. اسکریپت را اجرا کنید.
3. خروجی را در `git diff` ببینید و همراه با تغییر CSV در یک کامیت قرار دهید.

> اگر نیاز به ستون جدید دارید، اسکریپت را هم به‌روز کنید — هرگز مستندِ تولید‌شده را دستی ویرایش نکنید.

## قراردادهای CSV

| فایل | نکته‌های مهم |
|---|---|
| `integration_matrix.csv` | `direction` فقط `one-way` یا `two-way`؛ کدها باید از فهرست `NODES` در اسکریپت باشند؛ رابطهٔ دوطرفه به دو یال تبدیل می‌شود |
| `kpi_catalog.csv` | `unit` باید با کلیدهای `unit_fa` در اسکریپت هم‌خوان باشد؛ `formula` باید دقیق و محاسبه‌پذیر باشد |
| `alarm_catalog.csv` | `severity` یکی از `Critical/Major/Minor/Warning` |
| `roadmap.csv` | هزینه‌ها به «میلیون دلار» و زمان‌ها به «هفته» (از ابتدای پروژه) هستند |
| `master_data.csv` | `criticality` یکی از `Critical/High/Medium/Low`؛ مصرف‌کنندگان با `;` جدا می‌شوند |
| `risk_register.csv` | `score` باید برابر `probability × impact` باشد (اگر نباشد هشدار می‌گیرد)؛ سطح‌ها بر اساس امتیاز محاسبه می‌شوند |
| `event_catalog.csv` | نام‌گذاریِ موضوع `حوزه.زیرحوزه.موجودیت`؛ `dlq` یکی از `never/critical/standard/buffered`؛ `pii` فقط `yes/no` |
| `open_questions.csv` | `priority` یکی از «بلوکه‌کننده/مهم/قابل تأخیر»؛ `blocks` شامل فاز، شمارهٔ ADR و شناسهٔ ریسک است |
