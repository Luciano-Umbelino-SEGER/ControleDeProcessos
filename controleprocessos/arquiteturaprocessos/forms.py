import os
import re
from django import forms
from django.forms import inlineformset_factory
from django.forms.widgets import FileInput
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date
from django.forms.widgets import Select
from urllib.parse import urlparse

from .models import (
    Usuario, Telefone, Classificacao, MacroprocessoNivel1, MacroprocessoNivel2,
    ModelagemProcesso, Processo, TiposDocumento, ProcessoMapear, ContatoAreaSeger
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
                field.widget.attrs['style'] = 'text-transform: uppercase;'
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
# Modelagem de Processos
# ============================================================
class Form_ModelagemProcessoForm(forms.ModelForm):

    # ============================================================
    # 🔹 CAMPO: TÍTULO (substitui "nome")
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
            "data_elaboracao": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "data_aprovacao": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "vigencia_inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "vigencia_fim": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
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

        # Ajuste datas iniciais (evita quebra em edição)
        for fname in ["data_elaboracao", "data_aprovacao", "vigencia_inicio", "vigencia_fim"]:
            try:
                if getattr(self.instance, fname):
                    self.fields[fname].initial = getattr(self.instance, fname).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Classe base visual
        base_class = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        # Estilo geral
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            bg = "bg-gray-100" if (self.modo_visualizacao or self.modo_exclusao) else "bg-white"

            field.widget.attrs["class"] = f"{existing} {base_class} {bg}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)

            field.widget.attrs.update({
                "autocomplete": "off",
                "data-lpignore": "true",
                "autocorrect": "off",
                "autocapitalize": "off",
                "spellcheck": "false",
            })

        # Ajustes específicos
        self.fields["codigo"].widget.attrs["class"] += " uppercase"
        self.fields["sequencial"].widget.attrs.update({"inputmode": "numeric", "pattern": r"\d{1,4}", "maxlength": "4"})
        self.fields["versao"].widget.attrs.update({"inputmode": "numeric", "pattern": r"\d{1,4}", "maxlength": "4"})

        # PDF widget
        if "documento_modelagem_processo" in self.fields:
            fwidget = self.fields["documento_modelagem_processo"].widget
            fwidget.attrs.setdefault("tabindex", "0")
            fwidget.attrs.setdefault("accept", ".pdf,application/pdf")

            if self.modo_edicao or self.modo_visualizacao or self.modo_exclusao:
                self.fields["documento_modelagem_processo"].widget = FileInput(attrs=fwidget.attrs)

                if self.instance and self.instance.documento_modelagem_processo:
                    nome_arq = os.path.basename(self.instance.documento_modelagem_processo.name)
                    self.fields["documento_modelagem_processo"].widget.attrs["placeholder"] = nome_arq

        # Valores padrão para inclusão
        if self.modo_inclusao:
            self.fields["sequencial"].initial = "001"
            self.fields["versao"].initial = "01"

        # 🔹 ZEROS À ESQUERDA — edição / visualização
        if self.instance and self.instance.pk:
            if self.instance.sequencial is not None:
                self.initial["sequencial"] = f"{int(self.instance.sequencial):04d}"
            if self.instance.versao is not None:
                self.initial["versao"] = f"{int(self.instance.versao):02d}"

        # Usuário criador / atualização
        if self.usuario_logado and not self.instance.pk:
            self.instance.usuario = self.usuario_logado

        if self.usuario_logado and self.instance.pk:
            self.instance.usuario_atualizacao = self.usuario_logado

        # Modo somente leitura
        if self.modo_visualizacao or self.modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                field.widget.attrs["class"] += " bg-gray-100"

        # Guarda versão original
        self._versao_original = getattr(self.instance, "versao", None) if self.instance.pk else None

        if "link_normaprocedimento" in self.fields:
            self.fields["link_normaprocedimento"].widget.attrs.update({
                "type": "url",
                "placeholder": "https://exemplo.com/documento.pdf",
            })

            # 🔥 GARANTE QUE O CAMPO OCUPA TODA A LARGURA (NÃO QUEBRA LAYOUT)
            self.fields["link_normaprocedimento"].widget.attrs["class"] += " w-full"

    # ============================================================
    # VALIDAÇÕES
    # ============================================================
    def clean_titulo(self):
        titulo = (self.cleaned_data.get("titulo") or "").strip().upper()
        if not titulo:
            raise ValidationError("Informe o Título.")
        return titulo

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9._-]{2,20}", codigo):
            raise ValidationError(
                "Código inválido. Use 2 a 20 caracteres (A–Z, 0–9, ponto, hífen ou sublinhado)."
            )
        return codigo

    def clean_sequencial(self):
        seq = self.cleaned_data.get("sequencial")
        if not seq:
            raise ValidationError("Informe o número sequencial da modelagem de processos.")
        seq = str(seq).strip()
        if not seq.isdigit():
            raise ValidationError("O número sequencial deve conter apenas dígitos.")
        num = int(seq)
        if not (1 <= num <= 9999):
            raise ValidationError("O número sequencial deve estar entre 1 e 9999.")
        return num

    def clean_versao(self):
        ver = self.cleaned_data.get("versao")
        if ver is None:
            raise ValidationError("Informe a versão.")
        if not isinstance(ver, int):
            raise ValidationError("Versão deve ser um número inteiro.")
        if not (1 <= ver <= 9999):
            raise ValidationError("A versão deve estar entre 1 e 9999.")
        if self._versao_original is not None and ver < self._versao_original:
            raise ValidationError(
                f"A versão não pode ser menor que {self._versao_original}."
            )
        return ver

    def clean_documento_modelagem_processo(self):
        f = self.cleaned_data.get("documento_modelagem_processo")

        # 🔹 1. Nenhum arquivo enviado → mantém o atual
        if not f:
            return f

        # 🔹 2. Se NÃO tem content_type → é FieldFile (edição sem novo upload)
        if not hasattr(f, "content_type"):
            return f

        # 🔹 3. Novo upload → validar tipo básico
        content_type = f.content_type
        file_name = f.name.lower()

        is_pdf_type = content_type in ("application/pdf", "application/x-pdf")
        is_pdf_name = file_name.endswith(".pdf")

        if not (is_pdf_type or is_pdf_name):
            raise ValidationError("Envie um PDF válido (.pdf).")

        # 💡 4. VALIDAÇÃO EXTRA (nível enterprise)
        # Verifica assinatura real do arquivo (%PDF)
        if hasattr(f, "read"):
            header = f.read(4)
            f.seek(0)  # ⚠️ MUITO IMPORTANTE: voltar o ponteiro

            if header != b"%PDF":
                raise ValidationError("Arquivo não é um PDF válido.")

        return f

    # ============================================================
    # 🔹 VALIDAÇÃO: LINK NORMA DE PROCEDIMENTO
    # ============================================================
    def clean_link_normaprocedimento(self):
        link = self.cleaned_data.get("link_normaprocedimento")

        if not link:
            return link

        link = link.strip()

        parsed = urlparse(link)

        if not parsed.scheme or not parsed.netloc:
            raise ValidationError("Informe uma URL válida.")

        if parsed.scheme not in ("http", "https"):
            raise ValidationError("A URL deve começar com http:// ou https://.")

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
            obj.full_clean()
            obj.save()

        return obj

