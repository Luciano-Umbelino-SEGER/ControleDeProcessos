from django import forms
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
    email = forms.EmailField()


    class Meta:
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "setor", "cargo", "funcao", "perfil", "password1", "password2")

