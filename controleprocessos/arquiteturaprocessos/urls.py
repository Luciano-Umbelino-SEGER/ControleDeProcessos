from django.contrib import admin
from django.urls import path
from .views import (HomePage, ArquiteruraProcessos, CadastroProcessos, Estatisticas, BackLog,
                    CadastroUsuarios, DetalheUsuario, LogAcoes, CustomLoginView, CriarUsuario,
                    VisualizarUsuario, EditarUsuario, ExcluirUsuario, Classificacoes, CriarClassificacao,
                    MacroProcessoView, SubProcessoView, NormaView)
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
    path('usuario/<int:pk>/visualizar/', VisualizarUsuario.as_view(), name='visualizar_usuario'),
    path('usuario/<int:pk>/editar/', EditarUsuario.as_view(), name='editar_usuario'),
    path('usuario/<int:pk>/excluir/', ExcluirUsuario.as_view(), name='excluir_usuario'),
    path('detalheusuario/<int:pk>', DetalheUsuario.as_view(), name='detalheusuario'),
    path('logacoes/', LogAcoes.as_view(), name='logacoes'),
    path('fazer_login/', CustomLoginView.as_view(), name='fazer_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('classificacoes/', Classificacoes.as_view(), name='classificacoes'),
    path('criar_classificacao/', CriarClassificacao.as_view(), name='criar_classificacao'),
    #path('classificacoes/<int:pk>/exibir/', ExibirClassificacaoView.as_view(), name='exibir'),
    #path('classificacoes/<int:pk>/editar/', EditarClassificacaoView.as_view(), name='editar'),
    #path('classificacoes/<int:pk>/excluir/', ExcluirClassificacaoView.as_view(), name='excluir'),
    path('estrutura/macroprocesso/', MacroProcessoView.as_view(), name='macroprocesso'),
    path('estrutura/subprocesso/', SubProcessoView.as_view(), name='subprocesso'),
    path('estrutura/norma/', NormaView.as_view(), name='norma')
]
