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

from .models import (Usuario, Telefone, Classificacao, MacroprocessoNivel1, MacroprocessoNivel2,
                     ModelagemProcesso, Processo)

UserModel = get_user_model()

class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            try:
                user = UserModel.objects.get(username=username)

                if not user.check_password(password):
                    raise forms.ValidationError(
                        "Usuário ou senha incorretos. Verifique os dados e tente novamente.",
                        code='invalid_login',
                    )

                if not user.is_active:
                    raise forms.ValidationError(
                        "Usuário está com a conta inativa. Entre em contato com o administrador do sistema.",
                        code='inactive',
                    )

                # ✅ ESSENCIAL: define o usuário autenticado
                self.user_cache = user

            except UserModel.DoesNotExist:
                raise forms.ValidationError(
                    "Usuário ou senha incorretos. Verifique os dados e tente novamente.",
                    code='invalid_login',
                )

        return self.cleaned_data


class EmailAuthenticationForm(AuthenticationForm):
    """
    Formulário de login que permite usar email ou username
    """
    username = forms.CharField(
        label=_("E-mail ou Username"),
        widget=forms.TextInput(attrs={"autofocus": True})
    )

    def clean(self):
        input_value = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if input_value and password:
            # tenta encontrar usuário por username ou email
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

class Form_UsuarioForm(UserCreationForm):
    """
    Formulário para criação de usuário.
    Inclui os campos de senha.
    Desabilita todos os campos nos modos visualização e exclusão.
    """
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'placeholder': 'E-mail'}))

    class Meta:
        model = Usuario
        fields = (
            "username", "first_name", "last_name", "email",
            "setor", "cargo", "funcao", "perfil",
            "password1", "password2",
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
            "password1": "new-password",
            "password2": "new-password",
        }

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()

            input_type = getattr(field.widget, "input_type", "")
            if input_type in {"text", "email", "password"}:
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

        # Desabilita todos os campos se estiver em modo visualização ou exclusão
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

                # Aplica fundo cinza aos campos desabilitados
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()


class EditarUsuarioForm(forms.ModelForm):
    """
    Formulário para edição de usuário.
    Inclui campos de senha, mas só os valida no modo inclusão.
    """
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'placeholder': 'E-mail'}))
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Senha'}),
        required=False
    )
    password2 = forms.CharField(
        label="Confirmação de Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirme a Senha'}),
        required=False
    )

    class Meta:
        model = Usuario
        fields = (
            "username", "first_name", "last_name", "email",
            "setor", "cargo", "funcao", "perfil",
            "password1", "password2"
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
            "password1": "new-password",
            "password2": "new-password",
        }

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " " + base).strip()
            input_type = getattr(field.widget, "input_type", "")
            if input_type in {"text", "email", "password"}:
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

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        # Só valida as senhas se for modo inclusão
        if self.instance.pk is None:
            if not password1 or not password2:
                raise forms.ValidationError("Os campos de senha são obrigatórios.")
            if password1 != password2:
                raise forms.ValidationError("As senhas não coincidem.")
        return cleaned_data



class TelefoneForm(forms.ModelForm):
    """
    Formulário para cadastrar telefones
    """
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

# Formset de telefones
TelefoneFormSet = inlineformset_factory(
    Usuario,
    Telefone,
    form=TelefoneForm,
    extra=1,        # número de linhas iniciais
    can_delete=True # permite remover telefones
)

class Form_ClassificacaoForm(forms.ModelForm):
    """
    Formulário para criação de classificação.
    Aplica estilos e controla os modos de visualização, exclusão e edição.
    """
    class Meta:
        model = Classificacao
        fields = ['nome', 'descricao']

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        modo_edicao = kwargs.pop('modo_edicao', False)

        super().__init__(*args, **kwargs)
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

        # Desabilita todos os campos se estiver em modo visualização ou exclusão
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        # Se estiver em modo exclusão, pode aplicar lógica adicional
        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()

class Form_MacroProcessoNivel1Form(forms.ModelForm):
    """
    Formulário para criação de Macro Processos de Nivel1.
    Aplica estilos e controla os modos de visualização, exclusão e edição.
    """
    class Meta:
        model = MacroprocessoNivel1
        fields = ['nome', 'descricao', 'classificacao']

    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop('modo_visualizacao', False)
        modo_exclusao = kwargs.pop('modo_exclusao', False)
        modo_edicao = kwargs.pop('modo_edicao', False)

        super().__init__(*args, **kwargs)
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

        # Desabilita todos os campos se estiver em modo visualização ou exclusão
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        # Se estiver em modo exclusão, pode aplicar lógica adicional
        if modo_exclusao and self.instance:
            self.instance.is_active = False
            self.instance.data_ativacaodesativacao = timezone.now()

