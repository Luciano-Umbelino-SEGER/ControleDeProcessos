from datetime import datetime
import os
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.forms import inlineformset_factory
from django.http import JsonResponse, FileResponse, Http404

from .models import (Usuario, Telefone, ArquiteturaProcesso, MacroprocessoNivel1, MacroprocessoNivel2, LogAcoes,
                     Classificacao, ModelagemProcesso, Processo)
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.db.models import Exists, OuterRef
from .forms import (Form_UsuarioForm, EditarUsuarioForm, TelefoneForm, TelefoneFormSet, CustomAuthenticationForm,
                    Form_ClassificacaoForm, Form_MacroProcessoNivel1Form, Form_MacroProcessoNivel2Form,
                    Form_ModelagemProcessoForm, Form_ProcessoForm)
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_sameorigin  # ou xframe_options_exempt
from pathlib import Path
import mimetypes

@xframe_options_sameorigin  # permite ser exibido em <iframe> quando a página for da mesma origem
def visualizar_pdf(request, path):
    """
    Serve com segurança um PDF do MEDIA_ROOT para ser exibido em <iframe>.
    'path' deve ser relativo ao MEDIA_ROOT (ex.: 'modelagemprocessos/arquivo.pdf').
    """
    # Monta caminho absoluto com segurança
    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = (media_root / path).resolve()

    # Evita path traversal e garante existência do arquivo
    if not str(file_path).startswith(str(media_root)) or not file_path.exists() or not file_path.is_file():
        raise Http404("Arquivo não encontrado")

    # (Opcional) restringir a PDFs; comente se precisar abrir outros tipos
    ctype, _ = mimetypes.guess_type(str(file_path))
    if ctype != 'application/pdf':
        raise Http404("Tipo de arquivo não permitido")

    # Responder 'inline' para o navegador renderizar
    response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{file_path.name}"'

    # (Opcional, moderno) Reforçar CSP para iframes da mesma origem
    response['Content-Security-Policy'] = "frame-ancestors 'self'"

    return response

def get_modelagem_filtrada():
    hoje = timezone.now().date()

    modelos = ModelagemProcesso.objects.filter(
        documento_modelagem_processo__isnull=False
    ).exclude(
        documento_modelagem_processo=""
    ).filter(
        Q(vigencia_fim__isnull=True) | Q(vigencia_fim__gte=hoje)
    ).order_by("id")

    normas = ModelagemProcesso.objects.filter(
        link_normaprocedimento__isnull=False
    ).exclude(
        link_normaprocedimento=""
    ).filter(
        Q(vigencia_fim__isnull=True) | Q(vigencia_fim__gte=hoje)
    ).order_by("id")

    return modelos, normas

class HomePage(TemplateView):
    template_name = 'homepage.html'

