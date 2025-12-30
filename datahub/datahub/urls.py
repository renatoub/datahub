from core.views import alterar_status_view, criar_subatividade_view, dashboard_view
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

urlpatterns = [
    # Coloque as ações ANTES do admin ou com um nome bem específico
    path(
        "acoes/status/<int:pk>/<int:situacao_id>/",
        alterar_status_view,
        name="alterar_status",
    ),
    path(
        "acoes/nova-sub/<int:pk>/", criar_subatividade_view, name="criar_subatividade"
    ),
    path("admin/", admin.site.urls),
    path("", dashboard_view, name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
