import io
import zipfile
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.demo import DEMO_EMAIL
from accounts.models import User
from tracker.models import Application, Company

from .engine import tailor as engine
from .engine.llm import LLMError
from .engine.profile import month_to_iso, parse_profile
from .models import AgentRun, CareerEntry, CareerProfile

OWNER = "owner@example.com"
TEMPLATE = (settings.BASE_DIR / "agent" / "engine" / "profile_template.yaml").read_text(encoding="utf-8")
SAMPLE_JOB = (settings.BASE_DIR / "agent" / "fixtures" / "sample_job.txt").read_text(encoding="utf-8")
EM_DASH = "—"

# Every agent URL, so the lock can be checked on all of them at once.
AGENT_URLS = [
    ("get", "agent-status", None),
    ("get", "agent-profile", None),
    ("put", "agent-profile", None),
    ("get", "agent-entry-list", None),
    ("post", "agent-entry-list", None),
    ("post", "agent-entry-import-profile", None),
    ("post", "agent-entry-import-json", None),
    ("get", "agent-run-list", None),
    ("post", "agent-run-tailor", None),
    ("post", "agent-run-evaluate", None),
    ("get", "agent-run-detail", 1),
    ("get", "agent-run-docx", 1),
]


def url_for(name, pk):
    return reverse(name, args=[pk]) if pk else reverse(name)


@override_settings(AGENT_OWNER_EMAILS=[OWNER, DEMO_EMAIL], AGENT_PROVIDER="mock", AGENT_DAILY_RUN_LIMIT=25)
class AgentTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(email=OWNER, password="Agent-pass-2026")
        self.stranger = User.objects.create_user(email="stranger@example.com", password="Agent-pass-2026")
        self.demo = User.objects.create_user(email=DEMO_EMAIL, password="Demo-password-2026")
        self.client.force_authenticate(self.owner)

    def setup_record(self):
        CareerProfile.objects.create(owner=self.owner, yaml=TEMPLATE)
        res = self.client.post(reverse("agent-entry-import-profile"))
        self.assertEqual(res.status_code, 200, res.data)
        return res.data["imported"]

    def tailor(self, **body):
        return self.client.post(reverse("agent-run-tailor"), {"job_text": SAMPLE_JOB, **body})


# The agent spends the owner's money, so nobody else may reach it.
class AccessTests(AgentTestCase):
    def test_strangers_get_404_everywhere(self):
        self.client.force_authenticate(self.stranger)
        for method, name, pk in AGENT_URLS:
            res = getattr(self.client, method)(url_for(name, pk), {})
            self.assertEqual(res.status_code, 404, f"{method} {name} answered {res.status_code}")
        self.assertFalse(AgentRun.objects.exists())

    def test_demo_account_is_locked_out_even_if_listed(self):
        self.client.force_authenticate(self.demo)
        for method, name, pk in AGENT_URLS:
            res = getattr(self.client, method)(url_for(name, pk), {})
            self.assertEqual(res.status_code, 404, f"{method} {name} answered {res.status_code}")

    def test_logged_out_visitors_are_refused(self):
        self.client.force_authenticate(None)
        for method, name, pk in AGENT_URLS:
            res = getattr(self.client, method)(url_for(name, pk), {})
            self.assertEqual(res.status_code, 401, f"{method} {name} answered {res.status_code}")

    def test_owner_email_matches_case_insensitively(self):
        with override_settings(AGENT_OWNER_EMAILS=["Owner@Example.com"]):
            self.assertEqual(self.client.get(reverse("agent-status")).status_code, 200)

    @override_settings(AGENT_OWNER_EMAILS=[])
    def test_empty_setting_turns_the_agent_off(self):
        self.assertEqual(self.client.get(reverse("agent-status")).status_code, 404)
        self.assertFalse(self.client.get(reverse("me")).data["agent_enabled"])

    def test_me_tells_the_website_whether_to_show_the_agent(self):
        self.assertTrue(self.client.get(reverse("me")).data["agent_enabled"])
        self.client.force_authenticate(self.stranger)
        self.assertFalse(self.client.get(reverse("me")).data["agent_enabled"])
        self.client.force_authenticate(self.demo)
        self.assertFalse(self.client.get(reverse("me")).data["agent_enabled"])

    @override_settings(AGENT_OWNER_EMAILS=["new-owner@example.com"])
    def test_nobody_can_sign_up_with_the_owner_email(self):
        self.client.force_authenticate(None)
        for email in ("new-owner@example.com", "NEW-OWNER@example.com"):
            res = self.client.post(
                reverse("register"), {"email": email, "password": "A-strong-pass-2026", "full_name": "X"}
            )
            self.assertEqual(res.status_code, 400)
            self.assertIn("email", res.data)
        self.assertFalse(User.objects.filter(email="new-owner@example.com").exists())

    def test_other_owners_cannot_see_each_others_runs(self):
        self.setup_record()
        run_id = self.tailor().data["id"]
        second = User.objects.create_user(email="second@example.com", password="Agent-pass-2026")
        with override_settings(AGENT_OWNER_EMAILS=[OWNER, "second@example.com"]):
            self.client.force_authenticate(second)
            self.assertEqual(self.client.get(reverse("agent-run-detail", args=[run_id])).status_code, 404)
            self.assertEqual(self.client.get(reverse("agent-run-docx", args=[run_id])).status_code, 404)
            self.assertEqual(self.client.get(reverse("agent-run-list")).data["count"], 0)
            self.assertEqual(self.client.get(reverse("agent-entry-list")).data, [])


