# ۱۸. مدل داده و قراردادهای شناسه‌گذاری

> این سند «قراردادِ داده» ی پروژه است: چه موجودیت‌هایی داریم، کدام سرویس مالک آن‌هاست،
> چگونه به هم ارجاع می‌دهند، و هر کلاس داده چقدر نگه‌داری می‌شود.

## ۱۸-۱. مرزهای دامنه (Bounded Contexts)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                        هاب داده پایه (MDM) — Single Source of Truth            │
│   کالا · BOM · Recipe · دارایی · قطعه · طرف تجاری · سازمان · مهارت · مناطق     │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │ انتشار (API + رویداد)
   ┌────────────┼───────────┬───────────┬───────────┬───────────┬───────────┐
   ▼            ▼           ▼           ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  MES   │ │  LIMS  │ │  WMS   │ │  CMMS  │ │  HSE   │ │  ACS   │ │  ERP   │
│ تولید  │ │ کیفیت  │ │ انبار  │ │ نگهداشت│ │ ایمنی  │ │ حراست  │ │ مالی   │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │          │          │          │
    └──────────┴──────────┴────┬─────┴──────────┴──────────┴──────────┘
                               │  رویدادها (Kafka) · تله‌متری (Historian)
                    ┌──────────▼───────────┐
                    │  انبار داده / BI     │
                    │  + Audit Store (WORM)│
                    └──────────────────────┘
```

**قانون:** هیچ سرویسی مستقیماً به پایگاه‌دادهٔ سرویس دیگر نمی‌خواند. ارجاع فقط با **شناسه** است؛
ارجاع با API یا رویداد حل می‌شود. کلید خارجیِ بین‌پایگاه‌داده‌ای ممنوع (ADR-002).

## ۱۸-۲. هستهٔ تولید و ردیابی (مدل موجودیت)

```
                       ┌──────────────────┐
                       │   SalesOrder     │   (ERP)
                       │   so_id          │
                       └────────┬─────────┘
                                │ 1..n
                       ┌────────▼─────────┐        ┌──────────────────┐
                       │   WorkOrder      │◄───────│   Routing        │
                       │   wo_id          │  n..1  │   routing_id     │
                       │   product(GTIN)  │        └──────────────────┘
                       │   recipe_ver     │
                       │   line / shift   │        ┌──────────────────┐
                       │   planned_qty    │◄───────│   Recipe (ver)   │
                       └────┬────────┬────┘  n..1  │   recipe_id+ver  │
                            │        │             └──────────────────┘
                1..n        │        │ 1..n
        ┌───────────────────▼──┐  ┌──▼──────────────────────┐
        │  MaterialConsumption │  │   Batch (بچ محصول)      │
        │  material_batch_id   │  │   batch_id              │
        │  qty / uom           │  │   wo_id                 │
        │  bin_id              │  │   qty_produced          │
        │  scale_id / operator │  │   quality_status        │
        └──────────┬───────────┘  │   genealogy_ver         │
                   │              └──┬───────────────────┬──┘
                   │                 │                   │
        ┌──────────▼───────────┐     │ 1..n              │ 1..n
        │ VendorBatch (ماده)   │     │            ┌──────▼──────────┐
        │ vendor_batch_id      │     │            │  SSCC / Pallet  │
        │ supplier / expiry    │     │            │  sscc           │
        │ quality_status       │     │            │  shipment_id    │
        └──────────────────────┘     │            └──────┬──────────┘
                                     │                   │ n..1
                          ┌──────────▼──────────┐  ┌─────▼──────────┐
                          │  QualityResult      │  │   Shipment     │
                          │  sample_id / spec   │  │   shipment_id  │
                          │  value / verdict    │  │   customer     │
                          └─────────────────────┘  └────────────────┘

        ┌──────────────────────┐      ┌──────────────────────┐
        │  BatchGenealogyEdge  │      │  DowntimeEvent       │
        │  parent_type/id      │      │  equipment_id        │
        │  child_type/id       │      │  start/end_ts        │
        │  qty / uom           │      │  reason_id (درخت)    │
        └──────────────────────┘      │  wo_id (اختیاری)     │
                                      └──────────────────────┘
