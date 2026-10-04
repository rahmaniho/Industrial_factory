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

**سرمایه و زمان.** ۷ فاز، **۱۰۲ هفته (≈ ۲۴ ماه؛ تا ۳۰ ماه با احتیاط)**، **۴.۹۶ تا ۸.۴۲ میلیون دلار**
(≈ ۴۹۶–۸۴۲ میلیارد تومان با نرخ [فرض] ۱ USD = ۱۰۰,۰۰۰ تومان؛ **نسبت‌ها معتبرتر از اعداد مطلق‌اند**).
ارقام از جمعِ ۴۳ بستهٔ کار در [`data/roadmap.csv`](data/roadmap.csv) به‌دست آمده‌اند.
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
| ۳ | جدول جامع واحدها (۹ محور × ۱۴ واحد) | [`docs/03-units/`](docs/03-units/) + مدل داده و قراردادها: [`docs/17`](docs/17-architecture-decisions.md) تا [`docs/21`](docs/21-sequence-flows.md) |
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

### نمایشِ زنده در گیت‌هاب پیج (GitHub Pages)

نشانی پس از انتشار:

**https://rahmaniho.github.io/Industrial_factory/**

سایت یک فایلِ مستقل است (`site/index.html`) با CSS و جاوااسکریپتِ درونی و
**هیچ وابستگیِ خارجی** ندارد؛ داده‌ها را هنگامِ اجرا از `data/*.csv` می‌خواند
و در هر دو حالت — ریشهٔ دامنه و زیرمسیر — کار می‌کند.

فایل `pages.yml` روی هر push به `main` و `arena/**` مستندات را بازتولید می‌کند،
تست‌ها را اجرا می‌کند، پوشهٔ انتشار را می‌سازد و منتشر می‌کند.

بررسیِ اینکه انتشار واقعاً بدون خطا انجام شده است:

```bash
python3 tools/check_pages.py
```

این اسکریپت یکی‌یکی چک می‌کند: فعال‌بودنِ Pages روی مخزن، نتیجهٔ آخرین اجرای
workflow، نتیجهٔ هر گام (build و deploy)، بارگذاریِ بستهٔ انتشار، و در
دسترس‌بودنِ نشانیِ زنده — و گامِ آخر را روی **هر دو میزبان** (Pages و Vercel)
می‌سنجد: صفحهٔ `/`، `data/*.csv`، `docs/*.md`، `dashboard/` و مسیرِ کهنهٔ
`site/index.html`. خروجیِ آن ۰ است اگر همه‌چیز سبز باشد. برای سنجشِ بستهٔ
محلی قبل از انتشار: `python3 tools/check_pages.py --local http://127.0.0.1:8080/`.

> **اگر انتشار انجام نمی‌شود:** Pages باید یک‌بار روی مخزن فعال شود.
> مسیر: `Settings → Pages → Build and deployment → Source` را روی
> **GitHub Actions** بگذارید. این کار فقط از سویِ مالکِ مخزن ممکن است و
> workflow خودش نمی‌تواند آن را انجام دهد (توکنِ یکپارچه‌سازی دسترسی ندارد).
> پس از آن، هر push خودکار منتشر می‌شود.

ساخت و دیدنِ محلی، بدون نیاز به انتشار:

```bash
python3 tools/build_integration_matrix.py && python3 tools/build_catalogs.py && python3 tools/build_templates.py
python3 tools/build_site.py          # بستهٔ _site را می‌سازد و خودش هم بررسی می‌کند
cd _site && python3 -m http.server 8080 --bind 0.0.0.0
```

سپس `http://localhost:8080` را باز کنید. برای این‌که مسیرهای نسبی درست باشند،
سرور باید از **داخلِ پوشهٔ `_site/`** اجرا شود — یا مستقیماً
`python3 -m http.server 8080 -d _site`.

