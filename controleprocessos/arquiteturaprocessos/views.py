# views.py (revisado)
from datetime import datetime, time, timedelta
import os
import json
import re

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect, get_object_or_404
from collections import Counter
from django.urls import reverse, reverse_lazy
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django import forms
from django.forms import inlineformset_factory
from django.http import JsonResponse, FileResponse, Http404
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q, Max, Exists, OuterRef, Count
from calendar import month_abbr
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_sameorigin

from pathlib import Path
from urllib.parse import unquote
import mimetypes
from arquiteturaprocessos.utils.utils import usuario_tem_acesso_total, definir_senha_e_enviar_email, parse_date
from arquiteturaprocessos.utils.mixins import AcessoTotalRequiredMixin
from arquiteturaprocessos.utils.status_utils import contar_status, normalizar_status

from .models import (
    Usuario, Telefone, MacroprocessoNivel1, MacroprocessoNivel2,
    Classificacao, ModelagemProcesso, Processo, TiposDocumento,  ProcessoDocumento, ProcessoMapear,  ContatoAreaSeger,
)
from auditoria.models import LogAcaoSistema
from auditoria.services import registrar_log
from auditoria.utils import registrar_tentativa, esta_bloqueado, resetar_tentativas

from .forms import (
    Form_UsuarioForm, EditarUsuarioForm, TelefoneForm, TelefoneFormSet, CustomAuthenticationForm,
    Form_ClassificacaoForm, Form_MacroProcessoNivel1Form, Form_MacroProcessoNivel2Form,
    Form_ModelagemProcessoForm, Form_ProcessoForm, Form_TipoDocumentoForm, Form_ProcessoMapearForm,
)


# ---------------------------------------------------
# Utility to safely generate a username from names
# ---------------------------------------------------
def make_username_from_names(first_name: str, last_name: str) -> str:
    # cria nome.sobrenome em lowercase, sem espaços, mantendo apenas alfanumérico + ponto
    base = f"{(first_name or '').strip()}.{(last_name or '').strip()}"
    username = base.lower()
    # remove acentos/normalização simples (opcional: aqui apenas remove espaços e não-alphanum exceto '.')
    username = re.sub(r"\s+", "", username)
    username = re.sub(r"[^a-z0-9\.]", "", username)
    return username

# ---------------------------
# PDF visualizer (secure)
# ---------------------------
@xframe_options_sameorigin
def visualizar_pdf(request, path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = (media_root / path).resolve()

    if not str(file_path).startswith(str(media_root)) or not file_path.exists() or not file_path.is_file():
        raise Http404("Arquivo não encontrado")

    ctype, _ = mimetypes.guess_type(str(file_path))
    if ctype != 'application/pdf':
        raise Http404("Tipo de arquivo não permitido")

    response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{file_path.name}"'
    response['Content-Security-Policy'] = "frame-ancestors 'self'"
    return response

# ------------------------------------------------
# Modelagem filtrada helper por tipo de documento
# ------------------------------------------------
def get_modelagem_filtrada():
    hoje = timezone.now().date()

    base_qs = (
        ModelagemProcesso.objects
        .filter(
            Q(vigencia_fim__isnull=True) | Q(vigencia_fim__gte=hoje)
        )
        .select_related("tipo_documento")
        .order_by("titulo")
    )

    modelos = base_qs.filter(
        tipo_documento__nome__icontains="modelo"
    )

    normas = base_qs.filter(
        tipo_documento__nome__icontains="norma"
    )

    return modelos, normas


# -------------------------------
# Extrair Modelagens - Processos
# -------------------------------
def extrair_modelagens_do_post(request):
    ids = set()

    # base
    if request.POST.get("modelagem_processo"):
        ids.add(request.POST.get("modelagem_processo"))

    if request.POST.get("norma_procedimento"):
        ids.add(request.POST.get("norma_procedimento"))

    # extras
    ids.update(request.POST.getlist("modelagem_processo_extra[]"))
    ids.update(request.POST.getlist("norma_procedimento_extra[]"))

    # limpa vazios
    ids = {i for i in ids if i}

    return ModelagemProcesso.objects.filter(id__in=ids)

# ----------------------------------
# Recuperar Documentos - Processos
# ----------------------------------
def get_documentos_por_processo(processo):
    modelos = []
    normas = []

    relacoes = (
        ProcessoDocumento.objects
        .select_related("modelagem_processo__tipo_documento")
        .filter(processo=processo)
    )

    for rel in relacoes:
        doc = rel.modelagem_processo
        tipo_nome = doc.tipo_documento.nome.upper().strip()

        if tipo_nome == "MODELO DE PROCESSO":
            modelos.append(doc)
        elif tipo_nome == "NORMA DE PROCEDIMENTO":
            normas.append(doc)

    return modelos, normas

# =========================================
# UTIL – Persistência de Documentos (1 → N)
# =========================================
def salvar_documentos_processo(request, processo):
    """
    Salva (recria) todos os documentos associados a um processo,
    tanto para inclusão quanto para edição.
    """

    # 1️⃣ Remove todos os vínculos existentes (edição segura)
    ProcessoDocumento.objects.filter(processo=processo).delete()

    documentos_ids = []

    # 🔹 Modelo de Processo (base)
    modelo_principal = request.POST.get("modelagem_processo")
    if modelo_principal:
        documentos_ids.append(modelo_principal)

    # 🔹 Modelos de Processo (extras)
    documentos_ids.extend(
        request.POST.getlist("modelagem_processo_extra[]")
    )

    # 🔹 Norma de Procedimento (base)
    norma_principal = request.POST.get("norma_procedimento")
    if norma_principal:
        documentos_ids.append(norma_principal)

    # 🔹 Normas de Procedimento (extras)
    documentos_ids.extend(
        request.POST.getlist("norma_procedimento_extra[]")
    )

    # 2️⃣ Remove vazios e duplicados
    documentos_ids = list(
        set(filter(None, documentos_ids))
    )

    # 3️⃣ Cria os vínculos Processo ↔ Documento
    ProcessoDocumento.objects.bulk_create([
        ProcessoDocumento(
            processo=processo,
            modelagem_processo_id=doc_id
        )
        for doc_id in documentos_ids
    ])

# --------------------------------------
# Obter Responsável Contatos Area SEGER
# --------------------------------------
def buscar_contato_area(request):
    area_id = request.GET.get("area_id")

    if not area_id:
        return JsonResponse({}, status=400)

    try:
        contato = ContatoAreaSeger.objects.get(id=area_id, ativo=True)

        return JsonResponse({
            "titular": contato.titular or "",
            "telefone": contato.telefone or "",
            "email": contato.email or "",
        })

    except ContatoAreaSeger.DoesNotExist:
        return JsonResponse({}, status=404)

# ---------------------------
# Login view
# ---------------------------
def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


class CustomLoginView(LoginView):
    template_name = 'usuario/fazer_login.html'
    authentication_form = CustomAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('arquiteturaprocessos:arquiteturaprocessos')
        return super().dispatch(request, *args, **kwargs)

    # 🔥 👇 INSERIR AQUI
    def form_valid(self, form):
        username = self.request.POST.get("username", "").strip()
        ip = get_client_ip(self.request)

        # 🚫 BLOQUEIO ANTES DE AUTENTICAR
        if esta_bloqueado(username, ip):
            messages.error(
                self.request,
                "Muitas tentativas inválidas. Tente novamente em alguns minutos."
            )
            return self.form_invalid(form)

        # ✔ LOGIN OK → RESETA TENTATIVAS
        resetar_tentativas(username, ip)

        return super().form_valid(form)

    # 🔽 já existe
    def form_invalid(self, form):
        username = self.request.POST.get("username", "").strip()
        ip = get_client_ip(self.request)

        # 📊 REGISTRA TENTATIVA
        tentativas = registrar_tentativa(username, ip)

        # 🔒 VERIFICA BLOQUEIO
        bloqueado = esta_bloqueado(username, ip)

        # 🎨 DEFINE COR DINÂMICA
        if tentativas >= 5:
            cor = "text-red-700"
        elif tentativas >= 4:
            cor = "text-orange-600"
        else:
            cor = "text-gray-700"

        # 🧠 MENSAGEM FINAL
        if bloqueado:
            mensagem = "Usuário temporariamente bloqueado por excesso de tentativas."
        else:
            mensagem = f"Tentativas: {tentativas}/5"

        # 🎯 CONTADOR COM CORES
        if bloqueado:
            mensagem = "🔴 Usuário temporariamente bloqueado por excesso de tentativas."

        elif tentativas == 1:
            mensagem = f"🟢  Tentativas: {tentativas}/5"

        elif tentativas in [2, 3]:
            mensagem = f"🟠 Tentativas: {tentativas}/5"

        elif tentativas >= 4:
            mensagem = f"🔴 Tentativas: {tentativas}/5"

        form.add_error(
            None,
            f"Usuário ou senha incorretos. {mensagem}"
        )

        # 🔥 LOG (mantém como está)
        if bloqueado:
            registrar_log(
                request=self.request,
                acao="LOGIN_BLOQUEADO",
                modelo="Autenticação",
                descricao=f"Usuário {username} bloqueado por excesso de tentativas de login",
                dados_depois={
                    "username": username,
                    "ip": ip,
                    "tentativas": tentativas,
                }
            )
        else:
            registrar_log(
                request=self.request,
                acao="LOGIN_ERRO",
                modelo="Autenticação",
                descricao=f"Tentativa inválida ({tentativas}/5) - Usuário: {username}",
                dados_depois={
                    "username": username,
                    "ip": ip,
                }
            )

        return super().form_invalid(form)

# ---------------------------
# Alterar Senha
# ---------------------------
@login_required
def alterar_senha(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()

            update_session_auth_hash(request, user)

            # 🔥 LOG DA ALTERAÇÃO DE SENHA
            registrar_log(
                request=request,  # 🎯 próprio usuário
                acao="UPDATE",
                modelo="Autenticação",
                descricao="Usuário alterou sua senha",
                dados_depois={
                    "username": user.username
                }
            )

            messages.success(
                request,
                "Senha alterada com sucesso."
            )
            return redirect("arquiteturaprocessos:arquiteturaprocessos")

    else:
        form = PasswordChangeForm(user=request.user)

    return render(
        request,
        "usuario/alterar_senha.html",
        {"form": form}
    )

# ---------------------------
# Resetar Senha
# ---------------------------
@login_required
def resetar_senha_usuario(request, pk):
    if not usuario_tem_acesso_total(request.user):
        messages.error(
            request,
            "Você não tem permissão para reenviar link de senha."
        )
        return redirect("arquiteturaprocessos:cadastrousuarios")

    usuario = get_object_or_404(
        Usuario,
        pk=pk,
        is_master=False
    )

    try:
        # 🔥 ENVIA EMAIL CORRETO
        definir_senha_e_enviar_email(usuario, reset=True)

        # 🔥 LOG CORRETO
        registrar_log(
            request=request,  # 👤 ADMIN (executor)
            acao="UPDATE",
            modelo="Autenticação",
            descricao=f"Administrador solicitou redefinição de senha para {usuario.get_full_name()}",
            dados_depois={
                "usuario_afetado": usuario.username
            }
        )

    except Exception as e:
        messages.warning(
            request,
            "Houve falha ao enviar o e-mail de redefinição de senha."
        )

    messages.success(
        request,
        f"Um link para redefinição de senha foi enviado para "
        f"{usuario.get_full_name() or usuario.username}."
    )

    return redirect("arquiteturaprocessos:cadastrousuarios")

# ---------------------------
# Classificações CRUD
# ---------------------------
class Classificacoes(LoginRequiredMixin, ListView):
    model = Classificacao
    template_name = 'estrutura/classificacoes.html'
    context_object_name = 'classificacoes'
    queryset = Classificacao.objects.order_by('nome')


class CriarClassificacao(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_classificacao.html'
    form_class = Form_ClassificacaoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Classificação '{self.object.nome}' criada com sucesso!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível criar a classificação. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:classificacoes')


class VisualizarClassificacao(LoginRequiredMixin, DetailView):
    template_name = 'estrutura/form_classificacao.html'
    model = Classificacao
    context_object_name = 'classificacao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classificacao = self.get_object()
        context['form'] = Form_ClassificacaoForm(instance=classificacao, modo_visualizacao=True)
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

class EditarClassificacao(LoginRequiredMixin, UpdateView):
    model = Classificacao
    template_name = 'estrutura/form_classificacao.html'
    context_object_name = 'classificacao'
    form_class = Form_ClassificacaoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"Classificação '{self.object.nome}' atualizada com sucesso!")
        return resp

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar a classificação. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:classificacoes')

class ExcluirClassificacao(LoginRequiredMixin, DetailView):
    model = Classificacao
    template_name = 'estrutura/form_classificacao.html'
    context_object_name = 'classificacao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method != 'POST':
            context['form'] = Form_ClassificacaoForm(instance=self.get_object(), modo_exclusao=True)
        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
        })
        return context

    def post(self, request, *args, **kwargs):
        classificacao = self.get_object()
        processo_associado = Processo.objects.filter(classificacao=classificacao).first()
        if processo_associado:
            messages.error(request,
                f"Não é possível excluir a classificação '{classificacao.nome}', pois está associada ao processo '{processo_associado.nome}'."
            )
            return redirect('arquiteturaprocessos:classificacoes')

        classificacao.delete()
        messages.success(request, f"Classificação '{classificacao.nome}' excluída com sucesso!")
        return redirect('arquiteturaprocessos:classificacoes')

