from django.contrib import admin
from django.urls import path
from .views import (HomePageView, HomePage, ArquiteruraProcessos, CadastroProcessos, Estatisticas, BackLog,
                    CadastroUsuarios, LogAcoes)
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', HomePageView.as_view(), name='homepage'),
    path('arquiteturaprocessos/', ArquiteruraProcessos.as_view(), name='arquiteturaprocessos'),
    path('cadastroprocessos/', CadastroProcessos.as_view(), name='cadastroprocessos'),
    path('estatisticas/', Estatisticas.as_view(), name='estatisticas'),
    path('backlog/', BackLog.as_view(), name='backlog'),
    path('cadastrousuarios/', CadastroUsuarios.as_view(), name='cadastrousuarios'),
    path('logacoes/', LogAcoes.as_view(), name='logacoes'),
    path('fazer_login/', auth_views.LoginView.as_view(template_name='usuario/fazer_login.html'), name='fazer_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout')
]