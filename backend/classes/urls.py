from rest_framework.routers import DefaultRouter

from .views import ClassroomViewSet, DivisionViewSet, SubjectViewSet

router = DefaultRouter()
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("divisions", DivisionViewSet, basename="division")
router.register("subjects", SubjectViewSet, basename="subject")

urlpatterns = router.urls