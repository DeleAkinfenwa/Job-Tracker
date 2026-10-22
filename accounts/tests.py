from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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
