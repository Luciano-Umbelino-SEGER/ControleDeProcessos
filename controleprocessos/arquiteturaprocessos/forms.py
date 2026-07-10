import os
import re
from django import forms
from django.forms import inlineformset_factory
from django.forms.widgets import (FileInput, Select,)
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.encoding import iri_to_uri
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import date
from urllib.parse import (urlparse, unquote,)

from .models import (
    Usuario, Telefone, Classificacao, MacroprocessoNivel1, MacroprocessoNivel2,
    ModelagemProcesso, Processo, TiposDocumento, ProcessoMapear, ContatoAreaSeger,
    NormaProcedimento, SistemasUECI,
)
from django.db.models import Q

UserModel = get_user_model()

# ============================================================
# WidGet Customizado para Macro Engine
# ============================================================
class MacroSelect(forms.Select):

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):

        option = super().create_option(
            name, value, label, selected, index,
            subindex=subindex, attrs=attrs
        )

        if not value:
            return option

        # 🔥 Django 5: value é ModelChoiceIteratorValue
        try:
            real_value = value.value
        except AttributeError:
            real_value = value

        queryset = getattr(self.choices, "queryset", None)
        if not queryset:
            return option

        try:
            obj = queryset.get(pk=real_value)
        except queryset.model.DoesNotExist:
            return option

        # =========================
        # Macro N1
        # =========================
        if hasattr(obj, "classificacao_id"):
            option["attrs"]["data-classificacao"] = str(obj.classificacao_id)

        # =========================
        # Macro N2
        # =========================
        if hasattr(obj, "macroprocesso_nivel1_id"):
            option["attrs"]["data-macro1"] = str(obj.macroprocesso_nivel1_id)

            macro1 = obj.macroprocesso_nivel1
            option["attrs"]["data-classificacao"] = str(macro1.classificacao_id)

        return option

# ============================================================
# AUTENTICAÇÃO
# ============================================================
class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            try:
                user = UserModel.objects.get(username=username)

                if not user.check_password(password):
                    raise forms.ValidationError(
                        "LOGIN INVÁLIDO",
                        code='invalid_login',
                    )

                if not user.is_active:
                    raise forms.ValidationError(
                        "Usuário está com a conta inativa. Entre em contato com o administrador do sistema.",
                        code='inactive',
                    )

                self.user_cache = user

            except UserModel.DoesNotExist:
                raise forms.ValidationError(
                    "LOGIN INVÁLIDO",
                    code='invalid_login',
                )

        return self.cleaned_data


class EmailAuthenticationForm(AuthenticationForm):
    """
    Permite login por username ou email
    """
    username = forms.CharField(
        label=_("E-mail ou Username"),
        widget=forms.TextInput(attrs={"autofocus": True})
    )

    def clean(self):
        input_value = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if input_value and password:
            user = None
            try:
                user = UserModel.objects.get(username=input_value)
            except UserModel.DoesNotExist:
                try:
                    user = UserModel.objects.get(email=input_value)
                except UserModel.DoesNotExist:
                    user = None

            if user is not None and user.check_password(password):
                self.user_cache = user
            else:
                raise forms.ValidationError(_("Usuário ou senha inválidos."))
        return self.cleaned_data


# ============================================================
# FORMULÁRIO DE USUÁRIO (CRIAÇÃO) — versão estável (username editável)
# ============================================================
class Form_UsuarioForm(forms.ModelForm):
    """
    Formulário para criação de usuário (mantém username editável).
    Desabilita campos nos modos visualização/exclusão.
    """
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'placeholder': 'E-mail'}))

    class Meta:
        model = Usuario
        fields = (
            "username", "first_name", "last_name", "email",
            "setor", "cargo", "funcao", "perfil",
        )

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)

        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500  "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        autocomplete_map = {
            "username": "username",
            "first_name": "given-name",
            "last_name": "family-name",
            "email": "email",
        }

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()

            input_type = getattr(field.widget, "input_type", "")
            if input_type in {"text", "email", "password"}:
                field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = autocomplete_map.get(name, "off")

        # Ajustes para selects / choice fields
        for name in ["setor", "cargo", "funcao", "perfil"]:
            f = self.fields.get(name)
            if isinstance(f, forms.ModelChoiceField):
                f.empty_label = "Selecione..."
            elif isinstance(f, forms.ChoiceField):
                choices = list(f.choices)
                if not choices or choices[0][0] != "":
                    f.choices = [("", "Selecione...")] + choices

        # Desabilitar campos em modo visualização/exclusão
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        # Se for exclusão, marca desativado e seta data
        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()


# ============================================================
# EDITAR USUÁRIO (mantém username editável)
# ============================================================
class EditarUsuarioForm(forms.ModelForm):
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'placeholder': 'E-mail'}))

    class Meta:
        model = Usuario
        fields = (
            "username", "first_name", "last_name", "email",
            "setor", "cargo", "funcao", "perfil",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 bg-white "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        autocomplete_map = {
            "username": "username",
            "first_name": "given-name",
            "last_name": "family-name",
            "email": "email",
        }

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " " + base).strip()
            input_type = getattr(field.widget, "input_type", "")
            if input_type in {"text", "email"}:
                field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = autocomplete_map.get(name, "off")

        for name in ["setor", "cargo", "funcao", "perfil"]:
            f = self.fields.get(name)
            if isinstance(f, forms.ModelChoiceField):
                f.empty_label = "Selecione..."
            elif isinstance(f, forms.ChoiceField):
                choices = list(f.choices)
                if not choices or choices[0][0] != "":
                    f.choices = [("", "Selecione...")] + choices

# ============================================================
# TELEFONE + FORMSET
# ============================================================
class TelefoneForm(forms.ModelForm):
    class Meta:
        model = Telefone
        fields = ("ddd", "numero", "ramal")

        widgets = {
            "ddd": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 h-9 text-black",
                "placeholder": "DDD",
                "maxlength": "3",
            }),
            "numero": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 h-9 text-black",
                "placeholder": "Número",
                "maxlength": "9",
            }),
            "ramal": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 h-9 text-black",
                "placeholder": "Ramal",
                "maxlength": "5",
            }),
        }

