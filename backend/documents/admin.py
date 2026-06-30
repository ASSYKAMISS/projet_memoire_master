from django.contrib import admin
from .models import Document, Verification, PaquetPreuve

admin.site.register(Document)
admin.site.register(Verification)
admin.site.register(PaquetPreuve)