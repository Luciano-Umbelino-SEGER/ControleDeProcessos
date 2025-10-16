from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import Usuario, Telefone, Classificacao, MacroprocessoNivel1, MacroprocessoNivel2

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

# forms.py
from django import forms
from django.utils import timezone
from .models import MacroprocessoNivel2, MacroprocessoNivel1, Classificacao  # ajuste os imports conforme seu app


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
            field.widget.attrs["class"] = f"{existing} {base} {bg_color}".strip()
            field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["autocomplete"] = "off"

        # Ajustes específicos de widgets/ids
        self.fields["macroprocesso_nivel1"].label_from_instance = lambda obj: obj.nome
        self.fields["macroprocesso_nivel1"].widget.attrs.update({
            "id": "id_macroprocesso_nivel1"
        })
        # Altura maior para descrição
        self.fields["descricao"].widget.attrs["class"] += " h-32"

        # --- Desabilita campos em visualização/exclusão (igual ao Nível 1) ---
        if modo_visualizacao or modo_exclusao:
            for field in self.fields.values():
                field.disabled = True
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_classes} bg-gray-100".strip()

        # --- (Opcional) Lógica adicional no modo exclusão, se o modelo tiver os campos ---
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

