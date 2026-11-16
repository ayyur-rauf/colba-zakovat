from django.urls import path
from rest_framework.routers import SimpleRouter

from . import api

router = SimpleRouter()
router.register("teams", api.TeamViewSet, basename="zakovat-team")
router.register("games", api.GameViewSet, basename="zakovat-game")
router.register("questions", api.QuestionViewSet, basename="zakovat-question")

urlpatterns = [
    path("me/", api.MeView.as_view(), name="zakovat-me"),
    path("players/", api.PlayersView.as_view(), name="zakovat-players"),
    path("invitations/<int:pk>/respond/", api.InvitationRespondView.as_view(), name="zakovat-invite-respond"),
    path("registrations/<int:pk>/approve/", api.RegistrationApproveView.as_view(), name="zakovat-reg-approve"),
    path("appeals/<int:pk>/decide/", api.AppealDecideView.as_view(), name="zakovat-appeal-decide"),
    path("standings/", api.StandingsView.as_view(), name="zakovat-standings"),
    path("season-tiebreak/", api.SeasonTiebreakView.as_view(), name="zakovat-season-tiebreak"),
] + router.urls