> چیدمانِ بستهٔ انتشار فقط در `tools/build_site.py` تعریف شده است؛ همان اسکریپت را
> workflow پیج و `vercel.json` اجرا می‌کنند. اگر روزی فایلی به سایت اضافه شد،
> تنها همین‌جا باید ثبت شود.

### میزبانیِ دوم در Vercel (نشانیِ کوتاه‌تر)

مخزن علاوه بر Pages روی **Vercel** هم منتشر می‌شود:
**🌐 <https://industrialautomation-seven.vercel.app>**

Vercel برخلاف Pages «بدون build» ریشهٔ مخزن را منتشر می‌کند و چون `site/index.html`
در ریشه نیست، نشانیِ `/` خطایِ `404 NOT_FOUND` می‌داد (درحالی‌که
`/site/index.html` سالم کار می‌کرد). دو لایهٔ رفع:

| فایل | چه می‌کند |
|---|---|
| `vercel.json` | `buildCommand: python3 tools/build_site.py --out _site` و `outputDirectory: _site` ⇒ `/` همان سایت است |
| `index.html` (ریشهٔ مخزن) | صفحهٔ راهنما: اگر میزبانی build را اجرا نکرد، `/` را به `site/index.html` می‌فرستد |

تنظیماتِ لازم در پنل Vercel (یک‌بار): **Framework Preset = Other**؛ بقیه از
`vercel.json` خوانده می‌شود. اگر پوشهٔ Root Directory مخزن را روی `site/` گذاشته‌اید،
آن را به ریشهٔ مخزن برگردانید — وگرنه `data/` و `docs/` از دسترس می‌روند.

> در `vercel.json` عمداً هیچ `rewrites` سراسری («هر مسیر → index.html») نیست:
> سایت با یک `HEAD` روی `data/kpi_catalog.csv` تشخیص می‌دهد در ریشهٔ دامنه است یا
> زیرمسیر؛ اگر ۴۰۴ها به ۲۰۰ تبدیل شوند، تشخیص اشتباه می‌شود و صفحه بی‌صدا بی‌داده می‌ماند.

## نمای اختصاصیِ هر نقش («من با این نقش چه می‌بینم؟»)

در سایتِ پروژه (و در بخشِ «نقش‌ها و دسترسیِ» داشبورد) می‌توان یکی از ۲۴ نقش را انتخاب کرد و
دقیقاً همان چیزی را دید که آن نقش در سامانه می‌بیند:

یک منبع، سه نمایش: جدولِ «اعداد هدف» در مستند ۰۰، در داشبورد و در صفحهٔ نخستِ سایت
همگی از یک فایل (`exec_targets.csv`) خوانده می‌شوند. جدولِ «فازها، زمان و بودجه» در مستند ۰۰
و در داشبورد از `roadmap.csv` **جمع‌بسته** می‌شود — ادعایِ «این اعداد از CSV محاسبه شده‌اند»
اکنون با تست قفل شده است، نه با قول.

**احتیاط در ویرایشِ جدول‌ها:** یک «|» نارهانیده در مقدار، ستونِ اضافه می‌سازد و کلِ جدول را
در هر رندری می‌شکند. نمونهٔ واقعی که در این مخزن رخ داد و رفع شد: فرمولِ قدرمطلقِ `|مغایرت|`
(اکنون `abs(مغایرت)`) و مسیرِ `?direction=backward|forward`. تستِ
`test_markdown_tables_have_consistent_columns` همهٔ مستندات را پیوسته می‌سنجد.

| زیربخش | پرسشی که پاسخ می‌دهد | منبع داده |
|---|---|---|
| صفحه‌های من | کدام صفحه‌ها را با چه سطحی باز می‌کند؟ | `ui_matrix.csv` (۲۸ × ۲۴) |
| کاری که می‌کنم | در هر فازِ روز چه می‌کند و چه اثری بر جا می‌گذارد؟ | `role_journey.csv` |
| مسئولیت‌های من | در کدام فعالیت‌ها R یا A است؟ | `raci.csv` + `role_map.csv` |
| هشدارهای من | کدام هشدارها به او می‌رسد؟ | `alarm_catalog.csv` |
| شاخص‌های من | مالکِ کدام شاخص‌هاست؟ | `kpi_catalog.csv` |
| دسترسی به ماژول‌ها | در هر ماژول چه سطحی دارد؟ | `rbac.csv` |

