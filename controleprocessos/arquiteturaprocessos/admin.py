import re

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.utils.html import format_html
from django.db.models import IntegerField
from django.db.models.functions import Cast
from .models import (Perfil, Telefone, Usuario, MacroprocessoNivel1, MacroprocessoNivel2, ContatoAreaSeger)
from .forms import CPFUsuarioMixin, campo_cpf
from .utils.cpf import somente_digitos

# -------------------- Inline de Telefones --------------------
class TelefoneInline(admin.TabularInline):
    model = Telefone
    extra = 1
    fields = ('ddd', 'numero', 'ramal')


# -------------------- Formulário de edição do Usuário (Admin) --------------------
class UsuarioAdminChangeForm(CPFUsuarioMixin, UserChangeForm):
    """
    Formulário de edição do usuário no Django Admin.

    Reaproveita as regras de CPF da tela do SIGEMP (CPFUsuarioMixin):
    exibição formatada, normalização para 11 dígitos, dígitos verificadores
    e unicidade (desconsiderando o próprio usuário).

    Mesma regra da edição no SIGEMP: o CPF é obrigatório somente se o
    usuário já possui CPF. Um CPF cadastrado não pode ser apagado, mas
    pode ser corrigido por outro CPF válido e ainda não utilizado.
    """
    cpf = campo_cpf()

    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        possui_cpf = bool(self.instance and self.instance.pk and self.instance.cpf)
        self.configurar_campo_cpf(obrigatorio=possui_cpf)
        if possui_cpf:
            self.fields["cpf"].error_messages["required"] = (
                "O CPF já cadastrado não pode ser removido."
            )


def _fieldsets_com_cpf():
    """Inclui o CPF em "Informações pessoais", antes do e-mail."""
    fieldsets = []
    for nome, opcoes in BaseUserAdmin.fieldsets:
        campos = tuple(opcoes.get("fields", ()))
        if "email" in campos and "cpf" not in campos:
            posicao = campos.index("email")
            campos = campos[:posicao] + ("cpf",) + campos[posicao:]
            opcoes = {**opcoes, "fields": campos}
        fieldsets.append((nome, opcoes))
    return tuple(fieldsets)


# -------------------- Admin de Usuário --------------------
class UsuarioAdmin(BaseUserAdmin):
    inlines = [TelefoneInline]  # permite edição de telefones diretamente no admin

    form = UsuarioAdminChangeForm

    fieldsets = _fieldsets_com_cpf() + (
        ('Informações funcionais', {
            'fields': ('setor', 'cargo', 'funcao', 'perfil')
        }),
    )

    list_display = ('username', 'email', 'setor', 'cargo', 'funcao', 'perfil', 'telefones')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'cpf')
    list_filter = ('perfil', 'setor', 'cargo')

    def has_add_permission(self, request):
        """
        Criação de usuários desabilitada no Admin: a tela do SIGEMP é a
        única porta de entrada (CPF, perfil e username automático).
        """
        return False

    def get_readonly_fields(self, request, obj=None):
        """Username somente leitura: é a chave de acesso ao sistema."""
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None and "username" not in campos:
            campos.append("username")
        return campos

    def get_search_results(self, request, queryset, search_term):
        """
        Mantém as buscas existentes (username, nome, sobrenome, e-mail e CPF
        sem máscara) e permite buscar o CPF digitado com máscara
        (ex.: 600.182.917-91).
        """
        resultado, pode_duplicar = super().get_search_results(
            request, queryset, search_term
        )

        termo = (search_term or "").strip()
        digitos = somente_digitos(termo)

        if digitos and digitos != termo and re.fullmatch(r"[\d.\-\s]+", termo):
            resultado = resultado | queryset.filter(cpf__icontains=digitos)

        return resultado, pode_duplicar

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
