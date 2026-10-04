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
| `build_templates.py` | `tools/templates/*.md` + چند CSV | `docs/00`، `01`، `02`، `06`، `07`، `10`، `13`، `14`، `15`، `17`، `18`، `20`، `21`، `22`، `23` (متنِ ثابت + جدولِ داده‌محور) |
| `build_catalogs.py` | `data/master_data.csv` | `docs/05-master-data-ownership.md` |
| `build_catalogs.py` | `data/kpi_catalog.csv` | `docs/08-kpi-catalog.md` |
| `build_catalogs.py` | `data/alarm_catalog.csv` | `docs/09-alarm-map.md` |
| `build_catalogs.py` | `data/roadmap.csv` | `docs/11-roadmap.md` (شامل گانت متنی) |
| `build_catalogs.py` | `data/risk_register.csv` | `docs/12-risk-register.md` (امتیاز، نقشهٔ حرارتی ۵×۵، راهبرد کاهش) |
| `build_catalogs.py` | `data/event_catalog.csv` | `docs/19-event-catalog.md` (قراردادهای عمومی، جدول رویدادها، سیاست‌های ویژه) |
| `build_catalogs.py` | `data/open_questions.csv` | `docs/16-open-questions.md` + `docs/24-customer-questionnaire.md` |
| `build_catalogs.py` | `data/benefit_model.csv` + `data/financial_model.csv` | `docs/25-financial-model.md` (محرک‌ها، جریان نقدی، NPV/IRR، حساسیت) |
| `build_catalogs.py` | `data/ot_zones.csv` + `data/ot_conduits.csv` | `docs/26-ot-security-plan.md` (منطقه‌ها، کانال‌ها، قوانین امنیتی) |
| `build_catalogs.py` | `data/traceability.csv` | `docs/27-traceability-coverage.md` (پوششِ نیازمندی‌ها و ردیابی) |
| `build_site.py` | `site/` + `data/` + `docs/` + `dashboard/` | بستهٔ انتشار `_site` (یکسان برای Pages و Vercel) + بررسیِ اینکه هر منبعِ لازم در بسته هست |
| `test_build.py` | همهٔ فایل‌های `data/` و `docs/` | ۶۲ تست یکپارچگی، کیفیت و چیدمانِ بستهٔ انتشار (بدون خروجی) |
| `test_site.js` | `site/index.html` و `data/*.csv` | ۳۵ تستِ نمایشگر مارک‌داون، CSV و جست‌وجوی تمام‌متن |
| `check_pages.py` | مخزن + نشانیِ زندهٔ Pages و Vercel | انتشار را سرتاسری می‌سنجد: تنظیمات، workflow، artifact، و زنده‌بودنِ `/`، `data/`، `docs/`، `dashboard/` روی هر دو میزبان (`--local` برای سنجشِ بستهٔ محلی) |

## ویرایش ایمن

1. فایل CSV مربوطه را ویرایش کنید (ستون‌ها را تغییر ندهید؛ مقادیر را اصلاح کنید).
2. اسکریپت را اجرا کنید.
3. خروجی را در `git diff` ببینید و همراه با تغییر CSV در یک کامیت قرار دهید.
4. `python3 tools/test_build.py` و `node tools/test_site.js` را اجرا کنید تا یکپارچگیِ داده و سایت بررسی شود.

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
| `benefit_model.csv` | مبالغ به «میلیون دلار در سال»؛ محرک‌های یک‌باره در ستون‌های `oneoff_*` جداگانه می‌آیند |
| `financial_model.csv` | جمعِ ستون‌های سرمایه باید با بودجهٔ مصوب (۴.۹۶ / ۸.۴۲) برابر باشد؛ شیبِ منفعت صعودی و در سال آخر ۱۰۰ است |
| `ot_zones.csv` | `sl_target` یکی از `SL-1/SL-2/SL-3`؛ هر منطقه باید کنترل‌های کلیدی داشته باشد |
| `ot_conduits.csv` | مناطق باید از `ot_zones.csv` باشند؛ `denied_by_default` برای همهٔ کانال‌ها باید «بله» باشد |
| `raci.csv` | قالبِ طویل (فعالیت × نقش × مقدار)؛ هر فعالیت باید **دقیقاً یک A** و **حداقل یک R** داشته باشد |
| `ui_matrix.csv` | باید برای **همهٔ** نقش‌های `roles.csv` ردیف داشته باشد (۲۸ × ۲۴)؛ نماد فقط یکی از ● ◐ ○ — |
| `ui_matrix.csv` | قالبِ طویل و **کامل**: هر ترکیبِ صفحه×نقش یک ردیف دارد (بدون دسترسی = `—`) |
| `roles.csv` | کدهای نقش یکتا هستند و ماتریس فقط به همین کدها ارجاع می‌دهد |
| `nfr.csv` | هر الزام باید «مقدار هدف» و «روش اندازه‌گیری» داشته باشد |
| `ot_controls.csv` | `status` یکی از مقادیرِ موجود در مستند (الزامی / توصیه‌ای / …) |
| `retention_classes.csv` | ستونِ `deletable` باید صریحاً بله/خیر باشد |
| `role_map.csv` | هر نقش باید دارای `raci_actor` معتبر و دست‌کم یک نامِ مستعار باشد؛ اگر آگاهانه در صفِ اعلان نیست، دلیل در `notify_note` بنویسید |
| `role_journey.csv` | دقیقاً ۴ گامِ پیوسته برای هر نقش، و هر گام باید «سامانه» و «اثرِ قابل‌ردیابی» داشته باشد |
| `exec_targets.csv` | هر شاخص باید واحد، وضعیتِ فعلی، هر دو افق و منبعِ سنجش داشته باشد |
| `vendor_criteria.csv` | جمعِ وزن‌ها باید دقیقاً ۱۰۰٪ باشد |
| `input_params.csv` | هر ورودیِ فرضی باید برچسبِ `[فرض]` داشته باشد |
| `phase_summary.csv` | هر فازِ `roadmap.csv` باید اینجا ردیف داشته باشد (بازه و بودجه محاسبه می‌شود، دستی نوشته نمی‌شود) |
| `api_endpoints.csv` | ستونِ `group` باید دقیقاً یکی از پنج گروهِ مستندِ ۲۰ باشد |
| `arch_conduits.csv` | این‌ها «مسیرِ منطقیِ بین‌لایه‌ای» هستند (`C1`–`C7`)؛ با کاندویت‌های قابل‌پیکربندیِ `ot_conduits.csv` (`C-01`–`C-18`) اشتباه نشوند |
| `traceability.csv` | `group` یکی از «معیار پذیرش / تحویل‌دادنی / الزام نگارش / کیفیت مخزن»؛ هر ردیف باید روشِ راستی‌آزمایی داشته باشد |
