# مستند طراحی تفصیلی اتوماسیون یکپارچه کارخانه (DDD)

**نسخه ۱.۰ — مبنای اجرا** · تاریخ تدوین: ۱۴۰۴/۰۷/۱۱ (۲۰۲۶-۱۰-۰۳) · وضعیت: پیش‌نویس نهایی برای تصویب کمیته راهبری

این مخزن، «نقشهٔ اجرایی» اتوماسیون سرتاسری کارخانه است: از سنسور در کف کارگاه تا داشبورد مدیرعامل.
هدف این نیست که «چه چیزی خوب است» گفته شود؛ هدف این است که **یک تیم پروژه فردا صبح بتواند شروع کند**.

---

## ۱. خلاصهٔ مدیریتی (۱ صفحه)

**مسئله.** امروز داده در کارخانه در سه نقطه گسسته می‌شود: (الف) بین ماشین و سرپرست خط (ثبت دستی،
گزارش‌نویسی کاغذی)، (ب) بین کارگاه و انبار/QC (تلفن و فرم کاغذی)، (ج) بین عملیات و مالی
(داده با ۳ تا ۱۵ روز تأخیر وارد ERP می‌شود). نتیجه: OEE واقعی نامعلوم، بهای تمام‌شده تخمینی،
ردیابی بچ در بهترین حالت ۴ ساعت زمان می‌برد، و هر ممیزی (ISO/HACCP) یک پروژهٔ بحرانی است.

**راه‌حل.** یک معماری **رویدادمحور و API-First** بر پایهٔ Purdue/ISA-95 با ۶ تصمیمِ سخت:

| # | تصمیم معماری | اثر مستقیم |
|---|---|---|
| ۱ | **MDM (Master Data Hub) در لایهٔ ۳** به‌عنوان تنها منبع حقیقت | حذف ۷۰٪ ورود دستی تکراری |
| ۲ | **ستون فقرات رویداد**: MQTT/Sparkplug B در OT ↔ Kafka در IT، با پل در DMZ | جریان داده بدون گسست، زیر ثانیه |
| ۳ | **Historian + مدل یکسان تجهیز (Asset Model)** | OEE و بهای تمام‌شده از دادهٔ واقعی، نه تخمین |
| ۴ | **گیت‌های کیفیت/ایمنی به‌صورت قفل سیستمی** (Quality Gate, PTW Gate) | انطباق اجباری به‌جای انطباق داوطلبانه |
| ۵ | **Audit Trail تغییرناپذیر (hash-chain + WORM)** برای هر تراکنش | ممیزی در ساعات، نه هفته‌ها |
| ۶ | **Offline-First** در ایستگاه‌های کارگاهی | تولید در قطع شبکه متوقف نمی‌شود |

**اعداد هدف (Baseline → Target در ۳۰ ماه)** — جزئیات در [`docs/08-kpi-catalog.md`](docs/08-kpi-catalog.md)

| شاخص | وضعیت فعلی [فرض] | هدف | منبع داده |
|---|---|---|---|
| OEE | ۵۲٪ | ۷۵٪ | MES + Historian |
| ثبت دستی دادهٔ تولید | ۱۰۰٪ | < ۵٪ | MES |
| زمان ردیابی بچ (عقب/جلو) | ~۴ ساعت | < ۳۰ ثانیه | MES Genealogy |
| دقت موجودی انبار | ۸۴٪ | ≥ ۹۸٪ | WMS |
| بهای تمام‌شده | ماهانه/تخمینی | روزانه/واقعی | ERP ↔ MES |
| در دسترس‌بودن سامانه‌های L2/L3 | نامشخص | ۹۹.۹٪ | مانیتورینگ |
| انطباق مستند (ممیزی) | پروژه‌ای | پیوسته و خودکار | Audit Trail |

**سرمایه و زمان.** ۷ فاز، **۲۴ تا ۳۴ ماه**، **۴.۷ تا ۸.۱ میلیون دلار**
(≈ ۴۷۰–۸۱۰ میلیارد تومان با نرخ [فرض] ۱ USD = ۱۰۰,۰۰۰ تومان؛ **نسبت‌ها معتبرتر از اعداد مطلق‌اند**).
تقسیم تقریبی: ۴۲٪ خدمات نرم‌افزاری و یکپارچه‌سازی، ۳۸٪ سخت‌افزار OT/IT، ۲۰٪ احتیاطی و مدیریت تغییر.

**بزرگ‌ترین ریسک‌ها.** (۱) کیفیت Master Data در شروع، (۲) مقاومت فرهنگی در ثبت دیجیتال،
(۳) یکپارچه‌سازی با PLCهای قدیمی، (۴) امنیت OT حین اتصال. برنامهٔ کاهش در
[`docs/12-risk-register.md`](docs/12-risk-register.md).

**اولین سه کار (هفتهٔ جاری).** تشکیل «دفتر مدیریت داده» و تعیین مالکان Master Data ·
ممیزی As-Is شبکه و تجهیزات · انتخاب پایلوت: **یک خط بحرانی** برای فاز ۲.

---

