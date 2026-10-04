# ۲۱. سناریوهای توالیِ سرتاسری (Sequence Flows)

> این قالب، منبعِ متنِ `21-sequence-flows.md` است.
> جدول‌ها با نشانه‌هایی مانند `{{ flow_failures }}` جایگذاری شده‌اند و از فایل‌های `data/*.csv` ساخته می‌شوند.
> برای تغییرِ یک جدول، CSV را ویرایش کنید؛ برای تغییرِ متن، همین قالب را.


> این سند «تست‌نامهٔ زنده» ی پروژه است: هر جریان با دیاگرامِ توالی، مسیرِ شکست،
> و سناریوی UAT متناظر در [`13-uat-checklist.md`](13-uat-checklist.md) آمده است.
> دیاگرام‌ها با Mermaid نوشته شده‌اند و در GitHub نمایش داده می‌شوند.

---

## F1 — از دریافت مادهٔ اولیه تا مصرف در خط

### مسیر موفق

```mermaid
sequenceDiagram
    autonumber
    participant T as کامیون/ANPR
    participant S as باسکول
    participant W as WMS
    participant Q as LIMS
    participant M as MDM
    participant P as MES (ایستگاه خط)

    T->>W: ورود با پلاک (تطبیق ASN)
    W->>M: بررسی تأمین‌کننده (فهرست تأییدشده)
    M-->>W: approved
    T->>S: توزین ناخالص/خالص
    S->>W: اختلاف با PO = +1.9% ⇒ هشدار Minor
    W->>Q: ایجاد نمونه + قرنطینه خودکار
    Q->>Q: آزمون و ثبت نتیجه
    Q->>W: result.recorded ⇒ released
    W->>W: تخصیص مکان (دما/ناسازگاری/گردش)
    P->>W: درخواست مواد برای WO (کشش)
    W-->>P: لیست برداشت با FEFO
    P->>W: اسکن بچ + توزین ⇒ material.consumed
    W->>W: کسر موجودی + صدور stock.moved
    W->>ERP: fin.posting (مصرف مواد)
    W->>MES: تأیید
    MES->>MES: ثبت یالِ شجره‌نامه
```

### مسیر شکست و جبران

{{flow_failures}}

**سناریوی UAT:** UAT-01 · **رویدادها:** `wms.receipt.created`، `qms.result.recorded`، `material.consumed`

---

## F2 — از صدور دستور کار تا ترخیص بچ

### مسیر موفق

```mermaid
sequenceDiagram
    autonumber
    participant E as ERP/APS
    participant M as MES
    participant H as HR
    participant W as WMS
    participant Q as LIMS
    participant F as FGW/WMS

    E->>M: برنامه تولید / سفارش
    M->>M: زمان‌بندی و صدور WO با Recipe نسخه‌دار
    M->>H: بررسی صلاحیت اپراتور برای خط
    H-->>M: eligible / not eligible
    M->>W: رزرو مواد (در صورت کسری ⇒ پیشنهاد باززمان‌بندی)
    M->>M: گیت شروع: QC ورودی + Line Clearance + موجودی
    M->>M: اجرا؛ ثبت پارامترها در Historian
    M->>Q: نمونه‌برداری (نقاط کنترل)
    Q-->>M: نتیجه / انحراف
    alt انحراف خارج از حدود
        Q->>M: spec.breach ⇒ ایجاد NCR و قرنطینه
        M->>M: توقف ترخیص تا بستن NCR
    else انطباق
        Q->>M: batch.released با امضای QA
        M->>F: انتقال بچ به انبار محصول + SSCC
        M->>Q: تولید خودکار COA با داده واقعی
    end
```

### نقاط قفل و تصمیم

{{flow_gates}}

**سناریوی UAT:** UAT-02، UAT-03 · **رویدادها:** `mes.workorder.started`، `qms.result.recorded`، `batch.released`

---

## F3 — از خرابی تجهیز تا بستن دستور کار نگهداشت

```mermaid
sequenceDiagram
    autonumber
    participant PLC as PLC/SCADA
    participant M as MES
    participant C as CMMS
    participant H as HSE
    participant R as MRO (انبار فنی)
    participant F as FIN

    PLC->>C: آلارم / یا اپراتور QR اسکن می‌کند
    C->>C: ایجاد درخواست کار و اولویت‌بندی بر اساس بحرانی‌بودن دارایی
    C->>C: برنامه‌ریزی و پیشنهاد پنجرهٔ توقف
    C->>M: رزرو پنجرهٔ توقف در برنامهٔ تولید
    C->>H: بررسی نیاز به PTW/LOTO
    H-->>C: PTW تأییدشده / رد‌شده
    C->>R: رزرو قطعات (فقط با WO باز)
    R-->>C: قطعه رزرو شد / موجودی صفر ⇒ PR فوری
    C->>C: اجرا؛ ثبت زمان، علت خرابی، عکس
    C->>H: رفع LOTO و تحویل
    C->>F: ثبت هزینه (کار + قطعات + پیمانکار)
    C->>C: به‌روزرسانی MTBF/MTTR و تاریخچه دارایی
    alt خرابی تکرارشونده
        C->>C: ایجاد وظیفهٔ RCA و بازنگری برنامهٔ PM
    end
```

