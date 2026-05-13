from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('urls/', views.url_list, name='url_list'),
    path('urls/agregar/', views.url_add, name='url_add'),
    path('urls/<int:pk>/editar/', views.url_edit, name='url_edit'),
    path('urls/<int:pk>/eliminar/', views.url_delete, name='url_delete'),
    path('urls/<int:pk>/verificar/', views.url_check, name='url_check'),
    path('urls/verificar-todas/', views.url_check_all, name='url_check_all'),
    path('urls/<int:pk>/verificar-ajax/', views.url_check_ajax, name='url_check_ajax'),
    path('urls/<int:pk>/detalle/', views.url_detail, name='url_detail'),
    path('urls/<int:pk>/analizar/', views.url_analyze, name='url_analyze'),
    path('logs/', views.log_list, name='log_list'),
    path('errores/', views.error_list, name='error_list'),
    path('config/verificacion/', views.config_schedule, name='config_schedule'),
    path('config/telegram/', views.config_telegram, name='config_telegram'),
    path('config/telegram/test/', views.telegram_test, name='telegram_test'),
    path('config/telegram/get-updates/', views.telegram_get_updates, name='telegram_get_updates'),
    path('config/usuarios/', views.config_users, name='config_users'),
    path('scheduler-status/', views.scheduler_status, name='scheduler_status'),
    path('urls/<int:pk>/toggle-publico/', views.url_toggle_public, name='url_toggle_public'),
    path('public/<uuid:token>/', views.url_public, name='url_public'),
]
