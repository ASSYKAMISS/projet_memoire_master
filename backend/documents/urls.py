from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('documents/', views.document_list, name='document_list'),
    path('upload/', views.upload_document, name='upload_document'),
    path('<int:document_id>/', views.document_detail, name='document_detail'),
    path('verify/', views.verify_document, name='verify_document'),
    path('history/', views.operation_history, name='operation_history'),
    path('<int:document_id>/access/', views.document_access, name='document_access'),
    path('to-sign/',views.documents_to_sign,name='documents_to_sign'),
    
]