# ---------------------------------------------
# ARQUITETURA DE PROCESSOS (Tela Pública)
# ---------------------------------------------
class ArquiteruraProcessos(ListView):
    model = Processo
    template_name = "arquiteturaprocessos/arquiteturaprocessos.html"
    context_object_name = "processos"
    paginate_by = 30
    ordering = ["id"]

    # -----------------------------------------
    # Montagem de documentos (reutilizável)
    # -----------------------------------------
    def montar_docs(self, documentos_qs):
        modelos = []
        normas = []

        for pd in documentos_qs:
            mp = pd.modelagem_processo
            if not mp:
                continue

            modelo_pdf = None
            norma_link = None

            # 📄 PDF – Modelo de Processo
            if mp.documento_modelagem_processo:
                nome_pdf = os.path.basename(mp.documento_modelagem_processo.name)
                modelo_pdf = {
                    "displayname": nome_pdf,
                    "url": mp.documento_modelagem_processo.url,
                }

            # 🔗 LINK – Norma de Procedimento
            if mp.link_normaprocedimento:
                nome_link = os.path.basename(unquote(mp.link_normaprocedimento))
                norma_link = {
                    "displayname": nome_link,
                    "url": mp.link_normaprocedimento,
                }

            doc = {
                "titulo": mp.titulo or "",
                "tema": mp.tema or "",
                "versao": mp.versao or "",
                "emitente": mp.emitente or "",
                "vigencia": (
                    mp.vigencia_inicio.strftime("%d/%m/%Y")
                    if mp.vigencia_inicio else ""
                ),
                "modelo": modelo_pdf,  # 👈 PDF
                "norma": norma_link,  # 👈 LINK
            }

            # separação por tipo de documento
            if mp.tipo_documento_id == 1:
                modelos.append(doc)
            elif mp.tipo_documento_id == 2:
                normas.append(doc)

        return {
            "modelos": modelos,
            "normas": normas,
        }

    # -----------------------------------------
    # Query principal
    # -----------------------------------------
    from datetime import datetime, time

    def get_queryset(self):
        req = self.request.GET

        nome = req.get("nome", "").strip()
        classificacao = req.get("classificacao", "").strip()
        macro1 = req.get("macro1", "").strip()
        macro2 = req.get("macro2", "").strip()
        area = req.get("area", "").strip()

        cri_de = parse_date(req.get("criacao_de"))
        cri_ate = parse_date(req.get("criacao_ate"))

        # 🔥 Validação antes
        if cri_de and cri_ate and cri_ate < cri_de:
            messages.error(self.request, "A data final deve ser maior ou igual à data inicial.")
            return Processo.objects.none()

        qs = (
            Processo.objects
            .filter(parent__isnull=True)
            .select_related(
                "classificacao",
                "macroprocesso_nivel1",
                "macroprocesso_nivel2",
                "usuario_cadastro",
                "usuario_atualizacao",
            )
            .prefetch_related(
                "documentos__modelagem_processo__tipo_documento",
                "subprocessos__documentos__modelagem_processo__tipo_documento",
            )
            .order_by("id")
        )

        # --------------------
        # Filtros
        # --------------------
        if nome:
            qs = qs.filter(nome__icontains=nome)

        if classificacao:
            qs = qs.filter(classificacao_id=classificacao)

        if macro1:
            qs = qs.filter(macroprocesso_nivel1__nome__icontains=macro1)

        if macro2:
            qs = qs.filter(macroprocesso_nivel2__nome__icontains=macro2)

        if area:
            qs = qs.filter(area_responsavel__icontains=area)

        if cri_de:
            qs = qs.filter(data_criacao__gte=cri_de)

        if cri_ate:
            fim_do_dia = datetime.combine(cri_ate, time.max)
            qs = qs.filter(data_criacao__lte=fim_do_dia)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        page = ctx.get("page_obj")
        processos = page.object_list if page else ctx["processos"]

        documentos_por_processo = {}

        for proc in processos:
            # -------- PROCESSO --------
            docs = self.montar_docs(proc.documentos.all())

            proc.docs_modelos = docs["modelos"]
            proc.docs_normas = docs["normas"]
            proc.docs_count = len(docs["modelos"]) + len(docs["normas"])

            documentos_por_processo[str(proc.id)] = {
                "modelos": docs["modelos"],
                "normas": docs["normas"],
            }

            # -------- SUBPROCESSOS --------
            for sub in proc.subprocessos.all():
                sub_docs = self.montar_docs(sub.documentos.all())

                sub.docs_modelos = sub_docs["modelos"]
                sub.docs_normas = sub_docs["normas"]
                sub.docs_count = len(sub_docs["modelos"]) + len(sub_docs["normas"])

                documentos_por_processo[str(sub.id)] = {
                    "modelos": sub_docs["modelos"],
                    "normas": sub_docs["normas"],
                }

        ctx["classificacoes"] = Classificacao.objects.all().order_by("nome")
        ctx["documentos_por_processo"] = documentos_por_processo
        ctx["total_registros"] = self.object_list.count()

        return ctx

