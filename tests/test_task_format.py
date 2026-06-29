"""Unit tests for the shared task formatter (categorize / clean / parse / render)."""
from scripts.task_format import (
    ARBEIT, APPS, PERSOENLICH,
    bucket_for, clean_task, parse_open_tasks, render_groups,
    esc_v2, header_v2, expandable_v2, render_groups_v2,
)

SAMPLE = """\
# Open Tasks

## 🔴 Dringend
- [ ] **nennung-online.de Affiliate-Anfrage senden** ← HorseFinder Prio #1

## 💼 Beruf / HDP
### Claims Intake Workflow
- [ ] HubSpot Scope `crm.objects.tickets.write` eintragen
- [x] Accidents Pipeline aufbauen

## 🎯 Career & Ausbildung
### Consulting
- [ ] Begin structured case prep (Case in Point)
### TUM Master (MMT)
- [ ] Warte auf TUM-Entscheid

## 🟡 Projekte
### MyWardrobe
- [ ] URL Scraper bauen
"""


class TestCleanTask:
    def test_strips_checkbox_bold_and_arrow(self):
        assert clean_task("- [ ] **Foo bar** ← HorseFinder") == "Foo bar"

    def test_strips_label_prefix_and_backticks(self):
        assert clean_task("[Claims] HubSpot `scope` eintragen") == "HubSpot scope eintragen"

    def test_handles_checked_box(self):
        assert clean_task("- [x] done thing") == "done thing"


class TestBucketFor:
    def test_claims_is_arbeit(self):
        assert bucket_for("Claims Intake Workflow", "HubSpot scope") == ARBEIT

    def test_consulting_is_arbeit(self):
        assert bucket_for("Consulting", "case prep") == ARBEIT

    def test_tum_beats_career_section(self):
        # subsection TUM should win over the broader Career section
        assert bucket_for("TUM Master (MMT)", "Warte auf TUM-Entscheid") == PERSOENLICH

    def test_app_keyword(self):
        assert bucket_for("", "nennung-online Affiliate-Anfrage") == APPS

    def test_mywardrobe_section(self):
        assert bucket_for("MyWardrobe", "URL Scraper") == APPS


class TestParseOpenTasks:
    def test_only_open_items_with_buckets(self):
        items = parse_open_tasks(SAMPLE)
        texts = [t for _, t in items]
        assert "Accidents Pipeline aufbauen" not in texts  # [x] excluded
        assert ("📱 Apps" if False else APPS, "nennung-online.de Affiliate-Anfrage senden") in items
        # buckets assigned
        by_text = {t: b for b, t in items}
        assert by_text["HubSpot Scope crm.objects.tickets.write eintragen"] == ARBEIT
        assert by_text["Begin structured case prep (Case in Point)"] == ARBEIT
        assert by_text["Warte auf TUM-Entscheid"] == PERSOENLICH
        assert by_text["URL Scraper bauen"] == APPS


class TestRenderGroups:
    def test_renders_bucket_headers_and_bullets(self):
        out = render_groups(parse_open_tasks(SAMPLE))
        assert f"*{ARBEIT}*" in out
        assert f"*{APPS}*" in out
        assert f"*{PERSOENLICH}*" in out
        assert "• Warte auf TUM-Entscheid" in out
        assert "←" not in out and "**" not in out

    def test_cap_per_bucket(self):
        items = [(APPS, f"Task {i}") for i in range(6)]
        out = render_groups(items, cap_per_bucket=4)
        assert "_(+2 weitere)_" in out
        assert out.count("• Task") == 4


class TestMarkdownV2:
    def test_esc_escapes_specials(self):
        assert esc_v2("a.b-c!") == "a\\.b\\-c\\!"
        assert esc_v2("(x)") == "\\(x\\)"

    def test_header_emoji_outside_bold(self):
        # emoji must NOT sit directly after '*' (breaks Telegram bold)
        assert header_v2("🏢", "Arbeit") == "🏢 *Arbeit*"

    def test_expandable_blockquote_structure(self):
        q = expandable_v2("+2 weitere", ["• a", "• b"])
        lines = q.split("\n")
        assert lines[0].startswith("**>")   # expandable start
        assert lines[1].startswith(">")
        assert lines[-1].endswith("||")     # expandability mark

    def test_render_v2_caps_and_expands(self):
        items = [(APPS, f"Task {i}") for i in range(5)]
        out = render_groups_v2(items, cap_per_bucket=3)
        assert "📱 *Apps*" in out
        assert "**>" in out and out.rstrip().endswith("||")  # overflow expandable


class TestDedup:
    def test_duplicate_task_across_sections_kept_once(self):
        md = (
            "## 🔴 Dringend\n- [ ] nennung-online Anfrage\n"
            "## 🟡 Projekte\n### HorseFinder\n- [ ] nennung-online Anfrage ← siehe 🔴\n"
        )
        texts = [t for _, t in parse_open_tasks(md)]
        assert texts.count("nennung-online Anfrage") == 1
