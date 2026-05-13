from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.profile_view, name='profile'),
    path('admin/usuarios/', views.user_list_view, name='user_list'),
    path('admin/usuarios/crear/<str:role>/', views.user_form_view, name='user_form'),
    path('admin/usuarios/<int:pk>/editar/', views.user_edit_view, name='user_edit'),
]
