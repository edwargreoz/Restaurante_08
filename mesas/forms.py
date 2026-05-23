from django import forms
from .models import Mesa

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'capacidad', 'zona', 'estado']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Ej. 1, 2, 3...'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '4', 'placeholder': 'Cantidad máxima de personas'}),
            'zona': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero is not None and numero <= 0:
            raise forms.ValidationError("El número de mesa debe ser mayor a 0.")
        return numero

    def clean(self):
        cleaned_data = super().clean()
        capacidad = cleaned_data.get('capacidad')
        zona = cleaned_data.get('zona')

        if capacidad is not None and zona is not None:
            if capacidad < 1:
                self.add_error('capacidad', 'La capacidad mínima es de 1 persona.')
            if zona == 'VIP' and capacidad > 2:
                self.add_error('capacidad', 'Las mesas VIP tienen una capacidad máxima de 2 personas.')
            elif capacidad > 4:
                self.add_error('capacidad', 'La capacidad máxima para cualquier mesa es de 4 personas.')
        
        return cleaned_data
