import os
import re
from PIL import Image
from django import forms
from django.forms import inlineformset_factory
from django.forms.widgets import (FileInput, Select,)
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.encoding import iri_to_uri
from django.core.exceptions import ValidationError
from urllib.parse import (urlparse, unquote,)

from .models import (
    Usuario, Telefone, Classificacao, MacroprocessoNivel1, MacroprocessoNivel2, Processo,
    TiposDocumento, ProcessoMapear, ContatoAreaSeger, NormaProcedimento, SistemasUECI, AbrangenciaChoices,
)
from django.db.models import Q
from arquiteturaprocessos.utils.processos import validar_normas_processo

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
# CLASSIFICAÇÃO DE  MACROPROCESSOS
# ============================================================
class Form_ClassificacaoForm(forms.ModelForm):

    class Meta:
        model = Classificacao
        fields = ['nome', 'descricao', 'imagem']

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        modo_edicao = kwargs.pop('modo_edicao', False)

        super().__init__(*args, **kwargs)

        # ====================================================
        # DESCRIÇÃO
        # ====================================================
        if "descricao" in self.fields:
            self.fields["descricao"].max_length = 3000
            self.fields["descricao"].widget.attrs["maxlength"] = 3000
            self.fields["descricao"].widget.attrs["rows"] = 4

        # ====================================================
        # IMAGEM
        # ====================================================
        if "imagem" in self.fields:
            self.fields["imagem"].widget = forms.FileInput(
                attrs={
                    "id": "imagem",
                    "accept": ".jpg,.jpeg,.png,.webp,"
                              "image/jpeg,image/png,image/webp",
                }
            )

        self.label_suffix = ""

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():

            # A imagem possui uma área de upload própria no template.
            if name == "imagem":
                continue

            existing = field.widget.attrs.get("class", "")

            bg_color = (
                "bg-gray-100"
                if (modo_visualizacao or modo_exclusao)
                else "bg-white"
            )

            field.widget.attrs["class"] = (
                f"{existing} {base} {bg_color}"
            ).strip()

            field.widget.attrs.setdefault(
                "placeholder",
                field.label
            )

            field.widget.attrs["autocomplete"] = "off"

        # ====================================================
        # VISUALIZAÇÃO / EXCLUSÃO
        # ====================================================
        if modo_visualizacao or modo_exclusao:
            for name, field in self.fields.items():
                field.disabled = True

                if name != "imagem":
                    existing_classes = field.widget.attrs.get(
                        "class", ""
                    )

                    field.widget.attrs["class"] = (
                        f"{existing_classes} bg-gray-100"
                    ).strip()

        # ====================================================
        # EXCLUSÃO
        # ====================================================
        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()

    # ========================================================
    # VALIDAÇÃO DA IMAGEM
    # ========================================================
    def clean_imagem(self):
        imagem = self.cleaned_data.get("imagem")

        # ----------------------------------------------------
        # Em uma edição sem nova imagem, não há nada para
        # validar. Não abrimos nem processamos a imagem existente.
        # ----------------------------------------------------
        if "imagem" not in self.files:
            return imagem

        # ========================================================
        # TAMANHO MÁXIMO
        # ========================================================
        tamanho_maximo = 2 * 1024 * 1024  # 2 MB

        if imagem.size > tamanho_maximo:
            raise forms.ValidationError(
                "A imagem excede o tamanho máximo permitido de 2 MB."
            )

        # ========================================================
        # FORMATO E DIMENSÕES
        # ========================================================
        try:
            with Image.open(imagem) as imagem_pillow:

                formatos_permitidos = {
                    "JPEG",
                    "PNG",
                    "WEBP",
                }

                if imagem_pillow.format not in formatos_permitidos:
                    raise forms.ValidationError(
                        "Tipo de arquivo não permitido. "
                        "Selecione uma imagem JPG, JPEG, PNG ou WEBP."
                    )

                largura, altura = imagem_pillow.size

                if largura > 2000 or altura > 2000:
                    raise forms.ValidationError(
                        "A imagem excede as dimensões máximas permitidas "
                        "de 2000 × 2000 pixels."
                    )

        except forms.ValidationError:
            raise

        except Exception:
            raise forms.ValidationError(
                "Não foi possível validar a imagem selecionada."
            )

        finally:
            imagem.seek(0)

        return imagem

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
# Definição de Documentos
# ============================================================
class Form_TipoDocumentoForm(forms.ModelForm):
    class Meta:
        model = TiposDocumento
        fields = ['nome', 'descricao']

        labels = {
            'nome': 'Documento',
            'descricao': 'Definição',
        }

        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        somente_leitura = modo_visualizacao or modo_exclusao

        super().__init__(*args, **kwargs)

        MAX_DESCRICAO = 3000

        if "descricao" in self.fields:
            self.fields["descricao"].max_length = MAX_DESCRICAO
            self.fields["descricao"].widget.attrs["maxlength"] = MAX_DESCRICAO

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 focus:outline-none "
            "focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                'class',
                base + (' bg-gray-100' if somente_leitura else ' bg-white')
            )
            field.widget.attrs.setdefault('placeholder', field.label)

            # 🔠 Documento sempre armazenado em CAIXA ALTA
            if name == 'nome':
                field.widget.attrs.setdefault(
                    'style',
                    'text-transform: uppercase;'
                )
                field.widget.attrs['oninput'] = 'this.value = this.value.toUpperCase();'

        if somente_leitura:
            for field in self.fields.values():
                field.disabled = True

    # 🔒 REGRA DE DOMÍNIO: Documento sempre armazenado em CAIXA ALTA
    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if nome:
            return nome.strip().upper()

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

    tipo_processo_fake = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

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

    abrangencia = forms.ChoiceField(
        choices=AbrangenciaChoices.choices,
        label="Abrangência",
        widget=forms.RadioSelect,
    )

    data_elaboracao = forms.DateField(
        required=True,
        label="Data de Elaboração",
        input_formats=[
            "%Y-%m-%d",
            "%d/%m/%Y",
        ],
        widget=forms.DateInput(
            attrs={
                "placeholder": "dd/mm/aaaa",
                "autocomplete": "off",
                "maxlength": "10",
            }
        ),
    )

    data_aprovacao = forms.DateField(
        required=False,
        label="Data de Aprovação",
        input_formats=[
            "%Y-%m-%d",
            "%d/%m/%Y",
        ],
        widget=forms.DateInput(
            attrs={
                "placeholder": "dd/mm/aaaa",
                "autocomplete": "off",
                "maxlength": "10",
            }
        ),
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

            "objetivo": forms.Textarea(
                attrs={
                    "style": "height:140px;resize:none;overflow-y:auto;",
                }
            ),

            "documento_modelo_processo": forms.FileInput(
                attrs={
                    "class": (
                        "w-full h-[42px] border border-gray-300 rounded-md "
                        "px-3 py-2 text-black placeholder-gray-400 "
                        "focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                    ),
                    "accept": ".pdf,application/pdf",
                    "autocomplete": "off",
                }
            ),

        }

    # ------------------------------------------------
    # INIT – estilo base, bloqueios por modo
    # ------------------------------------------------
    def __init__(self, *args, **kwargs):
        self.modo_inclusao = kwargs.pop("modo_inclusao", False)
        self.modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        self.modo_exclusao = kwargs.pop("modo_exclusao", False)
        self.modo_edicao = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)

        # Obrigatoriedade tratada pela validação de negócio
        self.fields["nome"].required = False
        self.fields["objetivo"].required = False
        self.fields["area_responsavel"].required = False
        self.fields["gestor"].required = False
        self.fields["telefone"].required = False
        self.fields["email"].required = False

        # 🔑 GARANTIA DOS IDS PARA O TRIPLE FILTER (SEM QUEBRAR O LAYOUT)
        if "classificacao" in self.fields:
            self.fields["classificacao"].widget.attrs["id"] = "id_classificacao"

        if "macroprocesso_nivel1" in self.fields:
            self.fields["macroprocesso_nivel1"].widget.attrs["id"] = "id_macroprocesso_nivel1"

        if "macroprocesso_nivel2" in self.fields:
            self.fields["macroprocesso_nivel2"].widget.attrs["id"] = "id_macroprocesso_nivel2"

        if "objetivo" in self.fields:
            self.fields["objetivo"].widget.attrs["rows"] = 4

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
        # CAMPOS DATA
        # ====================================================
        campos_data = [
            "data_elaboracao",
            "data_aprovacao",
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

        # --------------------------------------------------------------------
        # Estilização e preenchimento dos campos
        # --------------------------------------------------------------------
        for name, field in self.fields.items():

            # ⛔ Campo nome é hidden — JS controla
            if name == "nome":
                continue

            field.widget.attrs["class"] = f"{base_class} {bg}"
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
                self.initial["versao_processo"] = f"{int(self.instance.versao_processo):03d}"

        # --------------------------------------------------------------------
        # Modo VISUALIZAÇÃO / EXCLUSÃO — trava tudo
        # --------------------------------------------------------------------
        if self.modo_visualizacao or self.modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

    # ------------------------------------------------
    # CLEAN – Regras finais de validação
    # ------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        parent = cleaned.get("parent")

        # =====================================================
        # 1. PROCESSO / SUBPROCESSO
        # =====================================================
        if not parent:
            cleaned["parent"] = None

        if parent:
            if parent.parent_id:
                self.add_error(
                    "parent",
                    "Um Subprocesso só pode ter como pai um PROCESSO, nunca outro Subprocesso."
                )

            if self.instance and parent == self.instance:
                self.add_error(
                    "parent",
                    "Processo não pode ser pai de si mesmo."
                )

        # =====================================================
        # VALIDAÇÕES DE NEGÓCIO (MODEL)
        # =====================================================
        processo = Processo()
        processo.tipo = cleaned.get("tipo_processo_fake")

        for campo, valor in cleaned.items():
            setattr(processo, campo, valor)

        erros = processo.validar_para_iniciar()

        for erro in erros:
            self.add_error(
                erro["campo"],
                erro["mensagem"]
            )

        # =====================================================
        # VALIDAÇÃO DAS NORMAS DE PROCEDIMENTO
        # =====================================================
        try:
            cleaned["normas_ids"] = validar_normas_processo(self.data)
        except ValidationError as e:
            self.add_error(None, e.message)

        return cleaned

# ----------------------------------
# Processo a Mapear - Formulário
# ----------------------------------
class Form_ProcessoMapearForm(forms.ModelForm):

    abrangencia = forms.ChoiceField(
        choices=AbrangenciaChoices.choices,
        label="Abrangência",
        widget=forms.RadioSelect,
    )

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
        queryset=ContatoAreaSeger.objects.filter(
            ativo=True
        ).order_by("nome_area"),
        required=False,
        label="Área Responsável",
        empty_label="Selecione uma área"
    )

    class Meta:
        model = ProcessoMapear
        exclude = (
            "uuid",
            "usuario_cadastro",
            "usuario_atualizacao",
            "data_criacao",
            "data_atualizacao",
            "usuario_finalizacao",
            "data_finalizacao",
            "status",
        )

        widgets = {
            "objetivo": forms.Textarea(
                attrs={"rows": "2"}
            ),
        }

    # ------------------------------------------------
    # INIT – estilo base, bloqueios por modo
    # ------------------------------------------------
    def __init__(self, *args, **kwargs):
        self.modo_inclusao = kwargs.pop(
            "modo_inclusao", False
        )
        self.modo_visualizacao = kwargs.pop(
            "modo_visualizacao", False
        )
        self.modo_exclusao = kwargs.pop(
            "modo_exclusao", False
        )
        self.modo_edicao = kwargs.pop(
            "modo_edicao", False
        )

        super().__init__(*args, **kwargs)

        # ------------------------------------------------
        # OBRIGATORIEDADE
        #
        # Processo a Mapear funciona como rascunho.
        # A validação completa para iniciar o processo
        # é realizada por validar_para_iniciar().
        #
        # Tipo e Abrangência permanecem obrigatórios,
        # pois são definidos por radio buttons.
        # ------------------------------------------------
        self.fields["nome"].required = False
        self.fields["objetivo"].required = False
        self.fields["area_responsavel"].required = False
        self.fields["gestor"].required = False
        self.fields["telefone"].required = False
        self.fields["email"].required = False
        self.fields["classificacao"].required = False
        self.fields["macroprocesso_nivel1"].required = False
        self.fields["macroprocesso_nivel2"].required = False
        self.fields["parent"].required = False
        self.fields["observacao"].required = False

        # ------------------------------------------------
        # GARANTIA DOS IDS PARA O TRIPLE FILTER
        # ------------------------------------------------
        if "classificacao" in self.fields:
            self.fields[
                "classificacao"
            ].widget.attrs["id"] = "id_classificacao"

        if "macroprocesso_nivel1" in self.fields:
            self.fields[
                "macroprocesso_nivel1"
            ].widget.attrs["id"] = "id_macroprocesso_nivel1"

        if "macroprocesso_nivel2" in self.fields:
            self.fields[
                "macroprocesso_nivel2"
            ].widget.attrs["id"] = "id_macroprocesso_nivel2"

        # ------------------------------------------------
        # LIMITES DE TEXTO
        # ------------------------------------------------
        if "objetivo" in self.fields:
            self.fields["objetivo"].max_length = 3000
            self.fields[
                "objetivo"
            ].widget.attrs["maxlength"] = 3000
            self.fields[
                "objetivo"
            ].widget.attrs["rows"] = 4

        if "observacao" in self.fields:
            self.fields["observacao"].max_length = 3000
            self.fields[
                "observacao"
            ].widget.attrs["maxlength"] = 3000

        # ------------------------------------------------
        # SELECT2 + EDIÇÃO
        # ------------------------------------------------
        if self.instance and self.instance.pk:
            area = self.instance.area_responsavel

            if area:
                self.fields[
                    "area_responsavel"
                ].queryset = (
                    ContatoAreaSeger.objects.filter(
                        Q(ativo=True) | Q(pk=area.pk)
                    ).order_by("nome_area")
                )

        self.label_suffix = ""

        # ------------------------------------------------
        # PROCESSO PAI
        # ------------------------------------------------
        self.fields["parent"].queryset = (
            Processo.objects.filter(
                parent__isnull=True
            ).order_by("nome")
        )

        self.fields["parent"].empty_label = "--------"

        # ------------------------------------------------
        # CLASSE PADRÃO
        # ------------------------------------------------
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

        # ------------------------------------------------
        # ESTILIZAÇÃO DOS CAMPOS
        # ------------------------------------------------
        for name, field in self.fields.items():

            # Rádio é controlado pelo template
            if name in ("tipo", "abrangencia"):
                continue

            # Nome é controlado pelos inputs visuais + JavaScript
            if name == "nome":
                continue

            existing = field.widget.attrs.get(
                "class", ""
            )

            field.widget.attrs["class"] = (
                f"{existing} {base_class} {bg}"
            ).strip()

            field.widget.attrs.setdefault(
                "placeholder",
                field.label
            )

            field.widget.attrs[
                "autocomplete"
            ] = "off"

        # ------------------------------------------------
        # MODO VISUALIZAÇÃO / EXCLUSÃO
        # ------------------------------------------------
        if (
            self.modo_visualizacao
            or self.modo_exclusao
        ):
            for field in self.fields.values():
                field.disabled = True

    # ------------------------------------------------
    # CLEAN – Regras para o rascunho
    # ------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        nome = cleaned.get("nome")
        tipo = cleaned.get("tipo")

        # ------------------------------------------------
        # NOME
        # O nome é obrigatório para identificar o
        # Processo a Mapear.
        # O template utiliza inputs visuais diferentes
        # conforme o Tipo, por isso fazemos o fallback
        # para esses campos.
        # ------------------------------------------------
        if not nome:
            nome_post = (
                self.data.get("nome")
                or self.data.get("id_nome")
            )

            if not nome_post:
                nome_post = (
                    self.data.get(
                        "subprocesso_input_visible"
                    )
                    or self.data.get(
                        "processo_input_visible"
                    )
                )

            if nome_post:
                cleaned["nome"] = nome_post.strip()
            else:
                self.add_error(
                    "nome",
                    "Informe o nome do Processo, "
                    "Subprocesso ou Outro."
                )

        # ------------------------------------------------
        # OBJETIVO
        # O Objetivo faz parte da identificação mínima
        # do rascunho.
        # ------------------------------------------------
        objetivo = cleaned.get("objetivo")

        if not objetivo or objetivo.strip() == "":
            self.add_error(
                "objetivo",
                "Informe o objetivo do Processo a Mapear."
            )

        # ------------------------------------------------
        # PROCESSO
        # Um Processo não possui Processo Pai.
        # ------------------------------------------------
        if tipo == ProcessoMapear.TIPO_PROCESSO:
            cleaned["parent"] = None

        # ------------------------------------------------
        # HERANÇA DO PROCESSO PAI
        # Quando existe Processo Pai, o Subprocesso
        # herda suas características.
        # ------------------------------------------------
        parent = cleaned.get("parent")

        if parent:
            cleaned["classificacao"] = (
                parent.classificacao
            )
            cleaned["macroprocesso_nivel1"] = (
                parent.macroprocesso_nivel1
            )
            cleaned["macroprocesso_nivel2"] = (
                parent.macroprocesso_nivel2
            )

        return cleaned

    # ------------------------------------------------
    # ÁREA RESPONSÁVEL
    #
    # IMPORTANTE: NÃO converter para string.
    # ------------------------------------------------
    def clean_area_responsavel(self):
        return self.cleaned_data.get(
            "area_responsavel"
        )

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