TelefoneFormSet = inlineformset_factory(
    Usuario,
    Telefone,
    form=TelefoneForm,
    extra=1,
    can_delete=True
)

# ============================================================
# CLASSIFICAÇÃO / MACROPROCESSOS / MODELAGEM / PROCESSO
# (mantive exatamente como na versão estável)
# ============================================================
class Form_ClassificacaoForm(forms.ModelForm):
    class Meta:
        model = Classificacao
        fields = ['nome', 'descricao']

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        modo_edicao = kwargs.pop('modo_edicao', False)

        super().__init__(*args, **kwargs)
        if "descricao" in self.fields:
            self.fields["descricao"].max_length = 3000
            self.fields["descricao"].widget.attrs["maxlength"] = 3000
            self.fields["descricao"].widget.attrs["rows"] = 4

        self.label_suffix = ""
        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()

# ============================================================
# MACROPROCESSO NIVEL 1
# ============================================================
class Form_MacroProcessoNivel1Form(forms.ModelForm):
    class Meta:
        model = MacroprocessoNivel1
        fields = ['nome', 'descricao', 'classificacao']

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        modo_edicao = kwargs.pop('modo_edicao', False)

        super().__init__(*args, **kwargs)
        if "descricao" in self.fields:
            self.fields["descricao"].max_length = 3000
            self.fields["descricao"].widget.attrs["maxlength"] = 3000
            self.fields["descricao"].widget.attrs["rows"] = 4

        self.label_suffix = ""
        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()

# ============================================================
# MACROPROCESSO NIVEL 2
# ============================================================
class Form_MacroProcessoNivel2Form(forms.ModelForm):
    classificacao = forms.ModelChoiceField(
        queryset=Classificacao.objects.all(),
        required=False,
        label="Classificação",
        widget=forms.Select(attrs={"id": "id_classificacao"})
    )

    class Meta:
        model = MacroprocessoNivel2
        fields = ["classificacao", "macroprocesso_nivel1", "nome", "descricao"]

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        modo_exclusao     = kwargs.pop("modo_exclusao", False)
        modo_edicao       = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)
        if "descricao" in self.fields:
            self.fields["descricao"].max_length = 3000
            self.fields["descricao"].widget.attrs["maxlength"] = 3000
            self.fields["descricao"].widget.attrs["rows"] = 4

        self.label_suffix = ""
        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        self.fields["macroprocesso_nivel1"].label_from_instance = lambda obj: obj.nome
        self.fields["macroprocesso_nivel1"].widget.attrs.update({
            "id": "id_macroprocesso_nivel1"
        })
        self.fields["descricao"].widget.attrs["class"] += " h-32"

        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        if modo_exclusao and self.instance:
            if hasattr(self.instance, "is_active"):
                self.instance.is_active = False
            if hasattr(self.instance, "data_ativacaodesativacao"):
                self.instance.data_ativacaodesativacao = timezone.now()

        # Filtra macroprocesso_nivel1 quando classificação é informada no request
        if "classificacao" in self.data:
            try:
                classificacao_id = int(self.data.get("classificacao") or 0)
                if classificacao_id:
                    self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.filter(
                        classificacao_id=classificacao_id
                    )
                else:
                    self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.all()
            except (ValueError, TypeError):
                self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.all()
        else:
            self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.all()

        # Se Macro N1 vier no request, preenche a classificação correspondente
        if "macroprocesso_nivel1" in self.data:
            try:
                macro_id = int(self.data.get("macroprocesso_nivel1") or 0)
                if macro_id:
                    macro = MacroprocessoNivel1.objects.get(id=macro_id)
                    self.fields["classificacao"].initial = macro.classificacao
            except (ValueError, MacroprocessoNivel1.DoesNotExist):
                pass
        elif self.instance and getattr(self.instance, "pk", None):
            if getattr(self.instance, "macroprocesso_nivel1", None):
                self.fields["classificacao"].initial = self.instance.macroprocesso_nivel1.classificacao

        # Garantia final de ids/names
        for name, field in self.fields.items():
            existing_id = field.widget.attrs.get("id")
            if not existing_id:
                field.widget.attrs["id"] = f"id_{name}"
            field.widget.attrs.setdefault("name", name)

