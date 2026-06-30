from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from documents import views as document_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', document_views.home, name='home'),
    path('documents/', include('documents.urls')),
    path('accounts/', include('accounts.urls')),
    path('blockchain/', include('blockchain_app.urls')),
    path('signatures/', include('signatures.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)