# --------------------------------
# Dashboard
# --------------------------------
class EstatisticasDashboard(LoginRequiredMixin, TemplateView):

    template_name = "estatisticas/dashboard.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        processos = Processo.objects.all()

        # 🔥 STATUS PADRONIZADO
        status_data = contar_status(processos)

        context["status_labels"] = ["Iniciado", "Ativo", "Concluído"]
        context["status_valores"] = [
            status_data["iniciado"],
            status_data["ativo"],
            status_data["concluido"],
        ]

        # ---------------------------
        # Classificação
        # ---------------------------
        classificacao = (
            Processo.objects
            .values("classificacao__nome")
            .annotate(total=Count("id"))
        )

        context["class_labels"] = [c["classificacao__nome"] for c in classificacao]
        context["class_valores"] = [c["total"] for c in classificacao]

        # ---------------------------
        # Área
        # ---------------------------
        area = (
            Processo.objects
            .values("area_responsavel")
            .annotate(total=Count("id"))
        )

        context["area_labels"] = [a["area_responsavel"] for a in area]
        context["area_valores"] = [a["total"] for a in area]

        # ---------------------------
        # Mês
        # ---------------------------
        ano_atual = datetime.now().year
        mes_atual = datetime.now().month

        dados = (
            Processo.objects
            .filter(data_criacao__year=ano_atual)
            .annotate(mes=TruncMonth("data_criacao"))
            .values("mes")
            .annotate(total=Count("id"))
        )

        dados_dict = {d["mes"].month: d["total"] for d in dados}

        mes_labels = []
        mes_valores = []

        for m in range(1, mes_atual + 1):
            mes_labels.append(datetime(ano_atual, m, 1).strftime("%b"))
            mes_valores.append(dados_dict.get(m, 0))

        context["mes_labels"] = mes_labels
        context["mes_valores"] = mes_valores

        return context

# --------------------------------
# Processos a Mapear
# --------------------------------
class EstatisticasProcessosMapear(LoginRequiredMixin, TemplateView):

    template_name = "estatisticas/estatisticaprocessos_mapear.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        processos_mapear = (
            ProcessoMapear.objects
            .values("area_responsavel")
            .annotate(total=Count("id"))
        )

        context["labels"] = [p["area_responsavel"] for p in processos_mapear]
        context["valores"] = [p["total"] for p in processos_mapear]

        return context

# --------------------------------
# Estatísticas de Processos
# --------------------------------
class EstatisticasProcessos(LoginRequiredMixin, TemplateView):

    template_name = "estatisticas/estatisticaprocessos.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        processos = Processo.objects.all()

        # 🔥 STATUS CENTRALIZADO
        status_data = contar_status(processos)

        context["total_processos"] = status_data["total"]
        context["total_iniciado"] = status_data["iniciado"]
        context["total_ativo"] = status_data["ativo"]
        context["total_concluido"] = status_data["concluido"]

        # 🔥 GRÁFICO DE ESTADO (FALTAVA ISSO!)
        context["estado_labels"] = ["Iniciado", "Ativo", "Concluído"]
        context["estado_valores"] = [
            status_data["iniciado"],
            status_data["ativo"],
            status_data["concluido"],
        ]

        # ---------------------------
        # Classificação
        # ---------------------------
        classificacao = (
            Processo.objects
            .values("classificacao__nome")
            .annotate(total=Count("id"))
        )

        context["class_labels"] = [c["classificacao__nome"] for c in classificacao]
        context["class_valores"] = [c["total"] for c in classificacao]

        # ---------------------------
        # Área x Status
        # ---------------------------

        areas = sorted(
            {p.area_responsavel for p in processos if p.area_responsavel}
        )

        status_lista = ["iniciado", "ativo", "concluido"]

        estrutura = {s: [0] * len(areas) for s in status_lista}

        for p in processos:

            area = p.area_responsavel
            status = normalizar_status(p.status)

            if area in areas and status in estrutura:
                index = areas.index(area)
                estrutura[status][index] += 1

        context["area_labels"] = areas
        context["area_iniciado"] = estrutura["iniciado"]
        context["area_ativo"] = estrutura["ativo"]
        context["area_concluido"] = estrutura["concluido"]

        return context

