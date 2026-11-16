from django.urls import path

from . import views

urlpatterns = [
    path("auth/email/request-code/", views.EmailRequestCodeView.as_view(), name="auth-email-request"),
    path("auth/email/verify/", views.EmailVerifyView.as_view(), name="auth-email-verify"),
    path("auth/google/", views.GoogleLoginView.as_view(), name="auth-google"),
    path("auth/telegram/", views.TelegramLoginView.as_view(), name="auth-telegram"),
    path("auth/refresh/", views.SafeTokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("health/", views.HealthView.as_view(), name="health"),
]
