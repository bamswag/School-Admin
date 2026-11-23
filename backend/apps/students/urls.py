from rest_framework.routers import DefaultRouter

from .views import StudentRecordViewSet

router = DefaultRouter()
router.register("students", StudentRecordViewSet, basename="student")
urlpatterns = router.urls
