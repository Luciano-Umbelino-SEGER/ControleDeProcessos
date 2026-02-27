# views.py (revisado)
from datetime import datetime
import os
import json
import re

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.forms import inlineformset_factory
from django.http import JsonResponse, FileResponse, Http404
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q, Max, Exists, OuterRef
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_sameorigin

from pathlib import Path
from urllib.parse import unquote
import mimetypes
from arquiteturaprocessos.utils.utils import usuario_tem_acesso_total, definir_senha_e_enviar_email
from arquiteturaprocessos.utils.mixins import AcessoTotalRequiredMixin
from arquiteturaprocessos.utils.utils import definir_senha_e_enviar_email

from .models import (
    Usuario, Telefone, MacroprocessoNivel1, MacroprocessoNivel2, LogAcoes,
    Classificacao, ModelagemProcesso, Processo, TiposDocumento,  ProcessoDocumento, BacklogProcesso,
)
from .forms import (
    Form_UsuarioForm, EditarUsuarioForm, TelefoneForm, TelefoneFormSet, CustomAuthenticationForm,
    Form_ClassificacaoForm, Form_MacroProcessoNivel1Form, Form_MacroProcessoNivel2Form,
    Form_ModelagemProcessoForm, Form_ProcessoForm, Form_TipoDocumentoForm, Form_BacklogProcessoForm,
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

# ---------------------------
# Login view
# ---------------------------
class CustomLoginView(LoginView):
    template_name = 'usuario/fazer_login.html'
    authentication_form = CustomAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('arquiteturaprocessos:arquiteturaprocessos')
        return super().dispatch(request, *args, **kwargs)

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

    definir_senha_e_enviar_email(usuario, reset=True)

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

    def parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

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
    def get_queryset(self):
        req = self.request.GET

        nome = req.get("nome", "").strip()
        classificacao = req.get("classificacao", "").strip()
        macro1 = req.get("macro1", "").strip()
        macro2 = req.get("macro2", "").strip()
        area = req.get("area", "").strip()

        cri_de = self.parse_date(req.get("criacao_de"))
        cri_ate = self.parse_date(req.get("criacao_ate"))
        atu_de = self.parse_date(req.get("atualizacao_de"))
        atu_ate = self.parse_date(req.get("atualizacao_ate"))

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
            qs = qs.filter(data_criacao__lte=cri_ate)

        if cri_de and cri_ate and cri_ate < cri_de:
            messages.error(self.request, "A data final deve ser maior ou igual à data inicial.")
            return qs.none()

        if atu_de:
            qs = qs.filter(data_atualizacao__gte=atu_de)

        if atu_ate:
            qs = qs.filter(data_atualizacao__lte=atu_ate)

        if atu_de and atu_ate and atu_ate < atu_de:
            messages.error(self.request, "A data final deve ser maior ou igual à data inicial.")
            return qs.none()

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

        return ctx


# --------------
# Estatísticas
# --------------
class Estatisticas(LoginRequiredMixin, ListView):
    template_name = 'estatisticas.html'
    model = Processo

#Aqui 1
# ---------------------------
#  Backlog de Processos
# ---------------------------
class BacklogProcessos(LoginRequiredMixin, ListView):
    model = BacklogProcesso
    template_name = 'backlogprocessos/backlogprocessos.html'
    context_object_name = 'backlogprocessos'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user.perfil.nome.lower() != 'administrador':
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-data_criacao')

        # Futuramente aqui entram os filtros
        # Ex: nome, classificacao, macroprocesso, etc.

        return queryset.select_related(
            'classificacao',
            'macroprocesso_nivel1',
            'macroprocesso_nivel2',
            'parent'
        )

#Aqui 2
# --------------------------------#
# Criar Backlog                   #
# --------------------------------#
class CriarBacklogProcesso(LoginRequiredMixin, CreateView):
    model = BacklogProcesso
    form_class = Form_BacklogProcessoForm
    template_name = "backlogprocessos/form_backlogprocesso.html"
    success_url = reverse_lazy("arquiteturaprocessos:backlogprocessos")

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
        backlog = form.save(commit=False)

        # 🔥 REGRA MÍNIMA ESTRUTURAL
        if backlog.tipo == BacklogProcesso.TIPO_PROCESSO:
            backlog.parent = None

        backlog.usuario_cadastro = self.request.user
        backlog.usuario_atualizacao = None

        backlog.save()

        messages.success(
            self.request,
            f"Backlog de Processos '{backlog.nome}' criado com sucesso!"
        )

        self.object = backlog
        return redirect(self.success_url)

# --------------------------------#
# Visualizar Backlog              #
# --------------------------------#
class VisualizarBacklogProcesso(LoginRequiredMixin, DetailView):
    model = BacklogProcesso
    form_class = Form_BacklogProcessoForm
    template_name = "backlogprocessos/form_backlogprocesso.html"
    context_object_name = 'backlogprocessos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        backlog = self.object

        context["form"] = Form_BacklogProcessoForm(
            instance=backlog
        )

        context.update({
            "modo_visualizacao": True,
            "modo_inclusao": False,
            "modo_edicao": False,
            "modo_exclusao": False,

            "cadastro_data": (
                timezone.localtime(backlog.data_criacao)
                .strftime("%d/%m/%Y %H:%M:%S")
            ),

            "cadastro_user": (
                backlog.usuario_cadastro.get_full_name()
                if backlog.usuario_cadastro else ""
            ),

            "atualizacao_data": (
                timezone.localtime(backlog.data_atualizacao)
                .strftime("%d/%m/%Y %H:%M:%S")
            ),

            "atualizacao_user": (
                backlog.usuario_atualizacao.get_full_name()
                if backlog.usuario_atualizacao else ""
            ),
        })

        return context
# --------------------------------#
# Editar Backlog                  #
# --------------------------------#
class EditarBacklogProcesso(LoginRequiredMixin, UpdateView):
    model = BacklogProcesso
    form_class = Form_BacklogProcessoForm
    template_name = "backlogprocessos/form_backlogprocesso.html"
    success_url = reverse_lazy("arquiteturaprocessos:backlogprocessos")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        backlog = self.object

        context.update({
            "modo_edicao": True,
            "modo_inclusao": False,
            "modo_visualizacao": False,
            "modo_exclusao": False,

            "cadastro_data": (
                timezone.localtime(backlog.data_criacao)
                .strftime("%d/%m/%Y %H:%M:%S")
            ),

            "cadastro_user": (
                backlog.usuario_cadastro.get_full_name()
                if backlog.usuario_cadastro else ""
            ),

            "atualizacao_data": timezone.localtime(
                timezone.now()
            ).strftime("%d/%m/%Y %H:%M:%S"),

            "atualizacao_user": (
                self.request.user.get_full_name()
                or self.request.user.username
            ),
        })

        return context

    def form_valid(self, form):
        backlog = form.save(commit=False)

        # 🔥 REGRA ESTRUTURAL MÍNIMA
        if backlog.tipo == BacklogProcesso.TIPO_PROCESSO:
            backlog.parent = None

        backlog.usuario_atualizacao = self.request.user
        backlog.save()

        messages.success(
            self.request,
            f"Backlog de Processos '{backlog.nome}' atualizado com sucesso!"
        )

        return super().form_valid(form)

# --------------------------------#
# Excluir Backlog                 #
# --------------------------------#
class ExcluirBacklogProcesso(LoginRequiredMixin, DetailView):
    model = BacklogProcesso
    form_class = Form_BacklogProcessoForm
    template_name = "backlogprocessos/form_backlogprocesso.html"
    context_object_name = "backlogprocessos"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        backlog = self.object

        context["form"] = Form_BacklogProcessoForm(instance=backlog)

        context.update({
            "modo_exclusao": True,
            "modo_visualizacao": False,
            "modo_inclusao": False,
            "modo_edicao": False,
        })

        return context

    def post(self, request, *args, **kwargs):
        backlog = self.get_object()
        backlog.delete()

        messages.success(
            request,
            f"Backlog '{backlog.nome}' excluído com sucesso!"
        )

        return redirect("arquiteturaprocessos:backlogprocessos")

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


# ---------------------------------
# LogAcoes — lista de logs (admin)
# ---------------------------------
class LogAcoes(LoginRequiredMixin, ListView):
    template_name = 'usuario/logacoes.html'
    model = LogAcoes

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.perfil or request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:arquiteturaprocessos')

        return super().dispatch(request, *args, **kwargs)

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

        # === 1) Recuperar parâmetros GET ===
        nome = self.request.GET.get("nome", "").strip()
        classificacao = self.request.GET.get("classificacao", "").strip()
        macro1 = self.request.GET.get("macro1", "").strip()
        macro2 = self.request.GET.get("macro2", "").strip()
        area = self.request.GET.get("area", "").strip()

        # === 2) Base inicial: TUDO (PAI + SUB) para aplicar filtros ===
        qs = (
            Processo.objects.all()
            .select_related(
                "classificacao",
                "macroprocesso_nivel1",
                "macroprocesso_nivel2",
            )
            .order_by("id")
        )

        # === 3) Aplicação dos filtros acumulativos ===
        if nome:
            qs = qs.filter(nome__icontains=nome)

        if classificacao:
            qs = qs.filter(classificacao_id=classificacao)

        if macro1:
            qs = qs.filter(
                macroprocesso_nivel1__nome__icontains=macro1
            )

        if macro2:
            qs = qs.filter(
                macroprocesso_nivel2__nome__icontains=macro2
            )

        if area:
            qs = qs.filter(
                area_responsavel__icontains=area
            )

        # === 4) Resolver PAI + SUBPROCESSOS ===
        pai_ids = qs.values_list("parent_id", flat=True)
        diretos = qs.filter(parent__isnull=True).values_list("id", flat=True)

        ids_finais = set(diretos) | set(pai_ids)
        ids_finais = {i for i in ids_finais if i is not None}

        # === 5) Retornar apenas PROCESSOS PAI ===
        queryset_final = (
            Processo.objects.filter(id__in=ids_finais)
            .select_related(
                "classificacao",
                "macroprocesso_nivel1",
                "macroprocesso_nivel2",
            )
            .prefetch_related(
                "subprocessos",
                "subprocessos__classificacao",
                "subprocessos__macroprocesso_nivel1",
                "subprocessos__macroprocesso_nivel2",
            )
            .order_by("id")
        )

        return queryset_final

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Necessário para preencher o select de classificação
        context["classificacoes"] = Classificacao.objects.all().order_by("nome")

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
        })

        return context

    # -------------------------------------------------
    # GRAVAÇÃO FINAL
    # -------------------------------------------------
    def form_valid(self, form):
        with transaction.atomic():
            processo = form.save(commit=False)

            processo.usuario_atualizacao = self.request.user
            processo.data_atualizacao = timezone.now()
            processo.save()

            # 🔥 DOCUMENTOS (1 → N)
            salvar_documentos_processo(self.request, processo)

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




