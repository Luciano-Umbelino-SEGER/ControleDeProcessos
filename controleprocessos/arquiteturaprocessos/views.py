from datetime import datetime
from django.utils import timezone
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages

from .models import ArquiteturaProcesso, Macroprocesso, Usuario, LogAcoes
from .forms import CriarUsuarioForm, TelefoneFormSet


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
        context['form'] = CriarUsuarioForm(instance=usuario)
        context['telefones'] = TelefoneFormSet(instance=usuario, prefix='telefones')
        context['modo_visualizacao'] = True
        return context

class EditarUsuario(LoginRequiredMixin, UpdateView):
    template_name = 'usuario/criarusuario.html'
    model = Usuario
    form_class = CriarUsuarioForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['telefones'] = TelefoneFormSet(self.request.POST, instance=self.object, prefix='telefones')
        else:
            context['telefones'] = TelefoneFormSet(instance=self.object, prefix='telefones')
        context['modo_edicao'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        telefones = context['telefones']
        if telefones.is_valid():
            self.object = form.save()
            telefones.instance = self.object
            telefones.save()
            messages.success(self.request, "Usuário atualizado com sucesso!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Corrija os erros abaixo.")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):

        class ExcluirUsuario(LoginRequiredMixin, DetailView):
            template_name = 'usuario/criarusuario.html'
            model = Usuario

            def post(self, request, *args, **kwargs):
                usuario = self.get_object()
                usuario.delete()
                messages.success(request, "Usuário excluído com sucesso!")
                return redirect('arquiteturaprocessos:cadastrousuarios')

            def get_context_data(self, **kwargs):
                context = super().get_context_data(**kwargs)
                usuario = self.get_object()
                context['form'] = CriarUsuarioForm(instance=usuario)
                context['telefones'] = TelefoneFormSet(instance=usuario, prefix='telefones')
                context['modo_exclusao'] = True
                return context

class ExcluirUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/criarusuario.html'
    model = Usuario

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        usuario.delete()
        messages.success(request, "Usuário excluído com sucesso!")
        return redirect('arquiteturaprocessos:cadastrousuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        context['form'] = CriarUsuarioForm(instance=usuario)
        context['telefones'] = TelefoneFormSet(instance=usuario, prefix='telefones')
        context['modo_exclusao'] = True
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
        """
        Injeta o formset de telefones no contexto.
        """
        if self.request.POST:
            context['telefones'] = TelefoneFormSet(self.request.POST, prefix='telefones')
        else:
            context['telefones'] = TelefoneFormSet(prefix='telefones')
        return context

    def form_valid(self, form):
        print("Entrou no form_valid")

        context = self.get_context_data()
        telefones = context['telefones']

        if telefones.is_valid():
            self.object = form.save(commit=False)

            # Captura campos extras
            is_active = self.request.POST.get("is_active")
            data_ativacao = self.request.POST.get("data_ativacaodesativacao")
            date_joined = self.request.POST.get("date_joined")

            print("is_active:", is_active)
            print("data_ativacaodesativacao:", data_ativacao)
            print("date_joined:", date_joined)

            self.object.is_active = is_active == "True"
            self.object.data_ativacaodesativacao = data_ativacao or timezone.now()
            self.object.date_joined = date_joined or timezone.now()

            self.object.save()
            print("Usuário salvo com ID:", self.object.pk)

            telefones.instance = self.object
            telefones.save()

            messages.success(self.request, "Usuário criado com sucesso!")
            return redirect(self.get_success_url())
        else:
            print("Erros no formset de telefones:", telefones.errors)
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
