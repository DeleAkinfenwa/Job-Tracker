import django_filters
from django.db.models import F
from rest_framework.filters import OrderingFilter

from .models import Application


# Extra query filters for applications: stage, company, date range and minimum salary.
class ApplicationFilter(django_filters.FilterSet):
    applied_after = django_filters.DateFilter(field_name="applied_on", lookup_expr="gte")
    applied_before = django_filters.DateFilter(field_name="applied_on", lookup_expr="lte")
    min_salary = django_filters.NumberFilter(field_name="salary_max", lookup_expr="gte")

    class Meta:
        model = Application
        fields = ["status", "company"]


class NullsLastOrderingFilter(OrderingFilter):
    """Like DRF's OrderingFilter, but rows with no value always sort last.

    Postgres puts NULLs first when sorting descending, so `?ordering=-salary_max`
    would otherwise list applications with no salary at the top.
    """

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset
        # Turn each "field" or "-field" into an ascending or descending sort with empty values last.
        expressions = [
            F(field[1:]).desc(nulls_last=True) if field.startswith("-") else F(field).asc(nulls_last=True)
            for field in ordering
        ]
        # Sort by id last so the order is stable across pages.
        return queryset.order_by(*expressions, "id")