# Aqui 1
# ============================================================
# Form_Sistema_UECIForm
# ============================================================
class Form_Sistema_UECIForm(forms.ModelForm):
    class Meta:
        model = SistemasUECI

        fields = [
            'sigla_sistema',
            'nome_sistema',
            'descricao',
        ]

        widgets = {
            'descricao': forms.Textarea(
                attrs={
                    'rows': 4,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        modo_visualizacao = kwargs.pop(
            'modo_visualizacao',
            False
        )

        modo_exclusao = kwargs.pop(
            'modo_exclusao',
            False
        )

        super().__init__(*args, **kwargs)

        # ====================================================
        # CONFIGURAÇÕES DOS CAMPOS
        # ====================================================

        self.fields['sigla_sistema'].widget.attrs.update({
            'maxlength': 10,
            'placeholder': 'Ex.: SIGEMP'
        })

        self.fields['nome_sistema'].widget.attrs.update({
            'maxlength': 200,
            'placeholder': 'Nome do Sistema'
        })

        self.fields['descricao'].widget.attrs.update({
            'maxlength': 3000,
            'placeholder': 'Descrição'
        })

        # ====================================================
        # CSS PADRÃO
        # ====================================================

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 focus:outline-none "
            "focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():

            field.widget.attrs.setdefault(
                'class',
                base + (
                    ' bg-gray-100'
                    if (
                        modo_visualizacao
                        or modo_exclusao
                    )
                    else
                    ' bg-white'
                )
            )

            # ================================================
            # SIGLA EM CAIXA ALTA
            # ================================================

            if name == 'sigla_sistema':
                field.widget.attrs.setdefault(
                    'style',
                    'text-transform: uppercase;'
                )

                field.widget.attrs['oninput'] = (
                    'this.value = this.value.toUpperCase();'
                )

        # ====================================================
        # VISUALIZAÇÃO / EXCLUSÃO
        # ====================================================

        if modo_visualizacao or modo_exclusao:

            for field in self.fields.values():

                field.disabled = True

    # ========================================================
    # NOME DO SISTEMA
    # ========================================================

    def clean_nome_sistema(self):

        nome = self.cleaned_data.get(
            'nome_sistema'
        )

        if nome:
            nome = " ".join(nome.split())

        return nome

    # ========================================================
    # DESCRIÇÃO
    # ========================================================

    def clean_descricao(self):

        descricao = self.cleaned_data.get(
            'descricao'
        )

        if descricao:
            descricao = descricao.strip()

        return descricao

# ============================================================
# TIPOS DE DOCUMENTO
# ============================================================
class Form_TipoDocumentoForm(forms.ModelForm):
    class Meta:
        model = TiposDocumento
        fields = ['nome', 'descricao']

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        super().__init__(*args, **kwargs)
        if "descricao" in self.fields:
            self.fields["descricao"].max_length = 3000
            self.fields["descricao"].widget.attrs["maxlength"] = 3000
            self.fields["descricao"].widget.attrs["rows"] = 4

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 focus:outline-none "
            "focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                'class',
                base + (' bg-gray-100' if (modo_visualizacao or modo_exclusao) else ' bg-white')
            )
            field.widget.attrs.setdefault('placeholder', field.label)

            # 🔠 Forçar digitação em CAIXA ALTA no campo nome
            if name == 'nome':
                field.widget.attrs.setdefault(
                    'style',
                    'text-transform: uppercase;'
                )
                field.widget.attrs['oninput'] = 'this.value = this.value.toUpperCase();'

        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

    # 🔒 REGRA DE DOMÍNIO: Nome sempre em CAIXA ALTA
    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            nome = nome.strip().upper()
        return nome

# ============================================================
# FORM NORMA DE PROCEDIMENTO
# ============================================================
class Form_NormaProcedimentoForm(forms.ModelForm):

    # ========================================================
    # META
    # ========================================================
    class Meta:

        model = NormaProcedimento

        exclude = (
            "data_cadastro",
            "usuario_cadastro",
            "data_atualizacao",
            "usuario_atualizacao",
        )

    # ========================================================
    # INIT
    # ========================================================
    def __init__(self, *args, **kwargs):

        self.modo_inclusao = kwargs.pop(
            "modo_inclusao",
            False
        )

        self.modo_visualizacao = kwargs.pop(
            "modo_visualizacao",
            False
        )

        self.modo_exclusao = kwargs.pop(
            "modo_exclusao",
            False
        )

        self.modo_edicao = kwargs.pop(
            "modo_edicao",
            False
        )

        super().__init__(*args, **kwargs)

        self.label_suffix = ""

        # ====================================================
        # CLASSE PADRÃO
        # ====================================================
        base_class = (
            "w-full h-[42px] "
            "border border-gray-300 rounded-md "
            "px-3 py-2 "
            "text-black "
            "placeholder-gray-400 "
            "focus:outline-none "
            "focus:ring-2 "
            "focus:ring-blue-500"
        )

        bg = (
            "bg-gray-100"
            if (
                self.modo_visualizacao
                or self.modo_exclusao
            )
            else "bg-white"
        )

        # ====================================================
        # CAMPOS TEXTO
        # ====================================================
        campos = [
            "nome_norma",
            "sistema",
            "codigo_norma",
            "versao",
            "emitente",
            "portaria_aprovacao",
        ]

        for campo in campos:

            if campo not in self.fields:
                continue

            self.fields[campo].widget.attrs.update({
                "class": f"{base_class} {bg}",
                "autocomplete": "off",
            })

        # ====================================================
        # CAMPOS DATA
        # ====================================================
        campos_data = [
            "data_elaboracao",
            "data_aprovacao",
            "vigencia_inicio",
            "vigencia_fim",
        ]

        for campo in campos_data:

            if campo not in self.fields:
                continue

            self.fields[campo].widget = forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": f"{base_class} {bg}",
                }
            )

        # ====================================================
        # SISTEMA
        # ====================================================
        self.fields["sistema"].queryset = (
            SistemasUECI.objects.order_by("nome_sistema")
        )

        self.fields["sistema"].empty_label = "Selecione..."

        self.fields["sistema"].widget.attrs.update({
            "class": f"{base_class} {bg}",
        })

        # ====================================================
        # NORMA
        # ====================================================
        self.fields["nome_norma"].widget.attrs.update({
            "placeholder": "Digite o nome da Norma...",
        })

        self.fields["nome_norma"].label = "Norma"

        # ====================================================
        # EMITENTE
        # ====================================================
        self.fields["emitente"].widget.attrs.update({
            "placeholder": "Emitente",
        })

        # ====================================================
        # PORTARIA
        # ====================================================
        self.fields["portaria_aprovacao"].widget.attrs.update({
            "placeholder": "Portaria",
        })

        # ====================================================
        # NR NORMA
        # ====================================================
        self.fields["codigo_norma"].widget.attrs.update({
            "placeholder": "Digite o Código da Norma",
            "maxlength": "15",
        })

        self.fields["codigo_norma"].label = "Código"

        # ====================================================
        # VERSÃO
        # ====================================================
        self.fields["versao"].widget.attrs.update({
            "placeholder": "0001",
            "maxlength": "4",
        })

        # ====================================================
        # LINK EXTERNO
        # ====================================================
        if "link_documento_norma" in self.fields:

            self.fields[
                "link_documento_norma"
            ].widget.attrs.update({

                "type": "text",

                "placeholder":
                    "https://exemplo.com/documento.pdf",

                "autocomplete": "off",

                "class": (
                    f"w-full h-[42px] "
                    f"border border-gray-300 rounded-md "
                    f"px-3 py-2 "
                    f"text-black "
                    f"{bg} "
                    f"focus:outline-none "
                    f"focus:ring-2 "
                    f"focus:ring-blue-500"
                ),
            })

        # ====================================================
        # URL LIMPA
        # ====================================================
        if (
            self.instance
            and self.instance.link_documento_norma
        ):

            self.initial[
                "link_documento_norma"
            ] = unquote(
                self.instance.link_documento_norma
            )

        # ====================================================
        # PDF
        # ====================================================
        if "documento_norma_procedimento" in self.fields:

            fwidget = self.fields[
                "documento_norma_procedimento"
            ].widget

            fwidget.attrs.setdefault(
                "tabindex",
                "0"
            )

            fwidget.attrs.setdefault(
                "accept",
                ".pdf,application/pdf"
            )

            if (self.modo_inclusao
                or self.modo_edicao):

                self.fields[
                    "documento_norma_procedimento"
                ].widget = FileInput(
                    attrs=fwidget.attrs
                )

                if (
                        self.instance
                        and self.instance.documento_norma_procedimento
                ):
                    nome_arq = os.path.basename(
                        self.instance
                        .documento_norma_procedimento.name
                    )

                    self.fields[
                        "documento_norma_procedimento"
                    ].widget.attrs[
                        "placeholder"
                    ] = nome_arq

        # ====================================================
        # REMOVE FILE INPUT
        # ====================================================
        if (
                self.modo_visualizacao
                or self.modo_exclusao
        ):
            self.fields.pop(
                "documento_norma_procedimento",
                None
            )

        # ====================================================
        # SOMENTE LEITURA
        # ====================================================
        if (
            self.modo_visualizacao
            or self.modo_exclusao
        ):

            for field in self.fields.values():

                field.disabled = True

                field.widget.attrs["class"] = (
                    field.widget.attrs.get(
                        "class",
                        ""
                    )
                    + " bg-gray-100"
                )

    def clean_nome_norma(self):

        nome = (
                self.cleaned_data.get("nome_norma") or ""
        ).strip()

        if not nome:
            raise ValidationError(
                "Informe o Nome da Norma."
            )

        return nome

    def clean_codigo_norma(self):

        codigo = (
                self.cleaned_data.get("codigo_norma") or ""
        ).strip()

        if not codigo:
            raise ValidationError(
                "Informe o Código."
            )

        return codigo

    def clean_versao(self):

        versao = (
                self.cleaned_data.get(
                    "versao"
                ) or ""
        ).strip()

        if not versao.isdigit():
            raise ValidationError(
                "Informe apenas números."
            )

        versao = versao.zfill(4)

        if versao == "0000":
            raise ValidationError(
                "A versão deve ser maior que 0000."
            )

        return versao

    def clean_data_elaboracao(self):

        data = self.cleaned_data.get(
            "data_elaboracao"
        )

        if not data:
            raise ValidationError(
                "Informe a Data de Elaboração."
            )

        return data

    def clean_documento_norma_procedimento(self):

        f = self.cleaned_data.get(
            "documento_norma_procedimento"
        )

        if not f:
            return f

        if not hasattr(f, "content_type"):
            return f

        content_type = f.content_type

        file_name = f.name.lower()

        is_pdf_type = content_type in (
            "application/pdf",
            "application/x-pdf",
        )

        is_pdf_name = file_name.endswith(".pdf")

        if not (
                is_pdf_type
                or is_pdf_name
        ):
            raise ValidationError(
                "Envie um PDF válido (.pdf)."
            )

        if hasattr(f, "read"):

            header = f.read(4)

            f.seek(0)

            if header != b"%PDF":
                raise ValidationError(
                    "Arquivo não é um PDF válido."
                )

        return f

    def clean_link_documento_norma(self):

        link = self.cleaned_data.get(
            "link_documento_norma"
        )

        if not link:
            return link

        link = link.strip()

        link = iri_to_uri(link)

        parsed = urlparse(link)

        if (
                not parsed.scheme
                or not parsed.netloc
        ):
            raise ValidationError(
                "Informe uma URL válida."
            )

        if parsed.scheme not in (
                "http",
                "https"
        ):
            raise ValidationError(
                "A URL deve começar com http:// ou https://."
            )

        return link

    def clean(self):

        cleaned_data = super().clean()

        # ============================================
        # NOVO PDF ENVIADO
        # ============================================
        pdf = self.files.get(
            "documento_norma_procedimento"
        )

        link = (
                cleaned_data.get(
                    "link_documento_norma"
                ) or ""
        ).strip()

        # ============================================
        # PDF EXISTENTE
        # ============================================
        remover_pdf = (
                self.data.get(
                    "remover_documento_norma_procedimento"
                ) == "1"
        )

        tem_pdf = (
                bool(pdf)
                or (
                        self.instance.pk
                        and self.instance.documento_norma_procedimento
                        and not remover_pdf
                )
        )

        # ============================================
        # LINK EXISTENTE
        # ============================================
        tem_link = bool(link)

        # ============================================
        # VALIDAÇÃO
        # ============================================
        if not tem_pdf and not tem_link:
            raise ValidationError(
                "Informe pelo menos um Documento PDF ou um Link do Documento."
            )

        data_elaboracao = cleaned_data.get(
            "data_elaboracao"
        )


        data_aprovacao = cleaned_data.get(
            "data_aprovacao"
        )

        if (
                data_elaboracao
                and data_aprovacao
                and data_aprovacao < data_elaboracao
        ):
            raise ValidationError(
                "A Data de Aprovação não pode ser anterior à Data de Elaboração."
            )



        inicio = cleaned_data.get(
            "vigencia_inicio"
        )

        fim = cleaned_data.get(
            "vigencia_fim"
        )

        if (
                inicio
                and fim
                and fim < inicio
        ):
            raise ValidationError(
                "A Vigência Final não pode ser menor que a Vigência Inicial."
            )

        return cleaned_data

    # ========================================================
    # SAVE
    # ========================================================
    def save(self, commit=True):

        obj = super().save(commit=False)

        if commit:
            obj.save()

        return obj

