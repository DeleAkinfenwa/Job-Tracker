"""Load a resume agent profile and career log into someone's account.

    python manage.py import_career_record you@example.com --profile profile.yaml --entries entries.json

entries.json is a list of entries, or a folder of one-entry JSON files (as exported by the Claude version).
"""

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from agent.engine.profile import parse_profile
from agent.models import CareerProfile
from agent.services import AgentUnavailable, import_entries


class Command(BaseCommand):
    help = "Load a resume agent profile (YAML) and career log (JSON) into an account."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--profile", help="Path to profile.yaml")
        parser.add_argument("--entries", help="Path to a JSON list of entries, or a folder of entry files")
        parser.add_argument("--replace", action="store_true", help="Delete the account's current log first")

    def handle(self, email, profile=None, entries=None, replace=False, **options):
        user = get_user_model().objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f"No account with the email {email}. Sign up first.")
        if profile:
            text = Path(profile).read_text(encoding="utf-8")
            try:
                parse_profile(text)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            CareerProfile.objects.update_or_create(owner=user, defaults={"yaml": text})
            self.stdout.write("Saved the profile.")
        if entries:
            path = Path(entries)
            if path.is_dir():
                items = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(path.glob("*.json"))]
                items.sort(key=lambda e: (str(e.get("entry_date")), e.get("id") or 0))
            else:
                items = json.loads(path.read_text(encoding="utf-8"))
            try:
                count = import_entries(user, items, replace=replace)
            except AgentUnavailable as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(f"Imported {count} career log entries.")