دو قاعده در این تخصیص رعایت شده است:

1. **هر نقش در ماتریس صفحه‌ها ردیف دارد** — ۲۸ صفحه × ۲۴ نقش = ۶۷۲ خانه؛ هیچ نقشی بدون صفحهٔ کاری نیست.
2. **مالک به «خاص‌ترین» نقش نسبت داده می‌شود** — هشدارِ «QC شیفت» به تکنسین QC می‌رسد نه مدیر QC؛
   اما یک مالکِ چندگانه مانند «QC + سرپرست انبار» به هر دو می‌رسد.

هر دو قاعده در `tools/test_build.py` و `tools/test_site.js` قفل شده‌اند.

## مستندات تکمیلیِ اجرایی (۱۶ تا ۲۷)

| # | مستند | کاربردِ عملی |
|---|---|---|
| ۱۷ | [`17-architecture-decisions.md`](docs/17-architecture-decisions.md) | ۱۴ ADR با گزینه‌های ردشده و شرط بازنگری — پاسخ به «چرا این‌طور؟» |
| ۱۸ | [`18-data-model.md`](docs/18-data-model.md) | مرزهای دامنه، مدل ردیابی (گراف)، قرارداد شناسه‌ها، کلاس‌های نگه‌داری |
| ۱۹ | [`19-event-catalog.md`](docs/19-event-catalog.md) | ۵۴ رویداد با تولیدکننده، مصرف‌کننده، کلیدِ باید و سیاستِ خطا |
| ۲۰ | [`20-api-contract.md`](docs/20-api-contract.md) | قرارداد REST/AsyncAPI، مدل خطا، باید، نسخه‌بندی، شاخص‌های سلامت |
| ۲۱ | [`21-sequence-flows.md`](docs/21-sequence-flows.md) | ۷ جریانِ سرتاسری با نمودار Mermaid + مسیر شکست + تست متناظر |
| ۲۲ | [`22-vendor-selection.md`](docs/22-vendor-selection.md) | مدل امتیازدهی، معیارهای حذف، POC دو‌هفته‌ای، بندهای قراردادی |
| ۲۳ | [`23-cutover-migration.md`](docs/23-cutover-migration.md) | مهاجرت داده، Runbookـ T-‎۱۴ تا T+‎۳۰، درخت بازگشت، آشتی‌سازی |
| ۲۴ | [`24-customer-questionnaire.md`](docs/24-customer-questionnaire.md) | پرسش‌نامهٔ ۳۰گانه برای تکمیل توسط مشتری — هر پاسخ یک «[فرض]» را حذف می‌کند |
| ۲۵ | [`25-financial-model.md`](docs/25-financial-model.md) | ۱۰ محرک ارزش، جریان نقدی ۵ ساله، NPV/IRR، تحلیل حساسیت |
| ۲۶ | [`26-ot-security-plan.md`](docs/26-ot-security-plan.md) | ۹ منطقهٔ امنیتی، ۱۸ کانال مجاز، قوانین غیرقابل‌مذاکره بر اساس IEC 62443 |
| ۲۷ | [`27-traceability-coverage.md`](docs/27-traceability-coverage.md) | ماتریس ردیابی: ۳۳ نیازمندی → مستند + داده + روش راستی‌آزمایی |

مستندات مکمل: [`docs/01-inputs-and-assumptions.md`](docs/01-inputs-and-assumptions.md) ·
[`docs/15-nfr-security-compliance.md`](docs/15-nfr-security-compliance.md) ·
[`docs/16-open-questions.md`](docs/16-open-questions.md)

