from django.urls import path
from . import views

urlpatterns = [
    path(
        '<int:document_id>/manual/',views.sign_manual, name='sign_manual'),
]