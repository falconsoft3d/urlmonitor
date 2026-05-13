from django import forms
from .models import MonitoredURL, SiteConfig

INPUT_CLASSES = (
    'w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'transition placeholder-gray-400'
)

SELECT_CLASSES = (
    'w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 bg-white '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition'
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


class ScheduleConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = ['auto_check_enabled', 'check_interval_minutes']
        labels = {
            'auto_check_enabled': 'Activar verificación automática',
            'check_interval_minutes': 'Intervalo de verificación',
        }
        widgets = {
            'check_interval_minutes': forms.Select(attrs={'class': SELECT_CLASSES}),
            'auto_check_enabled': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
        }


class TelegramConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = ['telegram_enabled', 'telegram_bot_token', 'telegram_chat_id']
        labels = {
            'telegram_enabled': 'Activar notificaciones Telegram',
            'telegram_bot_token': 'Token del Bot',
            'telegram_chat_id': 'ID del Grupo / Chat',
        }
        widgets = {
            'telegram_bot_token': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '123456789:ABCdefGhIJKlmNoPQRsTUVwxyz',
            }),
            'telegram_chat_id': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '-1001234567890',
            }),
            'telegram_enabled': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500',
            }),
        }
