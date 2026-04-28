import logging
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from .forms import ContratoForm
from .models import Contrato
from .services import llamar_api_ia, guardar_resultado_ia, obtener_resultado_ia

logger = logging.getLogger(__name__)

def registro(request):
    """
        Vista para el registro de nuevos usuarios.
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)  # Auto-login tras registro
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    
    return render(request, "registro/registro.html", {"form": form})

@login_required
def dashboard(request):
    """
        Función que muestra el listado de todos los contratos.
        Retorna:
            - render: template dashboard.html con la lista de contratos
    """
    contratos = Contrato.objects.all().order_by("-fecha_subida")
    return render(request, "contratos/dashboard.html", {"contratos": contratos})


