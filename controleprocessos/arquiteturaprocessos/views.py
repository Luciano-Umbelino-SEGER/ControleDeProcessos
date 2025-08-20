from .models import ArquiteturaProcesso, Macroprocesso, Usuario, LogAcoes
from django.shortcuts import render, redirect, reverse
from django.views.generic import TemplateView, ListView, FormView, View


# Create your views here.
class HomePageView(TemplateView):
    template_name = "homepage.html"

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

#class LogAcoes(listView):
class LogAcoes(ListView):
    template_name = 'usuario/logacoes.html'
    model = LogAcoes