# --------------------------------
# Comparativos
# --------------------------------
class EstatisticaComparativos(LoginRequiredMixin, TemplateView):

    template_name = "estatisticas/comparativos.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # -----------------------------
        # Processos Criados por mês
        # -----------------------------
        criados = (
            Processo.objects
            .annotate(mes=TruncMonth("data_criacao"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )

        # -----------------------------
        # Processos Concluídos por mês
        # -----------------------------
        concluidos = (
            Processo.objects
            .exclude(data_conclusao__isnull=True)
            .annotate(mes=TruncMonth("data_conclusao"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )

        # converter para dicionário
        dict_criados = {c["mes"].strftime("%b/%Y"): c["total"] for c in criados}
        dict_concluidos = {c["mes"].strftime("%b/%Y"): c["total"] for c in concluidos}

        meses = sorted(set(dict_criados.keys()) | set(dict_concluidos.keys()))

        valores_criados = [dict_criados.get(m, 0) for m in meses]
        valores_concluidos = [dict_concluidos.get(m, 0) for m in meses]

        context["labels"] = meses
        context["criados"] = valores_criados
        context["concluidos"] = valores_concluidos

        return context

# ---------------------------
#  Processo a Mapear
# ---------------------------
class ProcessosMapear(LoginRequiredMixin, ListView):
    model = ProcessoMapear
    template_name = 'processosmapear/processosmapear.html'
    context_object_name = 'processosmapear'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user.perfil.nome.lower() != 'administrador':
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['classificacoes'] = Classificacao.objects.all().order_by("nome")
        context['total_registros'] = self.get_queryset().count()

        return context

    def get_queryset(self):

        queryset = super().get_queryset().order_by('-data_criacao')

        # ===== FILTROS =====
        nome = self.request.GET.get("nome")
        tipo = self.request.GET.get("tipo")
        classificacao = self.request.GET.get("classificacao")
        macro1 = self.request.GET.get("macro1")
        macro2 = self.request.GET.get("macro2")
        area = self.request.GET.get("area")
        cri_de = parse_date(self.request.GET.get("criacao_de"))
        cri_ate = parse_date(self.request.GET.get("criacao_ate"))

        if cri_de and cri_ate and cri_ate < cri_de:
            messages.error(self.request, "A data final deve ser maior ou igual à data inicial.")
            return ProcessoMapear.objects.none()

        if nome:
            queryset = queryset.filter(nome__icontains=nome)

        if tipo:
            queryset = queryset.filter(tipo=tipo)

        if classificacao:
            queryset = queryset.filter(classificacao_id=classificacao)

        if macro1:
            queryset = queryset.filter(macroprocesso_nivel1__nome__icontains=macro1)

        if macro2:
            queryset = queryset.filter(macroprocesso_nivel2__nome__icontains=macro2)

        if area:
            queryset = queryset.filter(area_responsavel__icontains=area)

        if cri_de:
            queryset = queryset.filter(data_criacao__gte=cri_de)

        if cri_ate:
            fim_do_dia = datetime.combine(cri_ate, time.max)
            queryset = queryset.filter(data_criacao__lte=fim_do_dia)

        return queryset.select_related(
            'classificacao',
            'macroprocesso_nivel1',
            'macroprocesso_nivel2',
            'parent'
        )

# --------------------------------#
# Criar Processo a Mapear         #
# --------------------------------#
class CriarProcessoMapear(LoginRequiredMixin, CreateView):
    model = ProcessoMapear
    form_class = Form_ProcessoMapearForm
    template_name = "processosmapear/form_processomapear.html"
    success_url = reverse_lazy("arquiteturaprocessos:processosmapear")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        agora_local = timezone.localtime(timezone.now())

        context.update({
            "modo_inclusao": True,
            "modo_visualizacao": False,
            "modo_exclusao": False,
            "modo_edicao": False,

            "cadastro_data": agora_local.strftime("%d/%m/%Y %H:%M:%S"),
            "cadastro_user": self.request.user.get_full_name()
                             or self.request.user.username,

            "atualizacao_data": "",
            "atualizacao_user": "",
        })

        return context

    def form_valid(self, form):
        processomapear = form.save(commit=False)

        # 🔥 REGRA MÍNIMA ESTRUTURAL
        if processomapear.tipo == ProcessoMapear.TIPO_PROCESSO:
            processomapear.parent = None

        processomapear.usuario_cadastro = self.request.user
        processomapear.usuario_atualizacao = None

        processomapear.save()

        messages.success(
            self.request,
            f"Processo a Mapear '{processomapear.nome}' criado com sucesso!"
        )

        self.object = processomapear
        return redirect(self.success_url)

# --------------------------------#
# Visualizar Processo a Mapear    #
# --------------------------------#
class VisualizarProcessoMapear(LoginRequiredMixin, DetailView):
    model = ProcessoMapear
    form_class = Form_ProcessoMapearForm
    template_name = "processosmapear/form_processomapear.html"
    context_object_name = 'processomapear'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processomapear = self.object

        context["form"] = Form_ProcessoMapearForm(
            instance=processomapear
        )

        context.update({
            "modo_visualizacao": True,
            "modo_inclusao": False,
            "modo_edicao": False,
            "modo_exclusao": False,

            "cadastro_data": (
                timezone.localtime(processomapear.data_criacao)
                .strftime("%d/%m/%Y %H:%M:%S")
            ),

            "cadastro_user": (
                processomapear.usuario_cadastro.get_full_name()
                if processomapear.usuario_cadastro else ""
            ),

            "atualizacao_data": (
                timezone.localtime(processomapear.data_atualizacao)
                .strftime("%d/%m/%Y %H:%M:%S")
                if processomapear.data_atualizacao else ""
            ),

            "atualizacao_user": (
                processomapear.usuario_atualizacao.get_full_name()
                if processomapear.usuario_atualizacao else ""
            ),
        })

        return context
# --------------------------------#
# Editar Processo a Mapear        #
# --------------------------------#
class EditarProcessoMapear(LoginRequiredMixin, UpdateView):
    model = ProcessoMapear
    form_class = Form_ProcessoMapearForm
    template_name = "processosmapear/form_processomapear.html"
    success_url = reverse_lazy("arquiteturaprocessos:processosmapear")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processomapear = self.object

        if self.request.session.pop("confirmar_iniciar", None):
            context["confirmar_iniciar"] = True

        context.update({
            "modo_edicao": True,
            "modo_inclusao": False,
            "modo_visualizacao": False,
            "modo_exclusao": False,

            "cadastro_data": (
                timezone.localtime(processomapear.data_criacao)
                .strftime("%d/%m/%Y %H:%M:%S")
            ),

            "cadastro_user": (
                processomapear.usuario_cadastro.get_full_name()
                if processomapear.usuario_cadastro else ""
            ),

            "atualizacao_data": (
                timezone.localtime(processomapear.data_atualizacao)
                .strftime("%d/%m/%Y %H:%M:%S")
                if processomapear.data_atualizacao else ""
            ),

            "atualizacao_user": (
                processomapear.usuario_atualizacao.get_full_name()
                if processomapear.usuario_atualizacao else ""
            ),
        })

        return context

    def form_valid(self, form):
        processomapear = form.save(commit=False)

        if processomapear.tipo == ProcessoMapear.TIPO_PROCESSO:
            processomapear.parent = None

        acao = self.request.POST.get("acao")

        # 🔥 Validação forte antes do modal
        if acao == "iniciar":

            erros = processomapear.validar_para_iniciar()

            if erros:
                for erro in erros:
                    form.add_error(None, erro)

                return self.form_invalid(form)

        # 🔥 Persistência normal
        processomapear.usuario_atualizacao = self.request.user
        processomapear.data_atualizacao = timezone.now()
        processomapear.save()
        self.object = processomapear

        if acao == "iniciar":
            self.request.session["confirmar_iniciar"] = True
            return redirect(
                "arquiteturaprocessos:editar_processomapear",
                pk=processomapear.pk
            )

        messages.success(
            self.request,
            f"Processo a Mapear '{processomapear.nome}' atualizado com sucesso!"
        )

        return redirect(self.success_url)

# --------------------------------------------------#
# Iniciar Processo - Processo a Mapear --> processo #
# --------------------------------------------------#
class ExecutarIniciarProcessoMapear(LoginRequiredMixin, View):

    def post(self, request, pk):

        processomapear = get_object_or_404(ProcessoMapear, pk=pk)

        erros = processomapear.validar_para_iniciar()

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return redirect("arquiteturaprocessos:editar_processomapear", pk=pk)

        # 🔥 Transformação segura
        with transaction.atomic():

            processo = Processo.objects.create(
                nome=processomapear.nome.strip(),
                gestor=processomapear.gestor.strip(),
                email=processomapear.email.strip(),
                telefone=processomapear.telefone.strip(),
                objetivo=processomapear.objetivo.strip(),
                observacao=processomapear.observacao,
                classificacao=processomapear.classificacao,
                macroprocesso_nivel1=processomapear.macroprocesso_nivel1,
                macroprocesso_nivel2=processomapear.macroprocesso_nivel2,
                parent=processomapear.parent if processomapear.tipo == ProcessoMapear.TIPO_SUBPROCESSO else None,
                area_responsavel=processomapear.area_responsavel.strip(),
                usuario_cadastro=processomapear.usuario_cadastro,  # mantém autor original
            )

            processomapear.delete()

        messages.success(
            request,
            f"Processo '{processo.nome}' criado com sucesso!"
        )

        return redirect("arquiteturaprocessos:processos")

# --------------------------------#
# Excluir Processo a Mapear       #
# --------------------------------#
class ExcluirProcessoMapear(LoginRequiredMixin, DetailView):
    model = ProcessoMapear
    form_class = Form_ProcessoMapearForm
    template_name = "processosmapear/form_processomapear.html"
    context_object_name = "processosmapear"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processomapear = self.object

        context["form"] = Form_ProcessoMapearForm(
            instance=processomapear,
            modo_exclusao=True
        )

        context.update({
            "modo_exclusao": True,
            "modo_visualizacao": False,
            "modo_inclusao": False,
            "modo_edicao": False,

            # 🔵 CAMPOS DE AUDITORIA
            "cadastro_data": processomapear.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if processomapear.data_criacao else "",
            "cadastro_user": processomapear.usuario_cadastro if processomapear.usuario_cadastro else "",
            "atualizacao_data": processomapear.data_atualizacao.strftime(
                "%d/%m/%Y %H:%M:%S") if processomapear.data_atualizacao else "",
            "atualizacao_user": processomapear.usuario_atualizacao if processomapear.usuario_atualizacao else "",
        })

        return context

    def post(self, request, *args, **kwargs):
        processomapear = self.get_object()
        processomapear.delete()

        messages.success(
            request,
            f"Processo a Mapear '{processomapear.nome}' excluído com sucesso!"
        )

        return redirect("arquiteturaprocessos:processosmapear")

# ------------------------------
# Cadastro / Listagem Usuários
# ------------------------------
class CadastroUsuarios(LoginRequiredMixin, AcessoTotalRequiredMixin, ListView):
    template_name = 'usuario/cadastrousuarios.html'
    model = Usuario
    context_object_name = 'usuarios'

    def get_queryset(self):
        status = self.request.GET.get("status", "ativos")

        queryset = Usuario.objects.filter(is_master=False)

        if status == "inativos":
            return queryset.filter(is_active=False).order_by(
                "perfil__nome",
                "username"
            )

        return queryset.filter(is_active=True).order_by(
            "perfil__nome",
            "username"
        )

# ----------------------------------------
# Criar Usuário (com username automático)
# ----------------------------------------
class CriarUsuario(LoginRequiredMixin, AcessoTotalRequiredMixin, CreateView):
    template_name = 'usuario/form_usuario.html'
    form_class = Form_UsuarioForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        if self.request.POST:
            context['telefones'] = TelefoneFormSet(self.request.POST, prefix='telefones')
        else:
            context['telefones'] = TelefoneFormSet(prefix='telefones')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        telefones = context['telefones']

        if not telefones.is_valid():
            messages.error(self.request, "Corrija os erros abaixo nos telefones.")
            return self.render_to_response(self.get_context_data(form=form))

        user = form.save(commit=False)

        # 🔐 Garantias de segurança
        user.is_master = False
        user.set_unusable_password()

        # Username automático
        username = make_username_from_names(user.first_name, user.last_name)
        if not username:
            messages.error(
                self.request,
                "Nome e Sobrenome são necessários para gerar o username."
            )
            return self.render_to_response(self.get_context_data(form=form))

        if Usuario.objects.filter(username=username).exists():
            messages.error(
                self.request,
                f"Não foi possível criar o usuário: o username '{username}' já existe."
            )
            return self.render_to_response(self.get_context_data(form=form))

        user.username = username
        user.is_active = self.request.POST.get("is_active") == "True"
        user.data_ativacaodesativacao = timezone.now()
        user.date_joined = timezone.now()

        # Salva para obter PK
        user.save()

        # 🔐 Envio de e-mail para definição de senha
        try:
            definir_senha_e_enviar_email(user, reset=False)
        except Exception as e:
            messages.warning(
                self.request,
                "Usuário criado, mas houve falha no envio do e-mail de definição de senha."
            )

        # Telefones
        telefones.instance = user
        telefones.save()

        # (Parte 5.3) — envio de e-mail com senha_temporaria

        messages.success(
            self.request,
            f"Usuário {user.get_full_name()} criado com sucesso!"
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('arquiteturaprocessos:cadastrousuarios')


# ---------------------------
# Usuário — Visualizar
# ---------------------------
class VisualizarUsuario(LoginRequiredMixin, AcessoTotalRequiredMixin, DetailView):
    template_name = 'usuario/form_usuario.html'
    model = Usuario
    context_object_name = 'usuario'

    def get_object(self):
        return get_object_or_404(
            Usuario,
            pk=self.kwargs['pk'],
            is_master=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.object

        context['form'] = Form_UsuarioForm(instance=usuario, modo_visualizacao=True)

        TelefoneFormSetVisualizacao = inlineformset_factory(
             Usuario,
             Telefone,
             form=TelefoneForm,
             extra=0,
             can_delete=False
        )
        context['telefones'] = TelefoneFormSetVisualizacao(instance=usuario, prefix='telefones')

        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

# ---------------------------
# Usuário — Editar
# ---------------------------
class EditarUsuario(LoginRequiredMixin, AcessoTotalRequiredMixin, UpdateView):
    template_name = 'usuario/form_usuario.html'
    model = Usuario
    form_class = EditarUsuarioForm

    def get_object(self):
        return get_object_or_404(
            Usuario,
            pk=self.kwargs['pk'],
            is_master=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        TelefoneFormSetEdicao = inlineformset_factory(
            Usuario,
            Telefone,
            form=TelefoneForm,
            extra=0,
            can_delete=True
        )

        if self.request.POST:
            context['telefones'] = TelefoneFormSetEdicao(
                self.request.POST,
                instance=self.object,
                prefix='telefones'
            )
        else:
            context['telefones'] = TelefoneFormSetEdicao(
                instance=self.object,
                prefix='telefones'
            )

        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
        })
        return context

    # 🔥
    def form_valid(self, form):
        context = self.get_context_data()
        telefones = context['telefones']

        if not telefones.is_valid():
            messages.error(self.request, "Corrija os erros abaixo nos telefones.")
            return self.render_to_response(self.get_context_data(form=form))

        usuario = form.save(commit=False)

        # 🔥 Marca usuário para auditoria (IMPORTANTE pro seu log!)
        usuario.usuario_atualizacao = self.request.user

        usuario.save()

        telefones.instance = usuario
        telefones.save()

        messages.success(
            self.request,
            f"Usuário {usuario.get_full_name()} atualizado com sucesso!"
        )

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Não foi possível atualizar o usuário. Corrija os erros abaixo."
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:cadastrousuarios')

# -------------------------------
# Usuário — Excluir (desativar)
# -------------------------------
class ExcluirUsuario(LoginRequiredMixin, AcessoTotalRequiredMixin, DetailView):
    template_name = 'usuario/form_usuario.html'
    model = Usuario

    def get_object(self):
        usuario = get_object_or_404(
            Usuario,
            pk=self.kwargs['pk']
        )

        # 🛡️ TRAVA ABSOLUTA — Usuário Master
        if usuario.is_master:
            messages.error(
                self.request,
                "Este usuário é protegido pelo sistema e não pode ser desativado."
            )
            raise PermissionDenied

        return usuario

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()

        usuario.is_active = False
        usuario.data_ativacaodesativacao = timezone.now()
        usuario.save()

        messages.success(
            request,
            f"Usuário {usuario.get_full_name()} desativado com sucesso!"
        )
        return redirect('arquiteturaprocessos:cadastrousuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.object

        context['form'] = Form_UsuarioForm(
            instance=usuario,
            initial={
                'is_active': False,
                'data_ativacaodesativacao': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            modo_exclusao=True
        )

        TelefoneFormSetExclusao = inlineformset_factory(
            Usuario,
            Telefone,
            form=TelefoneForm,
            extra=0,
            can_delete=False
        )

        context['telefones'] = TelefoneFormSetExclusao(
            instance=usuario,
            prefix='telefones'
        )

        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
        })
        return context

# ---------------------------
# Macroprocessos N1 / N2
# ---------------------------
class MacroProcessoView(TemplateView):
    template_name = 'arquitetura/estrutura/macroprocesso.html'

class MacroProcessoNivel1View(LoginRequiredMixin, ListView):
    model = MacroprocessoNivel1
    template_name = 'estrutura/macroprocessonivel1.html'
    context_object_name = 'macroprocessonivel1'
    queryset = MacroprocessoNivel1.objects.order_by('nome')

class CriarMacroProcessoNivel1(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_macroprocessonivel1.html'
    form_class = Form_MacroProcessoNivel1Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 1 '{self.object.nome}' criada com sucesso!")
        return resp

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível criar o Macroprocesso de Nível 1. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:macroprocessonivel1')

class VisualizarMacroProcessoNivel1(LoginRequiredMixin, DetailView):
    template_name = 'estrutura/form_macroprocessonivel1.html'
    model = MacroprocessoNivel1
    context_object_name = 'macroprocessonivel1'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        macroprocessonivel1 = self.get_object()
        context['form'] = Form_MacroProcessoNivel1Form(instance=macroprocessonivel1, modo_visualizacao=True)
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

class EditarMacroProcessoNivel1(LoginRequiredMixin, UpdateView):
    model = MacroprocessoNivel1
    template_name = 'estrutura/form_macroprocessonivel1.html'
    context_object_name = 'macroprocessonivel1'
    form_class = Form_MacroProcessoNivel1Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 1 '{self.object.nome}' atualizado com sucesso!")
        return resp

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar o Macroprocesso de Nível 1. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:macroprocessonivel1')

class ExcluirMacroProcessoNivel1(LoginRequiredMixin, DetailView):
    model = MacroprocessoNivel1
    template_name = 'estrutura/form_macroprocessonivel1.html'
    context_object_name = 'macroprocessonivel1'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method != 'POST':
            context['form'] = Form_MacroProcessoNivel1Form(instance=self.get_object(), modo_exclusao=True)
        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
        })
        return context

    def post(self, request, *args, **kwargs):
        macroprocessonivel = self.get_object()
        try:
            macroprocessonivel.delete()
        except ProtectedError as e:
            protected_objs = getattr(e, 'protected_objects', None)
            if protected_objs:
                exemplos = ', '.join(str(o) for o in list(protected_objs)[:3])
                detalhes = f"Exemplos: {exemplos}."
            else:
                detalhes = ""
            messages.error(request,
                (
                    f"Não é possível excluir o Macroprocesso Nível 1 '{macroprocessonivel.nome}', "
                    "pois existem registros relacionados que impedem a exclusão. "
                    "Remova ou desassocie os itens relacionados antes de tentar novamente. "
                    f"{detalhes}"
                )
            )
            return redirect('arquiteturaprocessos:macroprocessonivel1')

        messages.success(request, f"Macroprocesso Nível 1 '{macroprocessonivel.nome}' excluído com sucesso!")
        return redirect('arquiteturaprocessos:macroprocessonivel1')

class MacroProcessoNivel2View(LoginRequiredMixin, ListView):
    model = MacroprocessoNivel2
    template_name = 'estrutura/macroprocessonivel2.html'
    context_object_name = 'macroprocessonivel2'

    def get_queryset(self):
        return MacroprocessoNivel2.objects.select_related(
            'macroprocesso_nivel1', 'macroprocesso_nivel1__classificacao'
        ).order_by(
        "macroprocesso_nivel1__classificacao__nome",
        "macroprocesso_nivel1__nome",
        "nome"
        )

class CriarMacroProcessoNivel2(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_macroprocessonivel2.html'
    form_class = Form_MacroProcessoNivel2Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 2 '{self.object.nome}' criado com sucesso!")
        return resp

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível criar o Macroprocesso de Nível 2. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:macroprocessonivel2')

class VisualizarMacroProcessoNivel2(LoginRequiredMixin, DetailView):
    template_name = 'estrutura/form_macroprocessonivel2.html'
    model = MacroprocessoNivel2
    context_object_name = 'macroprocessonivel2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        macroprocessonivel2 = self.get_object()
        context['form'] = Form_MacroProcessoNivel2Form(instance=macroprocessonivel2, modo_visualizacao=True)
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

class EditarMacroProcessoNivel2(LoginRequiredMixin, UpdateView):
    model = MacroprocessoNivel2
    template_name = 'estrutura/form_macroprocessonivel2.html'
    context_object_name = 'macroprocessonivel2'
    form_class = Form_MacroProcessoNivel2Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 2 '{self.object.nome}' atualizado com sucesso!")
        return resp

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar o Macroprocesso de Nível 2. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:macroprocessonivel2')

class ExcluirMacroProcessoNivel2(LoginRequiredMixin, DetailView):
    model = MacroprocessoNivel2
    template_name = 'estrutura/form_macroprocessonivel2.html'
    context_object_name = 'macroprocessonivel2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method != 'POST':
            context['form'] = Form_MacroProcessoNivel2Form(instance=self.get_object(), modo_exclusao=True)
        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
        })
        return context

    def post(self, request, *args, **kwargs):
        macroprocessonivel2 = self.get_object()
        processo_associado = Processo.objects.filter(macroprocesso_nivel2=macroprocessonivel2).first()
        if processo_associado:
            messages.error(request,
                f"Não é possível excluir o Macroprocesso Nível 2 '{macroprocessonivel2.nome}', pois está associado ao processo '{processo_associado.nome}'."
            )
            return redirect('arquiteturaprocessos:macroprocessonivel2')

        macroprocessonivel2.delete()
        messages.success(request, f"Macroprocesso Nível 2 '{macroprocessonivel2.nome}' excluído com sucesso!")
        return redirect('arquiteturaprocessos:macroprocessonivel2')

class SubProcessoView(TemplateView):
    template_name = 'arquitetura/estrutura/subprocesso.html'

# ---------------------------
# Tipos de Documento
# ---------------------------
class TipoDocumentoList(LoginRequiredMixin, ListView):
    model = TiposDocumento
    template_name = 'estrutura/tiposdocumento.html'
    context_object_name = 'tiposdocumento'
    queryset = TiposDocumento.objects.order_by('nome')

class CriarTipoDocumento(LoginRequiredMixin, CreateView):
    model = TiposDocumento
    form_class = Form_TipoDocumentoForm
    template_name = 'estrutura/form_tipodocumento.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['modo_visualizacao'] = False
        kwargs['modo_exclusao'] = False
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tipo de Documento '{self.object.nome}' criado com sucesso!")
        return response

    def get_success_url(self):
        return reverse('arquiteturaprocessos:tiposdocumento')

class VisualizarTipoDocumento(LoginRequiredMixin, DetailView):
    model = TiposDocumento
    template_name = 'estrutura/form_tipodocumento.html'
    context_object_name = 'tipodocumento'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = Form_TipoDocumentoForm(instance=self.get_object(), modo_visualizacao=True)
        ctx.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return ctx

class EditarTipoDocumento(LoginRequiredMixin, UpdateView):
    model = TiposDocumento
    form_class = Form_TipoDocumentoForm
    template_name = 'estrutura/form_tipodocumento.html'
    context_object_name = 'tipodocumento'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
        })
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['modo_visualizacao'] = False
        kwargs['modo_exclusao'] = False
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tipo de Documento '{self.object.nome}' atualizado com sucesso!")
        return response

    def get_success_url(self):
        return reverse('arquiteturaprocessos:tiposdocumento')

class ExcluirTipoDocumento(LoginRequiredMixin, DetailView):
    model = TiposDocumento
    template_name = 'estrutura/form_tipodocumento.html'
    context_object_name = 'tipodocumento'

    def post(self, request, *args, **kwargs):
        tipodocumento = self.get_object()

        # 🔒 Regra de domínio: impedir exclusão se houver vínculos
        existe_vinculo = ModelagemProcesso.objects.filter(
            tipo_documento=tipodocumento
        ).exists()

        if existe_vinculo:
            messages.error(
                request,
                "Não é possível excluir este Tipo de Documento porque ele está vinculado a uma ou mais Modelagens de Processo."
            )
            return redirect('arquiteturaprocessos:tiposdocumento')

        tipodocumento.delete()
        messages.success(
            request,
            f"Tipo de Documento '{tipodocumento.nome}' excluído com sucesso!"
        )
        return redirect('arquiteturaprocessos:tiposdocumento')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = Form_TipoDocumentoForm(
            instance=self.object,
            modo_exclusao=True
        )
        ctx.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
        })
        return ctx