# ============================================================
# Modelagem de Processos
# ============================================================
class Form_ModelagemProcessoForm(forms.ModelForm):

    # ============================================================
    # 🔹 CAMPO: TÍTULO
    # ============================================================
    titulo = forms.CharField(
        required=True,
        label="Título",
        widget=forms.TextInput(attrs={
            "class": "w-full border border-gray-300 rounded px-3 py-2 text-black "
                     "focus:ring-2 focus:ring-blue-500 focus:outline-none uppercase",
            "placeholder": "Digite o título",
            "autocomplete": "off",
        })
    )

    # ============================================================
    # 🔹 CAMPO: TIPO DE DOCUMENTO
    # ============================================================
    tipo_documento = forms.ModelChoiceField(
        queryset=TiposDocumento.objects.all().order_by("nome"),
        required=True,
        label="Tipo de Documento",
        widget=forms.Select(attrs={
            "class": "w-full border border-gray-300 rounded px-3 py-2 text-black "
                     "focus:ring-2 focus:ring-blue-500 focus:outline-none",
        })
    )

    # ============================================================
    # META
    # ============================================================
    class Meta:
        model = ModelagemProcesso

        exclude = (
            "usuario",
            "data_cadastro",
            "data_atualizacao",
            "usuario_atualizacao",
        )

        widgets = {
            "data_elaboracao": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),

            "data_aprovacao": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),

            "vigencia_inicio": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),

            "vigencia_fim": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),
        }

    # ============================================================
    # INIT
    # ============================================================
    def __init__(self, *args, **kwargs):

        self.usuario_logado = kwargs.pop("usuario_logado", None)

        self.modo_inclusao = kwargs.pop("modo_inclusao", False)
        self.modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        self.modo_exclusao = kwargs.pop("modo_exclusao", False)
        self.modo_edicao = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)

        self.label_suffix = ""
        self.fields["codigo"].label = "Sigla Sistema"

        # ========================================================
        # CAMPOS OPCIONAIS
        # ========================================================
        campos_opcionais = [
            "sistema",
            "codigo",
            "sequencial",
            "tema",
            "emitente",
            "versao",
            "data_elaboracao",
            "data_aprovacao",
            "portaria_aprovacao",
            "vigencia_inicio",
            "vigencia_fim",
            "link_normaprocedimento",
        ]

        for campo in campos_opcionais:
            if campo in self.fields:
                self.fields[campo].required = False

        # ========================================================
        # DATAS INICIAIS
        # ========================================================
        for fname in [
            "data_elaboracao",
            "data_aprovacao",
            "vigencia_inicio",
            "vigencia_fim",
        ]:
            try:
                valor = getattr(self.instance, fname)

                if valor:
                    self.fields[fname].initial = valor.strftime("%Y-%m-%d")

            except Exception:
                pass

        # ========================================================
        # CLASSE BASE
        # ========================================================
        base_class = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        # ========================================================
        # ESTILO GERAL
        # ========================================================
        for field in self.fields.values():

            existing = field.widget.attrs.get("class", "")

            bg = (
                "bg-gray-100"
                if (self.modo_visualizacao or self.modo_exclusao)
                else "bg-white"
            )

            field.widget.attrs["class"] = (
                f"{existing} {base_class} {bg}"
            ).strip()

            field.widget.attrs.setdefault(
                "placeholder",
                field.label
            )

            field.widget.attrs.update({
                "autocomplete": "off",
                "data-lpignore": "true",
                "autocorrect": "off",
                "autocapitalize": "off",
                "spellcheck": "false",
            })

        # ========================================================
        # AJUSTES ESPECÍFICOS
        # ========================================================
        self.fields["codigo"].widget.attrs["class"] += " uppercase"

        self.fields["sequencial"].widget.attrs.update({
            "inputmode": "numeric",
            "pattern": r"\d{1,4}",
            "maxlength": "4",
        })

        self.fields["versao"].widget.attrs.update({
            "inputmode": "numeric",
            "pattern": r"\d{1,4}",
            "maxlength": "4",
        })

        # ========================================================
        # PDF WIDGET
        # ========================================================
        if "documento_modelagem_processo" in self.fields:

            fwidget = self.fields["documento_modelagem_processo"].widget

            fwidget.attrs.setdefault("tabindex", "0")

            fwidget.attrs.setdefault(
                "accept",
                ".pdf,application/pdf"
            )

            if (
                self.modo_edicao
                or self.modo_visualizacao
                or self.modo_exclusao
            ):

                self.fields["documento_modelagem_processo"].widget = (
                    FileInput(attrs=fwidget.attrs)
                )

                if (
                    self.instance
                    and self.instance.documento_modelagem_processo
                ):
                    nome_arq = os.path.basename(
                        self.instance.documento_modelagem_processo.name
                    )

                    self.fields[
                        "documento_modelagem_processo"
                    ].widget.attrs["placeholder"] = nome_arq

        # ========================================================
        # ZEROS À ESQUERDA
        # ========================================================
        if self.instance and self.instance.pk:

            if self.instance.sequencial is not None:
                self.initial["sequencial"] = (
                    f"{int(self.instance.sequencial):04d}"
                )

            if self.instance.versao is not None:
                self.initial["versao"] = (
                    f"{int(self.instance.versao):02d}"
                )

        # ========================================================
        # USUÁRIO
        # ========================================================
        if self.usuario_logado and not self.instance.pk:
            self.instance.usuario = self.usuario_logado

        if self.usuario_logado and self.instance.pk:
            self.instance.usuario_atualizacao = self.usuario_logado

        # ========================================================
        # MODO SOMENTE LEITURA
        # ========================================================
        if self.modo_visualizacao or self.modo_exclusao:

            for field in self.fields.values():

                field.disabled = True

                field.widget.attrs["class"] += " bg-gray-100"

        # ========================================================
        # GUARDA VERSÃO ORIGINAL
        # ========================================================
        self._versao_original = (
            getattr(self.instance, "versao", None)
            if self.instance.pk
            else None
        )

        # ========================================================
        # LINK NORMA
        # ========================================================
        if "link_normaprocedimento" in self.fields:

            self.fields[
                "link_normaprocedimento"
            ].widget.attrs.update({
                "type": "url",
                "placeholder": "https://exemplo.com/documento.pdf",
            })

            self.fields[
                "link_normaprocedimento"
            ].widget.attrs["class"] += " w-full"

    # ============================================================
    # 🔹 TIPO DOCUMENTO
    # ============================================================
    def _is_norma_procedimento(self):

        tipo = self.cleaned_data.get("tipo_documento")

        if not tipo:
            return False

        nome = (tipo.nome or "").strip().upper()

        return nome == "NORMA DE PROCEDIMENTO"

    # ============================================================
    # VALIDAÇÕES
    # ============================================================
    def clean_titulo(self):

        titulo = (
            self.cleaned_data.get("titulo") or ""
        ).strip().upper()

        if not titulo:
            raise ValidationError("Informe o Título.")

        return titulo

    def clean_sistema(self):

        sistema = (
            self.cleaned_data.get("sistema") or ""
        ).strip().upper()

        if self._is_norma_procedimento() and not sistema:
            raise ValidationError("Informe o sistema.")

        return sistema or None

    def clean_codigo(self):

        codigo = (
            self.cleaned_data.get("codigo") or ""
        ).strip().upper()

        # Sigla do Sistema → obrigatório
        if self._is_norma_procedimento():

            if not codigo:
                raise ValidationError(
                    "Informe a sigla do sistema."
                )

        # Modelo → opcional
        else:

            if not codigo:
                return None

        if not re.fullmatch(r"[A-Z0-9._/-]{2,20}", codigo):
            raise ValidationError(
                "Sigla do Sistema inválida. Use 2 a 20 caracteres "
                "(A–Z, 0–9, ponto, hífen, barra ou sublinhado)."
            )

        return codigo

    def clean_sequencial(self):

        seq = self.cleaned_data.get("sequencial")

        if not seq:
            return None

        seq = str(seq).strip()

        if not seq.isdigit():
            raise ValidationError(
                "O número sequencial deve conter apenas dígitos."
            )

        num = int(seq)

        if not (1 <= num <= 9999):
            raise ValidationError(
                "O número sequencial deve estar entre 1 e 9999."
            )

        return str(num)

    def clean_tema(self):

        tema = (
                self.cleaned_data.get("tema") or ""
        ).strip()

        if self._is_norma_procedimento() and not tema:
            raise ValidationError("Informe o tema.")

        return tema or None

    def clean_emitente(self):

        emitente = (
            self.cleaned_data.get("emitente") or ""
        ).strip().upper()

        if self._is_norma_procedimento() and not emitente:
            raise ValidationError("Informe o emitente.")

        return emitente or None

    def clean_versao(self):

        ver = self.cleaned_data.get("versao")

        # Norma → obrigatório
        if self._is_norma_procedimento():

            if ver is None:
                raise ValidationError("Informe a versão.")

        # Modelo → opcional
        else:

            if ver in (None, ""):
                return None

        try:
            ver = int(ver)

        except (TypeError, ValueError):
            raise ValidationError(
                "Versão deve ser um número inteiro."
            )

        if not (1 <= ver <= 9999):
            raise ValidationError(
                "A versão deve estar entre 1 e 9999."
            )

        if (
            self._versao_original is not None
            and ver < self._versao_original
        ):
            raise ValidationError(
                f"A versão não pode ser menor que "
                f"{self._versao_original}."
            )

        return ver

    def clean_documento_modelagem_processo(self):

        f = self.cleaned_data.get(
            "documento_modelagem_processo"
        )

        # mantém arquivo atual
        if not f:
            return f

        # edição sem novo upload
        if not hasattr(f, "content_type"):
            return f

        content_type = f.content_type
        file_name = f.name.lower()

        is_pdf_type = content_type in (
            "application/pdf",
            "application/x-pdf",
        )

        is_pdf_name = file_name.endswith(".pdf")

        if not (is_pdf_type or is_pdf_name):
            raise ValidationError(
                "Envie um PDF válido (.pdf)."
            )

        # valida assinatura
        if hasattr(f, "read"):

            header = f.read(4)

            f.seek(0)

            if header != b"%PDF":
                raise ValidationError(
                    "Arquivo não é um PDF válido."
                )

        return f

    # ============================================================
    # 🔹 LINK NORMA
    # ============================================================
    def clean_link_normaprocedimento(self):

        link = self.cleaned_data.get(
            "link_normaprocedimento"
        )

        if not link:
            return link

        link = link.strip()

        parsed = urlparse(link)

        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(
                "Informe uma URL válida."
            )

        if parsed.scheme not in ("http", "https"):
            raise ValidationError(
                "A URL deve começar com http:// ou https://."
            )

        return link

    # ============================================================
    # SAVE
    # ============================================================
    def save(self, commit=True):

        obj = super().save(commit=False)

        if self.usuario_logado and not obj.usuario_id:
            obj.usuario = self.usuario_logado

        if self.usuario_logado and obj.pk:
            obj.usuario_atualizacao = self.usuario_logado

        if commit:
            obj.save()

        return obj