**نکتهٔ طراحی:** در این جریان، **هیچ کاری بدون PTW معتبر شروع نمی‌شود** (گیتِ سخت HSE).
اگر دارایی کلاس A باشد، نبود قطعه ⇒ PR فوری با هشدار `A040`.

**سناریوی UAT:** UAT-06 · **رویدادها:** `cmms.workorder.created`، `hse.ptw.approved`، `cmms.workorder.completed`

---

## F4 — خروج کالا از کارخانه (چهار شرط + تأیید دوگانه)

```mermaid
sequenceDiagram
    autonumber
    participant S as SAL (فروش)
    participant W as WMS/FGW
    participant Q as QMS
    participant G as SEC (حراست)
    participant C as مشتری

    S->>W: سفارش فروش + درخواست ارسال
    W->>W: تخصیص موجودی (ATP، FEFO، اولویت مشتری)
    W->>Q: استعلام وضعیت کیفی بچ‌ها
    Q-->>W: released / quarantine
    alt قرنطینه
        W-->>S: قفل ارسال (A028) + اطلاع QC
    else آزاد
        W->>W: Pick ⇒ ساخت پالت با SSCC ⇒ اسناد
        W->>G: درخواست مجوز خروج (۴ شرط)
        G->>G: بارنامه؟ فاکتور؟ تأیید انبار؟ QC؟
        G-->>W: مجوز صادر شد / رد با دلیل
        W->>W: بارگیری با تطبیق SSCCها
        G->>W: تأیید دومرحله‌ای ⇒ دروازه باز می‌شود
        W->>C: ارسال + رهگیری + e-POD
        W->>S: تأیید ارسال ⇒ آزادسازی صدور فاکتور
    end
```

**تستِ منفیِ الزامی:** حذف هر یک از چهار شرط باید منجر به **باز نشدن دروازه** شود
(این چهار حالت باید در UAT-08 یکی‌یکی اجرا و در Audit ثبت شوند).

---

## F5 — رویداد مالی خودکار و جبران (Saga)

```mermaid
sequenceDiagram
    autonumber
    participant P as MES
    participant B as Broker (Kafka)
    participant E as ERP
    participant I as IT/مانیتورینگ
    participant F as FIN

    P->>B: mes.workorder.completed (با idempotency_key)
    B->>E: تحویل رویداد
    E->>E: ایجاد سند مالی با ارجاع به source_event_id
    alt موفق
        E->>B: fin.posting.requested (posted)
        E->>F: نمایش در داشبورد مالی
    else شکست (اعتبارسنجی/در دسترس‌نبودن)
        E->>B: fin.posting.failed
        B->>I: هشدار A096 + ورود به DLQ
        I->>E: تلاش مجدد با backoff؛ در صورت تکرار ⇒ صف بررسی انسانی
    end
```

**قواعد جبران:** سند مالی هرگز «ویرایشِ درجا» نمی‌شود؛ اصلاح با **سند معکوس + سند صحیح** است،
هر دو با ارجاع به رویداد مبدأ. این کار ردیابی از صورت مالی تا رکورد سنسور را حفظ می‌کند.

---

## F6 — حالت آفلاین در کارگاه

```mermaid
sequenceDiagram
    autonumber
    participant O as اپراتور/تکنسین
    participant A as کلاینت (Outbox محلی)
    participant B as Broker
    participant S as سرور L3

    Note over A: قطع شبکه
    O->>A: ثبت مصرف / توقف / چک‌لیست
    A->>A: ذخیره با ULID محلی + نمایش «آفلاین (n مورد در صف)»
    Note over A: برقراری ارتباط
    A->>B: ارسال دسته‌ای به ترتیب ULID
    B->>S: تحویل با Idempotency-Key
    alt تکراری
        S-->>A: 200 OK (قبلاً ثبت شده؛ بدون ثبت مضاعف)
    else تعارض در تراکنش حساس
        S-->>A: 409 ⇒ انتقال به صف «بررسی انسانی»
    end
    A->>A: پاک‌سازی صف + نمایش «همگام شد»
```

**آستانه‌ها:** سقف آفلاین ۷۲ ساعت · نمایشِ دائمیِ وضعیت اتصال ·
برای کیفیت/ایمنی، حلِ تعارض با «آخرین نویسنده برنده» ممنوع.

---

## F7 — وضعیت اضطراری و تخلیه

```mermaid
sequenceDiagram
    autonumber
    participant Sensor as دتکتور گاز/حریق
    participant H as HSE
    participant M as MES
    participant G as SEC/ACS
    participant E as ERT

    Sensor->>H: عبور از آستانه
    H->>H: تعیین سطح و منطقه
    H->>M: دستور توقف ایمنِ منطقه
    H->>G: hse.emergency.declared (منطقه + سطح)
    G->>G: آزادسازی همهٔ گیت‌ها (Fail-safe)
    G->>G: تهیهٔ فهرست حاضران از لاگ تردد
    H->>E: فراخوان تیم واکنش + زنجیرهٔ جایگزین
    G->>H: گزارش حاضران در نقاط تجمع
    H->>H: ثبت رخداد و RCA
```

**الزام زمانی:** از تشخیص تا آزادسازی گیت‌ها ≤ ۳۰ ثانیه (سناریوی UAT-11).

---

## ۲۱-۱. ماتریس سناریو → تست پذیرش → شاخص

{{flow_monitoring}}

---

← بعدی: [`22-vendor-selection.md`](22-vendor-selection.md)