# ---------------------------------------------------
# LISTAGEM
# ---------------------------------------------------
class ModelagemProcessoView(LoginRequiredMixin, ListView):
    model = ModelagemProcesso
    template_name = 'estrutura/modelagemprocessos.html'
    context_object_name = 'modelagemprocessos'
    paginate_by = 20

    def get_queryset(self):
        termo = self.request.GET.get('q', '').strip()

        queryset = (
            ModelagemProcesso.objects
            .select_related('usuario', 'usuario_atualizacao', 'tipo_documento')
        )

        if termo:
            queryset = queryset.filter(
                Q(titulo__icontains=termo) |
                Q(tipo_documento__nome__icontains=termo) |
                Q(emitente__icontains=termo) |
                Q(sistema__icontains=termo) |
                Q(codigo__icontains=termo)
            )

        queryset = queryset.order_by(
            'tipo_documento__nome',
            'titulo',
            'codigo',
            'sequencial'
        )

        # Formatação visual do sequencial
        for obj in queryset:
            if obj.sequencial is not None:
                try:
                    obj.sequencial = f"{int(obj.sequencial):03d}"
                except (TypeError, ValueError):
                    pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['termo_busca'] = self.request.GET.get('q', '')
        return context

# ---------------------------------------------------
# CRIAR
# ---------------------------------------------------
class CriarModelagemProcesso(LoginRequiredMixin, CreateView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    form_class = Form_ModelagemProcessoForm
    success_url = reverse_lazy('arquiteturaprocessos:modelagemprocessos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'usuario_logado': self.request.user,
            'modo_inclusao': True,
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ultimo_seq = ModelagemProcesso.objects.aggregate(
            Max('sequencial')
        )['sequencial__max'] or 0

        try:
            proximo = int(ultimo_seq) + 1
        except (TypeError, ValueError):
            proximo = 1

        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
            'proximo_sequencial': f"{proximo:03d}",
        })
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.data_cadastro = timezone.now()

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"Modelagem de Processo '{self.object.titulo}' criada com sucesso!"
        )

        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Não foi possível criar a Modelagem de Processo. Corrija os erros abaixo."
        )
        return super().form_invalid(form)