> همهٔ اعدادِ کلیدی این طرح (بودجه، زمان‌بندی، شمارش‌ها) از فایل‌های `data/*.csv` محاسبه می‌شوند،
> بنابراین خلاصهٔ مدیریتی، نقشهٔ راه و داشبورد همواره با یکدیگر هم‌خوان‌اند.

## ۳. سایت زنده (GitHub Pages و Vercel)

این مخزن یک **سایت تعاملی** هم دارد که همهٔ بخش‌ها را قابل مرور و استفاده می‌کند:

| میزبان | نشانی | منشأ |
|---|---|---|
| گیت‌هاب پیج | **<https://rahmaniho.github.io/Industrial_factory/>** | `.github/workflows/pages.yml` → بستهٔ `_site` |
| Vercel | **<https://industrialautomation-seven.vercel.app>** | `vercel.json` → همان بستهٔ `_site` |

هر دو میزبان یک بسته را از یک اسکریپت (`tools/build_site.py`) می‌سازند؛ پس هیچ‌وقت
یکی «سایتِ کامل» و دیگری «۴۰۴» نمی‌شود.

| بخش | چه می‌کند |
|---|---|
| **نمای کلی** | خلاصهٔ مدیریتی، هدف‌های کمّی، خلاصهٔ مالی و نقشهٔ کاملِ ۴۰ مستند |
| **مرور اسناد** | همهٔ مستندات با نمایشگرِ مارک‌داونِ داخلی، فهرستِ درختی و جست‌وجو — بدون ترک صفحه |
| **داشبورد زنده** | ۱۰ بخشِ داده‌محور که مستقیماً از `data/*.csv` تغذیه می‌شوند |
| **چگونه استفاده کنیم** | فلسفهٔ مخزن، نقش هر لایه و مسیرِ پیشنهادی برای شروع |

سایت با `.github/workflows/pages.yml` روی هر push ساخته و منتشر می‌شود.

> **فعال‌سازی (یک‌بار، توسط مالک مخزن):**
> `Settings → Pages → Source` را روی **GitHub Actions** بگذارید.
> پس از آن، آدرس بالا در دسترس خواهد بود.

## ۴. داشبورد تعاملی

پوشهٔ [`dashboard/`](dashboard/index.html) یک نمای تعاملیِ RTL با **۱۰ بخش** است که
مستقیماً از فایل‌های `data/*.csv` تغذیه می‌کند؛ یعنی **اگر CSV را اصلاح کنید، داشبورد هم
به‌روز می‌شود** (Single Source of Truth):

ماتریس یکپارچگی · کاتالوگ شاخص‌ها · نقشهٔ هشدارها · کاتالوگ رویدادها · ثبت ریسک
(با نقشهٔ حرارتی) · پرسش‌های باز · مدل مالی (با نمودار جریان نقدی) · امنیت OT ·
گانتِ نقشهٔ راه · دادهٔ پایه

اجرا: `python3 -m http.server 8080 --bind 0.0.0.0` در ریشهٔ مخزن، سپس `dashboard/index.html`.

## ۵. اسنادِ تولید‌شده (Generated)

بخشی از مستندات از روی فایل‌های `data/*.csv` تولید می‌شوند تا مستند و داشبورد هیچ‌گاه
از یکدیگر جدا نشوند. **این فایل‌ها را مستقیماً ویرایش نکنید؛** مبدأ تغییر، فایل CSV است.

