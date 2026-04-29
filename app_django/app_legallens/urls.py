from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("subir/", views.subir_contrato, name="subir_contrato"),
    path("contrato/<int:pk>/", views.info_contrato, name="info_contrato"),
    path("contrato/<int:pk>/descargar/", views.descargar_pdf, name="descargar_pdf"),
    path("registro/", views.registro, name="registro"),
]