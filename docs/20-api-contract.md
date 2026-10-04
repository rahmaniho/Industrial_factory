# ۲۰. قرارداد سرویس‌ها (API Contract)

> «API-First» در این پروژه یعنی: **ابتدا قرارداد، بعداً پیاده‌سازی**.
> این سند قراردادهای لازم برای فازهای ۳ و ۴ است؛ نسخهٔ ماشین‌خوان (OpenAPI/AsyncAPI)
> باید در مخزنِ کدِ هر سرویس نگه‌داری و در CI اعتبارسنجی شود.

## ۲۰-۱. قراردادهای عمومی

| موضوع | قرارداد |
|---|---|
| پایهٔ مسیر | `https://{host}/api/{service}/v{major}` — مثال: `/api/mes/v1/work-orders` |
| نسخه‌بندی | نسخهٔ بزرگ در مسیر؛ تغییرِ شکننده ⇒ نسخهٔ جدید + ۶ ماه هم‌زیستی + تاریخ بازنشستگی اعلام‌شده |
| احراز | OAuth 2.0 / OIDC با JWT کوتاه‌عمر؛ سرویس‌به‌سرویس با mTLS؛ MFA برای عملیات حساس |
| مجوز | بر اساس RBAC + ABAC (رجوع به [`10-raci-rbac.md`](10-raci-rbac.md)) |
| همبستگی | سرآیندهای `X-Correlation-Id` و `X-Causation-Id` الزامی |
| باید (Idempotency) | سرآیند `Idempotency-Key` برای همهٔ درخواست‌های تغییردهنده (`POST`/`PATCH`) |
| صفحه‌بندی | `?limit=&cursor=` (مبتنی بر نشانک، نه offset)؛ حداکثر ۵۰۰ رکورد |
| مرتب‌سازی و فیلتر | `?sort=&filter[field]=` با فیلدهای مجازِ اعلام‌شده |
| خطا | RFC 7807 (`application/problem+json`) با `type`، `title`، `status`، `detail`، `correlation_id` |
| نرخ | محدودیت نرخ اعلام‌شده + سرآیندهای `RateLimit-*`؛ پاسخ ۴۲۹ با `Retry-After` |
| زمان | همهٔ زمان‌ها ISO-8601 با **UTC**؛ سرآیند `X-Site-Timezone` فقط برای راهنمایی نمایش |
| زبان | `Accept-Language: fa-IR` (پیش‌فرض)، `en-US`؛ پیام‌های خطا ترجمه‌شده با کد ثابت |
| ممیزی | هر درخواستِ تغییردهنده یک رکورد در Audit با actor، علت (در صورت نیاز) و قبل/بعد |

### نمونهٔ خطا

```json
{
  "type": "https://api.factory/errors/quality-gate-blocked",
  "title": "گیت کیفیت مسدود است",
  "status": 409,
  "detail": "بچ RM-14040701-A2 در وضعیت quarantine است و قابل مصرف نیست.",
  "correlation_id": "01J9Z8X0000000000000000000",
  "errors": [
    { "field": "vendor_batch_id", "code": "NOT_RELEASED", "message": "وضعیت فعلی: quarantine" }
  ]
}
```

## ۲۰-۲. فهرست سرویس‌های مورد نیاز

| سرویس | دامنه | وابستگی‌های داده‌ای |
|---|---|---|
| `mdm` | دادهٔ پایه و انتشار | مالکِ موجودیت‌ها |
| `mes` | دستور کار، مصرف، بچ، ردیابی، OEE | mdm، wms، qms، cmms |
| `qms` (LIMS) | نمونه، نتیجه، گیت کیفیت، NCR/CAPA | mdm، mes |
| `wms` | موجودی، مکان، حرکات، پالت/SSCC، ارسال | mdm، qms، mes |
| `cmms` | دارایی، درخواست/دستور کار، PM، PdM | mdm， mro، hse |
| `hse` | خطر، PTW/LOTO، رخداد، پایش | mdm، cmms، hr |
| `acs` | تردد، مجوز خروج، رخداد امنیتی | mdm، hr، wms |
| `hr` | پرسنل، مهارت، گواهی، شیفت، کارکرد | mdm |
| `erp` | سفارش، خرید، مالی، دارایی | mdm |
| `bi` | لایهٔ معنایی و پرس‌وجوی تحلیلی | همه (فقط خواندن) |
| `audit` | جست‌وجو و اثبات یکپارچگی | Audit Store |

## ۲۰-۳. نقاط پایانیِ کلیدی

نمادها: 🔒 نیازمند مجوز · ♻️ باید (Idempotent) · ⭐ بحرانی

