from django import forms
from .models import Contrato

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['nombre', 'cliente', 'tipo', 'archivo_pdf']
        # Controlamos el tipo de campo
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del contrato'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'archivo_pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
