from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    Perfil, Telefone, Usuario, Macroprocesso, Norma,
    Atualizacao_Norma, ArquiteturaProcesso, LogAtividade
)


class TelefoneInline(admin.TabularInline):
    model = Telefone
    extra = 1
    fields = ('ddd', 'numero', 'ramal')

class AtualizacaoNormaInline(admin.TabularInline):
    model = Atualizacao_Norma
    extra = 1
    fields = ('usuario', 'data_atualizacao', 'versao', 'descricao')

class UsuarioAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações funcionais', {
            'fields': ('setor', 'cargo', 'funcao', 'perfil')
        }),
    )
    inlines = [TelefoneInline]
    list_display = ('username', 'email', 'setor', 'cargo', 'funcao', 'mostrar_telefones')

    def mostrar_telefones(self, obj):
        telefones = obj.telefones.all()
        if not telefones:
            return "Nenhum telefone"
        return format_html("<br>".join([
            f"({t.ddd}) {t.numero} - Ramal: {t.ramal if t.ramal else 'N/A'}"
            for t in telefones
        ]))
    mostrar_telefones.short_description = "Telefones"

class NormaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario_cadastro', 'data_criacao')
    inlines = [AtualizacaoNormaInline]

# Registro dos modelos
admin.site.register(Perfil)
admin.site.register(Telefone)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Macroprocesso)
admin.site.register(Norma, NormaAdmin)
admin.site.register(Atualizacao_Norma)
admin.site.register(ArquiteturaProcesso)
admin.site.register(LogAtividade)
