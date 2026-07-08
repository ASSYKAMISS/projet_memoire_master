from django.urls import path
from . import views

urlpatterns = [
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('create-user/', views.create_user_by_responsable, name='create_user'),
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/role/', views.change_user_role, name='change_user_role'),
    path('organisations/', views.organisations, name='organisations'),
    path('departments/', views.departments, name='departments'),
]