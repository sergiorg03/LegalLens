from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="login", permanent=False), name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("subir/", views.subir_contrato, name="subir_contrato"),
    path("contrato/<int:pk>/", views.info_contrato, name="info_contrato"),
    path("contrato/<int:pk>/descargar/", views.descargar_pdf, name="descargar_pdf"),
    path("registro/", views.registro, name="registro"),
]
