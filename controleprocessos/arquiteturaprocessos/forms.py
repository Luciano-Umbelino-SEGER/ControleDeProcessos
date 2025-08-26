from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Usuario, Telefone

User = get_user_model()

class EmailAuthenticationForm(AuthenticationForm):
    """
    Formulário de login que permite usar email ou username
    """
    username = forms.CharField(
        label=_("Email ou Username"),
        widget=forms.TextInput(attrs={"autofocus": True})
    )

    def clean(self):
        input_value = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if input_value and password:
            # tenta encontrar usuário por username ou email
            try:
                user = User.objects.get(username=input_value)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=input_value)
                except User.DoesNotExist:
                    user = None

            if user is not None and user.check_password(password):
                self.user_cache = user
            else:
                raise forms.ValidationError(_("Usuário ou senha inválidos."))
        return self.cleaned_data

class CriarUsuarioForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput())

    class Meta:
        model = Usuario
        fields = (
            "username", "first_name", "last_name", "email",
            "setor", "cargo", "funcao", "perfil",
            "password1", "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # remove ":" automático após labels (opcional)
        self.label_suffix = ""

        base = (
            "w-full border border-gray-300 rounded-md px-3 py-2 "
            "text-black placeholder-gray-500 bg-white "
            "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )

        # autocompletes mais semânticos (melhora UX)
        autocomplete_map = {
            "username": "username",
            "first_name": "given-name",
            "last_name": "family-name",
            "email": "email",
            "password1": "new-password",
            "password2": "new-password",
        }

        # aplica classes e placeholders
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " " + base).strip()

            # placeholder só faz sentido em inputs de texto/email/senha
            input_type = getattr(field.widget, "input_type", "")
            if input_type in {"text", "email", "password"}:
                field.widget.attrs.setdefault("placeholder", field.label)

            # autocompletes
            field.widget.attrs["autocomplete"] = autocomplete_map.get(name, "off")

        # "placeholder" em selects = primeira opção vazia "Selecione..."
        for name in ["setor", "cargo", "funcao", "perfil"]:
            f = self.fields.get(name)
            if isinstance(f, forms.ModelChoiceField):
                f.empty_label = "Selecione..."
            elif isinstance(f, forms.ChoiceField):
                choices = list(f.choices)
                if not choices or choices[0][0] != "":
                    f.choices = [("", "Selecione...")] + choices

class TelefoneForm(forms.ModelForm):
    class Meta:
        model = Telefone
        fields = ("ddd", "numero", "ramal")

        widgets = {
            "ddd": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 py-2 text-black",
                "placeholder": "DDD"
            }),
            "numero": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 py-2 text-black",
                "placeholder": "Número"
            }),
            "ramal": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 py-2 text-black",
                "placeholder": "Ramal"
            }),
        }

# Formset de telefones
TelefoneFormSet = inlineformset_factory(
    Usuario, Telefone,
    form=TelefoneForm,
    extra=1,        # número de linhas iniciais
    can_delete=True # permite remover
)

