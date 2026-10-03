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
        "26-ot-security-plan.md",
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