### الف) MES — مدیریت تولید

| متد | مسیر | هدف | مجوز | ♻️ |
|---|---|---|---|---|
| `GET` | `/api/mes/v1/work-orders` | فهرست دستور کارها (فیلتر: خط، وضعیت، بازه) | `mes.wo.read` | — |
| `POST` | `/api/mes/v1/work-orders` | صدور دستور کار | `mes.wo.create` | ♻️ |
| `GET` | `/api/mes/v1/work-orders/{wo_id}` | جزئیات + پیشرفت | `mes.wo.read` | — |
| `POST` | `/api/mes/v1/work-orders/{wo_id}/start` | شروع (با گیت‌های BR-PRD-01) | `mes.wo.start` | ♻️ ⭐ |
| `POST` | `/api/mes/v1/work-orders/{wo_id}/consumptions` | ثبت مصرف (کسر خودکار موجودی) | `mes.consumption.create` | ♻️ ⭐ |
| `POST` | `/api/mes/v1/work-orders/{wo_id}/complete` | اتمام + اعلام بچ | `mes.wo.complete` | ♻️ ⭐ |
| `POST` | `/api/mes/v1/downtimes` | ثبت توقف با علت | `mes.downtime.create` | ♻️ |
| `GET` | `/api/mes/v1/oee?line=&from=&to=` | محاسبهٔ A×P×Q | `mes.oee.read` | — |

**نمونه — ثبت مصرف:**

```http
POST /api/mes/v1/work-orders/WO-14040711-0012/consumptions
Idempotency-Key: MES:consumption:WO-14040711-0012:RM-14040701-A2:1240.5
X-Correlation-Id: 01J9Z8X0000000000000000000
Content-Type: application/json

{
  "material_id": "GTIN-6260000000099",
  "vendor_batch_id": "RM-14040701-A2",
  "qty": 1240.5,
  "uom": "kg",
  "bin_id": "RM-Z1-A03-R12-B4",
  "scale_id": "SCALE-LN1-01",
  "weighed_by": "EMP-00431",
  "occurred_at": "2026-10-03T08:14:22.415Z"
}
```

```json
{
  "consumption_id": "01J9Z8X7K2M3N4P5Q6R7S8T9V0",
  "status": "posted",
  "stock_movement_id": "01J9Z8X7K2M3N4P5Q6R7S8T9V1",
  "genealogy_edges_created": 1,
  "warnings": []
}
```

اگر بچ قرنطینه باشد ⇒ `409` با `type=.../quality-gate-blocked` (مثال بالا).

### ب) QMS — گیت کیفیت و نتایج

| متد | مسیر | هدف | مجوز | ♻️ |
|---|---|---|---|---|
| `POST` | `/api/qms/v1/samples` | ثبت نمونه | `qms.sample.create` | ♻️ |
| `POST` | `/api/qms/v1/results` | ثبت نتیجهٔ آزمون | `qms.result.create` | ♻️ ⭐ |
| `POST` | `/api/qms/v1/batches/{batch_id}/release` | ترخیص بچ (امضای الکترونیکی) | `qms.release` 🔒 | ♻️ ⭐ |
| `POST` | `/api/qms/v1/batches/{batch_id}/quarantine` | قرنطینه | `qms.quarantine` 🔒 | ♻️ ⭐ |
| `GET` | `/api/qms/v1/specs/{item_id}` | مشخصات و حدود | `qms.spec.read` | — |

### ج) WMS — موجودی و ارسال

| متد | مسیر | هدف | مجوز | ♻️ |
|---|---|---|---|---|
| `GET` | `/api/wms/v1/stock?item=&bin=&status=` | موجودی با وضعیت کیفی | `wms.stock.read` | — |
| `GET` | `/api/wms/v1/atp?item=&qty=&date=` | موجودی قابل تعهد | `wms.atp.read` | — |
| `POST` | `/api/wms/v1/receipts` | ثبت رسید (قرنطینهٔ خودکار) | `wms.receipt.create` | ♻️ ⭐ |
| `POST` | `/api/wms/v1/movements` | حرکت/جابجایی با مکان مبدأ و مقصد | `wms.movement.create` | ♻️ |
| `POST` | `/api/wms/v1/pallets` | ساخت پالت با SSCC | `wms.pallet.create` | ♻️ |
| `POST` | `/api/wms/v1/shipments/{id}/dispatch` | اعلام ارسال (ماشهٔ فاکتور و مجوز خروج) | `wms.ship.dispatch` 🔒 | ♻️ ⭐ |

