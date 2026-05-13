from django import forms
from .models import MonitoredURL

INPUT_CLASSES = (
    'w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'transition placeholder-gray-400'
)


class MonitoredURLForm(forms.ModelForm):
    class Meta:
        model = MonitoredURL
        fields = ['name', 'url']
        labels = {
            'name': 'Nombre',
            'url': 'URL',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ej: Mi sitio web',
            }),
            'url': forms.URLInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'https://ejemplo.com',
            }),
        }
