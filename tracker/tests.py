from django.core.cache import cache
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Application, Company


# Shared setup: two users, with the first logged in and owning one company.
class TrackerTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="ada@example.com", password="Tracker-pass-2026")
        self.other = User.objects.create_user(email="grace@example.com", password="Tracker-pass-2026")
        self.client.force_authenticate(self.user)
        self.company = Company.objects.create(owner=self.user, name="Acme Corp", industry="Software")

    def create_app(self, **overrides):
        body = {"company_id": self.company.id, "role_title": "Backend Engineer", "status": "applied"}
        return self.client.post(reverse("application-list"), {**body, **overrides})

    def titles(self, url):
        return [a["role_title"] for a in self.client.get(url).data["results"]]


# Company endpoints: ownership, unique names, search, paging and privacy.
class CompanyTests(TrackerTestCase):
    def test_create_sets_owner(self):
        res = self.client.post(reverse("company-list"), {"name": "Globex", "website": "https://globex.example.com"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.get(id=res.data["id"]).owner, self.user)

    def test_duplicate_name_rejected_case_insensitively(self):
        res = self.client.post(reverse("company-list"), {"name": "acme corp"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", res.data)

    def test_other_users_can_reuse_a_name(self):
        self.client.force_authenticate(self.other)
        res = self.client.post(reverse("company-list"), {"name": "Acme Corp"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_list_search_and_application_count(self):
        Company.objects.create(owner=self.user, name="Alphabet")
        self.create_app()
        self.create_app()
        res = self.client.get(reverse("company-list"), {"search": "acme"})
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["application_count"], 2)

    def test_pagination(self):
        for i in range(5):
            Company.objects.create(owner=self.user, name=f"Company {i}")
        res = self.client.get(reverse("company-list"), {"limit": 2, "offset": 0})
        self.assertEqual(res.data["count"], 6)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIsNotNone(res.data["next"])

    def test_update_and_delete(self):
        url = reverse("company-detail", args=[self.company.id])
        self.assertEqual(self.client.patch(url, {"location": "Remote"}).data["location"], "Remote")
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Company.objects.filter(id=self.company.id).exists())

    def test_users_cannot_see_each_others_companies(self):
        self.client.force_authenticate(self.other)
        url = reverse("company-detail", args=[self.company.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("company-list")).data["count"], 0)


# Application endpoints: validation, filters, sorting, stats and privacy.
class ApplicationTests(TrackerTestCase):
    def test_create_includes_company_summary(self):
        res = self.create_app(salary_min=90000, salary_max=120000)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["company"]["name"], "Acme Corp")
        self.assertEqual(Application.objects.get(id=res.data["id"]).owner, self.user)

    def test_salary_range_validated(self):
        res = self.create_app(salary_min=150000, salary_max=100000)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_salary_checked_against_stored_value(self):
        app_id = self.create_app(salary_max=100000).data["id"]
        res = self.client.patch(reverse("application-detail", args=[app_id]), {"salary_min": 200000})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_database_also_enforces_salary_range(self):
        with self.assertRaises(IntegrityError):
            Application.objects.create(
                owner=self.user, company=self.company, role_title="X", salary_min=10, salary_max=5
            )

    def test_cannot_attach_to_another_users_company(self):
        theirs = Company.objects.create(owner=self.other, name="Initech")
        res = self.create_app(company_id=theirs.id)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company_id", res.data)

    def test_filter_search_and_ordering(self):
        self.create_app(role_title="Data Engineer", status="interviewing")
        self.create_app(role_title="ML Engineer", status="rejected", notes="Python heavy")
        self.create_app(role_title="Analyst", status="wishlist")
        url = reverse("application-list")

        self.assertEqual(self.titles(f"{url}?status=interviewing"), ["Data Engineer"])
        self.assertEqual(self.titles(f"{url}?ordering=role_title"), ["Analyst", "Data Engineer", "ML Engineer"])
        self.assertEqual(self.titles(f"{url}?search=python"), ["ML Engineer"])
        self.assertEqual(len(self.titles(f"{url}?search=acme")), 3)  # searches company name too

    def test_ordering_puts_missing_values_last(self):
        self.create_app(role_title="No salary listed")
        self.create_app(role_title="Lower", salary_max=90000)
        self.create_app(role_title="Higher", salary_max=150000)
        url = reverse("application-list")
        self.assertEqual(self.titles(f"{url}?ordering=-salary_max"), ["Higher", "Lower", "No salary listed"])
        self.assertEqual(self.titles(f"{url}?ordering=salary_max"), ["Lower", "Higher", "No salary listed"])

    def test_date_and_salary_filters(self):
        self.create_app(role_title="Old", applied_on="2026-01-10", salary_max=80000)
        self.create_app(role_title="Recent", applied_on="2026-09-01", salary_max=140000)
        url = reverse("application-list")
        self.assertEqual(self.titles(f"{url}?applied_after=2026-06-01"), ["Recent"])
        self.assertEqual(self.titles(f"{url}?min_salary=100000"), ["Recent"])

    def test_update_status_and_delete(self):
        app_id = self.create_app().data["id"]
        url = reverse("application-detail", args=[app_id])
        self.assertEqual(self.client.patch(url, {"status": "offer"}).data["status"], "offer")
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_other_users_cannot_read_applications(self):
        app_id = self.create_app().data["id"]
        self.client.force_authenticate(self.other)
        res = self.client.get(reverse("application-detail", args=[app_id]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_stats(self):
        for s in ["applied", "applied", "interviewing", "offer", "wishlist"]:
            self.create_app(status=s)
        stats = self.client.get(reverse("application-stats")).data
        counts = {row["status"]: row["count"] for row in stats["by_status"]}
        self.assertEqual(stats["total"], 5)
        self.assertEqual(counts["applied"], 2)
        self.assertEqual(counts["withdrawn"], 0)
        self.assertEqual(stats["response_rate"], 0.5)  # 2 of 4 submitted reached interview or offer

    def test_deleting_company_cascades(self):
        self.create_app()
        self.client.delete(reverse("company-detail", args=[self.company.id]))
        self.assertEqual(self.client.get(reverse("application-list")).data["count"], 0)