# ---------------------------------------------------
# VISUALIZAR
# ---------------------------------------------------
class VisualizarModelagemProcesso(LoginRequiredMixin, DetailView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        try:
            obj.sequencial = f"{int(obj.sequencial):03d}"
        except (TypeError, ValueError):
            pass

        context['form'] = Form_ModelagemProcessoForm(
            instance=obj,
            modo_visualizacao=True
        )
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context


# ---------------------------------------------------
# EDITAR
# ---------------------------------------------------
class EditarModelagemProcesso(LoginRequiredMixin, UpdateView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'
    form_class = Form_ModelagemProcessoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'usuario_logado': self.request.user,
            'modo_edicao': True,
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        try:
            obj.sequencial = f"{int(obj.sequencial):03d}"
        except (TypeError, ValueError):
            pass

        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
        })
        return context

    def form_valid(self, form):
        obj = form.instance
        obj.usuario_atualizacao = self.request.user
        obj.data_atualizacao = timezone.now()

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"Modelagem de Processo '{self.object.titulo}' atualizada com sucesso!"
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Não foi possível atualizar a Modelagem de Processo. Corrija os erros abaixo."
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:modelagemprocessos')


# ---------------------------------------------------
# EXCLUIR
# ---------------------------------------------------
class ExcluirModelagemProcesso(LoginRequiredMixin, DetailView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        try:
            obj.sequencial = f"{int(obj.sequencial):03d}"
        except (TypeError, ValueError):
            pass

        context['form'] = Form_ModelagemProcessoForm(
            instance=obj,
            modo_exclusao=True
        )
        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
        })
        return context

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        # Remove PDF do disco
        if obj.documento_modelagem_processo:
            try:
                if os.path.isfile(obj.documento_modelagem_processo.path):
                    os.remove(obj.documento_modelagem_processo.path)
            except Exception:
                pass

        titulo = obj.titulo
        obj.delete()

        messages.success(
            request,
            f"Modelagem de Processo '{titulo}' excluída com sucesso!"
        )
        return redirect('arquiteturaprocessos:modelagemprocessos')

# -------------------------------#
# Listagem - Processos           #
# -------------------------------#
class ProcessoView(LoginRequiredMixin, ListView):
    model = Processo
    template_name = 'processos/processos.html'
    context_object_name = 'processos'
    paginate_by = 20
    ordering = ['id']

    def get_queryset(self):
        req = self.request.GET

        nome = req.get("nome", "").strip()
        classificacao = req.get("classificacao", "").strip()
        macro1 = req.get("macro1", "").strip()
        macro2 = req.get("macro2", "").strip()
        area = req.get("area", "").strip()
        estado = req.get("estado", "").strip().lower()

        cri_de = parse_date(req.get("criacao_de"))
        cri_ate = parse_date(req.get("criacao_ate"))
        con_de = parse_date(req.get("conclusao_de"))
        con_ate = parse_date(req.get("conclusao_ate"))

        # 🔥 validação datas
        if cri_de and cri_ate and cri_ate < cri_de:
            messages.error(self.request, "A data final deve ser maior ou igual à inicial.")
            return Processo.objects.none()

        if con_de and con_ate and con_ate < con_de:
            messages.error(self.request, "A data final deve ser maior ou igual à inicial.")
            return Processo.objects.none()

        # 🔥 BASE: SOMENTE PROCESSOS (PAI)
        qs = (
            Processo.objects
            .filter(parent__isnull=True)
            .select_related(
                "classificacao",
                "macroprocesso_nivel1",
                "macroprocesso_nivel2",
            )
            .prefetch_related(
                "documentos",
                "subprocessos",
                "subprocessos__classificacao",
                "subprocessos__macroprocesso_nivel1",
                "subprocessos__macroprocesso_nivel2",
            )
            .order_by("id")
        )

        # --------------------
        # FILTROS
        # --------------------
        if nome:
            qs = qs.filter(nome__icontains=nome)

        if classificacao:
            qs = qs.filter(classificacao_id=classificacao)

        if macro1:
            qs = qs.filter(macroprocesso_nivel1__nome__icontains=macro1)

        if macro2:
            qs = qs.filter(macroprocesso_nivel2__nome__icontains=macro2)

        if area:
            qs = qs.filter(area_responsavel__icontains=area)

        # --------------------
        # ESTADO
        # --------------------
        if estado == "concluido":
            qs = qs.filter(data_conclusao__isnull=False)

        elif estado == "ativo":
            qs = qs.filter(
                data_conclusao__isnull=True,
                documentos__isnull=False
            ).distinct()

        elif estado == "iniciado":
            qs = qs.filter(
                data_conclusao__isnull=True,
                documentos__isnull=True
            )

        # --------------------
        # DATAS
        # --------------------
        if cri_de:
            qs = qs.filter(data_criacao__gte=cri_de)

        if cri_ate:
            fim = datetime.combine(cri_ate, time.max)
            qs = qs.filter(data_criacao__lte=fim)

        if con_de:
            qs = qs.filter(data_conclusao__date__gte=con_de)

        if con_ate:
            qs = qs.filter(data_conclusao__date__lte=con_ate)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 🔥 CONTADOR
        context["total_registros"] = self.object_list.count()

        # 🔥 LISTA
        context["classificacoes"] = Classificacao.objects.all().order_by("nome")

        # 🧠 NOVO — VALORES SELECIONADOS (ESSENCIAL)
        req = self.request.GET

        context["classificacao_selecionada"] = str(req.get("classificacao", ""))
        context["classificacoes_ids_str"] = {str(c.id): c.id for c in Classificacao.objects.all()}
        context["estado_selecionado"] = str(req.get("estado", ""))
        context["nome_busca"] = req.get("nome", "")
        context["macro1_busca"] = req.get("macro1", "")
        context["macro2_busca"] = req.get("macro2", "")
        context["area_busca"] = req.get("area", "")

        return context