### د) CMMS / HSE / HR — نگهداشت، ایمنی، نیرو

| متد | مسیر | هدف | مجوز | ♻️ |
|---|---|---|---|---|
| `POST` | `/api/cmms/v1/work-requests` | درخواست کار (از اسکن QR) | `cmms.wr.create` | ♻️ |
| `POST` | `/api/cmms/v1/work-orders/{id}/start` | شروع (با گیت PTW) | `cmms.wo.start` 🔒 | ♻️ ⭐ |
| `POST` | `/api/cmms/v1/work-orders/{id}/complete` | بستن با علت خرابی و زمان واقعی | `cmms.wo.complete` | ♻️ ⭐ |
| `POST` | `/api/hse/v1/permits` | درخواست PTW | `hse.ptw.create` | ♻️ ⭐ |
| `POST` | `/api/hse/v1/permits/{id}/approve` | تأیید مرحله‌ای | `hse.ptw.approve` 🔒 | ♻️ ⭐ |
| `GET` | `/api/hr/v1/competencies/eligible?skill=&line=` | واجدان شرایط حاضر | `hr.comp.read` | — |

### هـ) ردیابی و حسابرسی

| متد | مسیر | هدف | مجوز |
|---|---|---|---|
| `GET` | `/api/mes/v1/trace/{batch_id}?direction=backward\|forward` | گراف ردیابی | `mes.trace.read` |
| `POST` | `/api/mes/v1/trace/recall-simulation` | شبیه‌سازی فراخوان | `mes.trace.recall` 🔒 |
| `GET` | `/api/audit/v1/events?entity=&actor=&from=&to=` | جست‌وجوی حسابرسی | `audit.read` 🔒 |
| `GET` | `/api/audit/v1/chain/verify?from=&to=` | اثبات یکپارچگی زنجیره | `audit.verify` 🔒 |

## ۲۰-۴. معناشناسیِ رویدادها (AsyncAPI — خلاصه)

| قاعده | مقدار |
|---|---|
| تحویل | حداقل یک‌بار (At-Least-Once)؛ مصرف‌کننده باید idempotent باشد |
| ترتیب | در سطح کلیدِ پارتیشن (مثلاً `wo_id`) |
| تلاش مجدد | ۵ تلاش با backoff نمایی؛ سپس DLQ بر اساس سیاستِ [`19-event-catalog.md`](19-event-catalog.md) |
| سازگاری | `BACKWARD` در Schema Registry؛ حذفِ فیلد ممنوع؛ افزودن فیلد اختیاری مجاز |
| مستند | AsyncAPI برای هر تولیدکننده در مخزن کد + انتشار خودکار در پورتال توسعه‌دهندگان |

## ۲۰-۵. شاخص‌های سلامتِ یکپارچه‌سازی

| شاخص | تعریف | هدف | هشدار |
|---|---|---|---|
| درصد اسناد مالی خودکار (`K111`) | اسناد خودکار / کل اسناد | ≥ ۹۰٪ | `A096` |
| رویدادهای در DLQ | تعداد در ۲۴ ساعت گذشته | ۰ برای رویدادهای `critical` | `A099` |
| تأخیر مصرف‌کننده (Consumer Lag) | فاصلهٔ پردازش از انتهای موضوع | < ۳۰ ثانیه | `A099` |
| نرخ خطای ۵xx در API | خطاها / کل درخواست‌ها | < ۰٫۵٪ | مانیتورینگ |
| نرخ تلاشِ مجددِ ناشی از idempotency | تکرارهای شناسایی‌شده | پایش (نشانهٔ رفتار درست) | — |
| زمان پاسخ p95 | روی ۱۰ مسیرِ پرمصرف | < ۱ ثانیه | مانیتورینگ |

## ۲۰-۶. سیاستِ تغییرِ قرارداد

1. هر تغییر در قرارداد نیازمند Pull Request با بررسیِ معمار کل است.
2. تستِ قرارداد (Contract Test) برای هر مصرف‌کننده در CI اجرا می‌شود.
3. تغییرِ شکننده ⇒ نسخهٔ جدید + اعلام در «تغییراتِ قرارداد» + مهلت ۶ ماهه.
4. حذفِ یک نقطهٔ پایانی، مستلزمِ تأیید کتبیِ همهٔ مصرف‌کنندگانِ شناسایی‌شده است (از روی لاگ‌ها).
5. مستندِ OpenAPI همواره با پیاده‌سازی هم‌زمان به‌روز می‌شود؛ هرگونه مغایرت، باگ محسوب می‌شود.

---

← بعدی: [`21-sequence-flows.md`](21-sequence-flows.md)
