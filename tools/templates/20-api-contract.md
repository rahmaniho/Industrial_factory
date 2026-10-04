# ۲۰. قرارداد سرویس‌ها (API Contract)

> این قالب، منبعِ متنِ `20-api-contract.md` است.
> جدول‌ها با نشانه‌هایی مانند `{{ api_conventions }}` جایگذاری شده‌اند و از فایل‌های `data/*.csv` ساخته می‌شوند.
> برای تغییرِ یک جدول، CSV را ویرایش کنید؛ برای تغییرِ متن، همین قالب را.


> «API-First» در این پروژه یعنی: **ابتدا قرارداد، بعداً پیاده‌سازی**.
> این سند قراردادهای لازم برای فازهای ۳ و ۴ است؛ نسخهٔ ماشین‌خوان (OpenAPI/AsyncAPI)
> باید در مخزنِ کدِ هر سرویس نگه‌داری و در CI اعتبارسنجی شود.

## ۲۰-۱. قراردادهای عمومی

{{api_conventions}}

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

{{api_services}}

## ۲۰-۳. نقاط پایانیِ کلیدی

نمادها: 🔒 نیازمند مجوز · ♻️ باید (Idempotent) · ⭐ بحرانی

### الف) MES — مدیریت تولید

{{api_endpoints_mes}}

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

{{api_endpoints_qms}}

### ج) WMS — موجودی و ارسال

{{api_endpoints_wms}}

### د) CMMS / HSE / HR — نگهداشت، ایمنی، نیرو

{{api_endpoints_ops}}

### هـ) ردیابی و حسابرسی

{{api_endpoints_trace}}

## ۲۰-۴. معناشناسیِ رویدادها (AsyncAPI — خلاصه)

{{event_rules}}

## ۲۰-۵. شاخص‌های سلامتِ یکپارچه‌سازی

{{integration_slo}}

## ۲۰-۶. سیاستِ تغییرِ قرارداد

1. هر تغییر در قرارداد نیازمند Pull Request با بررسیِ معمار کل است.
2. تستِ قرارداد (Contract Test) برای هر مصرف‌کننده در CI اجرا می‌شود.
3. تغییرِ شکننده ⇒ نسخهٔ جدید + اعلام در «تغییراتِ قرارداد» + مهلت ۶ ماهه.
4. حذفِ یک نقطهٔ پایانی، مستلزمِ تأیید کتبیِ همهٔ مصرف‌کنندگانِ شناسایی‌شده است (از روی لاگ‌ها).
5. مستندِ OpenAPI همواره با پیاده‌سازی هم‌زمان به‌روز می‌شود؛ هرگونه مغایرت، باگ محسوب می‌شود.

---

← بعدی: [`21-sequence-flows.md`](21-sequence-flows.md)
