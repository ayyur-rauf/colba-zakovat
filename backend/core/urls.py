from django.urls import path

from . import manage_api as m

urlpatterns = [
    path("manage/employees/", m.EmployeesView.as_view()),
    path("manage/employees/import/", m.EmployeeImportView.as_view()),
    path("manage/employees/<int:pk>/", m.EmployeeDetailView.as_view()),
    path("manage/users/", m.UsersView.as_view()),
    path("manage/users/search/", m.UserSearchView.as_view()),
    path("manage/users/<int:pk>/<str:action>/", m.UserActionView.as_view()),
    path("manage/roles/", m.RolesView.as_view()),
    path("manage/roles/<int:pk>/", m.RoleDeleteView.as_view()),
    path("manage/seasons/", m.SeasonsView.as_view()),
    path("manage/seasons/<int:pk>/activate/", m.SeasonActivateView.as_view()),
    path("manage/audit/", m.AuditView.as_view()),
    path("announcements/", m.AnnouncementsView.as_view()),
    path("announcements/<int:pk>/", m.AnnouncementDetailView.as_view()),
]
