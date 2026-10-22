from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .demo import DEMO_EMAIL, DEMO_PASSWORD
from .models import User

PASSWORD = "Tracker-pass-2026"


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttle counters between tests

    def register(self, email="ada@example.com", password=PASSWORD):
        return self.client.post(reverse("register"), {"email": email, "password": password, "full_name": "Ada"})

    def test_register_returns_user_without_password(self):
        res = self.register()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["email"], "ada@example.com")
        self.assertNotIn("password", res.data)
        self.assertTrue(User.objects.get(email="ada@example.com").check_password(PASSWORD))

    def test_email_is_case_insensitive_and_unique(self):
        self.register()
        res = self.register(email="ADA@Example.com")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_weak_password_rejected(self):
        res = self.register(password="password")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_and_me(self):
        self.register()
        res = self.client.post(reverse("token_obtain_pair"), {"email": "ada@example.com", "password": PASSWORD})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", res.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        me = self.client.get(reverse("me"))
        self.assertEqual(me.data["email"], "ada@example.com")

        updated = self.client.patch(reverse("me"), {"full_name": "Ada Lovelace"})
        self.assertEqual(updated.data["full_name"], "Ada Lovelace")

    def test_refresh_token(self):
        self.register()
        tokens = self.client.post(reverse("token_obtain_pair"), {"email": "ada@example.com", "password": PASSWORD}).data
        res = self.client.post(reverse("token_refresh"), {"refresh": tokens["refresh"]})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_wrong_password(self):
        self.register()
        res = self.client.post(reverse("token_obtain_pair"), {"email": "ada@example.com", "password": "nope"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_routes_require_auth(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer garbage")
        self.assertEqual(self.client.get(reverse("company-list")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_health(self):
        self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok", "database": "ok"})


class DemoAccountTests(APITestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_demo", stdout=StringIO())

    def login_as_demo(self):
        res = self.client.post(reverse("token_obtain_pair"), {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_demo_user_is_flagged(self):
        self.login_as_demo()
        self.assertTrue(self.client.get(reverse("me")).data["is_demo"])

    def test_regular_user_is_not_flagged(self):
        user = User.objects.create_user(email="ada@example.com", password=PASSWORD)
        self.client.force_authenticate(user)
        self.assertFalse(self.client.get(reverse("me")).data["is_demo"])

    def test_demo_profile_cannot_be_edited(self):
        self.login_as_demo()
        res = self.client.patch(reverse("me"), {"full_name": "Vandal"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(User.objects.get(email=DEMO_EMAIL).full_name, "Demo User")

    def test_reset_restores_demo_data(self):
        demo = User.objects.get(email=DEMO_EMAIL)
        demo.applications.all().delete()
        demo.companies.filter(name="Lumen Robotics").update(name="Renamed")

        call_command("seed_demo", reset=True, stdout=StringIO())

        demo = User.objects.get(email=DEMO_EMAIL)
        self.assertEqual(demo.applications.count(), 5)
        self.assertTrue(demo.companies.filter(name="Lumen Robotics").exists())
        self.assertEqual(User.objects.filter(email=DEMO_EMAIL).count(), 1)

    def test_reset_leaves_other_users_alone(self):
        other = User.objects.create_user(email="ada@example.com", password=PASSWORD)
        other.companies.create(name="Acme")
        call_command("seed_demo", reset=True, stdout=StringIO())
        self.assertTrue(other.companies.filter(name="Acme").exists())
