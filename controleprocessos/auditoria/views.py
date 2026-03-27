import json
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from .models import LogAcaoSistema


# --------------------------------------------------------#
# 🔐 Restrição de acesso — apenas administradores          #
# --------------------------------------------------------#
class AdminOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


# --------------------------------#
# 📋 Listagem de Logs             #
# --------------------------------#
class LogAcaoListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
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
# 🔍 Função para gerar diferenças #
# --------------------------------#
def gerar_diff(antes, depois):
    if not antes or not depois:
        return []

    diff = []
    chaves = set(antes.keys()) | set(depois.keys())

    for chave in chaves:
        valor_antes = antes.get(chave)
        valor_depois = depois.get(chave)

        if valor_antes != valor_depois:
            diff.append({
                "campo": chave,
                "antes": valor_antes,
                "depois": valor_depois,
            })

    return diff


# --------------------------------#
# 📄 Detalhe do Log              #
# --------------------------------#
class LogAcaoDetailView(LoginRequiredMixin, AdminOnlyMixin, DetailView):
    model = LogAcaoSistema
    template_name = "auditoria/form_logacoes.html"
    context_object_name = "log"

    def get_queryset(self):
        return LogAcaoSistema.objects.select_related(
            "usuario", "usuario__perfil"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log = self.object

        # 🔹 JSON formatado (para exibição bonita)
        context["dados_antes_formatado"] = (
            json.dumps(log.dados_antes, indent=2, ensure_ascii=False)
            if log.dados_antes else "{}"
        )

        context["dados_depois_formatado"] = (
            json.dumps(log.dados_depois, indent=2, ensure_ascii=False)
            if log.dados_depois else "{}"
        )

        # 🔹 Diff amigável
        context["diff"] = gerar_diff(log.dados_antes, log.dados_depois)

        return context