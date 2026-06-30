from django.urls import path
from . import views

urlpatterns = [
    path('create-user/', views.create_user_by_responsable, name='create_user'),
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/role/', views.change_user_role, name='change_user_role'),
    path('departments/', views.departments, name='departments'),

]
