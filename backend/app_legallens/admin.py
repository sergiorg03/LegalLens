from django.contrib import admin
from django.utils import timezone
from .models import Contrato
import json
from collections import Counter

class LegalLensAdminSite(admin.AdminSite):
    site_header = "LegalLens Administration - Socio Senior"
    site_title = "LegalLens Admin"
    index_title = "Dashboard de Estadísticas Globales"

    def index(self, request, extra_context=None):
        today = timezone.now().date()
        
        # 1. Contratos hoy
        hoy_conteo = Contrato.objects.filter(fecha_subida__date=today).count()
        
        # 2. Trampas más comunes
        all_contracts = Contrato.objects.exclude(resultado_ia__isnull=True).exclude(resultado_ia="")
        traps_counter = Counter()
        for contract in all_contracts:
            try:
                data = json.loads(contract.resultado_ia)
                banderas = data.get("banderas_rojas", [])
                for bandera in banderas:
                    traps_counter[bandera] += 1
            except:
                continue
        
        trampas_comunes = traps_counter.most_common(5)

        extra_context = extra_context or {}
        extra_context.update({
            'hoy_conteo': hoy_conteo,
            'trampas_comunes': trampas_comunes,
        })
        return super().index(request, extra_context)

admin_site = LegalLensAdminSite(name='legal_admin')

@admin.register(Contrato, site=admin_site)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('nombre_orig_pdf', 'cliente', 'tipo', 'fecha_subida', 'riesgo_display')
    list_filter = ('tipo', 'fecha_subida')
    search_fields = ('nombre_orig_pdf', 'cliente')

    def riesgo_display(self, obj):
        res = obj.get_resultado()
        return res.get("riesgo_total", "Desconocido")
    riesgo_display.short_description = "Riesgo IA"
