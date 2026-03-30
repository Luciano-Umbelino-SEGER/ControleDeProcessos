import json
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.shortcuts import redirect

from .models import LogAcaoSistema
from .utils import gerar_diff


# --------------------------------------------------------#
# 🔐 Restrição de acesso — apenas administradores          #
# --------------------------------------------------------#
class AdminOnlyMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, "Acesso restrito a administradores.")
        return redirect("home")  # ajuste se necessário


# --------------------------------#
# 📋 Listagem de Logs             #
# --------------------------------#
class LogAcaoListView(AdminOnlyMixin, LoginRequiredMixin, ListView):
    model = LogAcaoSistema
    template_name = "auditoria/logacoes.html"
    context_object_name = "logs"
    paginate_by = 20

    def get_queryset(self):
        return (
            LogAcaoSistema.objects
            .select_related("usuario", "usuario__perfil")
            .order_by("-data_registro")
        )


# --------------------------------#
# 📄 Detalhe do Log              #
# --------------------------------#
class LogAcaoDetailView(AdminOnlyMixin, LoginRequiredMixin, DetailView):
    model = LogAcaoSistema
    template_name = "auditoria/form_logacoes.html"
    context_object_name = "log"

    def get_queryset(self):
        return LogAcaoSistema.objects.select_related(
            "usuario", "usuario__perfil"
        )

    def formatar_json(self, dados):
        try:
            return json.dumps(dados or {}, indent=2, ensure_ascii=False)
        except Exception:
            return "{}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log = self.object

        # 🔹 JSON formatado
        context["dados_antes_formatado"] = self.formatar_json(log.dados_antes)
        context["dados_depois_formatado"] = self.formatar_json(log.dados_depois)

        # 🔹 Diff só para UPDATE
        if log.acao == "UPDATE":
            context["diff"] = gerar_diff(log.dados_antes, log.dados_depois)
        else:
            context["diff"] = []

        return context