class Form_MacroProcessoNivel2Form(forms.ModelForm):
    """
    Formulário para criação/edição de Macro Processos de Nível 2.
    Aplica estilos e controla os modos de visualização, exclusão e edição,
    espelhando o comportamento do Form_MacroProcessoNivel1Form.
    """

    classificacao = forms.ModelChoiceField(
        queryset=Classificacao.objects.all(),
        required=False,
        label="Classificação",
        widget=forms.Select(attrs={
            "id": "id_classificacao"  # importante para o JS
        })
    )

    class Meta:
        model = MacroprocessoNivel2
        fields = ["classificacao", "macroprocesso_nivel1", "nome", "descricao"]

    def __init__(self, *args, **kwargs):
        # --- Modos (iguais ao Nível 1) ---
        modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        modo_exclusao     = kwargs.pop("modo_exclusao", False)
        modo_edicao       = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        # --- Estilos base (iguais ao Nível 1) ---
        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        # Aplica classes, placeholder e autocomplete para TODOS os campos
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            # preserva classes existentes, adiciona base e bg_color
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        # Ajustes específicos de widgets/ids
        # mantém label_from_instance para exibir nome do objeto
        self.fields["macroprocesso_nivel1"].label_from_instance = lambda obj: obj.nome
        # garante id explícito para macroprocesso_nivel1 (se quiser manter)
        self.fields["macroprocesso_nivel1"].widget.attrs.update({
            "id": "id_macroprocesso_nivel1"
        })
        # Altura maior para descrição (preserva as classes já setadas)
        self.fields["descricao"].widget.attrs["class"] += " h-32"

        # --- Desabilita campos em visualização/exclusão (igual ao Nível 1) ---
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        # --- (Opcional) Lógica adicional no modo exclusao, se o modelo tiver os campos ---
        if modo_exclusao and self.instance:
            if hasattr(self.instance, "is_active"):
                self.instance.is_active = False
            if hasattr(self.instance, "data_ativacaodesativacao"):
                self.instance.data_ativacaodesativacao = timezone.now()

        # --- Lógica de interdependência Classificação ↔ Macroprocesso N1 ---
        # Filtra Macro N1 quando uma classificação é informada no POST/GET (self.data)
        if "classificacao" in self.data:
            try:
                classificacao_id = int(self.data.get("classificacao") or 0)
                if classificacao_id:
                    self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.filter(
                        classificacao_id=classificacao_id
                    )
                else:
                    # Sem classificação => mostra todos (estado inicial)
                    self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.all()
            except (ValueError, TypeError):
                self.fields["macroprocesso_nivel1"].queryset = MacroprocessoNivel1.objects.all()
        else:
            # Primeira carga da tela (ou sem informar classificacao no request) => todos
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
        # Em modo edição (instance existente), inicializa classificação do macro vinculado
        elif self.instance and getattr(self.instance, "pk", None):
            if getattr(self.instance, "macroprocesso_nivel1", None):
                self.fields["classificacao"].initial = self.instance.macroprocesso_nivel1.classificacao

        # -----------------------
        # GARANTIA FINAL DE IDS
        # -----------------------
        # Aqui asseguramos que **todos** os widgets tenham um atributo 'id'
        # no formato id_<nome_campo> caso não exista — sem sobrescrever se já houver.
        for name, field in self.fields.items():
            existing_id = field.widget.attrs.get("id")
            if not existing_id:
                field.widget.attrs["id"] = f"id_{name}"
            # Assegura também que o atributo name do widget esteja correto (não altera layout)
            # (normalmente Django já define, mas garantimos para evitar inconsistências)
            field.widget.attrs.setdefault("name", name)