class ProfileTests(AgentTestCase):
    def test_starter_template_until_saved(self):
        res = self.client.get(reverse("agent-profile"))
        self.assertEqual(res.data["yaml"], TEMPLATE)
        self.assertIsNone(res.data["updated_at"])
        self.assertEqual([r["key"] for r in res.data["roles"]], ["acme", "startup"])

    def test_save_and_reload(self):
        res = self.client.put(reverse("agent-profile"), {"yaml": TEMPLATE.replace("Jordan Example", "Sam Sample")})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Sam Sample", CareerProfile.objects.get(owner=self.owner).yaml)

    def test_bad_yaml_is_refused_with_a_plain_message(self):
        for text in ("roles: [", "- just a list", "roles:\n  - key: x\n    company: Y\n"):
            res = self.client.put(reverse("agent-profile"), {"yaml": text})
            self.assertEqual(res.status_code, 400, text)
            self.assertIn("yaml", res.data)
        self.assertFalse(CareerProfile.objects.exists())


class CareerLogTests(AgentTestCase):
    def test_import_profile_bullets_replaces_an_earlier_import(self):
        self.assertEqual(self.setup_record(), 4)
        self.client.post(reverse("agent-entry-import-profile"))
        self.assertEqual(CareerEntry.objects.filter(owner=self.owner, source="resume").count(), 4)
        entry = CareerEntry.objects.filter(raw_text__startswith="Automated Azure").get()
        self.assertEqual(entry.entry_date.isoformat(), month_to_iso("Jan 2024"))
        self.assertIn("Terraform", entry.tools)

    def test_import_needs_a_profile(self):
        res = self.client.post(reverse("agent-entry-import-profile"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("profile", res.data["detail"])

    def test_log_work_without_ai_costs_nothing(self):
        self.setup_record()
        body = {"role": "acme", "entry_date": "2026-10-01", "raw_text": "Cut Terraform plan time for 3 services."}
        res = self.client.post(reverse("agent-entry-list"), body)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["tools"], ["Terraform"])
        self.assertEqual(res.data["metrics"], ["3"])
        self.assertFalse(AgentRun.objects.exists())

    def test_log_work_with_ai_counts_as_a_run(self):
        self.setup_record()
        body = {"role": "acme", "entry_date": "2026-10-01", "raw_text": "Moved 2 apps to Docker.", "use_ai": True}
        res = self.client.post(reverse("agent-entry-list"), body)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertIn("Docker", res.data["tools"])
        self.assertTrue(res.data["open_questions"])
        self.assertEqual(AgentRun.objects.get().kind, "extract")

    def test_unknown_role_is_refused(self):
        self.setup_record()
        res = self.client.post(
            reverse("agent-entry-list"), {"role": "nope", "entry_date": "2026-10-01", "raw_text": "x"}
        )
        self.assertEqual(res.status_code, 400)

    def test_import_json_from_the_claude_version(self):
        items = [
            {"id": 7, "entry_date": "2024-03-01", "role": "acme", "source": "resume", "raw_text": "Did a thing."},
            {"entry_date": "2025-01-15T00:00:00Z", "role": "acme", "raw_text": "Did more.", "tools": ["Azure"]},
        ]
        res = self.client.post(reverse("agent-entry-import-json"), {"entries": items}, format="json")
        self.assertEqual(res.data, {"imported": 2})
        res = self.client.post(
            reverse("agent-entry-import-json"), {"entries": items[:1], "replace": True}, format="json"
        )
        self.assertEqual(CareerEntry.objects.filter(owner=self.owner).count(), 1)
        bad = self.client.post(reverse("agent-entry-import-json"), {"entries": [{"role": "acme"}]}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(CareerEntry.objects.filter(owner=self.owner).count(), 1, "A bad import must change nothing")

    def test_entries_can_be_edited_and_deleted(self):
        self.setup_record()
        entry = CareerEntry.objects.first()
        url = reverse("agent-entry-detail", args=[entry.id])
        self.assertEqual(self.client.patch(url, {"summary": "Shorter."}).data["summary"], "Shorter.")
        self.assertEqual(self.client.delete(url).status_code, 204)


class TailorTests(AgentTestCase):
    def test_accuracy_check_removes_what_the_record_does_not_support(self):
        self.setup_record()
        res = self.tailor()
        self.assertEqual(res.status_code, 201, res.data)
        doc = res.data["result"]
        text = repr(doc["summary"]) + repr(doc["skills"]) + repr(doc["experience"])
        self.assertNotIn(EM_DASH, text)
        self.assertNotIn("Unsupported claim", text)
        self.assertNotIn("Led a team of 12", text)
        self.assertNotIn("Kafka", text)
        self.assertNotIn("10 years", text)
        self.assertIn("Automated Azure infrastructure", text, "A bullet with a string evidence id must be kept")
        removed = " ".join(doc["removed"])
        self.assertIn("Led a team of 12", removed)
        self.assertIn("Kafka", removed)

    def test_word_file_and_text(self):
        self.setup_record()
        run_id = self.tailor(job_title="Cloud Engineer at Globex").data["id"]
        res = self.client.get(reverse("agent-run-docx", args=[run_id]))
        self.assertEqual(res.status_code, 200)
        self.assertIn('filename="Jordan Example - Cloud Engineer at Globex.docx"', res["Content-Disposition"])
        with zipfile.ZipFile(io.BytesIO(res.content)) as z:
            body = z.read("word/document.xml").decode()
        self.assertIn("Automated Azure infrastructure", body)
        self.assertNotIn("Led a team of 12", body)
        text = self.client.get(reverse("agent-run-text", args=[run_id])).data["text"]
        self.assertIn("# Jordan Example", text)

    def test_resume_keeps_the_profile_it_was_written_with(self):
        self.setup_record()
        run_id = self.tailor().data["id"]
        CareerProfile.objects.filter(owner=self.owner).update(yaml=TEMPLATE.replace("Jordan Example", "Changed"))
        text = self.client.get(reverse("agent-run-text", args=[run_id])).data["text"]
        self.assertIn("Jordan Example", text)

    def test_fit_check(self):
        self.setup_record()
        res = self.client.post(reverse("agent-run-evaluate"), {"job_text": SAMPLE_JOB})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertIn("fit_score", res.data["result"])
        self.assertEqual(self.client.get(reverse("agent-run-docx", args=[res.data["id"]])).status_code, 404)

    def test_link_to_your_own_application_only(self):
        self.setup_record()
        mine = Application.objects.create(
            owner=self.owner, company=Company.objects.create(owner=self.owner, name="Globex"), role_title="Cloud Eng"
        )
        theirs = Application.objects.create(
            owner=self.stranger, company=Company.objects.create(owner=self.stranger, name="Initech"), role_title="X"
        )
        self.assertEqual(self.tailor(application_id=theirs.id).status_code, 400)
        res = self.tailor(application_id=mine.id)
        self.assertEqual(res.data["job_title"], "Cloud Eng at Globex")
        listed = self.client.get(reverse("agent-run-list"), {"application": mine.id}).data["results"]
        self.assertEqual([r["id"] for r in listed], [res.data["id"]])

    def test_needs_a_record_first(self):
        res = self.tailor()
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AgentRun.objects.exists())

    def test_job_text_is_required_and_capped(self):
        self.setup_record()
        self.assertEqual(self.client.post(reverse("agent-run-tailor"), {}).status_code, 400)
        self.assertEqual(self.tailor(job_text="x" * 20001).status_code, 400)


# Spending guards.
class BudgetTests(AgentTestCase):
    @override_settings(AGENT_DAILY_RUN_LIMIT=2)
    def test_daily_run_limit(self):
        self.setup_record()
        self.assertEqual(self.tailor().status_code, 201)
        self.assertEqual(self.client.post(reverse("agent-run-evaluate"), {"job_text": SAMPLE_JOB}).status_code, 201)
        res = self.tailor()
        self.assertEqual(res.status_code, 429)
        self.assertIn("limit of 2", res.data["detail"])
        self.assertEqual(AgentRun.objects.count(), 2)
        status_data = self.client.get(reverse("agent-status")).data
        self.assertEqual((status_data["runs_today"], status_data["daily_run_limit"]), (2, 2))

    @override_settings(AGENT_DAILY_TOKEN_LIMIT=1000)
    def test_daily_token_limit(self):
        self.setup_record()
        AgentRun.objects.create(owner=self.owner, kind="tailor", input_tokens=900, output_tokens=200)
        self.assertEqual(self.tailor().status_code, 429)

    def test_yesterdays_runs_do_not_count(self):
        self.setup_record()
        with override_settings(AGENT_DAILY_RUN_LIMIT=1):
            old = AgentRun.objects.create(owner=self.owner, kind="tailor")
            AgentRun.objects.filter(pk=old.pk).update(created_at=old.created_at.replace(year=2020))
            self.assertEqual(self.tailor().status_code, 201)

    def test_one_run_at_a_time(self):
        self.setup_record()
        AgentRun.objects.create(owner=self.owner, kind="tailor", ok=False, error="running")
        self.assertEqual(self.tailor().status_code, 409)

    @override_settings(AGENT_PROVIDER="anthropic", ANTHROPIC_API_KEY="")
    def test_missing_key_refuses_without_recording_a_run(self):
        self.setup_record()
        res = self.tailor()
        self.assertEqual(res.status_code, 503)
        self.assertIn("ANTHROPIC_API_KEY", res.data["detail"])
        self.assertFalse(AgentRun.objects.exists())
        self.assertFalse(self.client.get(reverse("agent-status")).data["configured"])

    def test_model_failure_is_recorded_and_still_counts(self):
        self.setup_record()
        with mock.patch("agent.engine.mock.MockLLM.complete", side_effect=LLMError("Model is down.")):
            res = self.tailor()
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.data["detail"], "Model is down.")
        run = AgentRun.objects.get()
        self.assertFalse(run.ok)
        self.assertEqual(run.error, "Model is down.")
        self.assertEqual(self.tailor().status_code, 201, "A failed run must not block the next one")

    @override_settings(AGENT_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key", AGENT_MODEL="test-model")
    def test_tokens_are_recorded_from_the_real_client(self):
        self.setup_record()
        reply = mock.Mock(
            content=[mock.Mock(text='{"summary": "", "experience": [], "skills": []}')],
            usage=mock.Mock(input_tokens=1200, output_tokens=300),
        )
        with mock.patch("anthropic.resources.Messages.create", return_value=reply) as create:
            res = self.tailor()
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(create.call_args.kwargs["model"], "test-model")
        self.assertEqual((res.data["input_tokens"], res.data["output_tokens"]), (1200, 300))


# The accuracy check on its own, with the fictional starter profile and its limits.
class AccuracyCheckTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = parse_profile(TEMPLATE)
        cls.evidence, n = [], 0
        for role in cls.profile["roles"]:
            for bullet in role["bullets"]:
                n += 1
                cls.evidence.append(
                    {
                        "id": n, "role": role["key"], "entry_date": month_to_iso(role["start"]), "raw_text": bullet,
                        "summary": bullet, "tools": [], "skills": [], "accomplishments": [bullet], "metrics": [],
                    }
                )  # fmt: skip

    def check(self, role, text, sources, summary="Software engineer with cloud and web experience."):
        raw = {"summary": summary, "experience": [{"role_key": role, "bullets": [{"text": text, "sources": sources}]}]}
        doc = engine.validate(raw, self.profile, self.evidence)
        return [b["text"] for r in doc["experience"] for b in r["bullets"]], doc

    def assertKept(self, role, text, sources):
        kept, doc = self.check(role, text, sources)
        self.assertEqual(kept, [text.replace(EM_DASH, ",").replace(" ,", ",")], doc["removed"])

    def assertRemoved(self, role, text, sources, reason=""):
        kept, doc = self.check(role, text, sources)
        self.assertEqual(kept, [], f"Should have been removed: {text}")
        self.assertIn(reason, " ".join(doc["removed"]))

    def test_a_faithful_rewording_is_kept(self):
        self.assertKept(
            "acme", "Automated Azure infrastructure deployments with Terraform for three product teams.", [1]
        )

    def test_evidence_ids_in_any_format(self):
        for sources in ("1", "#1", 1.0, ["1"], "1, 2"):
            kept, _ = self.check("acme", "Automated Azure deployments with Terraform.", sources)
            self.assertEqual(len(kept), 1, sources)

    def test_no_sources_or_made_up_sources(self):
        self.assertRemoved("acme", "Automated Azure deployments.", [], "no evidence")
        self.assertRemoved("acme", "Automated Azure deployments.", [99], "do not exist")

    def test_evidence_from_a_different_job(self):
        self.assertRemoved("acme", "Built React features for a billing portal.", [3], "different job")

    def test_raised_involvement(self):
        self.assertRemoved("startup", "Led the billing portal rebuild in React and Node.js.", [3])

    def test_numbers_must_come_from_the_evidence(self):
        self.assertRemoved("acme", "Automated Azure deployments with Terraform for 12 product teams.", [1])

    def test_tools_must_come_from_the_evidence(self):
        self.assertRemoved("acme", "Automated Azure deployments with Terraform and Ansible.", [1])

    def test_never_claim_and_no_experience(self):
        self.assertRemoved(
            "acme", "Automated Azure deployments with Terraform while holding a security clearance.", [1]
        )
        self.assertRemoved("acme", "Automated Azure deployments with Terraform and Kafka.", [1])

    def test_context_rule(self):
        self.assertKept("startup", "Wrote PostgreSQL queries for reporting dashboards.", [4])
        self.assertRemoved("startup", "Designed and tuned PostgreSQL clusters.", [4], "context")

    def test_years_and_summary(self):
        _, doc = self.check(
            "acme", "Automated Azure deployments with Terraform.", [1], summary="Brings 8 years of experience."
        )
        self.assertNotIn("8 years", doc["summary"])
        self.assertTrue(any("Summary sentence removed" in r for r in doc["removed"]))

    def test_em_dashes_are_replaced(self):
        kept, _ = self.check("acme", f"Automated Azure deployments {EM_DASH} with Terraform.", [1])
        self.assertEqual(kept, ["Automated Azure deployments, with Terraform."])

    def test_skills_must_be_in_the_record(self):
        raw = {"summary": "", "experience": [], "skills": [{"category": "Cloud", "items": ["Azure", "Kafka", "GCP"]}]}
        doc = engine.validate(raw, self.profile, self.evidence)
        self.assertEqual(doc["skills"], [{"category": "Cloud", "items": ["Azure"]}])