# -------------------------------
# Widgets - Selects customizados
# -------------------------------
class MacroN1Select(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        if value:
            try:
                obj = MacroprocessoNivel1.objects.get(pk=value)
                option['attrs']['data-classificacao'] = str(obj.classificacao_id)
            except MacroprocessoNivel1.DoesNotExist:
                pass

        return option


class MacroN2Select(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        if value:
            try:
                obj = MacroprocessoNivel2.objects.select_related('macroprocesso_nivel1').get(pk=value)

                option['attrs']['data-classificacao'] = str(obj.macroprocesso_nivel1.classificacao_id)
                option['attrs']['data-macro1'] = str(obj.macroprocesso_nivel1_id)

            except MacroprocessoNivel2.DoesNotExist:
                pass

        return option

# ----------------------------
# Processos - Formulário
# ----------------------------
class Form_ProcessoForm(forms.ModelForm):

    classificacao = forms.ModelChoiceField(
        queryset=Classificacao.objects.all(),
        label="Classificação"
    )

    macroprocesso_nivel1 = forms.ModelChoiceField(
        queryset=MacroprocessoNivel1.objects.all(),
        label="Macroprocesso Nível 1",
        widget=MacroSelect()
    )

    macroprocesso_nivel2 = forms.ModelChoiceField(
        queryset=MacroprocessoNivel2.objects.all(),
        label="Macroprocesso Nível 2",
        required=False,
        widget=MacroSelect()
    )

    area_responsavel = forms.ModelChoiceField(
        queryset=ContatoAreaSeger.objects.filter(ativo=True).order_by("nome_area"),
        required=False,
        label="Área Responsável",
        empty_label="Selecione uma área"
    )

    modelagem_processo = forms.ModelChoiceField(
        queryset=ModelagemProcesso.objects.all(),
        required=False,
        label="Modelo de Processo"
    )

    norma_procedimento = forms.ModelChoiceField(
        queryset=ModelagemProcesso.objects.all(),
        required=False,
        label="Norma de Procedimento"
    )

    class Meta:
        model = Processo
        exclude = (
            "usuario_cadastro",
            "usuario_atualizacao",
            "data_criacao",
            "data_atualizacao",
        )

        widgets = {
            "objetivo": forms.Textarea(attrs={"rows": "2"}),
            "observacao": forms.Textarea(attrs={"rows": "2"}),
        }

    # ------------------------------------------------
    # INIT – estilo base, bloqueios por modo
    # ------------------------------------------------
    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        modo_exclusao = kwargs.pop("modo_exclusao", False)
        modo_edicao = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)

        # 🔑 GARANTIA DOS IDS PARA O TRIPLE FILTER (SEM QUEBRAR O LAYOUT)
        if "classificacao" in self.fields:
            self.fields["classificacao"].widget.attrs["id"] = "id_classificacao"

        if "macroprocesso_nivel1" in self.fields:
            self.fields["macroprocesso_nivel1"].widget.attrs["id"] = "id_macroprocesso_nivel1"

        if "macroprocesso_nivel2" in self.fields:
            self.fields["macroprocesso_nivel2"].widget.attrs["id"] = "id_macroprocesso_nivel2"


        if "objetivo" in self.fields:
            self.fields["objetivo"].max_length = 3000
            self.fields["objetivo"].widget.attrs["maxlength"] = 3000
            self.fields["objetivo"].widget.attrs["rows"] = 4

        if "observacao" in self.fields:
            self.fields["observacao"].max_length = 3000
            self.fields["observacao"].widget.attrs["maxlength"] = 3000
            self.fields["observacao"].widget.attrs["rows"] = 4

        # 🔥 SELECT2 + EDIÇÃO (CORREÇÃO PRINCIPAL)
        if self.instance and self.instance.pk:
            area = self.instance.area_responsavel

            if area:
                self.fields["area_responsavel"].queryset = (
                    ContatoAreaSeger.objects.filter(
                        Q(ativo=True) | Q(pk=area.pk)
                    ).order_by("nome_area")
                )

        self.label_suffix = ""

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        # --------------------------------------------------------------------
        # Estilização e preenchimento dos campos
        # --------------------------------------------------------------------
        for name, field in self.fields.items():

            # ⛔ Campo nome é hidden — JS controla
            if name == "nome":
                continue

            bg = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{base} {bg}"
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        # ------------------------------------------------
        # Ajuste específico – versão do processo
        # ------------------------------------------------
        if "versao_processo" in self.fields:
            self.fields["versao_processo"].widget.attrs.update({
                "inputmode": "numeric",
                "pattern": r"\d{1,4}",
                "maxlength": "4",
                "placeholder": "Versão do Processo"
            })

            # padding quando estiver editando
            if self.instance and self.instance.pk and self.instance.versao_processo:
                self.initial["versao_processo"] = f"{int(self.instance.versao_processo):02d}"

        # --------------------------------------------------------------------
        # Modo VISUALIZAÇÃO / EXCLUSÃO — trava tudo
        # --------------------------------------------------------------------
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

    # ------------------------------------------------
    # CLEAN – Regras finais de validação
    # ------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        parent = cleaned.get("parent")
        nome = cleaned.get("nome")
        macro1 = cleaned.get("macroprocesso_nivel1")
        macro2 = cleaned.get("macroprocesso_nivel2")
        area = cleaned.get("area_responsavel")

        # 1️⃣ Nome obrigatório
        if not nome or nome.strip() == "":
            self.add_error("nome", "Informe o nome do Processo ou Subprocesso.")

        # 2️⃣ Regra principal (SUA REGRA)
        if not parent:
            cleaned["parent"] = None  # Processo

        # 3️⃣ Hierarquia
        if parent:
            if parent.parent_id:
                self.add_error(
                    "parent",
                    "Um Subprocesso só pode ter como pai um PROCESSO, nunca outro Subprocesso."
                )

            if self.instance and parent == self.instance:
                self.add_error("parent", "Processo não pode ser pai de si mesmo.")

        # 4️⃣ Macroprocesso
        if macro2 and macro1:
            if macro2.macroprocesso_nivel1_id != macro1.id:
                self.add_error(
                    "macroprocesso_nivel2",
                    "O Macroprocesso Nível 2 não pertence ao Macroprocesso Nível 1 selecionado."
                )

        # 🔥 5️⃣ Área obrigatória
        if not area:
            self.add_error("area_responsavel", "Área Responsável é obrigatória.")

        # 🔥 6️⃣ Gestor obrigatório
        if not (cleaned.get("gestor") or "").strip():
            self.add_error("gestor", "Gestor é obrigatório.")

        # 🔥 7️⃣ Telefone obrigatório
        if not (cleaned.get("telefone") or "").strip():
            self.add_error("telefone", "Telefone é obrigatório.")

        # 🔥 8️⃣ Email obrigatório + válido
        email = (cleaned.get("email") or "").strip()

        if not email:
            self.add_error("email", "E-mail é obrigatório.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                self.add_error("email", "E-mail inválido.")

        return cleaned

# ----------------------------------
# Processo a Mapear - Formulário
# ----------------------------------
class Form_ProcessoMapearForm(forms.ModelForm):

    classificacao = forms.ModelChoiceField(
        queryset=Classificacao.objects.all(),
        required=False,
        label="Classificação"
    )

    macroprocesso_nivel1 = forms.ModelChoiceField(
        queryset=MacroprocessoNivel1.objects.all(),
        required=False,
        label="Macroprocesso Nível 1",
        widget=MacroSelect()
    )

    macroprocesso_nivel2 = forms.ModelChoiceField(
        queryset=MacroprocessoNivel2.objects.all(),
        required=False,
        label="Macroprocesso Nível 2",
        widget=MacroSelect()
    )

    parent = forms.ModelChoiceField(
        queryset=Processo.objects.none(),
        required=False,
        label="Processo Pai"
    )

    area_responsavel = forms.ModelChoiceField(
        queryset=ContatoAreaSeger.objects.filter(ativo=True).order_by("nome_area"),
        required=False,
        label="Área Responsável",
        empty_label="Selecione uma área"
    )

    class Meta:
        model = ProcessoMapear
        exclude = (
            "usuario_cadastro",
            "usuario_atualizacao",
            "data_criacao",
            "data_atualizacao",
            "status",
        )

        widgets = {
            "objetivo": forms.Textarea(attrs={"rows": "2"}),
            "observacao": forms.Textarea(attrs={"rows": "2"}),
        }

    # ------------------------------------------------
    # INIT – Estilização + ajuste Select2 (CRÍTICO)
    # ------------------------------------------------
    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        modo_exclusao = kwargs.pop("modo_exclusao", False)
        modo_edicao = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)

        # 🔥 LIMITES TEXTO
        if "objetivo" in self.fields:
            self.fields["objetivo"].max_length = 3000
            self.fields["objetivo"].widget.attrs["maxlength"] = 3000
            self.fields["objetivo"].widget.attrs["rows"] = 4

        if "observacao" in self.fields:
            self.fields["observacao"].max_length = 3000
            self.fields["observacao"].widget.attrs["maxlength"] = 3000
            self.fields["observacao"].widget.attrs["rows"] = 4

        # 🔥 SELECT2 + EDIÇÃO (CORREÇÃO PRINCIPAL)
        if self.instance and self.instance.area_responsavel:
            area = self.instance.area_responsavel

            if area:
                self.fields["area_responsavel"].queryset = (
                    ContatoAreaSeger.objects.filter(
                        Q(ativo=True) | Q(pk=area.pk)
                    ).order_by("nome_area")
                )

        self.label_suffix = ""

        # 🔵 PROCESSO PAI
        self.fields["parent"].queryset = (
            Processo.objects.filter(parent__isnull=True)
            .order_by("nome")
        )
        self.fields["parent"].empty_label = "--------"

        # 🎨 ESTILO PADRÃO
        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():
            bg = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base} {bg}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        # 🔒 BLOQUEIO
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

    # ------------------------------------------------
    # CLEAN – Regras leves
    # ------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        nome = cleaned.get("nome")
        tipo = cleaned.get("tipo")

        # 🔥 fallback para inputs visuais
        if not nome:
            nome_post = self.data.get("nome") or self.data.get("id_nome")

            # tenta pegar dos inputs visíveis
            if not nome_post:
                nome_post = self.data.get("subprocesso_input_visible") or \
                            self.data.get("processo_input_visible")

            if nome_post:
                cleaned["nome"] = nome_post.strip()
            else:
                self.add_error("nome", "Informe o nome do Processo, Subprocesso ou Outro.")

        # restante continua igual
        objetivo = cleaned.get("objetivo")

        if not objetivo or objetivo.strip() == "":
            self.add_error("objetivo", "Informe o objetivo do Processo.")

        if tipo == ProcessoMapear.TIPO_PROCESSO:
            cleaned["parent"] = None

        parent = cleaned.get("parent")

        if parent:
            cleaned["classificacao"] = parent.classificacao
            cleaned["macroprocesso_nivel1"] = parent.macroprocesso_nivel1
            cleaned["macroprocesso_nivel2"] = parent.macroprocesso_nivel2

        macro1 = cleaned.get("macroprocesso_nivel1")
        macro2 = cleaned.get("macroprocesso_nivel2")

        if macro2 and macro1:
            if macro2.macroprocesso_nivel1_id != macro1.id:
                self.add_error(
                    "macroprocesso_nivel2",
                    "Macroprocesso Nível 2 não pertence ao Macroprocesso Nível 1 informado."
                )

        if macro2 and not macro1:
            self.add_error(
                "macroprocesso_nivel1",
                "Macroprocesso Nível 1 é obrigatório quando Macroprocesso Nível 2 for informado."
            )

        return cleaned

    # 🔥 IMPORTANTE: NÃO converter para string
    def clean_area_responsavel(self):
        return self.cleaned_data.get("area_responsavel")

