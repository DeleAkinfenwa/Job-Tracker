from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, CompanyViewSet

# Builds the list and detail URLs for each resource, e.g. /api/companies/ and /api/companies/<id>/.
router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("applications", ApplicationViewSet, basename="application")

urlpatterns = router.urls