class Form_ModelagemProcessoForm(forms.ModelForm):
    nome = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "w-full border border-gray-300 rounded px-3 py-2 text-black focus:ring-2 focus:ring-blue-500 focus:outline-none uppercase",
            "placeholder": "Nome da Norma de Procedimento",
            "data-lpignore": "true",
            "autocomplete": "new-password",
            "autocorrect": "off",
            "autocapitalize": "off",
            "spellcheck": "false",
        })
    )

    class Meta:
        model = ModelagemProcesso
        exclude = (
            'usuario',
            'data_cadastro',
            'data_atualizacao',
            'usuario_atualizacao',
        )
        widgets = {
            "data_elaboracao": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "data_aprovacao": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "vigencia_inicio": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "vigencia_fim": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario_logado = kwargs.pop("usuario_logado", None)
        self.modo_inclusao = kwargs.pop("modo_inclusao", False)
        self.modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        self.modo_exclusao = kwargs.pop("modo_exclusao", False)
        self.modo_edicao = kwargs.pop("modo_edicao", False)
        super().__init__(*args, **kwargs)

        # Ajuste datas
        for field_name in ["data_elaboracao", "data_aprovacao", "vigencia_inicio", "vigencia_fim"]:
            field = self.fields.get(field_name)
            if field and getattr(self.instance, field_name):
                field.initial = getattr(self.instance, field_name).strftime("%Y-%m-%d")

        self.label_suffix = ""
        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        # Ajuste de classes
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            bg_color = "bg-gray-100" if (self.modo_visualizacao or self.modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)

            field.widget.attrs.update({
                "autocomplete": "new-password",
                "data-lpignore": "true",
                "autocorrect": "off",
                "autocapitalize": "off",
                "spellcheck": "false",
            })

        # Ajuste campo código
        self.fields["codigo"].widget.attrs.update({
            "class": self.fields["codigo"].widget.attrs["class"] + " uppercase"
        })

        # Ajuste sequencial e versão
        self.fields["sequencial"].widget.attrs.update({"inputmode": "numeric", "pattern": r"\d{1,3}"})
        self.fields["versao"].widget.attrs.update({"inputmode": "numeric", "pattern": r"\d{1,2}"})

        # Ajuste PDF
        if "documento_modelagem_processo" in self.fields:
            from django.forms.widgets import FileInput
            import os

            fwidget = self.fields["documento_modelagem_processo"].widget
            fwidget.attrs.setdefault("tabindex", "0")
            fwidget.attrs.setdefault("accept", ".pdf,application/pdf")

            # Remover ClearableFileInput
            if self.modo_edicao or self.modo_visualizacao or self.modo_exclusao:
                self.fields["documento_modelagem_processo"].widget = FileInput(attrs=fwidget.attrs)

                if self.instance and self.instance.documento_modelagem_processo:
                    nome_arquivo = os.path.basename(self.instance.documento_modelagem_processo.name)
                    self.fields["documento_modelagem_processo"].widget.attrs["placeholder"] = nome_arquivo

        # Valores iniciais para inclusão
        if not self.instance or not self.instance.pk:
            self.fields["nome"].initial = "NORMA DE PROCEDIMENTO"
            self.fields["sequencial"].initial = "001"
            self.fields["versao"].initial = "01"

        # usuário
        if self.usuario_logado and (not self.instance or not self.instance.pk):
            self.instance.usuario = self.usuario_logado

        # Desabilita nos modos somente leitura
        if self.modo_visualizacao or self.modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                field.widget.attrs["class"] += " bg-gray-100"

        # Guarda versão original
        self._versao_original = getattr(self.instance, "versao", None) if self.instance and self.instance.pk else None

    # ----- VALIDATIONS -----

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip().upper()
        if not nome:
            raise ValidationError("Informe o Nome.")
        return nome

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9._-]{2,20}", codigo):
            raise ValidationError("Código inválido. Use 2 a 20 caracteres (A–Z, 0–9, ponto, hífen ou sublinhado).")
        return codigo

    def clean_sequencial(self):
        seq = self.cleaned_data.get("sequencial")
        if not seq:
            raise ValidationError("Informe o número sequencial da norma.")
        seq = str(seq).strip()
        if not seq.isdigit():
            raise ValidationError("O número sequencial deve conter apenas dígitos (0–9).")
        num = int(seq)
        if not (1 <= num <= 999):
            raise ValidationError("O número sequencial deve estar entre 1 e 999.")
        return num

    def clean_versao(self):
        ver = self.cleaned_data.get("versao")
        if ver is None:
            raise ValidationError("Informe a versão da norma.")
        if not isinstance(ver, int):
            raise ValidationError("Versão deve ser um número inteiro.")
        if not (1 <= ver <= 99):
            raise ValidationError("A versão deve estar entre 1 e 99.")
        if self._versao_original is not None and ver < self._versao_original:
            raise ValidationError(f"A versão não pode ser menor que {self._versao_original}.")
        return ver

    def clean(self):
        cleaned = super().clean()
        de, da = cleaned.get("data_elaboracao"), cleaned.get("data_aprovacao")
        vi, vf = cleaned.get("vigencia_inicio"), cleaned.get("vigencia_fim")

        if de and da and da < de:
            self.add_error("data_aprovacao", "Deve ser maior ou igual à Data de Elaboração.")
        if da and vi and vi < da:
            self.add_error("vigencia_inicio", "Deve ser maior ou igual à Data de Aprovação.")
        if vi and vf and vf <= vi:
            self.add_error("vigencia_fim", "Deve ser maior que Início da Vigência.")
        return cleaned

    def clean_documento_modelagem_processo(self):
        f = self.cleaned_data.get('documento_modelagem_processo')
        if not f:
            return f
        content_type = getattr(f, 'content_type', '') or ''
        is_pdf_type = content_type in ('application/pdf', 'application/x-pdf')
        is_pdf_name = f.name.lower().endswith('.pdf')
        if not (is_pdf_type or is_pdf_name):
            raise forms.ValidationError('Envie um arquivo PDF válido (.pdf).')
        return f

    def save(self, commit=True):
        """
        Ajuste cirúrgico: delega ao model a exclusão e renomeação do arquivo.
        Apenas associa usuários corretamente.
        """
        obj = super().save(commit=False)

        # Atribui usuário criador
        if self.usuario_logado and not obj.usuario_id:
            obj.usuario = self.usuario_logado

        # Atribui usuário de atualização
        if self.usuario_logado and obj.pk:
            obj.usuario_atualizacao = self.usuario_logado

        if commit:
            obj.save()

        return obj