# --------------------------------#
# Criar Processo                  #
# --------------------------------#
class CriarProcesso(LoginRequiredMixin, CreateView):
    model = Processo
    template_name = "processos/form_processo.html"
    form_class = Form_ProcessoForm
    success_url = reverse_lazy("arquiteturaprocessos:processos")

    # -------------------------------------------------
    # Contexto do template
    # -------------------------------------------------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        agora_local = timezone.localtime(timezone.now())
        modelos, normas = get_modelagem_filtrada()

        context.update({
            # listas para selects dinâmicos
            "modelos_processo": modelos,
            "normas_procedimento": normas,

            # controle de modos
            "modo_inclusao": True,
            "modo_visualizacao": False,
            "modo_exclusao": False,
            "modo_edicao": False,

            # auditoria — inclusão
            "cadastro_data": agora_local.strftime("%d/%m/%Y %H:%M:%S"),
            "cadastro_user": self.request.user.get_full_name() or self.request.user.username,

            # auditoria — atualização (vazia)
            "atualizacao_data": "",
            "atualizacao_user": "",

            # auditoria — conclusão (vazia)
            "conclusao_data": "",
            "conclusao_user": "",
        })

        return context

    # -------------------------------------------------
    # Persistência correta (Processo + N Documentos)
    # -------------------------------------------------
    def form_valid(self, form):
        with transaction.atomic():
            processo = form.save(commit=False)

            processo.usuario_cadastro = self.request.user
            processo.usuario_atualizacao = None
            processo.data_atualizacao = None
            processo.save()

            # 🔥 DOCUMENTOS (1 → N)
            salvar_documentos_processo(self.request, processo)

        messages.success(
            self.request,
            f"Processo '{processo.nome}' criado com sucesso!"
        )

        return super().form_valid(form)

    # -------------------------------------------------
    # Erro de validação
    # -------------------------------------------------
    def form_invalid(self, form):
        messages.error(
            self.request,
            "Há erros no formulário. Verifique os campos destacados."
        )
        return super().form_invalid(form)

