from django.contrib import admin
from django.urls import path
from .views import (HomePage, ArquiteruraProcessos, CadastroProcessos, CadastroSubProcessos, Estatisticas, BackLog,
                    CadastroUsuarios,  LogAcoes, CustomLoginView, CriarUsuario, VisualizarUsuario, EditarUsuario,
                    ExcluirUsuario, Classificacoes, CriarClassificacao, VisualizarClassificacao, EditarClassificacao,
                    ExcluirClassificacao, MacroProcessoNivel1View, CriarMacroProcessoNivel1, VisualizarMacroProcessoNivel1,
                    EditarMacroProcessoNivel1, ExcluirMacroProcessoNivel1, MacroProcessoNivel2View, CriarMacroProcessoNivel2,
                    VisualizarMacroProcessoNivel2, EditarMacroProcessoNivel2, ExcluirMacroProcessoNivel2, classificacao_por_macro1,
                    macroprocessos_por_classificacao, SubProcessoView, NormaView)
from django.contrib.auth import views as auth_views


app_name = "arquiteturaprocessos"

urlpatterns = [
    path('', HomePage.as_view(), name='homepage'),
    path('arquiteturaprocessos/', ArquiteruraProcessos.as_view(), name='arquiteturaprocessos'),
    path('cadastroprocessos/', CadastroProcessos.as_view(), name='cadastroprocessos'),
    path('cadastrosubprocessos/', CadastroSubProcessos.as_view(), name='cadastrosubprocessos'),
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
    path('form_macroprocessonivel1/', CriarMacroProcessoNivel1.as_view(), name='form_macroprocessonivel1'),
    path('macroprocessonivel1/<int:pk>/visualizar/', VisualizarMacroProcessoNivel1.as_view(), name='visualizar_macroprocessonivel1'),
    path('macroprocessonivel1/<int:pk>/editar/', EditarMacroProcessoNivel1.as_view(), name='editar_macroprocessonivel1'),
    path('macroprocessonivel1/<int:pk>/excluir/', ExcluirMacroProcessoNivel1.as_view(), name='excluir_macroprocessonivel1'),
    path('macroprocessonivel2/', MacroProcessoNivel2View.as_view(), name='macroprocessonivel2'),
    path('form_macroprocessonivel2/', CriarMacroProcessoNivel2.as_view(), name='form_macroprocessonivel2'),
    path('macroprocessonivel2/<int:pk>/visualizar/', VisualizarMacroProcessoNivel2.as_view(), name='visualizar_macroprocessonivel2'),
    path('macroprocessonivel2/<int:pk>/editar/', EditarMacroProcessoNivel2.as_view(), name='editar_macroprocessonivel2'),
    path('macroprocessonivel2/<int:pk>/excluir/', ExcluirMacroProcessoNivel2.as_view(), name='excluir_macroprocessonivel2'),
    path('estrutura/subprocesso/', SubProcessoView.as_view(), name='subprocesso'),
    path('estrutura/norma/', NormaView.as_view(), name='norma'),
    path('api/classificacao_por_macro1/<int:macro1_id>/', classificacao_por_macro1, name='classificacao_por_macro1'),
    path('api/macroprocessos_por_classificacao/<int:classificacao_id>/', macroprocessos_por_classificacao, name='macroprocessos_por_classificacao'),
]
