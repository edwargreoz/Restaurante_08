from django import forms
from django.contrib.auth.models import User, Group
from django.core.validators import RegexValidator
from django.utils.text import slugify

letras_validator = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    message='Este campo solo debe contener letras.'
)

class UsuarioForm(forms.ModelForm):
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
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Dejar en blanco para mantener la actual'}),
        required=False,
        label="Contraseña"
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
        label="Nombre de Usuario (Para iniciar sesión)"
    )
    email = forms.EmailField(
        required=False, 
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Correo Electrónico (Opcional)"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super(UsuarioForm, self).__init__(*args, **kwargs)
        # Si estamos editando y ya hay instancia
        if self.instance and self.instance.pk:
            self.fields['password'].help_text = "Déjalo en blanco si no deseas cambiar la contraseña."
            # Set initial rol
            if self.instance.is_superuser:
                self.fields['rol'].initial = 'Admin'
            else:
                grupo = self.instance.groups.first()
                if grupo:
                    self.fields['rol'].initial = grupo.name
        else:
            self.fields['password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Obligatoria para nuevos usuarios'

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        # Guardar nueva contraseña si se provee
        if password:
            user.set_password(password)
            
        rol = self.cleaned_data.get('rol')
        
        if rol == 'Admin':
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False
            
        if commit:
            user.save()
            # Actualizar grupos
            user.groups.clear()
            if rol != 'Admin':
                grupo, created = Group.objects.get_or_create(name=rol)
                user.groups.add(grupo)
                
        return user
