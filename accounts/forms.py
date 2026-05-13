from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth.models import User
from .models import UserProfile

INPUT_CLASSES = (
    'w-full border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2.5 '
    'text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'transition placeholder-gray-400 dark:placeholder-gray-500'
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'tu@correo.com',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Nombre de usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'tunombredeusuario',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Contraseña'
        self.fields['password1'].widget.attrs.update({
            'class': INPUT_CLASSES,
            'placeholder': '••••••••',
        })
        self.fields['password2'].label = 'Confirmar contraseña'
        self.fields['password2'].widget.attrs.update({
            'class': INPUT_CLASSES,
            'placeholder': '••••••••',
        })


class ProfileDataForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Tu nombre'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Tu apellido'}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'tu@correo.com'}),
        }


class AvatarForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('avatar',)
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': INPUT_CLASSES,
                'accept': 'image/*',
            }),
        }
        labels = {
            'avatar': 'Imagen de perfil',
        }


class UserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        required=False,
        label='Nueva contraseña',
        help_text='Deja en blanco para no cambiarla.',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Dejar en blanco para no cambiar',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'is_active', 'is_staff', 'is_superuser')
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'is_active': 'Cuenta activa',
            'is_staff': 'Staff (acceso al panel de admin)',
            'is_superuser': 'Superusuario (todos los permisos)',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'tu@correo.com'}),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
        }

class StyledPasswordChangeForm(DjangoPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Contraseña actual'
        self.fields['old_password'].widget.attrs.update({'class': INPUT_CLASSES, 'placeholder': '••••••••'})
        self.fields['new_password1'].label = 'Nueva contraseña'
        self.fields['new_password1'].widget.attrs.update({'class': INPUT_CLASSES, 'placeholder': '••••••••'})
        self.fields['new_password2'].label = 'Confirmar nueva contraseña'
        self.fields['new_password2'].widget.attrs.update({'class': INPUT_CLASSES, 'placeholder': '••••••••'})
