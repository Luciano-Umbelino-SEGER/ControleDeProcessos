from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    Perfil, Telefone, Usuario, MacroprocessoNivel1, MacroprocessoNivel2, NormaProcedimento,
    ArquiteturaProcesso, LogAcoes,
)


class TelefoneInline(admin.TabularInline):
    model = Telefone
    extra = 1
    fields = ('ddd', 'numero', 'ramal')

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

class NormaProcedimentoAdmin(admin.ModelAdmin):
    # Listagem
    list_display = (
        "identificacao",  # usa a propriedade derivada do model
        "emitente",
        "sistema",
        "data_cadastro",
        "usuario",
    )
    list_display_links = ("identificacao",)
    ordering = ("nome", "codigo", "sequencial", "versao", "tema")
    list_per_page = 25
    date_hierarchy = "data_cadastro"

    # Filtros e busca
    list_filter = ("tema", "emitente", "sistema")
    search_fields = ("nome", "codigo", "tema", "emitente", "sistema", "=sequencial", "=versao", "uuid")

    # Somente leitura (auditáveis)
    readonly_fields = ("uuid", "data_cadastro", "data_atualizacao", "usuario", "usuario_atualizacao")

    # Otimiza o carregamento dos FKs na lista
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("usuario", "usuario_atualizacao")

    # Auditoria automática: quem criou/atualizou
    def save_model(self, request, obj, form, change):
        if not change and obj.usuario_id is None:
            obj.usuario = request.user
        obj.usuario_atualizacao = request.user
        super().save_model(request, obj, form, change)

    # Coluna: Identificação amigável
    def identificacao(self, obj):
        return obj.identificacao_int
    identificacao.short_description = "Identificação"
    identificacao.admin_order_field = "nome"

# Registro dos modelos
admin.site.register(Perfil)
admin.site.register(Telefone)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(MacroprocessoNivel1)
admin.site.register(MacroprocessoNivel2)
admin.site.register(NormaProcedimento, NormaProcedimentoAdmin)
admin.site.register(ArquiteturaProcesso)
admin.site.register(LogAcoes)