| مستند | منبع داده | محتوا |
|---|---|---|
| `docs/04-integration-matrix.md` | `integration_matrix.csv` | ماتریس ۱۸×۱۸، آمار، جزئیات یال‌ها، الگوها، ضدالگوها |
| `docs/05-master-data-ownership.md` | `master_data.csv` | ۵۸ موجودیتِ دادهٔ پایه با مالک و سیستم مرجع |
| `docs/08-kpi-catalog.md` | `kpi_catalog.csv` | ۱۲۰ شاخص با فرمول، منبع داده، مالک و هدف |
| `docs/09-alarm-map.md` | `alarm_catalog.csv` | ۱۰۵ هشدار با سطح، مالک و SLA |
| `docs/11-roadmap.md` | `roadmap.csv` | ۴۳ بستهٔ کار + گانت متنی + بودجهٔ هر فاز |
| `docs/12-risk-register.md` | `risk_register.csv` | ۲۰ ریسک با امتیاز، سطح، نقشهٔ حرارتی و راهبرد کاهش |
| `docs/16-open-questions.md` | `open_questions.csv` | ۳۰ پرسش با اولویت، پیش‌فرض و پاسخ‌گو |
| `docs/19-event-catalog.md` | `event_catalog.csv` | ۵۴ رویداد با تولیدکننده، مصرف‌کننده و سیاستِ خطا |
| `docs/24-customer-questionnaire.md` | `open_questions.csv` | نسخهٔ قابل چاپ و تکمیلِ پرسش‌ها برای مشتری |
| `docs/25-financial-model.md` | `benefit_model.csv` + `financial_model.csv` | محرک‌های ارزش، جریان نقدی، NPV/IRR و تحلیل حساسیت |
| `docs/26-ot-security-plan.md` | `ot_zones.csv` + `ot_conduits.csv` | منطقه‌بندیِ OT، کانال‌های مجاز و قوانین امنیتی |
| `docs/27-traceability-coverage.md` | `traceability.csv` | پوششِ معیارهای پذیرش، تحویل‌دادنی‌ها و الزامات نگارش |
| `docs/07-ui-forms-by-role.md` | `roles.csv` + `ui_matrix.csv` | نقش‌ها و ماتریسِ دسترسیِ نقش × صفحه |
| `docs/10-raci-rbac.md` | `raci.csv` + `rbac.csv` + `sod_rules.csv` | مسئولیت‌ها، دسترسی و تفکیک وظایف |
| `docs/13-uat-checklist.md` | `uat_scenarios.csv` + `uat_criteria.csv` | سناریوهای پذیرش و معیارهای کمّی |
| `docs/06-hardware-sensors-catalog.md` | `sensors.csv` + `hw_principles.csv` + `hw_standards.csv` + `hw_cost_items.csv` | حجم تجهیزات، اصول انتخاب، مراجع و ردیف‌های هزینه‌ایِ فراموش‌شده |
| `docs/15-nfr-security-compliance.md` | `nfr.csv` + `ot_controls.csv` + `compliance.csv` + … | ۲۹ الزام غیرکارکردی، ۲۵ کنترل OT، استانداردها و گزارش‌های ممیزی |
| `docs/18-data-model.md` | `entities.csv` + `id_conventions.csv` + `retention_classes.csv` + … | موجودیت‌ها، قرارداد شناسه، کلاس‌های نگه‌داری و سیاست‌های تغییر |
| `docs/07-ui-forms-by-role.md` | `roles.csv` + `ui_matrix.csv` + `role_map.csv` + `role_journey.csv` | ۲۴ نقش، ۶۷۲ خانهٔ دسترسی، نگاشت به RACI و سفر کاریِ هر نقش |
| `docs/00-executive-summary.md` | `gaps.csv` + `adr_summary.csv` + `exec_targets.csv` + `phase_summary.csv` + … | گسست‌ها، شش تصمیمِ سخت، اعداد هدف، فازها، بازگشت سرمایه، حاکمیت |
| `docs/01-inputs-and-assumptions.md` | `input_params.csv` + `assumptions.csv` + `glossary.csv` + `unit_codes.csv` | پارامترهای ورودی، ثبتِ فرض‌ها، واژه‌نامه، کدهای واحدها |
| `docs/22-vendor-selection.md` | `vendor_criteria.csv` + `vendor_knockout.csv` + `vendor_scores.csv` + … | وزن‌های ارزیابی، معیارهای حذف، بندهای قرارداد |
| `docs/23-cutover-migration.md` | `cutover_principles.csv` + `migration_domains.csv` + `cutover_day.csv` + … | راهبرد انتقال، مهاجرت داده، Runbook و آشتی‌سازی |
| `docs/02-reference-architecture.md` | `arch_conduits.csv` + `latency_budgets.csv` + `tag_naming.csv` + … | کاندویت‌های منطقی، بودجهٔ تأخیر، نام‌گذاری تگ، پروتکل‌ها، تاب‌آوری |
| `docs/14-change-management.md` | `resistance.csv` + `change_roles.csv` + `training_plan.csv` + … | مقاومت و پاسخ، نقش‌ها، ارتباطات، آموزش، شاخص‌های پذیرش |
| `docs/17-architecture-decisions.md` | `hard_gates.csv` + `adr_index.csv` | گیت‌های سخت و فهرستِ تصمیمات |
| `docs/20-api-contract.md` | `api_endpoints.csv` + `api_conventions.csv` + `integration_slo.csv` + … | ۲۹ نقطهٔ پایانی، قراردادها و شاخص‌های سلامت |
| `docs/21-sequence-flows.md` | `flow_failures.csv` + `flow_gates.csv` + `flow_monitoring.csv` | نقاط شکست، گیت‌ها و پایشِ هر جریان |

