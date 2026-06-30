from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Departement


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'responsable', 'date_creation')
    search_fields = ('nom',)
    list_filter = ('date_creation',)