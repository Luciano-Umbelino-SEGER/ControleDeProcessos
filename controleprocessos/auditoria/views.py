import json
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q, Value
from django.db.models.functions import Concat

from .models import LogAcaoSistema
from .utils import gerar_diff
from arquiteturaprocessos.utils.utils import usuario_tem_acesso_total


# --------------------------------------------------------#
# 🔐 Restrição de acesso — apenas administradores          #
# --------------------------------------------------------#
class AdminOnlyMixin(UserPassesTestMixin):

    def test_func(self):
        return usuario_tem_acesso_total(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Acesso restrito a administradores.")
        return redirect("arquiteturaprocessos:arquiteturaprocessos")  # ajuste se necessário


# --------------------------------#
# 📋 Listagem de Logs             #
# --------------------------------#
class LogAcaoListView(AdminOnlyMixin, LoginRequiredMixin, ListView):
    model = LogAcaoSistema
    template_name = "auditoria/logacoes.html"
    context_object_name = "logs"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            LogAcaoSistema.objects
            .select_related("usuario", "usuario__perfil")
            .order_by("-data_registro")
        )

        # 🔍 FILTROS
        usuario = self.request.GET.get("usuario")
        perfil = self.request.GET.get("perfil")
        acao = self.request.GET.get("acao")
        modelo = self.request.GET.get("modelo")
        data_inicio = self.request.GET.get("data_inicio")
        data_fim = self.request.GET.get("data_fim")

        if usuario:
            queryset = queryset.annotate(
                nome_completo=Concat("usuario__first_name", Value(" "), "usuario__last_name")
            ).filter(
                Q(usuario__username__icontains=usuario) |
                Q(nome_completo__icontains=usuario)
            )

        if perfil:
            queryset = queryset.filter(usuario__perfil__nome__icontains=perfil)

        if acao:
            queryset = queryset.filter(acao=acao)

        if modelo:
            queryset = queryset.filter(modelo_afetado__icontains=modelo)

        if data_inicio:
            queryset = queryset.filter(data_registro__date__gte=data_inicio)

        if data_fim:
            queryset = queryset.filter(data_registro__date__lte=data_fim)

        return queryset  # 🔥 ESSENCIAL

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get("page_size")

        try:
            return int(page_size)
        except (TypeError, ValueError):
            return 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query_params = self.request.GET.copy()

        # 🔹 SEM PAGE (para paginação)
        query_params_no_page = query_params.copy()
        if "page" in query_params_no_page:
            query_params_no_page.pop("page")

        # 🔹 COM PAGE (para detalhe)
        context["query_string"] = query_params_no_page.urlencode()
        context["query_string_full"] = query_params.urlencode()

        return context


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

        context["query_string"] = self.request.GET.urlencode()

        # 🔹 JSON formatado
        context["dados_antes_formatado"] = self.formatar_json(log.dados_antes)
        context["dados_depois_formatado"] = self.formatar_json(log.dados_depois)

        # 🔹 Diff só para UPDATE
        if log.acao == "UPDATE":
            context["diff"] = gerar_diff(log.dados_antes, log.dados_depois)
        else:
            context["diff"] = []

        return context