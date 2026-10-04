#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تست‌های خودکار برای پایگاه دادهٔ مستندات (CSV) و مولّدها.

هدف: هر خطای داده‌ای که پیش‌تر دیر کشف می‌شد، اینجا و بلافاصله کشف شود.

اجرا:
    python3 -m unittest discover -s tools -p "test_*.py" -v
    یا:  python3 tools/test_build.py
"""
import csv
import io
import os
import re
import sys
import unittest
from collections import Counter
from glob import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DOCS = os.path.join(BASE, "docs")
TOOLS = os.path.join(BASE, "tools")

sys.path.insert(0, TOOLS)

STRICT = os.environ.get("STRICT_DOCS", "1") == "1"

CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")

# حروفِ فارسی (بدون علائم نگارشیِ عربی مانند ٬ ٪ که کنارِ ارقام طبیعی‌اند)
FA_LETTER = "[\u0622\u0627-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc\u06c0]"
# الف) رقمِ لاتینِ چسبیده به حرف فارسی (مانند «اثر5»)
DIGIT_GLUED_TO_FA = re.compile(FA_LETTER + r"[0-9]+|[0-9]+" + FA_LETTER)
# ب) واژه‌های شمارش که باید با رقم فارسی بیایند (مانند «30 پرسش»)
COUNT_WORDS = ("پرسش", "ریسک", "رویداد", "هشدار", "شاخص", "هفته", "ماه", "سال",
               "موجودیت", "بسته", "رابطه", "درصد")
COUNT_RE = re.compile(
    r"(?:\b[0-9]+(?:[.,][0-9]+)?\s+(?:" + "|".join(COUNT_WORDS) + r")\b)"
    r"|(?:(?:" + "|".join(COUNT_WORDS) + r")\s*\b[0-9]+(?:[.,][0-9]+)?\b)")


def read_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestCsvIntegrity(unittest.TestCase):
    """ساختار و یکپارچگیِ فایل‌های منبع."""

    def test_all_csv_parse(self):
        files = sorted(f for f in os.listdir(DATA) if f.endswith(".csv"))
        self.assertGreaterEqual(len(files), 8, "انتظار می‌رود حداقل ۸ فایل CSV وجود داشته باشد")
        for f in files:
            with self.subTest(f=f):
                rows = read_csv(f)
                self.assertGreater(len(rows), 0, f"{f} خالی است")
                # هیچ ستونی نباید کاملاً خالی باشد مگر ستون‌های اختیاری
                for col in rows[0].keys():
                    if col in ("notes", "depends_on", "linked_adrs", "prereq", "oneoff_low_musd",
                               "oneoff_high_musd", "annual_delta", "unit_value_usd"):
                        continue
                    filled = sum(1 for r in rows if (r.get(col) or "").strip())
                    self.assertGreater(filled, 0, f"{f}: ستون «{col}» کاملاً خالی است")

    def test_csv_rows_have_consistent_width(self):
        """همهٔ ردیف‌های هر CSV باید به تعدادِ ستون‌های سرآیند باشند."""
        import csv as _csv
        for f in sorted(x for x in os.listdir(DATA) if x.endswith(".csv")):
            with self.subTest(file=f):
                with open(os.path.join(DATA, f), encoding="utf-8") as fh:
                    rows = list(_csv.reader(fh))
                width = len(rows[0])
                for i, r in enumerate(rows[1:], start=2):
                    self.assertEqual(len(r), width,
                                     f"{f}:{i}: تعداد ستون ({len(r)}) با سرآیند ({width}) یکی نیست")

    def test_risk_scores_consistent(self):
        for r in read_csv("risk_register.csv"):
            with self.subTest(id=r["id"]):
                p, i, s = int(r["probability"]), int(r["impact"]), int(r["score"])
                self.assertEqual(p * i, s, f"{r['id']}: امتیاز با احتمال×اثر هم‌خوان نیست")
                band = "بحرانی" if s >= 15 else "بالا" if s >= 10 else "متوسط" if s >= 5 else "کم"
                self.assertEqual(r["band"], band, f"{r['id']}: سطح با امتیاز هم‌خوان نیست")

    def test_integration_matrix_nodes(self):
        from build_integration_matrix import NODES  # type: ignore
        valid = set(NODES)
        for r in read_csv("integration_matrix.csv"):
            with self.subTest(edge=f"{r['source']}->{r['target']}"):
                self.assertIn(r["source"], valid, f"گرهٔ مبدأ نامعتبر: {r['source']}")
                self.assertIn(r["target"], valid, f"گرهٔ مقصد نامعتبر: {r['target']}")
                self.assertNotEqual(r["source"], r["target"], "رابطهٔ خودی (self-edge) مجاز نیست")

    def test_each_unit_has_at_least_five_kpis(self):
        kpi = read_csv("kpi_catalog.csv")
        counts = Counter(r["unit"] for r in kpi)
        units = {"SEC", "HSE", "PRD", "QCL", "MRO", "RMW", "FGW", "HRM", "SAL",
                 "EXP", "FIN", "MNT", "ELE", "MEC", "UTL"}
        for u in sorted(units):
            with self.subTest(unit=u):
                self.assertGreaterEqual(counts.get(u, 0), 5,
                                        f"واحد {u} تنها {counts.get(u, 0)} شاخص دارد (حداقل ۵ لازم است)")
        for r in kpi:
            with self.subTest(kpi=r["id"]):
                self.assertTrue(r["formula"].strip(), f"{r['id']}: فرمول ندارد")
                self.assertTrue(r["source_system"].strip(), f"{r['id']}: منبع داده ندارد")
                self.assertTrue(r["data_owner"].strip(), f"{r['id']}: مالک ندارد")
                self.assertTrue(r["target"].strip(), f"{r['id']}: هدف ندارد")

    def test_raci_health_rules(self):
        """قواعدِ سلامتِ RACI همان‌هایی است که خودِ مستند ۱۰ اعلام کرده است."""
        rows = read_csv("raci.csv")
        acts = {}
        for r in rows:
            acts.setdefault(r["activity_id"], []).append(r)
        for aid, items in acts.items():
            v = [x["value"].upper() for x in items]
            n_a = sum(1 for x in v if "A" in x)
            n_r = sum(1 for x in v if "R" in x)
            with self.subTest(activity=aid):
                self.assertEqual(n_a, 1, f"فعالیت {aid}: باید دقیقاً یک A داشته باشد (اکنون {n_a})")
                self.assertGreaterEqual(n_r, 1, f"فعالیت {aid}: بدون R است؛ کار انجام نمی‌شود")

    def test_ui_matrix_is_complete_and_unique(self):
        rows = read_csv("ui_matrix.csv")
        seen = set()
        for r in rows:
            key = (r["page"], r["role"])
            with self.subTest(cell=key):
                self.assertNotIn(key, seen, f"خانهٔ تکراری: {key}")
                seen.add(key)
        pages = {r["page"] for r in rows}
        roles = {r["role"] for r in rows}
        with self.subTest(check="کامل‌بودنِ ماتریس"):
            self.assertEqual(len(seen), len(pages) * len(roles),
                             "هر ترکیبِ صفحه×نقش باید دقیقاً یک خانه داشته باشد")
        all_roles = {r["code"] for r in read_csv("roles.csv")}
        with self.subTest(check="پوششِ همهٔ نقش‌ها"):
            self.assertEqual(roles, all_roles,
                             "نقش‌های بدونِ ردیف در ماتریس: %s" % sorted(all_roles - roles))
        empty = [c for c in sorted(all_roles)
                 if all(r["access"] == "—" for r in rows if r["role"] == c)]
        with self.subTest(check="نقشِ بدونِ هیچ صفحه‌ای"):
            self.assertEqual(empty, [], "این نقش‌ها هیچ صفحه‌ای ندارند: %s" % empty)
        for r in rows:
            with self.subTest(cell=(r["page"], r["role"])):
                self.assertIn(r["access"], ("●", "◐", "○", "—"),
                              "نمادِ نامعتبر: %s" % r["access"])

    def test_exec_targets_are_complete(self):
        """جدولِ اهداف در سه جا مصرف می‌شود (مستند ۰۰، داشبورد، سایت) — باید کامل باشد."""
        rows = read_csv("exec_targets.csv")
        self.assertTrue(len(rows) >= 10, "انتظار حداقل ۱۰ شاخصِ هدف")
        for r in rows:
            with self.subTest(metric=r["metric"]):
                for col in ("unit", "baseline", "target_18m", "target_30m", "source"):
                    self.assertTrue(r[col].strip(), f"{r['metric']}: ستون {col} خالی است")
                self.assertNotEqual(r["target_30m"], r["baseline"],
                                    f"{r['metric']}: هدف با وضعیتِ فعلی یکی است")

    def test_vendor_weights_sum_to_one_hundred(self):
        def fa_num(v):
            """وزنِ فارسی/درشت‌نویس/خط‌تیره را به عدد تبدیل می‌کند؛ ناعدّد = صفر."""
            v = str(v).strip().strip("*").replace("٪", "").replace("٫", ".").strip()
            v = v.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
            try:
                return float(v)
            except ValueError:
                return 0.0
        crit = read_csv("vendor_criteria.csv")
        total = sum(fa_num(r["weight"]) for r in crit)
        with self.subTest(source="vendor_criteria"):
            self.assertAlmostEqual(total, 100.0, places=1,
                                   msg="جمع وزن‌ها باید ۱۰۰٪ باشد")
        # سطرِ «جمع وزنی» و سطرِ معیارهای حذف در جمعِ وزن‌ها حساب نمی‌شوند
        scores = [r for r in read_csv("vendor_scores.csv")
                  if not r["criterion"].strip().startswith("**")
                  and fa_num(r["weight"]) > 0]
        total_s = sum(fa_num(r["weight"]) for r in scores)
        with self.subTest(source="vendor_scores"):
            self.assertAlmostEqual(total_s, 100.0, places=1,
                                   msg="جمع وزن‌های برگهٔ امتیاز باید ۱۰۰ باشد")

    def test_phase_summary_matches_roadmap(self):
        phases = {r["phase"] for r in read_csv("roadmap.csv")}
        summary = read_csv("phase_summary.csv")
        for r in summary:
            with self.subTest(phase=r["phase"]):
                self.assertIn(r["phase"], phases,
                              "فازی در خلاصه هست که در نقشهٔ راه نیست")
                self.assertTrue(r["label"].strip(), "برچسبِ فاز خالی است")
                self.assertTrue(r["main_output"].strip(), "خروجیِ فاز خالی است")
        self.assertEqual({r["phase"] for r in summary}, phases,
                         "هر فازِ نقشهٔ راه باید در خلاصهٔ مدیریتی ردیف داشته باشد")

    def test_assumptions_are_labelled(self):
        for r in read_csv("input_params.csv"):
            with self.subTest(param=r["param"]):
                self.assertIn("[فرض]", r["tag"],
                              "هر ورودیِ فرضی باید برچسب [فرض] داشته باشد")
                self.assertTrue(r["verify"].strip() or r["verify"] == "—",
                                f"{r['param']}: روش تأیید مشخص نیست")
        for r in read_csv("assumptions.csv"):
            with self.subTest(assumption=r["id"]):
                self.assertTrue(r["assumption"].strip(), f"{r['id']}: متنِ فرض خالی است")

    def test_glossary_and_unit_codes_are_complete(self):
        for r in read_csv("glossary.csv"):
            with self.subTest(abbr=r["abbr"]):
                self.assertTrue(r["fa"].strip(), f"{r['abbr']}: معادل فارسی ندارد")
                self.assertTrue(r["desc"].strip(), f"{r['abbr']}: توضیح ندارد")
        pairs = read_csv("unit_codes.csv")
        codes = [r["code_a"] for r in pairs] + [r["code_b"] for r in pairs]
        codes = [c for c in codes if c.strip()]
        self.assertEqual(len(codes), len(set(codes)), "کدِ واحد تکراری است")
        for r in pairs:
            with self.subTest(code=r["code_a"]):
                self.assertTrue(r["name_a"].strip(), "نامِ واحد خالی است")

    def test_cutover_runbook_is_actionable(self):
        for f, cols in (("cutover_prep.csv", ("time", "action", "owner", "exit_criteria")),
                        ("cutover_day.csv", ("time", "action", "owner")),
                        ("post_cutover.csv", ("window", "action", "exit_criteria")),
                        ("reconciliation.csv", ("item", "method", "threshold", "frequency")),
                        ("migration_domains.csv", ("domain", "method", "owner"))):
            for r in read_csv(f):
                with self.subTest(source=f, row=r.get("time") or r.get("item") or r.get("domain")):
                    for c in cols:
                        self.assertTrue(r[c].strip(), f"{f}: ستون {c} خالی است")

    def test_role_map_covers_every_role(self):
        rmap = {r["code"]: r for r in read_csv("role_map.csv")}
        for r in read_csv("roles.csv"):
            self.assertIn(r["code"], rmap, "نقشِ بدون نگاشت: %s" % r["code"])
        actors = {r["actor"] for r in read_csv("raci.csv")}
        for code, r in rmap.items():
            with self.subTest(role=code):
                self.assertIn(r["raci_actor"], actors,
                              "%s → بازیگرِ نامعتبر %r" % (code, r["raci_actor"]))
                self.assertTrue(r["owner_aliases"].strip(),
                                "%s باید دست‌کم یک نامِ مستعار داشته باشد" % code)

    def test_role_aliases_match_real_owners(self):
        """هیچ نامِ مستعاری نباید بی‌اثر باشد (مگر نقشی که آگاهانه در صفِ اعلان نیست)."""
        RMAP = read_csv("role_map.csv")

        def best_in(aliases, part):
            """طولِ بلندترین نامِ مستعاری که در این بخش پدیدار می‌شود."""
            return max((len(a) for a in aliases.split("|") if a and a in part), default=0)

        def owns(aliases, field):
            """هر بخش از مالک به «خاص‌ترین» نقشِ پوشش‌دهنده نسبت داده می‌شود؛
            در نتیجه یک ردیفِ چندمالکه به همهٔ نقش‌های ذی‌ربط می‌رسد."""
            for raw in (field or "").split("+"):
                q = raw.strip()
                if not q:
                    continue
                mine = best_in(aliases, q)
                if mine and all(best_in(m["owner_aliases"], q) <= mine for m in RMAP):
                    return True
            return False

        total = {m["code"]: 0 for m in RMAP}
        for f, col in (("kpi_catalog.csv", "data_owner"), ("alarm_catalog.csv", "owner_role")):
            for r in read_csv(f):
                hit = [m["code"] for m in RMAP if owns(m["owner_aliases"], r[col])]
                with self.subTest(source=f, id=r["id"]):
                    self.assertTrue(hit, "مالکِ بدون نقش → %r" % r[col])
                for code in hit:
                    total[code] += 1
        dead = [(m["code"], m["owner_aliases"]) for m in RMAP
                if total[m["code"]] == 0 and not m["notify_note"].strip()]
        self.assertEqual(dead, [], "نام‌های مستعارِ بی‌اثر: %s" % dead)

        # خاص‌ترین تطبیق برنده است: هشدارِ «QC شیفت» برای تکنسین است، نه مدیرِ QC
        by_code = {m["code"]: m["owner_aliases"] for m in RMAP}
        self.assertTrue(owns(by_code["R03"], "QC شیفت"), "«QC شیفت» باید به R03 برسد")
        self.assertFalse(owns(by_code["R04"], "QC شیفت"), "«QC شیفت» نباید به مدیر QC برسد")
        self.assertTrue(owns(by_code["R04"], "QC"), "«QC» باید به مدیر QC برسد")
        # و یک مالکِ چندگانه به هر دو نقش می‌رسد
        self.assertTrue(owns(by_code["R04"], "QC + تأسیسات"))
        self.assertTrue(owns(by_code["R08"], "QC + تأسیسات"))

    def test_role_journey_is_complete(self):
        by = {}
        for r in read_csv("role_journey.csv"):
            by.setdefault(r["code"], []).append(int(r["step"]))
        for r in read_csv("roles.csv"):
            with self.subTest(role=r["code"]):
                self.assertEqual(by.get(r["code"], []), [1, 2, 3, 4],
                                 "%s باید ۴ گامِ پیوسته داشته باشد" % r["code"])
        for r in read_csv("role_journey.csv"):
            for col in ("phase", "action", "system", "evidence"):
                with self.subTest(role=r["code"], step=r["step"]):
                    self.assertTrue(r[col].strip(), "ستون %s خالی است" % col)

    def test_roles_and_rbac_are_consistent(self):
        codes = [r["code"] for r in read_csv("roles.csv")]
        self.assertEqual(len(codes), len(set(codes)), "کدِ نقش تکراری است")
        for r in read_csv("roles.csv"):
            with self.subTest(role=r["code"]):
                for col in ("role_fa", "workplace", "access_level", "devices"):
                    self.assertTrue(r[col].strip(), f"{r['code']}: ستون {col} خالی است")
        matrix_roles = {r["role"] for r in read_csv("ui_matrix.csv")}
        known = set(codes)
        with self.subTest(check="نقش‌های ناشناس در ماتریس"):
            self.assertEqual(sorted(matrix_roles - known), [],
                             "ماتریس به نقشی ارجاع می‌دهد که در roles.csv نیست")

    def test_sod_and_uat_rows_complete(self):
        for r in read_csv("sod_rules.csv"):
            with self.subTest(sod=r["id"]):
                self.assertTrue(r["control"].strip(), f"{r['id']}: کنترل سیستمی ندارد")
        for r in read_csv("uat_scenarios.csv"):
            with self.subTest(uat=r["id"]):
                self.assertTrue(r["pass_criteria"].strip(), f"{r['id']}: معیار عبور ندارد")
        for r in read_csv("uat_criteria.csv"):
            with self.subTest(area=r["area"]):
                self.assertTrue(r["threshold"].strip(), f"{r['criterion']}: آستانه ندارد")
                self.assertTrue(r["measurement"].strip(), f"{r['criterion']}: روش اندازه‌گیری ندارد")

    def test_traceability_rows_complete(self):
        for r in read_csv("traceability.csv"):
            with self.subTest(id=r["id"]):
                self.assertTrue(r["requirement"].strip(), f"{r['id']}: عنوان ندارد")
                self.assertTrue(r["verification"].strip(), f"{r['id']}: روش راستی‌آزمایی ندارد")
                self.assertIn(r["status"], ("تأمین", "در حال انجام", "باقی‌مانده"),
                              f"{r['id']}: وضعیت نامعتبر است")
                self.assertIn(r["group"], ("معیار پذیرش", "تحویل‌دادنی", "الزام نگارش", "کیفیت مخزن"),
                              f"{r['id']}: گروه نامعتبر است")

    def test_roadmap_costs_monotonic(self):
        for r in read_csv("roadmap.csv"):
            with self.subTest(wbs=r["wbs"]):
                lo, hi = float(r["cost_low_musd"]), float(r["cost_high_musd"])
                self.assertGreater(hi, 0, f"{r['wbs']}: هزینه باید مثبت باشد")
                self.assertLessEqual(lo, hi, f"{r['wbs']}: حد پایین از حد بالا بیشتر است")

    def test_event_catalog_naming(self):
        for r in read_csv("event_catalog.csv"):
            with self.subTest(topic=r["topic"]):
                self.assertGreaterEqual(
                    r["topic"].count("."), 1,
                    f"نام موضوع باید به صورت حوزه.موجودیت باشد: {r['topic']}")
                self.assertIn(r["dlq"], ("never", "critical", "standard", "buffered",
                                         "drop_after_log"),
                              f"{r['topic']}: سیاستِ خطا نامعتبر است")
                self.assertIn(r["pii"], ("yes", "no"), f"{r['topic']}: مقدار PII نامعتبر است")

    def test_open_questions_priorities(self):
        allowed = {"بلوکه\u200cکننده", "مهم", "قابل تأخیر"}
        for r in read_csv("open_questions.csv"):
            with self.subTest(id=r["id"]):
                self.assertIn(r["priority"], allowed, f"{r['id']}: اولویت نامعتبر است")
                self.assertIn("؟", r["question"],
                              f"{r['id']}: پرسش باید علامت سؤال داشته باشد")

    def test_ot_conduits_reference_known_zones(self):
        zones = {z["zone"] for z in read_csv("ot_zones.csv")}
        for c in read_csv("ot_conduits.csv"):
            with self.subTest(conduit=c["conduit"]):
                self.assertIn(c["from_zone"], zones, f"{c['conduit']}: منطقهٔ مبدأ نامعتبر")
                self.assertIn(c["to_zone"], zones, f"{c['conduit']}: منطقهٔ مقصد نامعتبر")

    def test_financial_model_balances(self):
        fin = read_csv("financial_model.csv")
        ben = read_csv("benefit_model.csv")
        capex = sum(float(r["capex_low_musd"]) for r in fin)
        self.assertAlmostEqual(capex, 4.96, places=2,
                               msg="جمعِ سرمایه باید با بودجهٔ مصوب هم‌خوان باشد")
        capex_hi = sum(float(r["capex_high_musd"]) for r in fin)
        self.assertAlmostEqual(capex_hi, 8.42, places=2,
                               msg="جمعِ سرمایه (حد بالا) باید با بودجهٔ مصوب هم‌خوان باشد")
        ramps = [float(r["benefit_ramp_pct"]) for r in fin]
        self.assertEqual(ramps, sorted(ramps), "شیبِ منفعت باید صعودی باشد")
        self.assertEqual(ramps[-1], 100.0, "منفعت باید در سال آخر به سطح کامل برسد")
        self.assertEqual(len(ben), 10, "انتظار می‌رود ۱۰ محرک ارزش تعریف شده باشد")


class TestDocs(unittest.TestCase):
    """کیفیتِ مستندات تولید‌شده."""

    GENERATED = [
        "04-integration-matrix.md", "05-master-data-ownership.md", "08-kpi-catalog.md",
        "09-alarm-map.md", "11-roadmap.md", "12-risk-register.md", "16-open-questions.md",
        "19-event-catalog.md", "24-customer-questionnaire.md", "25-financial-model.md",
        "26-ot-security-plan.md", "27-traceability-coverage.md",
    ]

    def test_generated_docs_exist(self):
        for name in self.GENERATED:
            with self.subTest(doc=name):
                self.assertTrue(os.path.exists(os.path.join(DOCS, name)),
                                f"{name} وجود ندارد — مولّد را اجرا کنید")

    def test_no_stray_cjk(self):
        for root, _, files in os.walk(BASE):
            if ".git" in root:
                continue
            for f in files:
                if not f.endswith((".md", ".csv", ".html", ".py")):
                    continue
                path = os.path.join(root, f)
                for i, line in enumerate(read_text(path).splitlines(), 1):
                    with self.subTest(file=path, line=i):
                        self.assertIsNone(CJK.search(line),
                                          f"{os.path.relpath(path, BASE)}:{i}: نویزِ نویسه‌ای")

    @unittest.skipUnless(STRICT, "STRICT_DOCS=0 برای نادیده‌گرفتنِ ارقام لاتین")
    def test_persian_digits_in_generated_prose(self):
        """در متنِ مستندات تولید‌شده، ارقامِ متصل به فارسی باید فارسی باشند."""
        for name in self.GENERATED:
            path = os.path.join(DOCS, name)
            if not os.path.exists(path):
                continue
            for i, line in enumerate(read_text(path).splitlines(), 1):
                if line.startswith(("|", "#", "```")) or not line.strip():
                    continue
                with self.subTest(doc=name, line=i, rule="چسبیده"):
                    self.assertIsNone(DIGIT_GLUED_TO_FA.search(line),
                                      f"{name}:{i}: رقمِ لاتین چسبیده به حرف فارسی")
                with self.subTest(doc=name, line=i, rule="شمارش"):
                    self.assertIsNone(COUNT_RE.search(line),
                                      f"{name}:{i}: رقمِ لاتین کنارِ واژهٔ شمارش")

    def test_markdown_tables_have_consistent_columns(self):
        """هر «|» درونِ یک خانه، ستونِ اضافه می‌سازد و کلِ جدول را می‌شکند.

        نمونهٔ واقعی: فرمولِ قدرمطلقِ `|مغایرت|` یا مسیرِ `?direction=backward|forward`.
        این تست همهٔ مستندات را می‌سنجد، دست‌نویس و تولیدی.
        """
        split = re.compile(r"(?<!\\)\|")     # «\|» رهانیده‌شده را نشمار
        for root, _, files in os.walk(DOCS):
            for f in files:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(root, f)
                in_fence, header = False, None
                for i, line in enumerate(read_text(path).splitlines(), 1):
                    if line.strip().startswith("```"):
                        in_fence = not in_fence
                        header = None
                        continue
                    if in_fence or not line.strip().startswith("|"):
                        header = None
                        continue
                    n = len(split.split(line)) - 2
                    if header is None:
                        header = n
                    else:
                        with self.subTest(doc=os.path.relpath(path, BASE), line=i):
                            self.assertEqual(
                                n, header,
                                f"{os.path.relpath(path, BASE)}:{i}: {n} خانه در برابر "
                                f"سرآیندِ {header} — احتمالاً «|» رهانیده‌نشده در مقدار")

    def test_no_broken_internal_links(self):
        for root, _, files in os.walk(DOCS):
            for f in files:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(root, f)
                for m in re.finditer(r"\]\((?!https?:|#)([^)]+)\)", read_text(path)):
                    target = m.group(1).split("#")[0]
                    if not target:
                        continue
                    full = os.path.normpath(os.path.join(root, target))
                    with self.subTest(doc=f, link=target):
                        self.assertTrue(os.path.exists(full), f"پیوند شکسته: {target}")

    def test_readme_deliverable_paths_exist(self):
        readme = read_text(os.path.join(BASE, "README.md"))
        for m in re.finditer(r"\]\((?!https?:|#)([^)]+)\)", readme):
            target = m.group(1).split("#")[0]
            if not target:
                continue
            with self.subTest(link=target):
                self.assertTrue(os.path.exists(os.path.join(BASE, target)),
                                f"پیوند شکسته در README: {target}")


class TestGenerators(unittest.TestCase):
    """مولّدها باید بدون خطا اجرا شوند و خروجیِ غیرتهی تولید کنند."""

    def test_build_catalogs_runs(self):
        import build_catalogs  # type: ignore
        for fn in (build_catalogs.build_master_data, build_catalogs.build_kpi,
                   build_catalogs.build_alarms, build_catalogs.build_roadmap,
                   build_catalogs.build_events, build_catalogs.build_risk,
                   build_catalogs.build_questions, build_catalogs.build_questionnaire,
                   build_catalogs.build_finance, build_catalogs.build_ot_security):
            with self.subTest(builder=fn.__name__):
                fn()   # در صورت خطا، تست شکست می‌خورد

    def test_build_integration_matrix_runs(self):
        import build_integration_matrix  # type: ignore
        build_integration_matrix.main() if hasattr(build_integration_matrix, "main") else None
        self.assertTrue(os.path.exists(os.path.join(DOCS, "04-integration-matrix.md")))

    def test_regeneration_is_idempotent(self):
        """اجرای دوبارهٔ مولّد نباید خروجی را تغییر دهد."""
        import importlib
        import build_catalogs  # type: ignore
        targets = ["25-financial-model.md", "26-ot-security-plan.md", "12-risk-register.md"]
        before = {t: read_text(os.path.join(DOCS, t)) for t in targets
                  if os.path.exists(os.path.join(DOCS, t))}
        importlib.reload(build_catalogs)
        for fn in (build_catalogs.build_risk, build_catalogs.build_finance,
                   build_catalogs.build_ot_security):
            fn()
        for t, content in before.items():
            with self.subTest(doc=t):
                self.assertEqual(content, read_text(os.path.join(DOCS, t)),
                                 f"{t} پس از بازتولید تغییر کرده است")

    def test_persian_digit_helper(self):
        import build_catalogs  # type: ignore
        self.assertEqual(build_catalogs.fa(0), "۰")
        self.assertEqual(build_catalogs.fa(12345), "۱۲۳۴۵")

    def test_financial_helpers(self):
        import build_catalogs  # type: ignore
        # −۱۰۰ در سال ۱، سپس ۵۰ در هر سال ⇒ تجمعی در پایان سال ۳ صفر می‌شود
        flows = [-100.0, 50.0, 50.0, 50.0]
        self.assertAlmostEqual(build_catalogs._payback(flows), 3.0, places=5)
        # بازگشتِ دقیق در پایان سال ۲
        self.assertAlmostEqual(build_catalogs._payback([-100.0, 100.0]), 2.0, places=5)
        # بازگشتِ میان‌سال: −۱۰۰، سپس ۶۰ و ۶۰ ⇒ تجمعی −۴۰ مانده؛ ۴۰/۶۰ از سال ۳ لازم است
        self.assertAlmostEqual(build_catalogs._payback([-100.0, 60.0, 60.0]), 2.667, places=2)
        self.assertIsNone(build_catalogs._payback([-10.0, 1.0]))   # هرگز بازنمی‌گردد
        self.assertAlmostEqual(build_catalogs._npv(0.0, flows), sum(flows), places=6)
        irr = build_catalogs._irr(flows)
        self.assertIsNotNone(irr)
        self.assertGreater(irr, 0.2)


class TestDashboard(unittest.TestCase):
    """داشبورد باید به همهٔ منابع داده اشاره کند."""

    def test_all_csvs_are_loaded(self):
        html = read_text(os.path.join(BASE, "dashboard", "index.html"))
        for f in sorted(x for x in os.listdir(DATA) if x.endswith(".csv")):
            with self.subTest(csv=f):
                self.assertIn(f, html, f"{f} در داشبورد بارگذاری نشده است")

    def test_every_section_has_a_nav_button(self):
        html = read_text(os.path.join(BASE, "dashboard", "index.html"))
        sections = set(re.findall(r'<section id="(sec-[a-z]+)"', html))
        buttons = set(re.findall(r'data-sec="(sec-[a-z]+)"', html))
        self.assertEqual(sections, buttons, "هر بخش باید دکمهٔ ناوبری داشته باشد و برعکس")


class TestTemplates(unittest.TestCase):
    """مستنداتِ مبتنی‌بر قالب باید با CSVها هم‌خوان باشند."""

    TPL_DIR = os.path.join(BASE, "tools", "templates")

    def setUp(self):
        sys.path.insert(0, os.path.join(BASE, "tools"))

    def test_templates_exist(self):
        self.assertTrue(os.path.isdir(self.TPL_DIR))
        files = [f for f in os.listdir(self.TPL_DIR) if f.endswith(".md")]
        self.assertGreaterEqual(len(files), 3, "حداقل سه قالب انتظار می‌رود")
        for f in files:
            with self.subTest(tpl=f):
                self.assertTrue(os.path.exists(os.path.join(DOCS, f)),
                                f"خروجی برای {f} تولید نشده است")

    def test_every_placeholder_is_defined(self):
        import build_templates as bt  # type: ignore
        ph = bt.build_placeholders()
        for f in sorted(x for x in os.listdir(self.TPL_DIR) if x.endswith(".md")):
            body = read_text(os.path.join(self.TPL_DIR, f))
            for m in re.findall(r"\{\{(\w+)\}\}", body):
                with self.subTest(tpl=f, placeholder=m):
                    self.assertIn(m, ph, f"نشانهٔ تعریف‌نشده در {f}: {m}")

    def test_regeneration_is_idempotent(self):
        import build_templates as bt  # type: ignore
        before = {f: read_text(os.path.join(DOCS, f))
                  for f in os.listdir(self.TPL_DIR) if f.endswith(".md")}
        self.assertEqual(bt.main(), 0, "مولّدِ قالب‌ها با خطا مواجه شد")
        for f, content in before.items():
            with self.subTest(doc=f):
                self.assertEqual(content, read_text(os.path.join(DOCS, f)),
                                 f"{f} پس از بازتولید تغییر کرده است")

    def test_notice_is_stripped_from_output(self):
        for f in os.listdir(self.TPL_DIR):
            if not f.endswith(".md"):
                continue
            with self.subTest(doc=f):
                self.assertNotIn("این قالب، منبعِ متنِ", read_text(os.path.join(DOCS, f)))


class TestSiteData(unittest.TestCase):
    """سایت داده‌ها را با همان نامِ فایل می‌خواند؛ یک اشتباهِ تایپی نباید بی‌صدا بگذرد."""

    def _site_sources(self):
        html = open(os.path.join(BASE, "site", "index.html"), encoding="utf-8").read()
        m = re.search(r"await Promise\.all\(\[([^\]]+)\]\.map\(csv\)\)", html)
        self.assertTrue(m, "فهرستِ منابعِ داده در site/index.html یافت نشد")
        return [x.strip().strip('"') for x in m.group(1).split(",") if x.strip()]

    def test_site_csv_names_resolve_to_files(self):
        for name in self._site_sources():
            path = os.path.join(BASE, "data", name + ".csv")
            self.assertTrue(os.path.exists(path), "سایت منبعِ ناموجود می‌خواند: %s" % name)

    def test_site_reads_every_role_related_source(self):
        need = {"roles", "ui_matrix", "rbac", "raci", "role_map", "role_journey",
                "kpi_catalog", "alarm_catalog"}
        self.assertEqual(need - set(self._site_sources()), set(),
                         "نمای نقش بدون این منابع کار نمی‌کند")

    def test_site_csv_helper_appends_extension(self):
        html = open(os.path.join(BASE, "site", "index.html"), encoding="utf-8").read()
        self.assertIn('name.endsWith(".csv")', html,
                      "csv() باید پسوند را خودش اضافه کند؛ در غیر این صورت همهٔ "
                      "درخواست‌ها ۴۰۴ می‌شوند و صفحه بی‌صدا به مقدارِ جایگزین می‌افتد")


class TestPagesWorkflow(unittest.TestCase):
    """دستورِ ساخت در workflow نباید از مولّدها و تست‌های واقعی جا بماند.

    پیش‌زمینه: وقتی build_templates.py به مجموعه اضافه شد، باید در هر دو
    workflow دستی درج می‌شد؛ اگر فراموش می‌شد، سایتِ منتشرشده با آنچه محلی
    تأیید شده بود فرق می‌کرد. این کلاس آن انحراف را غیرممکن می‌کند.
    """

    WF = os.path.join(BASE, ".github", "workflows", "pages.yml")
    DOCS_WF = os.path.join(BASE, ".github", "workflows", "docs.yml")

    def _read(self, path):
        self.assertTrue(os.path.exists(path), "فایل یافت نشد: %s" % path)
        return read_text(path)

    def test_pages_workflow_runs_every_generator(self):
        wf = self._read(self.WF)
        present = sorted(f for f in os.listdir(os.path.join(BASE, "tools"))
                         if f.startswith("build_") and f.endswith(".py"))
        self.assertTrue(present, "هیچ مولّدی در tools/ یافت نشد")
        for gen in present:
            with self.subTest(generator=gen):
                self.assertIn("tools/" + gen, wf,
                              "%s در workflow اجرا نمی‌شود — سایتِ منتشرشده کهنه می‌ماند" % gen)

    def test_pages_workflow_runs_both_test_suites(self):
        wf = self._read(self.WF)
        for cmd in ("tools/test_build.py", "tools/test_site.js"):
            with self.subTest(suite=cmd):
                self.assertIn(cmd, wf, "%s در workflow اجرا نمی‌شود" % cmd)

    def test_pages_workflow_publishes_every_needed_path(self):
        wf = self._read(self.WF)
        for token in ("site/index.html", "data/*.csv", "dashboard/index.html",
                      "docs/*.md", "docs/03-units/*.md", "README.md", ".nojekyll"):
            with self.subTest(path=token):
                self.assertIn(token, wf, "%s در بستهٔ انتشار نیست" % token)

    def test_pages_workflow_has_required_permissions(self):
        wf = self._read(self.WF)
        for perm in ("pages: write", "id-token: write"):
            with self.subTest(permission=perm):
                self.assertIn(perm, wf, "بدونِ %s استقرار ممکن نیست" % perm)

    def test_docs_workflow_mirrors_pages_generators(self):
        """هر مولّدی که Pages اجرا می‌کند باید در بررسیِ مستندات هم باشد."""
        pages, docs = self._read(self.WF), self._read(self.DOCS_WF)
        for gen in sorted(set(re.findall(r"tools/(build_\w+\.py)", pages))):
            with self.subTest(generator=gen):
                self.assertIn(gen, docs,
                              "%s در workflow مستندات نیست — مستندات کهنه بررسی می‌شوند" % gen)

    def test_local_build_recipe_matches_workflow(self):
        """دستورِ README برای اجرای محلی باید همان چیزی باشد که CI می‌سازد."""
        wf = self._read(self.WF)
        readme = read_text(os.path.join(BASE, "README.md"))
        for gen in sorted(set(re.findall(r"tools/(build_\w+\.py)", wf))):
            with self.subTest(generator=gen):
                self.assertIn(gen, readme, "%s در دستورِ محلیِ README نیست" % gen)


class TestSite(unittest.TestCase):
    """صفحهٔ منتشرشده در GitHub Pages باید با محتوای مخزن هم‌خوان باشد."""

    SITE = os.path.join(BASE, "site", "index.html")

    def setUp(self):
        if not os.path.exists(self.SITE):
            self.skipTest("site/index.html وجود ندارد")
        self.html = read_text(self.SITE)

    def test_doc_manifest_paths_exist(self):
        paths = re.findall(r'\{p:"([^"]+)"', self.html)
        self.assertGreaterEqual(len(paths), 40, "فهرست اسناد باید همهٔ مستندات را پوشش دهد")
        for pth in paths:
            with self.subTest(path=pth):
                self.assertTrue(os.path.exists(os.path.join(BASE, pth)),
                                f"مسیر در فهرست سایت وجود ندارد: {pth}")

    def test_doc_manifest_is_complete(self):
        paths = set(re.findall(r'\{p:"([^"]+)"', self.html))
        real = {"README.md"}
        real |= {"docs/" + os.path.basename(f) for f in glob(os.path.join(DOCS, "*.md"))}
        real |= {"docs/03-units/" + os.path.basename(f)
                 for f in glob(os.path.join(DOCS, "03-units", "*.md"))}
        with self.subTest(compare="مستنداتِ بدون ورودی در سایت"):
            self.assertEqual(sorted(real - paths), [],
                             "این مستندات در فهرست سایت نیستند")
        with self.subTest(compare="ورودی‌های بدون فایل"):
            self.assertEqual(sorted(paths - real), [],
                             "این ورودی‌ها فایل متناظر ندارند")

    def test_no_external_dependencies(self):
        """صفحه نباید به هیچ منبع خارجی (CDN/فونت/کتابخانه) وابسته باشد."""
        for m in re.finditer(r'(?:src|href)="(https?://[^"]+)"', self.html):
            with self.subTest(url=m.group(1)):
                self.assertTrue(m.group(1).startswith("https://github.com/"),
                                f"منبع خارجیِ غیرمجاز: {m.group(1)}")
        self.assertNotIn("cdn.", self.html.lower().replace("githubusercontent", ""))
        self.assertNotIn('rel="stylesheet" href="http', self.html)

    def test_pages_workflow_publishes_needed_paths(self):
        wf = os.path.join(BASE, ".github", "workflows", "pages.yml")
        self.assertTrue(os.path.exists(wf), "workflow انتشار در Pages وجود ندارد")
        body = read_text(wf)
        for token in ("_site/data", "_site/docs", "_site/dashboard", "site/index.html",
                      "docs/03-units", ".nojekyll"):
            with self.subTest(token=token):
                self.assertIn(token, body, f"{token} در workflow کپی نشده است")

    def test_dashboard_is_embedded(self):
        self.assertIn('id="dashFrame"', self.html)
        self.assertIn("dashboard/index.html", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