# ----------------------------
# Processos
# ----------------------------
class Form_ProcessoForm(forms.ModelForm):

    # Campo extra para o radio (Processo/Subprocesso)
    tipo_processo = forms.ChoiceField(
        choices=[("processo", "Processo"), ("subprocesso", "Subprocesso")],
        widget=forms.RadioSelect(attrs={"class": "mr-2"}),
        required=True,
        label="Tipo"
    )

    classificacao = forms.ModelChoiceField(
        queryset=Classificacao.objects.all(),
        label="Classificação"
    )

    macroprocesso_nivel1 = forms.ModelChoiceField(
        queryset=MacroprocessoNivel1.objects.all(),
        label="Macroprocesso Nível 1"
    )

    macroprocesso_nivel2 = forms.ModelChoiceField(
        queryset=MacroprocessoNivel2.objects.all(),
        label="Macroprocesso Nível 2",
        required=False
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
    # INIT – remove estilização do campo nome,
    # e mantém estilo dos demais campos.
    # ------------------------------------------------
    def __init__(self, *args, **kwargs):
        modo_visualizacao = kwargs.pop("modo_visualizacao", False)
        modo_exclusao = kwargs.pop("modo_exclusao", False)
        modo_edicao = kwargs.pop("modo_edicao", False)

        super().__init__(*args, **kwargs)

        self.label_suffix = ""

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        for name, field in self.fields.items():

            # ⛔ Campo nome é hidden — JS controla
            if name == "nome":
                continue

            # fundo dependendo do modo
            bg = "bg-gray-100" if (modo_visualizacao or modo_exclusao) else "bg-white"
            field.widget.attrs["class"] = f"{base} {bg}"
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        # MODO VISUALIZAÇÃO / EXCLUSÃO — trava tudo
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True

        # Travar radio fora da inclusão
        if modo_visualizacao or modo_exclusao or modo_edicao:
            if "tipo_processo" in self.fields:
                self.fields["tipo_processo"].disabled = True

    # ------------------------------------------------
    # CLEAN – Regras finais de validação
    # ------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        tipo = cleaned.get("tipo_processo")
        parent = cleaned.get("parent")
        nome = cleaned.get("nome")

        # 1️⃣ Nome é obrigatório SEMPRE
        if not nome or nome.strip() == "":
            self.add_error("nome", "Informe o nome do Processo ou Subprocesso.")

        # 2️⃣ Processo não pode ter parent
        if tipo == "processo":
            cleaned["parent"] = None

        # 3️⃣ Subprocesso precisa obrigatoriamente de parent
        if tipo == "subprocesso":
            if not parent:
                self.add_error("parent", "Selecione o processo pai para o subprocesso.")

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