## ۲. نقشهٔ اسناد (Deliverables ۱ تا ۱۴)

| # | خروجی | فایل |
|---|---|---|
| ۱ | خلاصه مدیریتی | این صفحه + [`docs/00-executive-summary.md`](docs/00-executive-summary.md) |
| ۲ | معماری لایه‌ای + جریان داده (ASCII/Mermaid) | [`docs/02-reference-architecture.md`](docs/02-reference-architecture.md) |
| ۳ | جدول جامع واحدها (۹ محور × ۱۴ واحد) | [`docs/03-units/`](docs/03-units/) |
| ۴ | ماتریس یکپارچگی بین‌واحدی | [`docs/04-integration-matrix.md`](docs/04-integration-matrix.md) + [`data/integration_matrix.csv`](data/integration_matrix.csv) |
| ۵ | فهرست Master Data و مالکیت | [`docs/05-master-data-ownership.md`](docs/05-master-data-ownership.md) + [`data/master_data.csv`](data/master_data.csv) |
| ۶ | فهرست تجهیزات و حسگرها به تفکیک واحد | [`docs/06-hardware-sensors-catalog.md`](docs/06-hardware-sensors-catalog.md) |
| ۷ | فهرست فرم‌ها و صفحات UI به تفکیک نقش | [`docs/07-ui-forms-by-role.md`](docs/07-ui-forms-by-role.md) |
| ۸ | جدول KPI با فرمول و منبع | [`docs/08-kpi-catalog.md`](docs/08-kpi-catalog.md) + [`data/kpi_catalog.csv`](data/kpi_catalog.csv) |
| ۹ | نقشهٔ هشدارها و سطح‌بندی | [`docs/09-alarm-map.md`](docs/09-alarm-map.md) + [`data/alarm_catalog.csv`](data/alarm_catalog.csv) |
| ۱۰ | ماتریس نقش–دسترسی (RACI + RBAC) | [`docs/10-raci-rbac.md`](docs/10-raci-rbac.md) |
| ۱۱ | نقشهٔ راه فازبندی + هزینه | [`docs/11-roadmap.md`](docs/11-roadmap.md) + [`data/roadmap.csv`](data/roadmap.csv) |
| ۱۲ | تحلیل ریسک + برنامهٔ کاهش | [`docs/12-risk-register.md`](docs/12-risk-register.md) |
| ۱۳ | معیارهای پذیرش (UAT) و چک‌لیست راه‌اندازی | [`docs/13-uat-checklist.md`](docs/13-uat-checklist.md) |
| ۱۴ | آموزش و مدیریت تغییر | [`docs/14-change-management.md`](docs/14-change-management.md) |

مستندات مکمل: [`docs/01-inputs-and-assumptions.md`](docs/01-inputs-and-assumptions.md) ·
[`docs/15-nfr-security-compliance.md`](docs/15-nfr-security-compliance.md) ·
[`docs/16-open-questions.md`](docs/16-open-questions.md)

## ۳. داشبورد تعاملی

پوشهٔ [`dashboard/`](dashboard/index.html) یک نمای تعاملیِ RTL از ماتریس یکپارچگی،
کاتالوگ KPI، نقشهٔ هشدارها و گانتِ نقشهٔ راه است که مستقیماً از فایل‌های `data/*.csv` تغذیه می‌کند؛
یعنی **اگر CSV را اصلاح کنید، داشبورد هم به‌روز می‌شود** (Single Source of Truth).

اجرا: `python3 -m http.server 8080 --bind 0.0.0.0` در ریشهٔ مخزن، سپس `dashboard/index.html`.

## ۵. اسنادِ تولید‌شده (Generated)

بعضی مستندات از فایل‌های `data/*.csv` تولید می‌شوند تا مستند و داشبورد هیچ‌وقت از هم جدا نشوند:

```bash
python3 tools/build_integration_matrix.py   # => docs/04-integration-matrix.md
python3 tools/build_catalogs.py             # => docs/05 , 08 , 09 , 11
```

**مستنداتِ تولید‌شده را مستقیماً ویرایش نکنید**؛ فایل CSV مربوطه را تغییر دهید و اسکریپت را اجرا کنید.
جزئیات بیشتر در [`tools/README.md`](tools/README.md).

## ۴. قراردادهای این مخزن

- همهٔ اسناد **فارسی/RTL** هستند؛ اصطلاحات فنی کنار معادل انگلیسی می‌آیند.
- هر ادعای کمی یا با `[فرض]` برچسب خورده یا به یک KPI/ماژول/ردیف جدول ارجاع داده شده است.
- فایل‌های `data/*.csv` **منبع ماشین‌خوان** جداول‌اند؛ `docs/*.md` نمای انسانی همان داده.
- تغییر در هر CSV باید با تغییر در مستند مرتبط همراه باشد (بررسی در Code Review).

---

*برای شروع مطالعه: از [`docs/00-executive-summary.md`](docs/00-executive-summary.md) شروع کنید،
سپس [`docs/02-reference-architecture.md`](docs/02-reference-architecture.md)،
و برای هر واحد سراغ [`docs/03-units/`](docs/03-units/) بروید.*
