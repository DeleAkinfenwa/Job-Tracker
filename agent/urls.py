from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CareerEntryViewSet, ProfileView, RunViewSet, StatusView

router = DefaultRouter()
router.register("entries", CareerEntryViewSet, basename="agent-entry")
router.register("runs", RunViewSet, basename="agent-run")

urlpatterns = [
    path("status/", StatusView.as_view(), name="agent-status"),
    path("profile/", ProfileView.as_view(), name="agent-profile"),
    *router.urls,
]
