# ۱۹. کاتالوگ رویدادها (Event Catalog)

> تولید‌شده از `data/event_catalog.csv`.
> این کاتالوگ «قراردادِ زندهٔ» یکپارچه‌سازی است: هر رویداد یک تولیدکننده، یک یا چند مصرف‌کننده، یک کلیدِ باید (Idempotency) و یک سیاستِ خطا دارد.
> قالب کامل رویداد و قواعد `correlation_id` / `causation_id` در [`02-reference-architecture.md`](02-reference-architecture.md#۲-۳-قالب-استاندارد-رویداد-event-envelope) آمده است.

تعداد رویدادهای تعریف‌شده: **54**

## ۱۹-۱. قراردادهای عمومی

| موضوع | قرارداد |
|---|---|
| نام‌گذاری موضوع | `حوزه.زیرحوزه.موجودیت` — مثال: `mes.workorder.created` |
| ترتیب | تضمینِ ترتیب **در سطح کلیدِ پارتیشن** (مثلاً `asset_id` یا `wo_id`)؛ ترتیبِ سراسری تضمین نمی‌شود |
| تحویل | **حداقل یک‌بار** (At-Least-Once) ⇒ مصرف‌کننده باید idempotent باشد |
| تکرار | تلاش مجدد با backoff نمایی (۱s، ۵s، ۳۰s، ۵m، ۳۰m) سپس DLQ |
| نگه‌داری | مطابق ستون «نگه‌داری (روز)»؛ امکان بازپخش (Replay) برای مصرف‌کننده‌های جدید |
| سازگاری | نسخهٔ اسکیما در `schema_version`؛ سیاستِ Schema Registry = `BACKWARD` |
| حریم خصوصی | ستون «PII» مشخص می‌کند آیا رویداد حاوی ارجاع به شخص هست یا نه |
| خطا | سه سطح: `never` (هرگز دور ریخته نشود)، `critical` (DLQ + هشدار)، `buffered` (تلورانسِ از دست رفتنِ جزئی در تله‌متری)، `standard` (DLQ بدون هشدار فوری) |

## ۱۹-۲. کاتالوگ

| موضوع (Topic) | نوع رویداد | تولیدکننده | مصرف‌کنندگان | کلیدهای اصلی پیام | فرکانس | حجم/روز | نگه‌داری (روز) | PII | Idempotency | سیاست خطا | حساسیت |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ot.line.telemetry` | `sensor.reading` | SCADA/Historian | Historian، PdM، MES | `tag`, `ts`, `value`, `quality` | Real-time | 2000000 | 730 | خیر | `tag+ts` | buffered | Critical |
| `ot.line.events` | `equipment.state_changed` | SCADA | MES، CMMS، BI | `asset_id`, `state`, `ts`, `duration_s` | On-event | 5000 | 730 | خیر | `asset_id+ts` | drop_after_log | High |
| `ot.line.alarm` | `alarm.raised` | SCADA/Alarm Console | HSE، CMMS، MES، BI | `alarm_id`, `asset_id`, `severity`, `ts` | On-event | 3000 | 1095 | خیر | `alarm_id+ts` | drop_after_log | Critical |
| `ot.line.counter` | `production.counted` | PLC/SCADA | MES | `asset_id`, `counter`, `good_qty`, `scrap_qty` | Real-time | 50000 | 730 | خیر | `asset_id+ts` | buffered | High |
| `mes.workorder.created` | `workorder.created` | MES | ERP، WMS، CMMS، BI | `wo_id`, `product`, `recipe_ver`, `qty`, `line`, `shift` | On-event | 60 | 2555 | خیر | `wo_id` | critical | Critical |
| `mes.workorder.started` | `workorder.started` | MES | WMS، HRM، BI | `wo_id`, `line`, `operator_ids`, `ts` | On-event | 60 | 2555 | بله | `wo_id` | critical | Critical |
| `mes.workorder.completed` | `workorder.completed` | MES | ERP، WMS، FIN، BI | `wo_id`, `qty_produced`, `scrap`, `ts` | On-event | 60 | 2555 | خیر | `wo_id` | critical | Critical |
| `material.consumed` | `material.consumed` | MES | WMS، ERP، FIN، BI | `wo_id`, `material`, `vendor_batch`, `qty`, `uom`, `bin` | On-event | 4000 | 2555 | خیر | `wo_id+material+vendor_batch` | critical | Critical |
| `material.returned` | `material.returned` | MES | WMS، FIN | `wo_id`, `material`, `vendor_batch`, `qty`, `bin` | On-event | 300 | 2555 | خیر | `wo_id+material+vendor_batch` | critical | High |
| `batch.created` | `batch.created` | MES | WMS، LIMS، BI | `batch_id`, `wo_id`, `product`, `line`, `ts` | On-event | 60 | 2555 | خیر | `batch_id` | critical | Critical |
| `batch.genealogy.edge` | `batch.genealogy.edge` | MES | WMS، BI | `parent_type`, `parent_id`, `child_id`, `qty` | On-event | 20000 | 2555 | خیر | `parent+child` | critical | Critical |
| `batch.released` | `batch.released` | LIMS/MES | WMS، ERP، SAL، BI | `batch_id`, `verdict`, `qa_signature_id` | On-event | 60 | 3650 | خیر | `batch_id` | critical | Critical |
| `batch.quarantined` | `batch.quarantined` | LIMS/MES | WMS، BI | `batch_id`, `reason`, `ncr_id` | On-event | 30 | 3650 | خیر | `batch_id` | critical | Critical |
| `batch.rejected` | `batch.rejected` | LIMS/MES | WMS، FIN، BI | `batch_id`, `reason`, `disposition` | On-event | 10 | 3650 | خیر | `batch_id` | critical | Critical |
| `qms.sample.requested` | `sample.requested` | MES | LIMS | `sample_id`, `batch_id`, `spec_id`, `control_point` | On-event | 500 | 1095 | خیر | `sample_id` | critical | High |
| `qms.result.recorded` | `result.recorded` | LIMS | MES، SPC، BI | `sample_id`, `param`, `value`, `unit`, `verdict` | On-event | 3000 | 3650 | خیر | `sample_id+param` | critical | Critical |
| `qms.spec.breach` | `spec.breach` | LIMS | MES، HSE، BI | `sample_id`, `param`, `value`, `limits` | On-event | 200 | 3650 | خیر | `sample_id+param` | critical | Critical |
| `qms.ncr.created` | `ncr.created` | QMS | MES، HSE، FIN، BI | `ncr_id`, `batch_id`, `severity`, `description` | On-event | 150 | 3650 | خیر | `ncr_id` | critical | High |
| `qms.capa.closed` | `capa.closed` | QMS | BI، HSE | `capa_id`, `ncr_id`, `effectiveness` | On-event | 120 | 3650 | خیر | `capa_id` | standard | Medium |
| `wms.receipt.created` | `receipt.created` | WMS | ERP، QCL، SEC، BI | `receipt_id`, `po_id`, `supplier`, `vehicle`, `weight` | On-event | 60 | 2555 | خیر | `receipt_id` | critical | High |
| `wms.stock.moved` | `stock.moved` | WMS | ERP، FIN، BI | `movement_id`, `item`, `batch`, `from_bin`, `to_bin`, `qty` | On-event | 8000 | 2555 | خیر | `movement_id` | critical | Critical |
| `wms.stock.adjusted` | `stock.adjusted` | WMS | FIN، BI | `adjustment_id`, `item`, `bin`, `qty`, `reason` | On-event | 200 | 2555 | خیر | `adjustment_id` | critical | High |
| `wms.quarantine.set` | `wms.quarantine.set` | WMS | MES، QCL، BI | `item`, `batch`, `bin`, `reason` | On-event | 50 | 3650 | خیر | `item+batch+ts` | critical | Critical |
| `wms.pick.confirmed` | `pick.confirmed` | WMS | MES، SAL، BI | `pick_id`, `so_id`, `sscc`, `qty` | On-event | 3000 | 2555 | خیر | `pick_id` | critical | High |
| `wms.pallet.built` | `pallet.built` | WMS | SAL، EXP، BI | `sscc`, `batch_ids`, `qty`, `weight` | On-event | 400 | 2555 | خیر | `sscc` | critical | High |
| `wms.shipment.dispatched` | `shipment.dispatched` | WMS | SAL، EXP، FIN، SEC، BI | `shipment_id`, `so_id`, `vehicle`, `ssccs`, `ts` | On-event | 40 | 2555 | خیر | `shipment_id` | critical | Critical |
| `wms.pod.confirmed` | `pod.confirmed` | WMS/CRM | SAL، FIN، BI | `shipment_id`, `delivery_ts`, `signature_ref` | On-event | 40 | 2555 | خیر | `shipment_id` | critical | High |
| `cmms.workrequest.created` | `workrequest.created` | CMMS | MES، MRO، BI | `wr_id`, `asset_id`, `source`, `description`, `priority` | On-event | 120 | 2555 | خیر | `wr_id` | critical | High |
| `cmms.workorder.created` | `workorder.created` | CMMS | MRO، HSE، MES، FIN | `wo_mnt_id`, `asset_id`, `type`, `priority`, `planned_start` | On-event | 150 | 3650 | خیر | `wo_mnt_id` | critical | High |
| `cmms.workorder.started` | `workorder.started` | CMMS | MES، HSE، MRO | `wo_mnt_id`, `technician_ids`, `ptw_id`, `ts` | On-event | 150 | 3650 | بله | `wo_mnt_id` | critical | Critical |
| `cmms.workorder.completed` | `workorder.completed` | CMMS | MES، FIN، BI | `wo_mnt_id`, `failure_mode`, `duration`, `parts`, `cost` | On-event | 150 | 3650 | خیر | `wo_mnt_id` | critical | High |
| `pdm.health.scored` | `asset.health.scored` | PdM | CMMS، BI | `asset_id`, `health_score`, `predicted_failure_window` | Hourly | 1200 | 730 | خیر | `asset_id+ts` | buffered | High |
| `pdm.anomaly.detected` | `anomaly.detected` | PdM | CMMS، BI | `asset_id`, `metric`, `score`, `recommendation` | On-event | 60 | 1095 | خیر | `asset_id+metric+ts` | critical | High |
| `hse.ptw.requested` | `ptw.requested` | HSE | CMMS، SEC، BI | `ptw_id`, `type`, `asset_id`, `requester`, `window` | On-event | 40 | 3650 | بله | `ptw_id` | critical | Critical |
| `hse.ptw.approved` | `ptw.approved` | HSE | CMMS، MES | `ptw_id`, `approver`, `conditions`, `valid_until` | On-event | 40 | 3650 | بله | `ptw_id` | critical | Critical |
| `hse.ptw.expired` | `ptw.expired` | HSE | CMMS، SEC | `ptw_id`, `asset_id`, `ts` | On-event | 40 | 3650 | خیر | `ptw_id` | standard | Critical |
| `hse.loto.engaged` | `loto.engaged` | HSE | CMMS، MES | `loto_id`, `asset_id`, `isolation_points`, `verified_by` | On-event | 60 | 3650 | بله | `loto_id` | critical | Critical |
| `hse.gas.alarm` | `gas.alarm.raised` | HSE | SEC، MES، CMMS، BI | `point_id`, `gas`, `concentration`, `threshold` | On-event | 20 | 3650 | خیر | `point_id+ts` | critical | Critical |
| `hse.incident.reported` | `incident.reported` | HSE | HRM، FIN، BI | `incident_id`, `type`, `severity`, `location`, `person_ref` | On-event | 15 | 3650 | بله | `incident_id` | critical | Critical |
| `hse.emergency.declared` | `emergency.declared` | HSE | SEC، MES، CMMS، BI | `level`, `zone`, `ts`, `declared_by` | On-event | 2 | 3650 | خیر | `zone+ts` | critical | Critical |
| `sec.access.event` | `access.granted_denied` | ACS | HRM، BI، SIEM | `access_id`, `person_ref`, `zone`, `door`, `result`, `ts` | Real-time | 3000 | 1095 | بله | `access_id` | critical | High |
| `sec.gatepass.issued` | `gatepass.issued` | ACS | WMS، SAL، BI | `gate_pass_id`, `shipment_id`, `vehicle`, `checks` | On-event | 40 | 1095 | خیر | `gate_pass_id` | critical | Critical |
| `sec.intrusion.detected` | `intrusion.detected` | VMS | SEC، HSE، SIEM | `camera_id`, `zone`, `confidence`, `clip_ref` | On-event | 20 | 1095 | خیر | `camera_id+ts` | critical | Critical |
| `hr.attendance.raw` | `attendance.raw` | ACS | HRM، FIN، MES | `person_ref`, `event_ts`, `device`, `result` | Real-time | 3000 | 1095 | بله | `person_ref+ts` | buffered | High |
| `hr.competency.expired` | `competency.expired` | HRM | HSE، MES، CMMS | `person_ref`, `cert_id`, `expiry` | Daily | 20 | 3650 | بله | `person_ref+cert_id` | standard | Critical |
| `hr.shift.assigned` | `shift.assigned` | HRM/T&A | MES، CMMS، BI | `person_ref`, `shift`, `line`, `date` | Daily | 500 | 1095 | بله | `person_ref+date` | standard | Medium |
| `fin.posting.requested` | `posting.requested` | ERP | FIN، BI | `posting_id`, `source_event_id`, `amount`, `accounts` | On-event | 5000 | 3650 | خیر | `source_event_id` | critical | Critical |
| `fin.posting.failed` | `posting.failed` | ERP | IT، BI | `posting_id`, `source_event_id`, `error` | On-event | 20 | 3650 | خیر | `source_event_id` | critical | Critical |
| `fin.cost.calculated` | `cost.calculated` | ERP | MES، BI | `batch_id`, `cost_per_uom`, `variance_breakdown` | On-event | 60 | 3650 | خیر | `batch_id` | critical | High |
| `mdm.entity.changed` | `entity.changed` | MDM | ERP، MES، WMS، CMMS، BI | `entity_type`, `entity_id`, `version`, `changed_fields` | On-event | 500 | 3650 | خیر | `entity_id+version` | critical | High |
| `mdm.quality.violation` | `quality.violation` | MDM | BI، DMO | `entity_type`, `entity_id`, `rule`, `detail` | On-event | 50 | 1095 | خیر | `entity_id+rule+ts` | standard | High |
| `audit.trail.append` | `audit.appended` | Audit Store | BI، SIEM | `event_id`, `actor`, `entity`, `action`, `prev_hash`, `hash` | On-event | 60000 | 2555 | بله | `event_id` | never | Critical |
| `it.service.degraded` | `service.degraded` | Monitoring | IT، BI | `service`, `metric`, `value`, `threshold` | On-event | 100 | 365 | خیر | `service+ts` | standard | Critical |
| `it.sync.lagging` | `sync.lagging` | Monitoring | IT، MDM | `pipeline`, `lag_seconds`, `threshold` | Real-time | 50 | 365 | خیر | `pipeline+ts` | standard | High |

## ۱۹-۳. سیاست‌های ویژه

| موضوع | سیاست | دلیل |
|---|---|---|
| تله‌متری با حجم بالا | `buffered` — از دست رفتنِ مقطعی تلورانس می‌شود، اما نرخِ از دست‌رفتگی پایش و در داشبورد نمایش داده می‌شود | اقتصادی‌ترین رفتار برای داده‌ای که نمونه‌اش دوباره می‌آید |
| `audit.trail.append` | `never` — هرگز دور ریخته نمی‌شود | مبنای اثباتِ انطباق (ADR-005) |
| رویدادهای مالی | `critical` — DLQ با هشدار فوری | هر رویداد باید دقیقاً یک سند مالی داشته باشد |
| رویدادهای ایمنی | `critical` + تحویلِ چندکاناله (مستقل از Kafka) | در بدترین سناریو هم باید به دست مسئول برسد |
| رویدادهای حاوی PII | فقط **شناسه**؛ جزئیات با API مجاز؛ نگه‌داری محدود | انطباق با حریم خصوصی و سازگاری با WORMِ غیرقابل‌حذف |

## ۱۹-۴. مالکیتِ موضوعات و کنترل دسترسی

| گروه موضوع | تولیدکنندهٔ مجاز | مصرف‌کنندهٔ مجاز | مالک موضوع |
|---|---|---|---|
| `ot.*` | SCADA / لبهٔ OT | Historian، MES، PdM، CMMS | مهندس ابزار دقیق |
| `mes.*` | MES | ERP، WMS، FIN، BI | مدیر تولید |
| `wms.*` | WMS | MES، ERP، SEC، SAL، FIN، BI | سرپرست انبار |
| `qms.*` | LIMS / QMS | MES، HSE، BI | مدیر کیفیت |
| `cmms.*` / `pdm.*` | CMMS / PdM | MES، MRO، HSE، FIN، BI | مدیر نت |
| `hse.*` | HSE | SEC، CMMS، MES، HRM، BI | مدیر HSE |
| `sec.*` | ACS / VMS | HRM، WMS، BI، SIEM | مسئول حراست |
| `hr.*` | HRM / T&A | MES، CMMS، FIN، BI (بدون جزئیات PII) | مدیر منابع انسانی |
| `fin.*` | ERP | BI، MES | مدیر مالی |
| `mdm.*` | MDM | همهٔ سامانه‌ها | دفتر مدیریت داده |
| `audit.*` | Audit Store | BI، SIEM | افسر امنیت OT |
| `it.*` | مانیتورینگ | IT، BI | مدیر IT |

