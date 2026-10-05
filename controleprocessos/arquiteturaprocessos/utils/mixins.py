from django.contrib import messages
from django.shortcuts import redirect

from arquiteturaprocessos.utils.utils import tem_permissao


class PermissaoRequiredMixin:
    """
    Permite acesso apenas a usuários que possuem
    a permissão exigida pela funcionalidade.
    """

    permissao_modulo = None
    permissao_funcionalidade = None
    permissao_acao = None

    def dispatch(self, request, *args, **kwargs):
        if not tem_permissao(
            request.user,
            self.permissao_modulo,
            self.permissao_funcionalidade,
            self.permissao_acao,
        ):
            messages.warning(
                request,
                "Você não tem permissão para acessar esta funcionalidade."
            )
            return redirect("arquiteturaprocessos:homepage")

        return super().dispatch(request, *args, **kwargs)