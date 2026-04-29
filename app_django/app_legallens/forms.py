from django import forms
from .models import Contrato

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['nombre', 'tipo', 'archivo_pdf']
        # Controlamos el tipo de campo
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del contrato'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'archivo_pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
