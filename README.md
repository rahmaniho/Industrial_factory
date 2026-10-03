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

### مستندات تکمیلیِ اجرایی (۱۶ تا ۲۷)

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

## ۳. سایت زنده (GitHub Pages)

این مخزن یک **سایت تعاملی** هم دارد که همهٔ بخش‌ها را قابل مرور و استفاده می‌کند:

**🌐 <https://rahmaniho.github.io/Industrial_factory/>**

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

بازتولید همهٔ موارد بالا:

```bash
python3 tools/build_integration_matrix.py && python3 tools/build_catalogs.py
```

کیفیت این مخزن با ۲۰ تست خودکار پایش می‌شود؛ اجرا:

```bash
python3 tools/test_build.py     # ۲۸ تستِ داده و مستندات (پایتون)
node tools/test_site.js         # ۱۸ تستِ سایت و داشبورد (جاوااسکریپت)
```

همین بررسی‌ها در GitHub Actions (`.github/workflows/docs.yml`) اجرا می‌شوند و اگر
مستندِ تولید‌شده با CSV هم‌خوان نباشد، ساخت شکست می‌خورد.

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
