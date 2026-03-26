from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from .models import LogAcaoSistema
from django.contrib.auth.mixins import UserPassesTestMixin

# --------------------------------------------------------#
# LogAcao - Restrição de acesso, só para administradores  #
# --------------------------------------------------------#
class AdminOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

# --------------------------------#
# LogAcao - Listagem de Logs      #
# --------------------------------#
class LogAcaoListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = LogAcaoSistema
    template_name = "auditoria/logacoes.html"
    context_object_name = "logs"
    paginate_by = 20

    def get_queryset(self):
        return LogAcaoSistema.objects.select_related("usuario").order_by("-data_registro")

# --------------------------------#
# LogAcao - Detalhe do Log        #
# --------------------------------#
class LogAcaoDetailView(LoginRequiredMixin, AdminOnlyMixin, DetailView):
    model = LogAcaoSistema
    template_name = "auditoria/logacoes_detail.html"
    context_object_name = "log"
