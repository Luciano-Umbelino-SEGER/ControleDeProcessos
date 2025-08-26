from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView, ListView, DetailView, FormView
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


class CriarUsuario(LoginRequiredMixin, FormView):
    template_name = 'usuario/criarusuario.html'
    form_class = CriarUsuarioForm

    def get_context_data(self, **kwargs):
        """
        Injeta o formset de telefones no contexto.
        """
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['telefones'] = TelefoneFormSet(self.request.POST, prefix='telefones')
        else:
            context['telefones'] = TelefoneFormSet(prefix='telefones')
        return context

    def form_valid(self, form):
        """
        Salva usuário e os telefones vinculados.
        """
        context = self.get_context_data()
        telefones = context['telefones']

        if telefones.is_valid():
            # Salva usuário primeiro
            self.object = form.save()

            # Associa o formset ao usuário criado
            telefones.instance = self.object
            telefones.save()

            messages.success(self.request, "Usuário criado com sucesso!")
            return redirect(self.get_success_url())
        else:
            # Se os telefones forem inválidos, renderiza o form com erros
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        """
        Caso o form principal seja inválido.
        """
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