# ----------------------------
# Widgets customizados
# ----------------------------
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
        to_field_name="nome_area",
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

        # 1️⃣ Nome é obrigatório SEMPRE
        if not nome or nome.strip() == "":
            self.add_error("nome", "Informe o nome do Processo ou Subprocesso.")

        # 2️⃣ PROCESSO → parent deve ser None
        if not parent:
            cleaned["parent"] = None  # Processo

        # 3️⃣ SUBPROCESSO → parent deve ser um Processo (não outro subprocesso)
        if parent and parent.parent_id:
            self.add_error(
                "parent",
                "Um Subprocesso só pode ter como pai um PROCESSO, nunca outro Subprocesso."
            )

        # 4️⃣ Validação macroprocesso n1/n2
        macro1 = cleaned.get("macroprocesso_nivel1")
        macro2 = cleaned.get("macroprocesso_nivel2")

        if macro2 and macro1:
            if macro2.macroprocesso_nivel1_id != macro1.id:
                self.add_error(
                    "macroprocesso_nivel2",
                    "O Macroprocesso Nível 2 não pertence ao Macroprocesso Nível 1 selecionado."
                )

        return cleaned

    def clean_area_responsavel(self):
        area = self.cleaned_data.get("area_responsavel")
        return area.nome_area if area else ""
    
#
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
        if self.instance and self.instance.pk:
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
        objetivo = cleaned.get("objetivo")
        tipo = cleaned.get("tipo")
        parent = cleaned.get("parent")

        if not nome or nome.strip() == "":
            self.add_error("nome", "Informe o nome do Processo ou Subprocesso.")

        if not objetivo or objetivo.strip() == "":
            self.add_error("objetivo", "Informe o objetivo do Processo.")

        # 🔥 REGRA DE DOMÍNIO
        if tipo == ProcessoMapear.TIPO_PROCESSO:
            cleaned["parent"] = None

        if tipo == ProcessoMapear.TIPO_SUBPROCESSO and not parent:
            self.add_error("parent", "Subprocesso deve estar vinculado a um Processo.")

        return cleaned

    # 🔥 IMPORTANTE: NÃO converter para string
    def clean_area_responsavel(self):
        return self.cleaned_data.get("area_responsavel")

