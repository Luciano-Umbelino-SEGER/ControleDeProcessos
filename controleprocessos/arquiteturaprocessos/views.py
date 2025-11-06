from datetime import datetime
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
                    Form_ClassificacaoForm, Form_MacroProcessoNivel1Form, Form_MacroProcessoNivel2Form, Form_ModelagemProcessoForm)
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

def classificacao_por_macro1(request, macro1_id):
    try:
        macro1 = MacroprocessoNivel1.objects.get(id=macro1_id)
        return JsonResponse({'classificacao': macro1.classificacao.nome})
    except MacroprocessoNivel1.DoesNotExist:
        return JsonResponse({'classificacao': ''})

def macroprocessos_por_classificacao(request, classificacao_id):
    macroprocessos = MacroprocessoNivel1.objects.filter(classificacao_id=classificacao_id)
    data = [{'id': m.id, 'nome': m.nome} for m in macroprocessos]
    return JsonResponse({'macroprocessos': data})

class SubProcessoView(TemplateView):
    template_name = 'arquitetura/estrutura/subprocesso.html'

# Listagem
class ModelagemProcessoView(LoginRequiredMixin, ListView):
    model = ModelagemProcesso
    template_name = 'estrutura/modelagemprocessos.html'
    context_object_name = 'modelagemprocessos'
    paginate_by = 20  # quantidade de registros por página

    def get_queryset(self):
        # Obtém o termo de busca enviado pelo usuário
        termo = self.request.GET.get('q', '').strip()

        # Query base com leve otimização via select_related
        queryset = (
            ModelagemProcesso.objects
            .select_related('usuario', 'usuario_atualizacao')
        )

        # Filtro de busca (tema, emitente, sistema, código)
        if termo:
            queryset = queryset.filter(
                Q(tema__icontains=termo) |
                Q(emitente__icontains=termo) |
                Q(sistema__icontains=termo) |
                Q(codigo__icontains=termo)
            )

        # Ordenação padrão (tema, código e sequencial)
        return queryset.order_by('tema', 'codigo', 'sequencial')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # mantém o termo de busca no template
        context['termo_busca'] = self.request.GET.get('q', '')
        return context

# -------------------
# Criar
# -------------------
class CriarModelagemProcesso(LoginRequiredMixin, CreateView):
    template_name = 'estrutura/form_modelagemprocesso.html'
    form_class = Form_ModelagemProcessoForm
    # Use a URL da listagem corretamente nomeada no seu urls.py
    success_url = reverse_lazy('arquiteturaprocessos:modelagemprocessos')

    def get_form_kwargs(self):
        """Passa flags de modo e o usuário logado para o Form (como seu Form espera)."""
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
        """Mantém as mesmas flags no contexto para o template, caso use condicionais."""
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_inclusao': True,
            'modo_visualizacao': False,
            'modo_exclusao': False,
            'modo_edicao': False,
        })
        return context

    def form_valid(self, form):
        """Apenas dispara a mensagem de sucesso. O seu Form já seta usuário ao salvar."""
        response = super().form_valid(form)
        messages.success(self.request, f"Modelagem de Processo '{self.object.tema}' criada com sucesso!")
        return response

    def form_invalid(self, form):
        """Mostra o aviso + lista dos erros por campo, para ficar claro o que corrigir."""
        messages.error(
            self.request,
            mark_safe("Não foi possível criar a Modelagem de Processo. Corrija os erros abaixo:" + form.errors.as_ul())
        )
        return super().form_invalid(form)



# -------------------
# Visualizar
# -------------------
class VisualizarModelagemProcesso(LoginRequiredMixin, DetailView):
    template_name = 'estrutura/form_modelagemprocesso.html'
    model = ModelagemProcesso
    context_object_name = 'modelagemprocesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        norma = self.get_object()
        context['form'] = Form_ModelagemProcessoForm(instance=norma, modo_visualizacao=True)
        context.update({
            'modo_visualizacao': True,
            'modo_inclusao': False,
            'modo_exclusao': False,
            'modo_edicao': False
        })
        return context

# -------------------
# Editar
# -------------------
class EditarModelagemProcesso(LoginRequiredMixin, UpdateView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'
    form_class = Form_ModelagemProcessoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modo_edicao': True,
            'modo_inclusao': False,
            'modo_visualizacao': False,
            'modo_exclusao': False
        })
        return context

    def form_valid(self, form):
        # Atualiza o usuário que está fazendo a alteração
        form.instance.usuario_atualizacao = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Norma de Procedimento '{self.object.tema}' atualizada com sucesso!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar a Norma de Procedimento. Corrija os erros abaixo.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('arquiteturaprocessos:ModelagemProcesso')

# -------------------
# Excluir
# -------------------
class ExcluirModelagemProcesso(LoginRequiredMixin, DetailView):
    model = ModelagemProcesso
    template_name = 'estrutura/form_modelagemprocesso.html'
    context_object_name = 'modelagemprocesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method != 'POST':
            context['form'] = Form_ModelagemProcessoForm(instance=self.get_object(), modo_exclusao=True)
        context.update({
            'modo_exclusao': True,
            'modo_visualizacao': False,
            'modo_inclusao': False,
            'modo_edicao': False
        })
        return context

    def post(self, request, *args, **kwargs):
        norma = self.get_object()
        norma.delete()
        messages.success(request, f"Modelagem de Processos '{norma.tema}' excluída com sucesso!")
        return redirect('arquiteturaprocessos:modelagemprocesso')

class ProcessoView(LoginRequiredMixin, ListView):
    model = Processo
    template_name = 'processos/processos.html'  # nova pasta processos
    context_object_name = 'processos'
    paginate_by = 20  # quantidade de registros por página

    # Caso queira ordenar por nome:
    ordering = ['nome']

class CriarProcesso(LoginRequiredMixin, CreateView):
    model = Processo
    template_name = 'processos/form_processo.html'
    fields = [
        'nome',
        'classificacao',
        'macroprocesso_nivel1',
        'macroprocesso_nivel2',
        'area_responsavel',
        'gestor',
        'norma',
        'parent',
    ]
    success_url = reverse_lazy('arquiteturaprocessos:processos')

    def form_valid(self, form):
        form.instance.responsavel = self.request.user
        return super().form_valid(form)



class CadastroSubProcessos(LoginRequiredMixin, ListView):
    template_name = 'cadastrosubprocessos.html'
    model = MacroprocessoNivel1