# --------------------------------#
# Visualizar Processo             #
# --------------------------------#
class VisualizarProcesso(LoginRequiredMixin, DetailView):
    model = Processo
    template_name = "processos/form_processo.html"
    context_object_name = "processo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processo = self.get_object()

        # -------------------------------------------------
        # Listas para os selects
        # -------------------------------------------------
        modelos, normas = get_modelagem_filtrada()
        context["modelos_processo"] = modelos
        context["normas_procedimento"] = normas

        # -------------------------------------------------
        # Form em modo visualização
        # -------------------------------------------------
        context["form"] = Form_ProcessoForm(
            instance=processo,
            modo_visualizacao=True
        )

        # -------------------------------------------------
        # 🔥 Documentos associados (1 → N)
        # -------------------------------------------------
        documentos_qs = (
            ProcessoDocumento.objects
            .select_related(
                "modelagem_processo",
                "modelagem_processo__tipo_documento"
            )
            .filter(processo=processo)
        )

        modelos_hidratados = []
        normas_hidratadas = []

        for doc in documentos_qs:
            mp = doc.modelagem_processo
            tipo_nome = (mp.tipo_documento.nome or "").lower()

            dados = {
                "id": mp.id,
                "titulo": mp.titulo,
                "tema": mp.tema,
                "versao": mp.versao,
                "emitente": mp.emitente,
                "sistema": mp.sistema,
                "vigencia": (
                    mp.vigencia_inicio.strftime("%Y-%m-%d")
                    if mp.vigencia_inicio else ""
                ),
            }

            # -------------------------------------------------
            # PDF e LINK (sempre presentes, mesmo que vazios)
            # -------------------------------------------------
            dados["pdf"] = (
                mp.documento_modelagem_processo.url
                if mp.documento_modelagem_processo
                else ""
            )

            dados["link"] = mp.link_normaprocedimento or ""

            # -------------------------------------------------
            # Separação por tipo de documento
            # -------------------------------------------------
            if "modelo" in tipo_nome:
                modelos_hidratados.append(dados)
            else:
                normas_hidratadas.append(dados)

        # -------------------------------------------------
        # Envio para hidratação via JS
        # -------------------------------------------------
        context.update({
            "modelos_hidratados": modelos_hidratados,
            "normas_hidratadas": normas_hidratadas,
        })

        # -------------------------------------------------
        # Controle de modo + auditoria
        # -------------------------------------------------
        context.update({
            "modo_visualizacao": True,
            "modo_inclusao": False,
            "modo_exclusao": False,
            "modo_edicao": False,
            "desabilitar": True,

            "cadastro_data": (
                timezone.localtime(processo.data_criacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_criacao else ""
            ),
            "cadastro_user": (
                processo.usuario_cadastro.get_full_name()
                if processo.usuario_cadastro else ""
            ),
            "atualizacao_data": (
                timezone.localtime(processo.data_atualizacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_atualizacao else ""
            ),
            "atualizacao_user": (
                processo.usuario_atualizacao.get_full_name()
                if processo.usuario_atualizacao else ""
            ),
            # auditoria — conclusao
            "conclusao_data": (
                timezone.localtime(processo.data_conclusao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_conclusao else ""
            ),
            "conclusao_user": (
                processo.usuario_conclusao.get_full_name()
                if processo.usuario_conclusao else ""
            ),
        })

        return context

# --------------------------------#
# Editar Processo                 #
# --------------------------------#
class EditarProcesso(LoginRequiredMixin, UpdateView):
    model = Processo
    template_name = 'processos/form_processo.html'
    form_class = Form_ProcessoForm
    success_url = reverse_lazy('arquiteturaprocessos:processos')

    def dispatch(self, request, *args, **kwargs):

        processo = self.get_object()

        if processo.status == "concluido":
            messages.error(
                request,
                f"O processo '{processo.nome}' já está concluído e não pode ser editado."
            )
            return redirect("arquiteturaprocessos:processos")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processo = self.object

        # -------------------------------------------------
        # Listas para os selects
        # -------------------------------------------------
        modelos, normas = get_modelagem_filtrada()
        context["modelos_processo"] = modelos
        context["normas_procedimento"] = normas

        # -------------------------------------------------
        # SELECTS DEPENDENTES (macroprocessos)
        # -------------------------------------------------
        context["macroprocesso_nivel1_list"] = (
            MacroprocessoNivel1.objects.filter(classificacao=processo.classificacao)
            if processo.classificacao_id else MacroprocessoNivel1.objects.none()
        )

        context["macroprocesso_nivel2_list"] = (
            MacroprocessoNivel2.objects.filter(
                macroprocesso_nivel1=processo.macroprocesso_nivel1
            )
            if processo.macroprocesso_nivel1_id else MacroprocessoNivel2.objects.none()
        )

        # -------------------------------------------------
        # 🔥 Documentos associados (1 → N) — IGUAL AO VISUALIZAR
        # -------------------------------------------------
        documentos_qs = (
            ProcessoDocumento.objects
            .select_related(
                "modelagem_processo",
                "modelagem_processo__tipo_documento"
            )
            .filter(processo=processo)
        )

        modelos_hidratados = []
        normas_hidratadas = []

        for doc in documentos_qs:
            mp = doc.modelagem_processo
            tipo_nome = (mp.tipo_documento.nome or "").lower()

            dados = {
                "id": mp.id,
                "titulo": mp.titulo,
                "tema": mp.tema,
                "versao": mp.versao,
                "emitente": mp.emitente,
                "sistema": mp.sistema,
                "vigencia": (
                    mp.vigencia_inicio.strftime("%Y-%m-%d")
                    if mp.vigencia_inicio else ""
                ),
            }

            # -------------------------------------------------
            # PDF e LINK (sempre presentes, mesmo que vazios)
            # -------------------------------------------------
            dados["pdf"] = (
                mp.documento_modelagem_processo.url
                if mp.documento_modelagem_processo
                else ""
            )

            dados["link"] = mp.link_normaprocedimento or ""

            # -------------------------------------------------
            # Separação por tipo de documento
            # -------------------------------------------------
            if "modelo" in tipo_nome:
                modelos_hidratados.append(dados)
            else:
                normas_hidratadas.append(dados)

        # -------------------------------------------------
        # Envio para hidratação via JS
        # -------------------------------------------------
        context.update({
            "modelos_hidratados": modelos_hidratados,
            "normas_hidratadas": normas_hidratadas,
        })

        # -------------------------------------------------
        # Controle de modo + auditoria
        # -------------------------------------------------
        context.update({
            "modo_edicao": True,
            "modo_inclusao": False,
            "modo_visualizacao": False,
            "modo_exclusao": False,

            "cadastro_data": (
                timezone.localtime(processo.data_criacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_criacao else ""
            ),
            "cadastro_user": (
                processo.usuario_cadastro.get_full_name()
                if processo.usuario_cadastro else ""
            ),

            "atualizacao_data": timezone.localtime(
                timezone.now()
            ).strftime("%d/%m/%Y %H:%M:%S"),
            "atualizacao_user": (
                self.request.user.get_full_name()
                or self.request.user.username
            ),
            "conclusao_data": (
                timezone.localtime(processo.data_conclusao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_conclusao else ""
            ),
            "conclusao_user": (
                processo.usuario_conclusao.get_full_name()
                or processo.usuario_conclusao.username
                if processo.usuario_conclusao else ""
            ),
        })

        return context

    # -------------------------------------------------
    # GRAVAÇÃO FINAL
    # -------------------------------------------------
    def form_valid(self, form):
        with transaction.atomic():

            # 🔥 ESTADO ANTES (PROCESSO)
            processo_original = self.get_object()

            processo_antigo = Processo.objects.get(pk=processo_original.pk)

            dados_antes = {
                "nome": processo_antigo.nome,
                "status": processo_antigo.status,
                "classificacao": processo_antigo.classificacao_id,
                "macro_nivel1": processo_antigo.macroprocesso_nivel1_id,
                "macro_nivel2": processo_antigo.macroprocesso_nivel2_id,
            }

            # 🔥 ESTADO ANTES (DOCUMENTOS)
            docs_antes = set(
                ProcessoDocumento.objects
                .filter(processo=processo_original)
                .values_list("modelagem_processo__titulo", flat=True)
            )

            # -----------------------------------------
            # SALVANDO PROCESSO
            # -----------------------------------------
            processo = form.save(commit=False)

            processo.usuario_atualizacao = self.request.user
            processo.data_atualizacao = timezone.now()
            processo.save()

            # -----------------------------------------
            # SALVANDO DOCUMENTOS
            # -----------------------------------------
            salvar_documentos_processo(self.request, processo)

            # 🔥 ESTADO DEPOIS (PROCESSO)
            dados_depois = {
                "nome": processo.nome,
                "status": processo.status,
                "classificacao": processo.classificacao_id,
                "macro_nivel1": processo.macroprocesso_nivel1_id,
                "macro_nivel2": processo.macroprocesso_nivel2_id,
            }

            # 🔥 ESTADO DEPOIS (DOCUMENTOS)
            docs_depois = set(
                ProcessoDocumento.objects
                .filter(processo=processo)
                .values_list("modelagem_processo__titulo", flat=True)
            )

            adicionados = docs_depois - docs_antes
            removidos = docs_antes - docs_depois

            # -----------------------------------------
            # 🔥 LOG DO PROCESSO
            # -----------------------------------------
            registrar_log(
                request=self.request,
                acao="UPDATE",
                modelo="Processo",
                objeto_id=str(processo.id),
                descricao=f"Processo '{processo.nome}' atualizado",
                dados_antes=dados_antes,
                dados_depois=dados_depois,
            )

            # -----------------------------------------
            # 🔥 LOG DOS DOCUMENTOS (SE HOUVER ALTERAÇÃO)
            # -----------------------------------------
            if adicionados or removidos:

                descricao_docs = []

                if adicionados:
                    descricao_docs.append(f"Adicionados: {', '.join(adicionados)}")

                if removidos:
                    descricao_docs.append(f"Removidos: {', '.join(removidos)}")

                registrar_log(
                    request=self.request,
                    acao="UPDATE",
                    modelo="ProcessoDocumento",
                    objeto_id=str(processo.id),
                    descricao=" | ".join(descricao_docs),
                    dados_antes={"documentos": list(docs_antes)},
                    dados_depois={"documentos": list(docs_depois)},
                )

        messages.success(
            self.request,
            f"Processo '{processo.nome}' atualizado com sucesso!"
        )

        return redirect(self.success_url)

# --------------------------------#
# Excluir Processo                #
# --------------------------------#
class ExcluirProcesso(LoginRequiredMixin, DetailView):
    model = Processo
    template_name = 'processos/form_processo.html'
    context_object_name = 'processo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processo = self.get_object()

        # -------------------------------------------------
        # Listas para os selects
        # -------------------------------------------------
        modelos, normas = get_modelagem_filtrada()
        context["modelos_processo"] = modelos
        context["normas_procedimento"] = normas

        # -------------------------------------------------
        # Form em modo exclusão
        # -------------------------------------------------
        context["form"] = Form_ProcessoForm(
            instance=processo,
            modo_exclusao=True
        )

        # -------------------------------------------------
        # 🔥 Documentos associados (1 → N) — IGUAL AO VISUALIZAR
        # -------------------------------------------------
        documentos_qs = (
            ProcessoDocumento.objects
            .select_related(
                "modelagem_processo",
                "modelagem_processo__tipo_documento"
            )
            .filter(processo=processo)
        )

        modelos_hidratados = []
        normas_hidratadas = []

        for doc in documentos_qs:
            mp = doc.modelagem_processo
            tipo_nome = (mp.tipo_documento.nome or "").lower()

            dados = {
                "id": mp.id,
                "titulo": mp.titulo,
                "tema": mp.tema,
                "versao": mp.versao,
                "emitente": mp.emitente,
                "sistema": mp.sistema,
                "vigencia": (
                    mp.vigencia_inicio.strftime("%Y-%m-%d")
                    if mp.vigencia_inicio else ""
                ),
            }

            # ------------------------------
            # MODELO DE PROCESSO (arquivo local)
            # ------------------------------
            if "modelo" in tipo_nome:
                dados["arquivo"] = (
                    mp.documento_modelagem_processo.url
                    if mp.documento_modelagem_processo
                    else ""
                )
                modelos_hidratados.append(dados)

            # ------------------------------
            # NORMA DE PROCEDIMENTO (URL externa)
            # ------------------------------
            else:
                dados["arquivo"] = mp.link_normaprocedimento or ""
                normas_hidratadas.append(dados)

        # -------------------------------------------------
        # Envio para hidratação via JS
        # -------------------------------------------------
        context.update({
            "modelos_hidratados": modelos_hidratados,
            "normas_hidratadas": normas_hidratadas,
        })

        # -------------------------------------------------
        # Subprocessos associados
        # -------------------------------------------------
        subprocessos = processo.subprocessos.all()

        # -------------------------------------------------
        # Controle de modo + auditoria
        # -------------------------------------------------
        context.update({
            "modo_exclusao": True,
            "modo_visualizacao": False,
            "modo_inclusao": False,
            "modo_edicao": False,
            "desabilitar": True,

            "subprocessos_existentes": subprocessos,

            "cadastro_data": (
                timezone.localtime(processo.data_criacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_criacao else ""
            ),
            "cadastro_user": (
                processo.usuario_cadastro.get_full_name()
                if processo.usuario_cadastro else ""
            ),
            "atualizacao_data": (
                timezone.localtime(processo.data_atualizacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_atualizacao else ""
            ),
            "atualizacao_user": (
                processo.usuario_atualizacao.get_full_name()
                if processo.usuario_atualizacao else ""
            ),
            # auditoria — conclusao
            "conclusao_data": (
                timezone.localtime(processo.data_conclusao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_conclusao else ""
            ),
            "conclusao_user": (
                processo.usuario_conclusao.get_full_name()
                or processo.usuario_conclusao.username
                if processo.usuario_conclusao else ""
            ),
        })

        return context

    def post(self, request, *args, **kwargs):
        processo = self.get_object()

        # -------------------------------------------------
        # 1️⃣ Verifica se existem subprocessos
        # -------------------------------------------------
        subprocessos = processo.subprocessos.all()

        if subprocessos.exists():
            lista = ", ".join([s.nome for s in subprocessos])
            messages.error(
                request,
                f"Não é possível excluir o processo '{processo.nome}'. "
                f"Existem subprocessos associados: {lista}"
            )
            return redirect(request.path)

        # -------------------------------------------------
        # 2️⃣ Exclusão definitiva
        # -------------------------------------------------
        processo.delete()
        messages.success(
            request,
            f"Processo '{processo.nome}' excluído com sucesso!"
        )
        return redirect('arquiteturaprocessos:processos')

# --------------------------------#
# Concluir Processo               #
# --------------------------------#
@login_required
def concluir_processo(request, pk):

    processo = get_object_or_404(Processo, pk=pk)

    # ---------------------------------
    # Segurança: só POST pode concluir
    # ---------------------------------
    if request.method != "POST":
        return redirect("arquiteturaprocessos:editar_processo", pk=pk)

    # ---------------------------------
    # Verifica se pode concluir
    # ---------------------------------
    if not processo.pode_concluir:

        subprocessos_nao_iniciados = [
            sub.nome for sub in processo.subprocessos.all()
            if sub.status == "iniciado"
        ]

        lista_html = "<br>".join(
            f"<strong>{nome}</strong>"
            for nome in subprocessos_nao_iniciados
        )

        messages.error(
            request,
            mark_safe(
                f"""
                Não é possível concluir o processo '<strong>{processo.nome}</strong>'.
                <br><br>
                Existem subprocessos que ainda estão no estado de 'Iniciado':
                <br>
                {lista_html}
                <br><br>
                Ative, conclua ou exclua os subprocessos que não são necessários.
                """
            )
        )

        return redirect("arquiteturaprocessos:editar_processo", pk=pk)

    # ---------------------------------
    # Conclusão em cascata
    # ---------------------------------
    agora = timezone.now()

    with transaction.atomic():

        # conclui subprocessos ativos
        for sub in processo.subprocessos.filter(data_conclusao__isnull=True):

            if sub.status == "ativo":

                sub.data_conclusao = agora
                sub.usuario_conclusao = request.user
                sub.save()

        # conclui processo pai
        processo.data_conclusao = agora
        processo.usuario_conclusao = request.user
        processo.save()

    messages.success(
        request,
        f"Processo '{processo.nome}' concluído com sucesso!"
    )

    return redirect("arquiteturaprocessos:processos")

# -------------------------------------
# View customizada para Reset de Senha
# -------------------------------------
class CustomPasswordResetConfirmView(PasswordResetConfirmView):

    def form_valid(self, form):
        response = super().form_valid(form)

        user = self.user if self.user else None  # 🔥 usuário alvo (quem está redefinindo)

        try:
            registrar_log(
                request=self.request,
                acao="UPDATE",
                modelo="Autenticação",
                descricao="Usuário definiu/redefiniu sua senha via link de recuperação",
                dados_depois={
                    "username": user.username,
                    "nome": user.get_full_name()
                }
            )
        except Exception:
            # 🔒 Segurança: nunca quebrar fluxo de senha
            pass

        return response
