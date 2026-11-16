from django.urls import path
from rest_framework.routers import SimpleRouter

from . import api

router = SimpleRouter()
router.register("books", api.BookViewSet, basename="kitob-book")
router.register("rounds", api.RoundViewSet, basename="kitob-round")

urlpatterns = [
    path("reviews/<int:pk>/file/", api.ReviewFileView.as_view(), name="kitob-review-file"),
    path("reviews/<int:pk>/grade/", api.GradeView.as_view(), name="kitob-review-grade"),
    path("my-card/", api.MyCardView.as_view(), name="kitob-my-card"),
    path("leaderboard/", api.LeaderboardView.as_view(), name="kitob-leaderboard"),
] + router.urls