# ----------------------------------
# Área Responsável - Formulário
# ----------------------------------
class Form_AreaResponsavelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # 🔥 CAPTURA MODOS (PADRÃO DO SISTEMA)
        self.modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        self.modo_exclusao = kwargs.pop('modo_exclusao', False)
        self.modo_edicao = kwargs.pop('modo_edicao', False)
        self.modo_inclusao = kwargs.pop('modo_inclusao', False)

        super().__init__(*args, **kwargs)

        # 🔒 REGRAS DE OBRIGATORIEDADE
        self.fields['nome_area'].required = True
        self.fields['titular'].required = False
        self.fields['telefone'].required = False
        self.fields['email'].required = False

        # 🔒 ORIGEM CONTROLADA PELO SISTEMA
        self.fields['origem'].initial = "MANUAL"
        self.fields['origem'].disabled = True

        # 🔥 COMPORTAMENTO POR MODO (PADRÃO DO SISTEMA)
        if self.modo_visualizacao or self.modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

    class Meta:
        model = ContatoAreaSeger
        fields = [
            'nome_area',
            'titular',
            'telefone',
            'email',
            'origem',
        ]

        widgets = {
            'nome_area': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-md px-3 py-2 h-[42px] text-black',
                'placeholder': 'Nome da área...'
            }),

            'titular': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-md px-3 py-2 h-[42px] text-black',
                'placeholder': 'Titular...'
            }),

            'telefone': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-md px-3 py-2 h-[42px] text-black',
                'placeholder': 'Telefone(s)...'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'w-full border border-gray-300 rounded-md px-3 py-2 h-[42px] text-black',
                'placeholder': 'E-mail...'
            }),

            'origem': forms.Select(attrs={
                'class': 'w-full bg-gray-100 border border-gray-300 rounded-md px-3 py-2 h-[42px] text-black cursor-not-allowed'
            }),
        }

    # 🔎 VALIDAÇÃO
    def clean_nome_area(self):
        nome = self.cleaned_data.get('nome_area')
        return nome.strip() if nome else nome