from django.urls import path
from . import views

urlpatterns = [
    path('audit/', views.blockchain_audit, name='blockchain_audit'),
    path('audit/<int:audit_id>/verify/', views.verify_blockchain_audit, name='verify_blockchain_audit'),
]