from django.contrib import admin
from .models import MonitoredURL


@admin.register(MonitoredURL)
class MonitoredURLAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'status', 'status_code', 'response_time', 'last_checked', 'user')
    list_filter = ('status', 'user')
    search_fields = ('name', 'url')
    readonly_fields = ('last_checked', 'created_at', 'updated_at', 'status_code', 'response_time')
