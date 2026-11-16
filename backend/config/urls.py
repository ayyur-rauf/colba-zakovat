from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "Colba platformasi — boshqaruv"
admin.site.site_title = "Colba platformasi"
admin.site.index_title = "Boshqaruv paneli"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("core.urls")),
    path("api/zakovat/", include("zakovat.urls")),
    path("api/kitob/", include("kitobxonlik.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Serverda ochiq media (kitob muqovalari) Django orqali beriladi — hajmi kichik.
    # PDF kitoblar va izoh fayllari bu yerda emas: ular faqat API orqali, kirgan xodimga.
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
