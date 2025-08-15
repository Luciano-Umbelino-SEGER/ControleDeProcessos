from .models import ArquiteturaProcesso, Macroprocesso, Usuario
from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView

# Create your views here.
class HomePage(TemplateView):
    template_name = 'homepage.html'

class ArquiteruraProcessos(ListView):
    template_name = 'arquiteruraprocessos.html'
    model = ArquiteturaProcesso

#class CadastroProcessos(DetailView):
class CadastroProcessos(ListView):
    template_name = 'cadastroprocessos.html'
    model = Macroprocesso

class Estatisticas(ListView):
    template_name = 'estatisticas.html'
    model = ArquiteturaProcesso

class BackLog(ListView):
    template_name = 'backlog.html'
    model = ArquiteturaProcesso

#class CadastroUsuarios(DetailView):
class CadastroUsuarios(ListView):
    template_name = 'usuario/cadastrousuarios.html'
    model = Usuario

#class Login(DetailView):
class Login(ListView):
    template_name = 'usuario/login.html'
    model = Usuario