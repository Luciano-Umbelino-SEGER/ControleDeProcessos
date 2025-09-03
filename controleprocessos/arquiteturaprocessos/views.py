from datetime import datetime
from django.utils import timezone
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.forms import inlineformset_factory

from .models import Usuario, Telefone, ArquiteturaProcesso, Macroprocesso, LogAcoes
from .forms import CriarUsuarioForm, EditarUsuarioForm, TelefoneForm, TelefoneFormSet


class HomePage(TemplateView):
    template_name = 'homepage.html'


class CustomLoginView(LoginView):
    template_name = 'usuario/fazer_login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('arquiteturaprocessos:homepage')
        return super().dispatch(request, *args, **kwargs)


class ArquiteruraProcessos(ListView):
    template_name = 'arquiteruraprocessos.html'
    model = ArquiteturaProcesso


class CadastroProcessos(LoginRequiredMixin, ListView):
    template_name = 'cadastroprocessos.html'
    model = Macroprocesso


class Estatisticas(LoginRequiredMixin, ListView):
    template_name = 'estatisticas.html'
    model = ArquiteturaProcesso


class BackLog(LoginRequiredMixin, ListView):
    template_name = 'backlog.html'
    model = ArquiteturaProcesso


class VisualizarUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/criarusuario.html'
    model = Usuario
    context_object_name = 'usuario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        context['form'] = CriarUsuarioForm(instance=usuario, modo_visualizacao=True)
        context['telefones'] = TelefoneFormSet(instance=usuario, prefix='telefones')
        context['modo_visualizacao'] = True
        context['modo_inclusao'] = False
        context['modo_exclusao'] = False
        context['modo_edicao'] = False
        return context


class EditarUsuario(LoginRequiredMixin, UpdateView):
    template_name = 'usuario/criarusuario.html'
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

            messages.success(self.request, "Usuário atualizado com sucesso!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Corrija os erros abaixo.")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('arquiteturaprocessos:cadastrousuarios')


class ExcluirUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/criarusuario.html'
    model = Usuario

    def post(self, request, *args, **kwargs):
        # Obtém o usuário
        usuario = self.get_object()

        # Exclusão lógica: apenas desativa o usuário e registra a data/hora
        usuario.is_active = False
        usuario.data_ativacaodesativacao = timezone.now()
        usuario.save(update_fields=['is_active', 'data_ativacaodesativacao'])

        messages.success(request, f"Usuário {usuario.username} desativado com sucesso!")
        return redirect('arquiteturaprocessos:cadastrousuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        initial_data = {
            'is_active': usuario.is_active,
            'data_ativacaodesativacao': usuario.data_ativacaodesativacao.strftime("%d/%m/%Y %H:%M:%S")
            if usuario.data_ativacaodesativacao else timezone.localtime().strftime("%d/%m/%Y %H:%M:%S")
        }

        context['form'] = CriarUsuarioForm(instance=usuario, initial=initial_data, modo_exclusao=True)

        # Telefones
        context['telefones'] = TelefoneFormSet(instance=usuario, prefix='telefones')

        # Modos
        context['modo_exclusao'] = True
        context['modo_visualizacao'] = False
        context['modo_inclusao'] = False
        context['modo_edicao'] = False
        # **Nome do usuário para o modal**
        context['usuario_nome'] = usuario.username

        return context

class CadastroUsuarios(LoginRequiredMixin, ListView):
    template_name = 'usuario/cadastrousuarios.html'
    model = Usuario

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:homepage')

        return super().dispatch(request, *args, **kwargs)


class CriarUsuario(LoginRequiredMixin, CreateView):
    template_name = 'usuario/criarusuario.html'
    form_class = CriarUsuarioForm

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

            messages.success(self.request, "Usuário criado com sucesso!")
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, "Por favor, corrija os erros abaixo.")
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('arquiteturaprocessos:cadastrousuarios')


class DetalheUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/detalheusuario.html'
    model = Usuario

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:homepage')

        return super().dispatch(request, *args, **kwargs)


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
