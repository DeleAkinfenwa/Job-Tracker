from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import ApplicationFilter, NullsLastOrderingFilter
from .models import Application, Company
from .serializers import ApplicationSerializer, ApplicationStatsSerializer, CompanySerializer


class OwnedQuerysetMixin:
    """Scope every query to the logged-in user and set them as owner on create.

    Because other users' rows are filtered out of the queryset, requesting one
    returns 404 rather than 403, so record IDs can't be probed.
    """

    # Only return rows that belong to the logged-in user.
    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    # New rows are always owned by whoever created them.
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


# CRUD endpoints for companies, with search, an industry filter and sorting.
class CompanyViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    queryset = Company.objects.annotate(application_count=Count("applications"))
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["industry"]
    search_fields = ["name", "industry", "location"]
    ordering_fields = ["name", "created_at", "application_count"]
    ordering = ["name"]


# CRUD endpoints for applications, with search, filters and sorting (empty values last).
class ApplicationViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    queryset = Application.objects.select_related("company")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, NullsLastOrderingFilter]
    filterset_class = ApplicationFilter
    search_fields = ["role_title", "notes", "company__name"]
    ordering_fields = ["created_at", "applied_on", "role_title", "salary_max"]
    ordering = ["-created_at"]

    # GET /api/applications/stats/ for the summary panel.
    @extend_schema(responses=ApplicationStatsSerializer)
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Counts by status and the share of submitted applications that got a response."""
        # Count applications per stage in one query, filling in zero for empty stages.
        counts = {status: 0 for status in Application.Status.values}
        rows = self.get_queryset().order_by().values("status").annotate(n=Count("id"))
        counts.update({row["status"]: row["n"] for row in rows})

        # Response rate = applications that got an interview or offer / applications sent.
        submitted = sum(counts[s] for s in Application.SUBMITTED)
        responded = sum(counts[s] for s in Application.RESPONDED)
        data = {
            "total": sum(counts.values()),
            "by_status": [{"status": s, "count": n} for s, n in counts.items()],
            "response_rate": round(responded / submitted, 3) if submitted else 0.0,
        }
        return Response(ApplicationStatsSerializer(data).data)
