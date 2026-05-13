from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

INPUT_CLASSES = (
    'w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'transition placeholder-gray-400'
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
