from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import IntegerField
from django.db.models.functions import Cast
from .models import (Perfil, Telefone, Usuario, MacroprocessoNivel1, MacroprocessoNivel2, ContatoAreaSeger)

# -------------------- Inline de Telefones --------------------
class TelefoneInline(admin.TabularInline):
    model = Telefone
    extra = 1
    fields = ('ddd', 'numero', 'ramal')


# -------------------- Admin de Usuário --------------------
class UsuarioAdmin(BaseUserAdmin):
    inlines = [TelefoneInline]  # permite edição de telefones diretamente no admin

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações funcionais', {
            'fields': ('setor', 'cargo', 'funcao', 'perfil')
        }),
    )

    list_display = ('username', 'email', 'setor', 'cargo', 'funcao', 'perfil', 'telefones')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('perfil', 'setor', 'cargo')

    def telefones(self, obj):
        qs = obj.telefones.all()
        if not qs:
            return "Nenhum telefone cadastrado"
        return format_html("<br>".join([
            f"({t.ddd}) {t.numero} - Ramal: {t.ramal if t.ramal else 'N/A'}"
            for t in qs
        ]))
    telefones.short_description = "Telefones"

@admin.register(ContatoAreaSeger)
class ContatoAreaSegerAdmin(admin.ModelAdmin):
    list_display = ("nome_area", "titular", "telefone", "email", "atualizado_em")
    search_fields = ("nome_area", "titular", "email")
    list_filter = ("atualizado_em",)
    ordering = ("nome_area",)

# -------------------- Registro de Outros Modelos --------------------
admin.site.register(Perfil)
admin.site.register(Telefone)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(MacroprocessoNivel1)
admin.site.register(MacroprocessoNivel2)
