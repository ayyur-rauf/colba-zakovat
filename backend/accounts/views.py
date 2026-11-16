from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from core.models import Season

from . import auth_services as svc
from .models import AuthIdentity, User, mask_phone

Provider = AuthIdentity.Provider


# ------------------------------------------------------------- yordamchi

def me_payload(user: User) -> dict:
    emp = user.employee
    season = Season.current()
    return {
        "id": user.pk,
        "name": str(user),
        "status": user.status,
        "is_admin": user.is_superuser,
        "employee": None if emp is None else {
            "full_name": emp.full_name,
            "branch": emp.branch.name,
            "position": emp.position,
            "phone": mask_phone(emp.phone),
        },
        "roles": [
            {"role": r.role, "module": r.module, "season": r.season.name if r.season_id else None}
            for r in user.role_assignments.select_related("season")
        ],
        "identities": [i.provider for i in user.identities.all()],
        "season": None if season is None else {"name": season.name, "start": season.start_date,
                                               "end": season.end_date},
    }


def login_response(result: svc.LoginResult) -> Response:
    user = result.user
    if user.status == User.Status.PENDING:
        return Response(
            {"status": "pending",
             "detail": "Akkauntingiz yaratildi va admin tasdig'ini kutmoqda. "
                       "Siz xodimlar ro'yxatida topilmadingiz."},
            status=status.HTTP_202_ACCEPTED,
        )
    if not user.can_login:
        return Response({"status": "blocked", "detail": "Akkaunt faol emas. Admin bilan bog'laning."},
                        status=status.HTTP_403_FORBIDDEN)
    return Response({"status": "active", **svc.issue_tokens(user), "user": me_payload(user)})


def auth_error(exc: svc.AuthError) -> Response:
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class AuthView(APIView):
    """Kirish endpointlari. Token bilan murojaat qilinsa — kirish o'rniga usulni bog'laydi."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def linking(self, request):
        return request.user and request.user.is_authenticated


# ------------------------------------------------------------- email

class EmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)


class EmailRequestCodeView(AuthView):
    def post(self, request):
        s = EmailRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            code = svc.request_email_code(s.validated_data["email"], allow_unknown=self.linking(request))
        except svc.AuthError as exc:
            return auth_error(exc)
        # Email ro'yxatda bormi-yo'qmi — oshkor qilinmaydi
        data = {"detail": "Agar bu email ro'yxatda bo'lsa, unga kod yuborildi."}
        if code and svc.dev_codes_visible():
            data["dev_code"] = code  # faqat DEBUG + konsol pochta
        return Response(data)


class EmailVerifyView(AuthView):
    def post(self, request):
        s = EmailVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            email = svc.check_email_code(s.validated_data["email"], s.validated_data["code"])
            if self.linking(request):
                svc.link_identity(request.user, Provider.EMAIL, email)
                return Response({"detail": "Email akkauntga bog'landi."})
            result = svc.resolve_login(Provider.EMAIL, email, email=email)
        except svc.AuthError as exc:
            return auth_error(exc)
        return login_response(result)


# ------------------------------------------------------------- Google

class GoogleSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class GoogleLoginView(AuthView):
    def post(self, request):
        s = GoogleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            info = svc.verify_google(s.validated_data["id_token"])
            extra = {"email": info["email"]}
            if self.linking(request):
                svc.link_identity(request.user, Provider.GOOGLE, info["sub"], extra=extra)
                return Response({"detail": "Google akkaunt bog'landi."})
            result = svc.resolve_login(Provider.GOOGLE, info["sub"], email=info["email"],
                                       display_name=info["name"], extra=extra)
        except svc.AuthError as exc:
            return auth_error(exc)
        return login_response(result)


# ------------------------------------------------------------- Telegram

class TelegramLoginView(AuthView):
    """Body — Telegram Login Widget qaytargan maydonlar (id, first_name, username, auth_date, hash, ...)."""

    def post(self, request):
        if not isinstance(request.data, dict):
            return Response({"detail": "Noto'g'ri so'rov."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = svc.verify_telegram(dict(request.data))
            uid = data["id"]
            username = data.get("username", "")
            name = " ".join(x for x in (data.get("first_name"), data.get("last_name")) if x)
            extra = {"username": username}
            if self.linking(request):
                svc.link_identity(request.user, Provider.TELEGRAM, uid, extra=extra)
                return Response({"detail": "Telegram akkaunt bog'landi."})
            result = svc.resolve_login(Provider.TELEGRAM, uid, telegram_username=username,
                                       display_name=name, extra=extra)
        except svc.AuthError as exc:
            return auth_error(exc)
        return login_response(result)


# ------------------------------------------------------------- token va profil

class SafeTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        from rest_framework_simplejwt.tokens import RefreshToken
        user_id = RefreshToken(attrs["refresh"]).payload.get("user_id")
        user = User.objects.filter(pk=user_id).select_related("employee").first()
        if user is None or not user.can_login:
            raise InvalidToken("Akkaunt faol emas.")
        return data


class SafeTokenRefreshView(TokenRefreshView):
    serializer_class = SafeTokenRefreshSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(me_payload(request.user))


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})
