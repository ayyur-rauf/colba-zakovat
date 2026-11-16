from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class ColbaJWTAuthentication(JWTAuthentication):
    """Token yaroqli bo'lsa ham, bloklangan / ishdan ketgan xodim kira olmaydi."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.can_login:
            raise AuthenticationFailed("Akkaunt faol emas.", code="user_inactive")
        return user
