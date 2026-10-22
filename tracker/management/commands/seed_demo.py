from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.demo import DEMO_EMAIL, DEMO_PASSWORD
from accounts.models import User
from tracker.models import Application, Company

COMPANIES = [
    ("Northwind Analytics", "https://northwind.example.com", "Data", "Remote"),
    ("Blue Harbor Health", "https://blueharbor.example.com", "Healthcare", "Philadelphia, PA"),
    ("Lumen Robotics", "https://lumen.example.com", "Robotics", "New York, NY"),
]

S = Application.Status
APPLICATIONS = [
    (0, "Backend Engineer", S.INTERVIEWING, 110_000, 135_000, 12),
    (0, "Data Platform Engineer", S.APPLIED, 120_000, 145_000, 5),
    (1, "Python Developer", S.OFFER, 105_000, 125_000, 30),
    (1, "API Engineer", S.REJECTED, None, None, 21),
    (2, "ML Infrastructure Engineer", S.WISHLIST, 140_000, 170_000, None),
]


class Command(BaseCommand):
    help = "Load a demo user with sample companies and applications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo user and everything they own, then load fresh demo data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        existing = User.objects.filter(email=DEMO_EMAIL)
        if options["reset"]:
            existing.delete()  # companies and applications are removed by CASCADE
        elif existing.exists():
            self.stdout.write("Demo data already loaded.")
            return

        user = User.objects.create_user(email=DEMO_EMAIL, password=DEMO_PASSWORD, full_name="Demo User")
        companies = [
            Company.objects.create(owner=user, name=n, website=w, industry=i, location=loc)
            for n, w, i, loc in COMPANIES
        ]
        today = timezone.localdate()
        Application.objects.bulk_create(
            Application(
                owner=user,
                company=companies[idx],
                role_title=title,
                status=status,
                salary_min=lo,
                salary_max=hi,
                applied_on=today - timedelta(days=days_ago) if days_ago else None,
            )
            for idx, title, status, lo, hi, days_ago in APPLICATIONS
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded demo data. Log in as {DEMO_EMAIL} / {DEMO_PASSWORD}"))
