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

    def tem_acesso_permitido(self, usuario):
        return tem_permissao(
            usuario,
            self.permissao_modulo,
            self.permissao_funcionalidade,
            self.permissao_acao,
        )

    def dispatch(self, request, *args, **kwargs):
        if not self.tem_acesso_permitido(request.user):
            messages.warning(
                request,
                "Você não tem permissão para acessar esta funcionalidade."
            )
            return redirect("arquiteturaprocessos:homepage")

        return super().dispatch(request, *args, **kwargs)
