from django.contrib import messages
from django.shortcuts import redirect
from arquiteturaprocessos.utils.utils import usuario_tem_acesso_total

class AcessoTotalRequiredMixin:
    """
    Permite acesso apenas a usuários com acesso total
    (Administrador ou Usuário Master)
    """

    def dispatch(self, request, *args, **kwargs):
        if not usuario_tem_acesso_total(request.user):
            messages.warning(
                request,
                "Você não tem permissão para acessar esta funcionalidade."
            )
            return redirect('arquiteturaprocessos:arquiteturaprocessos')

        return super().dispatch(request, *args, **kwargs)
