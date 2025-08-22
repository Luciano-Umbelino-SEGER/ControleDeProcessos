from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    Perfil, Telefone, Usuario, Macroprocesso, Norma,
    Atualizacao_Norma, ArquiteturaProcesso, LogAcoes
)


class TelefoneInline(admin.TabularInline):
    model = Telefone
    extra = 1
    fields = ('ddd', 'numero', 'ramal')

class AtualizacaoNormaInline(admin.TabularInline):
    model = Atualizacao_Norma
    extra = 1
    fields = ('usuario', 'data_atualizacao', 'versao', 'descricao')

from django.utils.html import format_html
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario


class UsuarioAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações funcionais', {
            'fields': ('setor', 'cargo', 'funcao', 'perfil', 'telefones')
        }),
    )

    readonly_fields = ('telefones',)  # só exibe, não edita
    list_display = ('username', 'email', 'setor', 'cargo', 'funcao', 'perfil', 'telefones')

    def telefones(self, obj):
        qs = obj.telefones.all()
        if not qs:
            return "Nenhum telefone cadastrado"
        return format_html("<br>".join([
            f"({t.ddd}) {t.numero} - Ramal: {t.ramal if t.ramal else 'N/A'}"
            for t in qs
        ]))
    telefones.short_description = "Telefones"



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
admin.site.register(LogAcoes)
