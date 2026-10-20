from django.contrib import messages
from django.shortcuts import redirect

from arquiteturaprocessos.utils.utils import tem_permissao


class PermissaoRequiredMixin:
    """
    Exige permissão de Visualizar para acessar a funcionalidade
    e a permissão específica para executar outras operações.
    """

    permissao_modulo = None
    permissao_funcionalidade = None
    permissao_acao = None

    def tem_acesso_permitido(self, usuario):
        modulo = self.permissao_modulo
        funcionalidade = self.permissao_funcionalidade
        acao = self.permissao_acao

        if not modulo or not funcionalidade or not acao:
            return False

        # A permissão Visualizar é obrigatória.
        if not tem_permissao(
            usuario,
            modulo,
            funcionalidade,
            "Visualizar",
        ):
            return False

        # Para Visualizar, a permissão básica já foi verificada.
        if acao == "Visualizar":
            return True

        # Demais operações exigem também a permissão específica.
        return tem_permissao(
            usuario,
            modulo,
            funcionalidade,
            acao,
        )

    def dispatch(self, request, *args, **kwargs):
        if not self.tem_acesso_permitido(request.user):
            messages.warning(
                request,
                "Você não tem permissão para acessar esta funcionalidade.",
            )
            return redirect("arquiteturaprocessos:homepage")

        return super().dispatch(request, *args, **kwargs)