from .models import ArquiteturaProcesso, Macroprocesso, Usuario, LogAcoes, Telefone
from django.shortcuts import render, redirect, reverse
from django.views.generic import TemplateView, ListView, DetailView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages

# Create your views here.
class HomePage(TemplateView):
    template_name = 'homepage.html'

class CustomLoginView(LoginView):
    template_name = 'usuario/fazer_login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('arquiteturaprocessos:homepage')  # redireciona se já estiver logado
        return super().dispatch(request, *args, **kwargs)

class ArquiteruraProcessos(ListView):
    template_name = 'arquiteruraprocessos.html'
    model = ArquiteturaProcesso

#class CadastroProcessos(DetailView):
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
            return redirect('arquiteturaprocessos:homepage')  # ou uma página de acesso negado

        return super().dispatch(request, *args, **kwargs)


class DetalheUsuario(LoginRequiredMixin, DetailView):
    template_name = 'usuario/detalheusuario.html'
    model = Usuario

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:homepage')  # ou uma página de acesso negado

        return super().dispatch(request, *args, **kwargs)


#class LogAcoes(listView):
class LogAcoes(LoginRequiredMixin, ListView):
    template_name = 'usuario/logacoes.html'
    model = LogAcoes

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.perfil.nome.casefold() != 'administrador':
            messages.warning(request, "Você não tem permissão para acessar esta página.")
            return redirect('arquiteturaprocessos:homepage')  # ou uma página de acesso negado

        return super().dispatch(request, *args, **kwargs)





