from django.conf import settings
from django.db import models
from django.db.models import F, Q


# Adds created and updated timestamps to any model that inherits it.
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# A company the user is interested in; each user keeps their own list.
class Company(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=500, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=255, blank=True)

    # Sort by name, and don't allow the same company name twice for one user.
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_company_name_per_owner"),
        ]

    def __str__(self) -> str:
        return self.name


# One job application: the role, its stage in the pipeline, salary range and notes.
class Application(TimeStampedModel):
    # The stages an application moves through.
    class Status(models.TextChoices):
        WISHLIST = "wishlist", "Wishlist"
        APPLIED = "applied", "Applied"
        INTERVIEWING = "interviewing", "Interviewing"
        OFFER = "offer", "Offer"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    # Statuses that mean the application was actually sent, and those that mean the company responded.
    SUBMITTED = {Status.APPLIED, Status.INTERVIEWING, Status.OFFER, Status.REJECTED}
    RESPONDED = {Status.INTERVIEWING, Status.OFFER}

    # Each application belongs to one user and one of their companies.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="applications")
    role_title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WISHLIST, db_index=True)
    job_url = models.URLField(max_length=500, blank=True)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    applied_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Newest first, with an index for the common "my applications in this stage" query.
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"])]
        constraints = [
            # Enforced by the database too, not just by the API.
            models.CheckConstraint(
                condition=Q(salary_min__isnull=True) | Q(salary_max__isnull=True) | Q(salary_min__lte=F("salary_max")),
                name="salary_min_lte_salary_max",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role_title} at {self.company}"
