from django.contrib import admin
from .models import Sistema


@admin.register(Sistema)
class SistemaAdmin(admin.ModelAdmin):
    list_display = ("nome", "url", "rota", "ativo", "ordem")
    search_fields = ("nome",)
    list_filter = ("ativo",)
    ordering = ("ordem", "nome")