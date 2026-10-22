from rest_framework.pagination import LimitOffsetPagination


class DefaultPagination(LimitOffsetPagination):
    """`?limit=20&offset=40` style paging. Responses include count, next and previous links."""

    default_limit = 20
    max_limit = 100
