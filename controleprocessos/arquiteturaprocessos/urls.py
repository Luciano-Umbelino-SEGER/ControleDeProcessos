from django.contrib import admin
from django.urls import path
from .views import (HomePage, ArquiteruraProcessos, CadastroProcessos, Estatisticas, BackLog,
                    CadastroUsuarios,  LogAcoes, CustomLoginView, CriarUsuario, VisualizarUsuario, EditarUsuario,
                    ExcluirUsuario, Classificacoes, CriarClassificacao, VisualizarClassificacao, EditarClassificacao,
                    ExcluirClassificacao, MacroProcessoNivel1View, MacroProcessoNivel2View, SubProcessoView, NormaView)
from django.contrib.auth import views as auth_views


app_name = "arquiteturaprocessos"

urlpatterns = [
    path('', HomePage.as_view(), name='homepage'),
    path('arquiteturaprocessos/', ArquiteruraProcessos.as_view(), name='arquiteturaprocessos'),
    path('cadastroprocessos/', CadastroProcessos.as_view(), name='cadastroprocessos'),
    path('estatisticas/', Estatisticas.as_view(), name='estatisticas'),
    path('backlog/', BackLog.as_view(), name='backlog'),
    path('cadastrousuarios/', CadastroUsuarios.as_view(), name='cadastrousuarios'),
    path('form_usuario/', CriarUsuario.as_view(), name='form_usuario'),
    path('usuario/<int:pk>/visualizar/', VisualizarUsuario.as_view(), name='visualizar_usuario'),
    path('usuario/<int:pk>/editar/', EditarUsuario.as_view(), name='editar_usuario'),
    path('usuario/<int:pk>/excluir/', ExcluirUsuario.as_view(), name='excluir_usuario'),
    path('logacoes/', LogAcoes.as_view(), name='logacoes'),
    path('fazer_login/', CustomLoginView.as_view(), name='fazer_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('classificacoes/', Classificacoes.as_view(), name='classificacoes'),
    path('form_classificacao/', CriarClassificacao.as_view(), name='form_classificacao'),
    path('classificacoes/<int:pk>/visualizar/', VisualizarClassificacao.as_view(), name='visualizar_classificacao'),
    path('classificacoes/<int:pk>/editar/', EditarClassificacao.as_view(), name='editar_classificacao'),
    path('classificacoes/<int:pk>/excluir/', ExcluirClassificacao.as_view(), name='excluir_classificacao'),
    path('macroprocessonivel1/', MacroProcessoNivel1View.as_view(), name='macroprocessonivel1'),
    path('macroprocessonivel2/', MacroProcessoNivel2View.as_view(), name='macroprocessonivel2'),
    path('estrutura/subprocesso/', SubProcessoView.as_view(), name='subprocesso'),
    path('estrutura/norma/', NormaView.as_view(), name='norma')
]
