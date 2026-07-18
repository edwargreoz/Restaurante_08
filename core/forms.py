from django import forms
from django.core.validators import RegexValidator


letras_validator = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    message='Este campo solo debe contener letras.'
)


class UsuarioForm(forms.Form):
    ROLES_CHOICES = [
        ('Mozo', 'Mozo'),
        ('Cocinero', 'Cocinero'),
        ('Cajero', 'Cajero'),
        ('Admin', 'Administrador'),
    ]

    rol = forms.ChoiceField(
        choices=ROLES_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Rol del Usuario"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar en blanco para mantener la actual'
        }),
        required=False,
        label="Contrasena"
    )
    first_name = forms.CharField(
        validators=[letras_validator],
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Nombres"
    )
    last_name = forms.CharField(
        validators=[letras_validator],
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Apellidos"
    )
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Nombre de Usuario (Para iniciar sesion)"
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Correo Electronico (Opcional)"
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Activo"
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario:
            self.fields['username'].initial = usuario.username
            self.fields['first_name'].initial = usuario.first_name
            self.fields['last_name'].initial = usuario.last_name
            self.fields['email'].initial = usuario.email
            self.fields['is_active'].initial = usuario.is_active
            if usuario.is_superuser:
                self.fields['rol'].initial = 'Admin'
            elif usuario.grupos:
                self.fields['rol'].initial = usuario.grupos[0]
            self.fields['password'].help_text = "Dejalo en blanco si no deseas cambiar la contrasena."
        else:
            self.fields['password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Obligatoria para nuevos usuarios'