class CustomLoginView(LoginView):
    template_name = 'usuario/fazer_login.html'
    authentication_form = CustomAuthenticationForm  # ✅ Usa o formulário customizado

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('arquiteturaprocessos:homepage')
        return super().dispatch(request, *args, **kwargs)


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
        context['modo_inclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
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

        context['modo_visualizacao'] = True
        context['modo_inclusao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context


class EditarClassificacao(LoginRequiredMixin, UpdateView):
    model = Classificacao
    template_name = 'estrutura/form_classificacao.html'
    context_object_name = 'classificacao'
    form_class = Form_ClassificacaoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo_edicao'] = True
        context['modo_inclusao'] = False
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Classificação '{self.object.nome}' atualizada com sucesso!")
        return response

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

        context['modo_exclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_inclusao'] = False
        context['modo_edicao'] = False
        return context

    def post(self, request, *args, **kwargs):
        classificacao = self.get_object()
        processo_associado = ArquiteturaProcesso.objects.filter(classificacao=classificacao).first()

        if processo_associado:
            messages.error(
                request,
                f"Não é possível excluir a classificação '{classificacao.nome}', pois está associada ao processo '{processo_associado.macroprocesso.nome}'."
            )
            return redirect('arquiteturaprocessos:classificacoes')

        classificacao.delete()
        messages.success(
            request,
            f"Classificação '{classificacao.nome}' excluída com sucesso!"
        )
        return redirect('arquiteturaprocessos:classificacoes')

class ArquiteruraProcessos(ListView):
    template_name = 'arquiteruraprocessos.html'
    model = ArquiteturaProcesso


class Estatisticas(LoginRequiredMixin, ListView):
    template_name = 'estatisticas.html'
    model = ArquiteturaProcesso


class BackLog(LoginRequiredMixin, ListView):
    template_name = 'backlog.html'
    model = ArquiteturaProcesso


class VisualizarUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/form_usuario.html'
    model = Usuario
    context_object_name = 'usuario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        context['form'] = Form_UsuarioForm(instance=usuario, modo_visualizacao=True)
        TelefoneFormSetVisualizacao = inlineformset_factory(
            Usuario,
            Telefone,
            form=TelefoneForm,
            extra=0,
            can_delete=False
        )
        context['telefones'] = TelefoneFormSetVisualizacao(instance=usuario, prefix='telefones')
        context['modo_visualizacao'] = True
        context['modo_inclusao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context


class EditarUsuario(LoginRequiredMixin, UpdateView):
    template_name = 'usuario/form_usuario.html'
    model = Usuario
    form_class = EditarUsuarioForm

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
            context['telefones'] = TelefoneFormSetEdicao(self.request.POST, instance=self.object, prefix='telefones')
        else:
            context['telefones'] = TelefoneFormSetEdicao(instance=self.object, prefix='telefones')

        context['modo_edicao'] = True
        context['modo_inclusao'] = False
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        telefones = context['telefones']

        if telefones.is_valid():
            self.object = form.save(commit=False)

            # 🔒 Proteção contra alteração indevida de datas
            if not self.object.date_joined:
                self.object.date_joined = timezone.now()
            # data_ativacaodesativacao não altera no modo edição

            # Atualiza is_active
            is_active = self.request.POST.get("is_active")
            self.object.is_active = is_active == "True"

            # Atualiza a senha apenas se o usuário digitou uma nova
            password1 = form.cleaned_data.get("password1")
            if password1:
                self.object.set_password(password1)

            self.object.save()

            # Salva telefones
            telefones.instance = self.object
            telefones.save()

            messages.success(self.request, f"Usuário {self.object.get_full_name()} atualizado com sucesso!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Corrija os erros abaixo.")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('arquiteturaprocessos:cadastrousuarios')


class ExcluirUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/form_usuario.html'
    model = Usuario

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()

        # Exclusão lógica
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
        usuario = self.get_object()

        # Atualiza os valores antes de passar para o form
        usuario.is_active = False
        usuario.data_ativacaodesativacao = timezone.now()

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
        context['telefones'] = TelefoneFormSetExclusao(instance=usuario, prefix='telefones')

        context['modo_exclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_inclusao'] = False
        context['modo_edicao'] = False
        return context

class CadastroUsuarios(LoginRequiredMixin, ListView):
    template_name = 'usuario/cadastrousuarios.html'
    model = Usuario
    context_object_name = 'usuarios'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:homepage')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        status = self.request.GET.get("status", "ativos")

        if status == "inativos":
            return Usuario.objects.filter(is_active=False).order_by("perfil__nome", "username")
        return Usuario.objects.filter(is_active=True).order_by("perfil__nome", "username")

class CriarUsuario(LoginRequiredMixin, CreateView):
    template_name = 'usuario/form_usuario.html'
    form_class = Form_UsuarioForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo_inclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        if self.request.POST:
            context['telefones'] = TelefoneFormSet(self.request.POST, prefix='telefones')
        else:
            context['telefones'] = TelefoneFormSet(prefix='telefones')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        telefones = context['telefones']

        if telefones.is_valid():
            self.object = form.save(commit=False)

            # 🔒 Proteção contra alteração indevida de datas
            self.object.is_active = self.request.POST.get("is_active") == "True"
            self.object.data_ativacaodesativacao = timezone.now()
            self.object.date_joined = timezone.now()

            self.object.save()
            telefones.instance = self.object
            telefones.save()

            messages.success(self.request, f"Usuário {self.object.get_full_name()} criado com sucesso!")

            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, "Por favor, corrija os erros abaixo.")
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('arquiteturaprocessos:cadastrousuarios')

class LogAcoes(LoginRequiredMixin, ListView):
    template_name = 'usuario/logacoes.html'
    model = LogAcoes

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:homepage')

        return super().dispatch(request, *args, **kwargs)

class MacroProcessoView(TemplateView):
    template_name = 'arquitetura/estrutura/macroprocesso.html'

class MacroProcessoNivel1View(LoginRequiredMixin,ListView):
    model = MacroprocessoNivel1
    template_name = 'estrutura/macroprocessonivel1.html'
    context_object_name = 'macroprocessonivel1'
    queryset = MacroprocessoNivel1.objects.order_by('nome')

class CriarMacroProcessoNivel1(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_macroprocessonivel1.html'
    form_class = Form_MacroProcessoNivel1Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo_inclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 1 '{self.object.nome}' criada com sucesso!")
        return response

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

        context['modo_visualizacao'] = True
        context['modo_inclusao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context


class EditarMacroProcessoNivel1(LoginRequiredMixin, UpdateView):
    model = MacroprocessoNivel1
    template_name = 'estrutura/form_macroprocessonivel1.html'
    context_object_name = 'macroprocessonivel1'
    form_class = Form_MacroProcessoNivel1Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo_edicao'] = True
        context['modo_inclusao'] = False
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 1 '{self.object.nome}' atualizado com sucesso!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar o Macroprocesso de Nível 1. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:macroprocessonivel1')

# sua view ajustada
class ExcluirMacroProcessoNivel1(LoginRequiredMixin, DetailView):
    model = MacroprocessoNivel1
    template_name = 'estrutura/form_macroprocessonivel1.html'
    context_object_name = 'macroprocessonivel1'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method != 'POST':
            context['form'] = Form_MacroProcessoNivel1Form(instance=self.get_object(), modo_exclusao=True)

        context['modo_exclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_inclusao'] = False
        context['modo_edicao'] = False
        return context

    def post(self, request, *args, **kwargs):
        macroprocessonivel = self.get_object()

        try:
            # tenta deletar diretamente — se houver FK com on_delete=PROTECT, ProtectedError será lançado
            macroprocessonivel.delete()
        except ProtectedError as e:
            # tenta extrair alguns exemplos de objetos protegidos para uma mensagem mais informativa
            protected_objs = getattr(e, 'protected_objects', None)
            if protected_objs:
                # limita a lista a 3 exemplos para não inundar a mensagem
                exemplos = ', '.join(str(o) for o in list(protected_objs)[:3])
                detalhes = f"Exemplos: {exemplos}."
            else:
                detalhes = ""

            messages.error(
                request,
                (
                    f"Não é possível excluir o Macroprocesso Nível 1 '{macroprocessonivel.nome}', "
                    "pois existem registros relacionados que impedem a exclusão. "
                    "Remova ou desassocie os itens relacionados antes de tentar novamente. "
                    f"{detalhes}"
                )
            )
            # redireciona para a lista (ou altere para onde preferir)
            return redirect('arquiteturaprocessos:macroprocessonivel1')

        # se chegou aqui, exclusão OK
        messages.success(
            request,
            f"Macroprocesso Nível 1 '{macroprocessonivel.nome}' excluído com sucesso!"
        )
        return redirect('arquiteturaprocessos:macroprocessonivel1')

class MacroProcessoNivel2View(LoginRequiredMixin, ListView):
    model = MacroprocessoNivel2
    template_name = 'estrutura/macroprocessonivel2.html'
    context_object_name = 'macroprocessonivel2'

    def get_queryset(self):
        return MacroprocessoNivel2.objects.select_related(
            'macroprocesso_nivel1', 'macroprocesso_nivel1__classificacao'
        ).order_by('nome')

class CriarMacroProcessoNivel2(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_macroprocessonivel2.html'
    form_class = Form_MacroProcessoNivel2Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo_inclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 2 '{self.object.nome}' criado com sucesso!")
        return response

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

        context['modo_visualizacao'] = True
        context['modo_inclusao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context

class EditarMacroProcessoNivel2(LoginRequiredMixin, UpdateView):
    model = MacroprocessoNivel2
    template_name = 'estrutura/form_macroprocessonivel2.html'
    context_object_name = 'macroprocessonivel2'
    form_class = Form_MacroProcessoNivel2Form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo_edicao'] = True
        context['modo_inclusao'] = False
        context['modo_visualizacao'] = False
        context['modo_exclusao'] = False
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Macroprocesso de Nível 2 '{self.object.nome}' atualizado com sucesso!")
        return response

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

        context['modo_exclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_inclusao'] = False
        context['modo_edicao'] = False
        return context

    def post(self, request, *args, **kwargs):
        macroprocessonivel2 = self.get_object()

        # Verifica se há processos associados a esse macroprocesso de nível 2
        processo_associado = ArquiteturaProcesso.objects.filter(macroprocesso_nivel2=macroprocessonivel2).first()

        if processo_associado:
            messages.error(
                request,
                f"Não é possível excluir o Macroprocesso Nível 2 '{macroprocessonivel2.nome}', pois ele está associado a um ou mais processos na arquitetura."
            )
            return redirect('arquiteturaprocessos:macroprocessonivel2')

        macroprocessonivel2.delete()
        messages.success(
            request,
            f"Macroprocesso Nível 2 '{macroprocessonivel2.nome}' excluído com sucesso!"
        )
        return redirect('arquiteturaprocessos:macroprocessonivel2')

class SubProcessoView(TemplateView):
    template_name = 'arquitetura/estrutura/subprocesso.html'

# -------------------------------#
# Listagem - Modelagem Processos #
# -------------------------------#
class ModelagemProcessoView(LoginRequiredMixin, ListView):
    model = ModelagemProcesso
    template_name = 'estrutura/modelagemprocessos.html'
    context_object_name = 'modelagemprocessos'
    paginate_by = 20

    def get_queryset(self):
        termo = self.request.GET.get('q', '').strip()
        queryset = ModelagemProcesso.objects.select_related('usuario', 'usuario_atualizacao')
        if termo:
            queryset = queryset.filter(
                Q(tema__icontains=termo) |
                Q(emitente__icontains=termo) |
                Q(sistema__icontains=termo) |
                Q(codigo__icontains=termo)
            )
        queryset = queryset.order_by('tema', 'codigo', 'sequencial')

        # 🔹 Formata o sequencial com zeros à esquerda (para exibição na lista)
        for obj in queryset:
            if obj.sequencial is not None:
                try:
                    obj.sequencial = f"{int(obj.sequencial):03}"
                except (TypeError, ValueError):
                    obj.sequencial = obj.sequencial
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['termo_busca'] = self.request.GET.get('q', '')
        return context


# -----------------------------#
# Criar Modelarem de Processos #
# -----------------------------#
class CriarModelagemProcesso(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_modelagemprocesso.html'
    form_class = Form_ModelagemProcessoForm
    success_url = reverse_lazy('arquiteturaprocessos:modelagemprocessos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'usuario_logado': self.request.user,
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return kwargs

    def get_context_data(self, **kwargs):
        from django.db.models import Max
        from .models import ModelagemProcesso

        context = super().get_context_data(**kwargs)

        ultimo_sequencial = ModelagemProcesso.objects.aggregate(Max('sequencial'))['sequencial__max'] or 0

        try:
            proximo_sequencial = int(ultimo_sequencial) + 1
        except (TypeError, ValueError):
            proximo_sequencial = 1

        sequencial_formatado = f"{proximo_sequencial:03}"

        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
            'proximo_sequencial': sequencial_formatado,
        })
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.data_cadastro = timezone.now()
        response = super().form_valid(form)
        messages.success(self.request, f"Modelagem de Processo '{self.object.tema}' criada com sucesso!")
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Não foi possível criar a Modelagem de Processo. Corrija os erros abaixo: " + str(form.errors)
        )
        return super().form_invalid(form)


# ----------------------------------#
# Visualizar Modelarem de Processos #
# ----------------------------------#
class VisualizarModelagemProcesso(LoginRequiredMixin, DetailView):
    template_name = 'estrutura/form_modelagemprocesso.html'
    model = ModelagemProcesso
    context_object_name = 'modelagemprocesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        # 🔹 Formata o sequencial
        try:
            obj.sequencial = f"{int(obj.sequencial):03}"
        except (TypeError, ValueError):
            pass

        context['form'] = Form_ModelagemProcessoForm(instance=obj, modo_visualizacao=True)
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False
        })
        return context


# ------------------------------#
# Editar Modelarem de Processos #
# ------------------------------#
class EditarModelagemProcesso(LoginRequiredMixin, UpdateView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'
    form_class = Form_ModelagemProcessoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        modelagem = self.get_object()

        # Exibição formatada (opcional)
        if modelagem.sequencial is not None:
            modelagem.sequencial = f"{int(modelagem.sequencial):03d}"

        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'form': Form_ModelagemProcessoForm(
                instance=modelagem,
                modo_edicao=True,
            ),
        })
        return context

    def form_valid(self, form):
        obj = form.instance
        obj.usuario_atualizacao = self.request.user
        obj.data_atualizacao = timezone.now()

        # REMOVIDO: não apagar arquivo aqui — o model.save() faz isso corretamente

        response = super().form_valid(form)
        messages.success(self.request, f"Modelagem de Processo '{self.object.tema}' atualizada com sucesso!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar a Modelagem de Processo. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:modelagemprocessos')

# -------------------------------#
# Excluir Modelarem de Processos #
# -------------------------------#
class ExcluirModelagemProcesso(LoginRequiredMixin, DetailView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        # 🔹 Formata o sequencial
        try:
            obj.sequencial = f"{int(obj.sequencial):03}"
        except (TypeError, ValueError):
            pass

        if self.request.method != 'POST':
            context['form'] = Form_ModelagemProcessoForm(instance=obj, modo_exclusao=True)
        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False
        })
        return context

    def post(self, request, *args, **kwargs):
        norma = self.get_object()
        if norma.documento_modelagem_processo and os.path.isfile(norma.documento_modelagem_processo.path):
            os.remove(norma.documento_modelagem_processo.path)
        norma.delete()
        messages.success(request, f"Modelagem de Processos '{norma.tema}' excluída com sucesso!")
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

        # === 4) Se filtrou subprocessos, precisamos retornar APENAS os processos PAI,
        # mas mantendo na tabela os subprocessos associados.
        # Obtemos todos os PAI relacionados aos resultados filtrados.
        pai_ids = (
            qs.values_list("parent_id", flat=True)
        )

        # processos que são pai direto
        diretos = qs.filter(parent__isnull=True).values_list("id", flat=True)

        # conjunto final de PAI = pais diretos + pais dos subprocessos filtrados
        ids_finais = set(diretos) | set(pai_ids)

        # remover None (subprocessos sem pai)
        ids_finais = {i for i in ids_finais if i is not None}

        # === 5) Agora retornamos APENAS os processos pai filtrados ===
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
    template_name = 'processos/form_processo.html'
    form_class = Form_ProcessoForm
    success_url = reverse_lazy('arquiteturaprocessos:processos')

    # Força o modo_inclusao no form
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["modo_visualizacao"] = False
        kwargs["modo_exclusao"] = False
        kwargs["modo_edicao"] = False
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        agora_local = timezone.localtime(timezone.now())
        modelos, normas = get_modelagem_filtrada()

        context.update({
            # listas para os selects
            "modelos_processo": modelos,
            "normas_procedimento": normas,

            # controle de modos
            "modo_inclusao": True,
            "modo_visualizacao": False,
            "modo_exclusao": False,
            "modo_edicao": False,

            # 🔵 AUDITORIA — inclusão
            "cadastro_data": agora_local.strftime("%d/%m/%Y %H:%M:%S"),
            "cadastro_user": self.request.user.get_full_name() or self.request.user.username,

            # 🔵 AUDITORIA — atualização (vazia)
            "atualizacao_data": "",
            "atualizacao_user": "",
        })

        return context

    def form_valid(self, form):
        processo = form.instance

        # 🔵 Auditoria registro novo
        processo.usuario_cadastro = self.request.user
        processo.usuario_atualizacao = None
        processo.data_atualizacao = None

        messages.success(
            self.request,
            f"Processo '{processo.nome}' criado com sucesso!"
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Há erros no formulário. Verifique os campos destacados."
        )
        return super().form_invalid(form)

    def form_valid(self, form):

        processo = form.instance

        # 🔵 GRAVAÇÃO DO NOVO CAMPO
        processo.norma_procedimento = form.cleaned_data.get("norma_procedimento")
        processo.modelagem_processo = form.cleaned_data.get("modelagem_processo")

        # auditoria
        processo.usuario_cadastro = self.request.user
        processo.usuario_atualizacao = None
        processo.data_atualizacao = None

        messages.success(
            self.request,
            f"Processo '{processo.nome}' criado com sucesso!"
        )

        return super().form_valid(form)

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
    template_name = 'processos/form_processo.html'
    context_object_name = 'processo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        processo = self.get_object()

        modelos, normas = get_modelagem_filtrada()
        context["modelos_processo"] = modelos
        context["normas_procedimento"] = normas

        # form carregado corretamente
        context['form'] = Form_ProcessoForm(
            instance=processo,
            modo_visualizacao=True
        )

        # Auditoria — Sempre readonly (o template já marca como readonly)
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
            "desabilitar": True,

            # 📌 Auditoria – Exibição
            'cadastro_data': (
                timezone.localtime(processo.data_criacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_criacao else ""
            ),
            'cadastro_user': (
                processo.usuario_cadastro.get_full_name()
                if processo.usuario_cadastro else ""
            ),

            'atualizacao_data': (
                timezone.localtime(processo.data_atualizacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_atualizacao else ""
            ),
            'atualizacao_user': (
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
        processo = self.object  # Sempre disponível no UpdateView

        # Carrega selects de PDF
        modelos, normas = get_modelagem_filtrada()
        context["modelos_processo"] = modelos
        context["normas_procedimento"] = normas

        # -------------------------------
        # SELECTS DEPENDENTES (n1/n2)
        # -------------------------------
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

        # -------------------------------
        # AUDITORIA
        # -------------------------------
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

            "atualizacao_data": timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M:%S"),
            "atualizacao_user": (
                self.request.user.get_full_name() or self.request.user.username
            ),
        })

        return context

    # ------------------------------------------------------------
    # GRAVAÇÃO FINAL (validação principal já está no forms.py)
    # ------------------------------------------------------------
    def form_valid(self, form):
        processo = form.instance

        # Atualiza auditoria
        processo.usuario_atualizacao = self.request.user
        processo.data_atualizacao = timezone.now()

        messages.success(
            self.request,
            f"Processo '{processo.nome}' atualizado com sucesso!"
        )

        return super().form_valid(form)

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

        modelos, normas = get_modelagem_filtrada()
        context["modelos_processo"] = modelos
        context["normas_procedimento"] = normas

        # Lista de subprocessos
        subprocessos = processo.subprocessos.all()

        context['form'] = Form_ProcessoForm(instance=processo, modo_exclusao=True)

        # 🔵 AUDITORIA + MODOS
        context.update({
            'cadastro_data': (
                timezone.localtime(processo.data_criacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_criacao else ""
            ),
            'cadastro_user': (
                processo.usuario_cadastro.get_full_name()
                if processo.usuario_cadastro else ""
            ),
            'atualizacao_data': (
                timezone.localtime(processo.data_atualizacao).strftime("%d/%m/%Y %H:%M:%S")
                if processo.data_atualizacao else ""
            ),
            'atualizacao_user': (
                processo.usuario_atualizacao.get_full_name()
                if processo.usuario_atualizacao else ""
            ),

            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False,
            "desabilitar": True,

            # 🔵 subprocessos para o template
            "subprocessos_existentes": subprocessos,
        })

        return context

    def post(self, request, *args, **kwargs):
        processo = self.get_object()

        # 1️⃣ Verifica se existem subprocessos
        subprocessos = processo.subprocessos.all()

        if subprocessos.exists():
            lista = ", ".join([s.nome for s in subprocessos])
            messages.error(
                request,
                f"Não é possível excluir o processo '{processo.nome}'. "
                f"Existem subprocessos associados: {lista}"
            )
            return redirect(request.path)

        # 2️⃣ Se não existir nenhum subprocesso → excluir normalmente
        processo.delete()
        messages.success(request, f"Processo '{processo.nome}' excluído com sucesso!")
        return redirect('arquiteturaprocessos:processos')







