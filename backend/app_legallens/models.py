from django.db import models
import uuid
import json

# Create your models here.
def ruta_pdf(instance, filename):
    extension = filename.split(".")[-1]
    return f"archivos_pdf/archivo_{uuid.uuid4().hex}.{extension}"

class Contrato(models.Model):
    TIPO_CONTRATO = [
        ("ALQUILER", "Contrato de Alquiler"),
        ("NDA", "Acuerdo de Confidencialidad (NDA)"),
    ]

    nombre = models.CharField(max_length=255)
    cliente = models.CharField(max_length=255, default="Desconocido")
    tipo = models.CharField(max_length=20, choices=TIPO_CONTRATO, default="ALQUILER")
    fecha_subida = models.DateTimeField(auto_now_add=True)
    resultado_ia = models.TextField(blank=True, null=True)

    archivo_pdf = models.FileField(upload_to=ruta_pdf)
    nombre_orig_pdf = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nombre_orig_pdf

    def get_resultado(self):
        """Devuelve el JSON parseado de la IA como un diccionario."""
        try:
            return json.loads(self.resultado_ia)
        except (json.JSONDecodeError, TypeError):
            return {"motivo": "Sin procesar", "riesgo_total": "Bajo"}