```

**نکتهٔ کلیدی:** ردیابی با **گرافِ یال‌ها** (`BatchGenealogyEdge`) مدل می‌شود، نه با درخت.
چون در فرآیند واقعی یک بچِ ماده به چند بچِ محصول می‌رود و برعکس (تقسیم و ادغام).
این تصمیم مستقیماً امکانِ پاسخِ زیر ۳۰ ثانیه در سناریوی فراخوان را فراهم می‌کند.

## ۱۸-۳. موجودیت‌های هسته و مالک سرویس

| موجودیت | سرویس مالک | کلید | ارجاع‌های اصلی | کلاس نگه‌داری |
|---|---|---|---|---|
| WorkOrder | MES | `wo_id` | product، recipe_ver، routing، line، shift | عملیاتی ۷y |
| Batch | MES | `batch_id` | wo، product، quality_status | عملیاتی ۷y |
| MaterialConsumption | MES | `consumption_id` (ULID) | wo، vendor_batch، bin، scale، operator | عملیاتی ۷y |
| BatchGenealogyEdge | MES | `edge_id` | parent، child، qty | عملیاتی ۷y |
| DowntimeEvent | MES | `downtime_id` | equipment، reason، wo | عملیاتی ۳y |
| VendorBatch | WMS | `vendor_batch_id` | item، supplier، bin، quality_status | عملیاتی ۷y |
| StockMovement | WMS | `movement_id` | item، batch، from_bin، to_bin، ref_doc | عملیاتی ۷y |
| SSCC/Pallet | WMS | `sscc` | batches، shipment، bin | عملیاتی ۷y |
| Sample / QualityResult | LIMS | `sample_id` / `result_id` | batch، spec، method، instrument | انطباق ۱۰y |
| NCR / CAPA | QMS | `ncr_id` / `capa_id` | batch، item، root_cause | انطباق ۱۰y |
| Asset | CMMS | `asset_id` | parent، class، cost_center، criticality | عمر دارایی + ۵y |
| WorkRequest / WorkOrder(MNT) | CMMS | `wo_mnt_id` | asset، skill، ptw، parts | عملیاتی ۱۰y |
| FailureEvent | CMMS | `failure_id` | asset، failure_mode، cause | عملیاتی ۱۰y |
| PTW / LOTO | HSE | `ptw_id` | asset، wo_mnt، approvals، gas_reading | انطباق ۱۰y |
| Incident | HSE | `incident_id` | person، location، severity | انطباق ۱۰y |
| AccessEvent | ACS | `access_id` (ULID) | person، zone، door، result | امنیتی ۱y (ویدئو ۳۰d) |
| GatePass | ACS/WMS | `gate_pass_id` | shipment، vehicle، approvals | عملیاتی ۳y |
| Person / Competency | HRM | `person_id` | org_unit، skills، certs | طبق قانون کار |
| ShiftAssignment | HRM/T&A | `assignment_id` | person، shift، line، date | عملیاتی ۳y |
| SalesOrder / Invoice | ERP | `so_id` / `invoice_id` | customer، items، shipment | مالی ۱۰y |
| FinancialPosting | ERP | `posting_id` | source_event_id، accounts، cost_center | مالی ۱۰y |
| AuditEvent | Audit Store | `event_id` (ULID) | actor، entity، correlation_id | WORM طبق کلاس |

## ۱۸-۴. قراردادهای شناسه

| نوع | قالب | مثال | توضیح |
|---|---|---|---|
| `event_id` | ULID (26 حرف) | `01J9Z8X7K2M3N4P5Q6R7S8T9V0` | قابل مرتب‌سازی زمانی؛ تولید آفلاین |
| `correlation_id` | ULID | — | یکتا برای هر زنجیرهٔ فرآیند |
| `batch_id` (محصول) | `B-YYMMDD-XX` | `B-14040711-03` | سال/ماه/روز شمسی + شمارندهٔ خط |
| `vendor_batch_id` | `RM-YYMMDD-<کد تامین‌کننده>` | `RM-14040701-A2` | کد تأمین‌کننده از MDM |
| `wo_id` | `WO-YYMMDD-NNNN` | `WO-14040711-0012` | — |
| `wo_mnt_id` | `MW-YYYY-NNNNNN` | `MW-1404-001234` | سال مالی + شمارنده |
| `asset_id` | مطابق درخت دارایی | `THR1-PRD-LN1-PMP-P04` | هم‌راستا با قرارداد نام تگ |
| `bin_id` | `ZONE-AISLE-RACK-BIN` | `RM-Z1-A03-R12-B4` | مکان‌محوری دو لایه‌ای |
| `sscc` | GS1 SSCC-18 | — | تخصیص از محدودهٔ GS1 سازمان |
| GTIN | GS1 (۸/۱۲/۱۳/۱۴ رقم) | `6260000000013` | کالای تجاری |
| GLN | GS1 (۱۳ رقم) | — | مکان/طرف تجاری |
| `person_id` | `EMP-NNNNN` | `EMP-00431` | شمارهٔ پرسنلی |
| `sample_id` | `SMP-YYMMDD-NNN` | `SMP-14040711-014` | — |
| `posting_id` | داخلی ERP | — | با ارجاع به `source_event_id` |

## ۱۸-۵. کلاس‌های نگه‌داری و پاک‌سازی

| کلاس | دامنه | مدت | رسانه | قابل حذف؟ |
|---|---|---|---|---|
| **تله‌متری خام** | مقادیر سنسور با برچسب زمان | ۲ سال فشرده + نمونه‌برداری‌شده ۱۰ سال | Historian + object store | بله (پس از انقضا) |
| **عملیاتی** | تراکنش‌های تولید/انبار/نگهداشت | ۳ تا ۱۰ سال | پایگاه داده + پشتیبان | خیر (آرشیو) |
| **انطباق** | نتایج کیفیت، CAPA، PTW، حوادث | ۱۰ سال [فرض] | پایگاه داده + WORM | خیر |
| **مالی** | اسناد حسابداری | ۱۰ سال [فرض] | ERP + آرشیو | خیر |
| **حسابرسی (Audit)** | رویدادهای تراکنش‌های بحرانی | ۷ سال (هم‌راستا با طولانی‌ترین کلاس مرتبط) | WORM + تکرار خارج از سایت | **هرگز** |
| **امنیتی** | لاگ تردد، دسترسی‌ها، SIEM | ۱ سال آنلاین + ۳ سال آرشیو | SIEM/آرشیو | خیر |
| **ویدئو** | تصاویر دوربین‌ها | ۳۰ روز (رخدادها تا بسته‌شدن پرونده + ۱ سال) | NVR + WORM برای رخدادها | خیر (برای رخدادها) |
| **شخصی (PII)** | داده‌های پرسنلی حساس | طبق قانون کار و سیاست حریم خصوصی | پایگاه داده با رمزنگاری | بله (با فرآیند) |
| **تحلیلی** | انبار داده و مکعب‌ها | ۵ سال | DWH | بله (بازسازی از Kafka) |

> **حداقل‌سازی:** رویدادها نباید حاوی دادهٔ شخصیِ مستقیم یا جزئیات مالی باشند؛
> فقط شناسه + مقدارِ مورد نیاز. این هم امنیت را بهتر می‌کند و هم با ADR-005 (WORMِ غیرقابل‌حذف) سازگار است.

## ۱۸-۶. یکپارچگیِ مرجع بین سرویس‌ها (بدون FK)

| رابطه | سیاست | مکانیزم کنترل |
|---|---|---|
| WorkOrder → Recipe | نسخهٔ Recipe در لحظهٔ صدور **قفل** می‌شود | ذخیرهٔ `recipe_ver` روی WO |
| WorkOrder → Asset | ارجاع با شناسه؛ در صورت حذف دارایی، WO تاریخچه می‌ماند | حذف منطقی (Soft Delete) |
| Consumption → VendorBatch | اعتبارسنجی در لحظهٔ اسکن (نه پس از آن) | فراخوانی همزمان به WMS (گیت) |
| Batch → QualityResult | Batch بدون نتیجهٔ اجباری، قابل ترخیص نیست | گیت کیفیت در MES |
| StockMovement → FinancialPosting | هر حرکتِ ارزش‌دار باید دقیقاً یک سند داشته باشد | شمارش انطباق + هشدار `A096` |
| AuditEvent → هر موجودیت | ارجاع با `entity.type` + `entity.id` | بدون وابستگی سخت |

## ۱۸-۷. سیاست تغییرِ دادهٔ پایه (SCD)

| نوع تغییر | سیاست | مثال |
|---|---|---|
| **نوع ۰ (ثابت)** | تغییر ممنوع | `event_id`، `posting_id`، شناسه‌های تراکنشی |
| **نوع ۱ (بازنویسی)** | اصلاحِ خطا با ثبت علت | نام کالا، آدرس |
| **نوع ۲ (تاریخچه)** | نسخهٔ جدید با بازهٔ اعتبار | Recipe، BOM، قیمت، مشخصات کیفی |
| **انقضا** | غیرفعال‌سازی به‌جای حذف | کالای متوقف‌شده، دارایی اسقاط‌شده، قطعهٔ جایگزین‌شده |

**قانون:** هیچ موجودیتِ پایه‌ای که در یک تراکنشِ تاریخی استفاده شده، به‌صورت فیزیکی حذف یا بازنویسی نمی‌شود؛
تغییر با نسخهٔ جدید و بازهٔ اعتبار انجام می‌شود تا گزارش‌های گذشته بازتولیدپذیر بمانند.

## ۱۸-۸. ابعاد مشترک برای تحلیل (Conformed Dimensions)

برای اینکه BI یک عدد بدهد، همهٔ جداولِ واقعیت باید از این ابعادِ مشترک استفاده کنند:

| بُعد | منبع | کلید | ویژگی‌های کلیدی |
|---|---|---|---|
| زمان | تقویمِ سایت | `date_key` / `shift_key` | شمسی/میلادی، شیفت، تعطیلی |
| محصول | MDM | `item_key` | GTIN، گروه، بسته‌بندی |
| تجهیز/خط | MDM/CMMS | `asset_key` | درخت، کلاس، بحرانی‌بودن |
| مکان/انبار | MDM/WMS | `bin_key` | ناحیه، کلاس دمایی |
| سازمان/مرکز هزینه | MDM/ERP | `cost_center_key` | واحد، مدیر |
| پرسنل | HRM | `person_key` | نقش، مهارت، شیفت (بدون PII در DWH) |
| طرف تجاری | MDM/ERP | `partner_key` | مشتری/تأمین‌کننده، بخش |
| بچ | MES | `batch_key` | محصول، خط، وضعیت کیفی |

---

← بعدی: [`19-event-catalog.md`](19-event-catalog.md)
