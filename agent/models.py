from django.conf import settings
from django.db import models


# The fixed facts for resumes: contact details, job titles and dates, skills, depth notes and limits, as YAML.
class CareerProfile(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_profile")
    yaml = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Career profile for {self.owner}"


# One thing you did at work, in your own words. Every resume bullet must cite at least one of these.
class CareerEntry(models.Model):
    class Source(models.TextChoices):
        LOG = "log", "Work log"
        RESUME = "resume", "From profile bullets"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_entries")
    entry_date = models.DateField()
    role = models.CharField(max_length=80, help_text="The role key from your profile, e.g. acme.")
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.LOG)
    raw_text = models.TextField()
    summary = models.TextField(blank=True)
    tools = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    accomplishments = models.JSONField(default=list, blank=True)
    metrics = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["entry_date", "id"]
        verbose_name_plural = "career entries"

    def __str__(self) -> str:
        return f"#{self.pk} {self.role}: {self.raw_text[:50]}"

    # The shape the engine expects.
    def as_evidence(self) -> dict:
        return {
            "id": self.pk,
            "entry_date": self.entry_date.isoformat(),
            "role": self.role,
            "source": self.source,
            "raw_text": self.raw_text,
            "summary": self.summary,
            "tools": list(self.tools or []),
            "skills": list(self.skills or []),
            "accomplishments": list(self.accomplishments or []),
            "metrics": list(self.metrics or []),
        }


# One call to the AI: a fit check, a tailored resume, or reading a work log. Also the record the daily cap counts.
class AgentRun(models.Model):
    class Kind(models.TextChoices):
        EVALUATE = "evaluate", "Fit check"
        TAILOR = "tailor", "Tailored resume"
        EXTRACT = "extract", "Work log"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_runs")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    application = models.ForeignKey(
        "tracker.Application", null=True, blank=True, on_delete=models.SET_NULL, related_name="agent_runs"
    )
    job_title = models.CharField(max_length=200, blank=True)
    job_text = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)
    # The profile as it was for this run, so a downloaded resume never changes later.
    profile_snapshot = models.JSONField(default=dict, blank=True)
    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.job_title or ''} ({self.created_at:%Y-%m-%d})"
