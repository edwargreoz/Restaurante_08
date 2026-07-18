from django import forms
from dominio.entidades.mesa import Mesa


class MesaForm(forms.Form):
    numero = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': '1',
            'placeholder': 'Ej. 1, 2, 3...'
        })
    )
    capacidad = forms.IntegerField(
        min_value=1, max_value=4,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': '1', 'max': '4',
            'placeholder': 'Cantidad maxima de personas'
        })
    )
    zona = forms.ChoiceField(
        choices=[(z, z) for z in Mesa.ZONAS_VALIDAS],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    estado = forms.ChoiceField(
        choices=[(e, e) for e in Mesa.ESTADOS_VALIDOS],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, mesa_service=None, instance_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mesa_service = mesa_service
        self.instance_id = instance_id

    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero is not None and numero <= 0:
            raise forms.ValidationError("El numero de mesa debe ser mayor a 0.")
        if numero is not None and self.mesa_service:
            mesas = self.mesa_service.listar_activas()
            for m in mesas:
                if m.numero == numero and m.id != self.instance_id:
                    raise forms.ValidationError("Ya existe una mesa activa con este numero.")
        return numero

    def clean(self):
        cleaned_data = super().clean()
        capacidad = cleaned_data.get('capacidad')
        zona = cleaned_data.get('zona')

        if capacidad is not None and zona is not None:
            if capacidad < 1:
                self.add_error('capacidad', 'La capacidad minima es de 1 persona.')
            if zona == 'VIP' and capacidad > 2:
                self.add_error('capacidad', 'Las mesas VIP tienen una capacidad maxima de 2 personas.')
            elif capacidad > 4:
                self.add_error('capacidad', 'La capacidad maxima para cualquier mesa es de 4 personas.')

        return cleaned_data
