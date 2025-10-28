from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import IntegerField
from django.db.models.functions import Cast
from .models import (Perfil, Telefone, Usuario, MacroprocessoNivel1, MacroprocessoNivel2,
                     NormaProcedimento, ArquiteturaProcesso, LogAcoes,)

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


# -------------------- Admin de Normas de Procedimento --------------------
@admin.register(NormaProcedimento)
class NormaProcedimentoAdmin(admin.ModelAdmin):
    list_display = (
        "sequencial_formatado",
        "versao_formatada",
        "identificacao",
        "emitente",
        "sistema",
        "data_cadastro",
        "usuario",
    )
    list_display_links = ("identificacao",)
    ordering = ("sequencial", "versao", "nome", "codigo", "tema")
    list_per_page = 25
    date_hierarchy = "data_cadastro"

    list_filter = ("tema", "emitente", "sistema")
    search_fields = (
        "nome",
        "codigo",
        "tema",
        "emitente",
        "sistema",
        "=sequencial",
        "=versao",
        "uuid",
    )

    readonly_fields = (
        "uuid",
        "data_cadastro",
        "data_atualizacao",
        "usuario",
        "usuario_atualizacao",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("usuario", "usuario_atualizacao")
        return qs.annotate(
            sequencial_num=Cast("sequencial", IntegerField()),
            versao_num=Cast("versao", IntegerField()),
        )

    def sequencial_formatado(self, obj):
        try:
            return f"{int(obj.sequencial):03d}"
        except (ValueError, TypeError):
            return obj.sequencial or "-"
    sequencial_formatado.short_description = "Sequencial"
    sequencial_formatado.admin_order_field = "sequencial_num"

    def versao_formatada(self, obj):
        try:
            return f"{int(obj.versao):02d}"
        except (ValueError, TypeError):
            return obj.versao or "-"
    versao_formatada.short_description = "Versão"
    versao_formatada.admin_order_field = "versao_num"

    def identificacao(self, obj):
        return obj.identificacao_int
    identificacao.short_description = "Identificação"
    identificacao.admin_order_field = "nome"

    def save_model(self, request, obj, form, change):
        if not obj.usuario_id:
            obj.usuario = request.user
        obj.usuario_atualizacao = request.user
        super().save_model(request, obj, form, change)


# -------------------- Registro de Outros Modelos --------------------
admin.site.register(Perfil)
admin.site.register(Telefone)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(MacroprocessoNivel1)
admin.site.register(MacroprocessoNivel2)
admin.site.register(ArquiteturaProcesso)
admin.site.register(LogAcoes)
