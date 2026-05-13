from django.contrib import admin
from .models import MonitoredURL, CheckLog


@admin.register(MonitoredURL)
class MonitoredURLAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'status', 'status_code', 'response_time', 'last_checked')
    list_filter = ('status',)
    search_fields = ('name', 'url')
    readonly_fields = ('last_checked', 'created_at', 'updated_at', 'status_code', 'response_time')


@admin.register(CheckLog)
class CheckLogAdmin(admin.ModelAdmin):
    list_display = ('monitored_url', 'checked_at', 'status', 'status_code', 'response_time', 'error')
    list_filter = ('status',)
    search_fields = ('monitored_url__name', 'monitored_url__url')
    readonly_fields = ('monitored_url', 'checked_at', 'status', 'status_code', 'response_time', 'error')