بازتولید همهٔ موارد بالا:

```bash
python3 tools/build_integration_matrix.py && python3 tools/build_catalogs.py
```

کیفیت این مخزن با ۹۶ تست خودکار پایش می‌شود؛ اجرا:

```bash
python3 tools/test_build.py     # ۶۱ تستِ داده، مستندات و بستهٔ انتشار (پایتون)
node tools/test_site.js         # ۳۵ تستِ سایت و داشبورد (جاوااسکریپت)
python3 tools/build_site.py --check   # بستهٔ انتشار را می‌سازد و فقط بررسی می‌کند
```

همین بررسی‌ها در GitHub Actions (`.github/workflows/docs.yml`) اجرا می‌شوند و اگر
مستندِ تولید‌شده با CSV هم‌خوان نباشد، ساخت شکست می‌خورد.

همهٔ ۱۵ مستندِ اصلی (۰۰، ۰۱، ۰۲، ۰۶، ۰۷، ۱۰، ۱۳، ۱۴، ۱۵، ۱۷، ۱۸، ۲۰، ۲۱، ۲۲، ۲۳) ترکیبی‌اند:
متن در قالب (`tools/templates/`) و جدول‌ها از CSV. مستندات ۰۳ تا ۰۵، ۰۸، ۰۹، ۱۱، ۱۲، ۱۶، ۱۹ و ۲۴ تا ۲۷
کاملاً تولیدی‌اند. هیچ جدولی در هیچ مستندی دستی نوشته نمی‌شود.
بازتولید آن‌ها:

```bash
python3 tools/build_templates.py
```

جزئیات خط لوله، قراردادهای CSV و شیوهٔ ویرایش ایمن: [`tools/README.md`](tools/README.md)

## ۶. قراردادهای این مخزن

- همهٔ اسناد **فارسی/RTL** هستند؛ اصطلاحات فنی کنار معادل انگلیسی می‌آیند.
- هر ادعای کمی یا با `[فرض]` برچسب خورده یا به یک KPI/ماژول/ردیف جدول ارجاع داده شده است.
- فایل‌های `data/*.csv` **منبع ماشین‌خوان** جداول‌اند؛ `docs/*.md` نمای انسانی همان داده.
- تغییر در هر CSV باید با تغییر در مستند مرتبط همراه باشد (بررسی در Code Review).

---

## ۷. از کجا شروع کنید

*برای شروع مطالعه: از [`docs/00-executive-summary.md`](docs/00-executive-summary.md) شروع کنید،
سپس [`docs/02-reference-architecture.md`](docs/02-reference-architecture.md)،
و برای هر واحد سراغ [`docs/03-units/`](docs/03-units/) بروید.*
