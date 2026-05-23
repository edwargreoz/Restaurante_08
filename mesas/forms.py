from django import forms
from .models import Mesa

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'capacidad', 'zona', 'estado']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Ej. 1, 2, 3...'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad máxima de personas'}),
            'zona': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero is not None and numero <= 0:
            raise forms.ValidationError("El número de mesa debe ser mayor a 0.")
        return numero
