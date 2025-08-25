from django.contrib import admin
from django.urls import path
from .views import (HomePage, ArquiteruraProcessos, CadastroProcessos, Estatisticas, BackLog,
                    CadastroUsuarios, DetalheUsuario, LogAcoes, CustomLoginView, CriarUsuario)
from django.contrib.auth import views as auth_views


app_name = "arquiteturaprocessos"

urlpatterns = [
    path('', HomePage.as_view(), name='homepage'),
    path('arquiteturaprocessos/', ArquiteruraProcessos.as_view(), name='arquiteturaprocessos'),
    path('cadastroprocessos/', CadastroProcessos.as_view(), name='cadastroprocessos'),
    path('estatisticas/', Estatisticas.as_view(), name='estatisticas'),
    path('backlog/', BackLog.as_view(), name='backlog'),
    path('cadastrousuarios/', CadastroUsuarios.as_view(), name='cadastrousuarios'),
    path('criarusuario/', CriarUsuario.as_view(), name='criarusuario'),
    path('detalheusuario/<int:pk>', DetalheUsuario.as_view(), name='detalheusuario'),
    path('logacoes/', LogAcoes.as_view(), name='logacoes'),
    path('fazer_login/', CustomLoginView.as_view(), name='fazer_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout')
]