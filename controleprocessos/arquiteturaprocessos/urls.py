from django.contrib import admin
from django.urls import path, reverse_lazy
from . import views
from .views import (ArquiteruraProcessos, CadastroUsuarios, CustomLoginView, CustomPasswordResetConfirmView, alterar_senha,
                    CriarUsuario, VisualizarUsuario, EditarUsuario, ExcluirUsuario, Classificacoes, CriarClassificacao,
                    VisualizarClassificacao, EditarClassificacao, ExcluirClassificacao, MacroProcessoNivel1View,
                    CriarMacroProcessoNivel1, VisualizarMacroProcessoNivel1, EditarMacroProcessoNivel1,
                    ExcluirMacroProcessoNivel1, MacroProcessoNivel2View, CriarMacroProcessoNivel2, VisualizarMacroProcessoNivel2,
                    EditarMacroProcessoNivel2, ExcluirMacroProcessoNivel2, TipoDocumentoList, CriarTipoDocumento,
                    VisualizarTipoDocumento,EditarTipoDocumento, ExcluirTipoDocumento, ModelagemProcessoView,
                    CriarModelagemProcesso, VisualizarModelagemProcesso, EditarModelagemProcesso, ExcluirModelagemProcesso,
                    ProcessoView, CriarProcesso, VisualizarProcesso, EditarProcesso, ExcluirProcesso, SubProcessoView,
                    ProcessosMapear, CriarProcessoMapear, VisualizarProcessoMapear, EditarProcessoMapear, ExcluirProcessoMapear,
                    ExecutarIniciarProcessoMapear, FinalizarProcessoMapear, EstatisticasDashboard, EstatisticasProcessosMapear,
                    EstatisticaComparativos, AreasResponsaveisList, CriarAreasResponsaveis, VisualizarAreasResponsaveis,
                    EditarAreasResponsaveis, ExcluirAreasResponsaveis, ImportarContatosSeger, ReativarAreasResponsaveis,
                    exportar_modelagemprocessos_csv, exportar_modelagemprocessos_txt, exportar_modelagemprocessos_xlsx,
                    exportar_modelagemprocessos_pdf)
from .api_views import (classificacao_por_macro1, macroprocessos_por_classificacao, macro2_por_macro1,
                        macro1_e_classificacao_por_macro2, macro1_todos, macro2_todos, processos_pai)
from .utils_views import verificar_similaridade

from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

app_name = "arquiteturaprocessos"

urlpatterns = [
    path('doc/pdf/<path:path>/', views.visualizar_pdf, name='visualizar_pdf'),
    # Home Page - Arquitetura de Processos
    path('', ArquiteruraProcessos.as_view(), name='homepage'),
    # Arquitetura de Processos
    path('arquiteturaprocessos/', ArquiteruraProcessos.as_view(), name='arquiteturaprocessos'),
    # Estatísticas
    path("estatisticas/", EstatisticasDashboard.as_view(), name="estatisticas_dashboard"),
    path("estatisticas/processos-mapear/", EstatisticasProcessosMapear.as_view(), name="estatisticaprocessos_mapear" ),
    path("estatisticas/processos/", views.EstatisticasProcessos.as_view(), name="estatisticas_processos"),
    path("estatisticas/comparativos/", EstatisticaComparativos.as_view(), name="estatisticas_comparativos"),
    # Selecionar Processos Pai
    path('api/processos/', views.buscar_processos, name='buscar_processos'),
    # Obter dados do Processos Pai para Herança de Subprocesso
    path("processo/<int:pk>/dados/", views.obter_dados_processo, name="obter_dados_processo"),
    # Obter dados do Contato Área Responsável
    path("buscar-contato-area/", views.buscar_contato_area, name="buscar_contato_area"),
    # Processo a Mapear
    path('processosmapear/', ProcessosMapear.as_view(), name='processosmapear'),
    path('processosmapear/novo/', CriarProcessoMapear.as_view(), name='criar_processomapear'),
    path('processosmapear/<int:pk>/visualizar/', VisualizarProcessoMapear.as_view(), name='visualizar_processomapear'),
    path('processosmapear/<int:pk>/editar/', EditarProcessoMapear.as_view(), name='editar_processomapear'),
    path('processosmapear/<int:pk>/excluir/', ExcluirProcessoMapear.as_view(), name='excluir_processomapear'),
    path("processosmapear/<int:pk>/executar-iniciar/", ExecutarIniciarProcessoMapear.as_view(), name="executar_iniciar_processomapear"),
    path('processosmapear/<int:pk>/finalizar/', FinalizarProcessoMapear.as_view(), name='finalizar_processomapear'),
    # Usuários
    path('cadastrousuarios/', CadastroUsuarios.as_view(), name='cadastrousuarios'),
    path('usuario/novo/', CriarUsuario.as_view(), name='criar_usuario'),
    path('usuario/<int:pk>/visualizar/', VisualizarUsuario.as_view(), name='visualizar_usuario'),
    path('usuario/<int:pk>/editar/', EditarUsuario.as_view(), name='editar_usuario'),
    path('usuario/<int:pk>/excluir/', ExcluirUsuario.as_view(), name='excluir_usuario'),
    # --> Reset de Senha (fluxo por link)
    path("usuario/<int:pk>/resetar-senha/", views.resetar_senha_usuario, name="resetar_senha_usuario",),
    path("senha/reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(
          template_name="usuario/password_reset_confirm.html", success_url=reverse_lazy("arquiteturaprocessos:password_reset_complete"),),
          name="password_reset_confirm",),
    path("senha/reset/concluido/", auth_views.PasswordResetCompleteView.as_view(template_name="usuario/password_reset_complete.html"),
          name="password_reset_complete",),
    # --> Alterar senha (usuário logado)
    path("senha/alterar/", alterar_senha, name="alterar_senha",),
    # Login
    path('fazer_login/', CustomLoginView.as_view(), name='fazer_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Classificações
    path('classificacoes/', Classificacoes.as_view(), name='classificacoes'),
    path('classificacao/novo/', CriarClassificacao.as_view(), name='criar_classificacao'),
    path('classificacoes/<int:pk>/visualizar/', VisualizarClassificacao.as_view(), name='visualizar_classificacao'),
    path('classificacoes/<int:pk>/editar/', EditarClassificacao.as_view(), name='editar_classificacao'),
    path('classificacoes/<int:pk>/excluir/', ExcluirClassificacao.as_view(), name='excluir_classificacao'),
    # Macroprocesso Nivel 1
    path('macroprocessonivel1/', MacroProcessoNivel1View.as_view(), name='macroprocessonivel1'),
    path('macroprocessonivel1/novo/', CriarMacroProcessoNivel1.as_view(), name='criar_macroprocessonivel1'),
    path('macroprocessonivel1/<int:pk>/visualizar/', VisualizarMacroProcessoNivel1.as_view(), name='visualizar_macroprocessonivel1'),
    path('macroprocessonivel1/<int:pk>/editar/', EditarMacroProcessoNivel1.as_view(), name='editar_macroprocessonivel1'),
    path('macroprocessonivel1/<int:pk>/excluir/', ExcluirMacroProcessoNivel1.as_view(), name='excluir_macroprocessonivel1'),
    # Macroprocesso Nivel 2
    path('macroprocessonivel2/', MacroProcessoNivel2View.as_view(), name='macroprocessonivel2'),
    path('macroprocessonivel2/novo/', CriarMacroProcessoNivel2.as_view(), name='criar_macroprocessonivel2'),
    path('macroprocessonivel2/<int:pk>/visualizar/', VisualizarMacroProcessoNivel2.as_view(), name='visualizar_macroprocessonivel2'),
    path('macroprocessonivel2/<int:pk>/editar/', EditarMacroProcessoNivel2.as_view(), name='editar_macroprocessonivel2'),
    path('macroprocessonivel2/<int:pk>/excluir/', ExcluirMacroProcessoNivel2.as_view(), name='excluir_macroprocessonivel2'),
    path('estrutura/subprocesso/', SubProcessoView.as_view(), name='subprocesso'),
    # Tipos de Documento
    path('tiposdocumento/', TipoDocumentoList.as_view(), name='tiposdocumento'),
    path('tiposdocumento/novo/', CriarTipoDocumento.as_view(), name='criar_tipodocumento'),
    path('tiposdocumento/<int:pk>/', VisualizarTipoDocumento.as_view(), name='visualizar_tipodocumento'),
    path('tiposdocumento/<int:pk>/editar/', EditarTipoDocumento.as_view(), name='editar_tipodocumento'),
    path('tiposdocumento/<int:pk>/excluir/', ExcluirTipoDocumento.as_view(), name='excluir_tipodocumento'),
    # Modelagem Processos
    path('modelagemprocessos/', ModelagemProcessoView.as_view(), name='modelagemprocessos'),
    path('modelagemprocesso/novo/', CriarModelagemProcesso.as_view(), name='criar_modelagemprocesso'),
    path('modelagemprocesso/<int:pk>/visualizar/', VisualizarModelagemProcesso.as_view(), name='visualizar_modelagemprocesso'),
    path('modelagemprocesso/<int:pk>/editar/', EditarModelagemProcesso.as_view(), name='editar_modelagemprocesso'),
    path('modelagemprocesso/<int:pk>/excluir/', ExcluirModelagemProcesso.as_view(), name='excluir_modelagemprocesso'),
    # Exportação de Arquivos
    path('modelagemprocessos/exportar/csv/', exportar_modelagemprocessos_csv, name='exportar_modelagemprocessos_csv'),
    path('modelagemprocessos/exportar/txt/', exportar_modelagemprocessos_txt, name='exportar_modelagemprocessos_txt'),
    path('modelagemprocessos/exportar/xlsx/', exportar_modelagemprocessos_xlsx, name='exportar_modelagemprocessos_xlsx'),
    path('modelagemprocessos/exportar/pdf/', exportar_modelagemprocessos_pdf, name='exportar_modelagemprocessos_pdf'),
    # Áreas Responsáveis
    path('areasresponsaveis/', AreasResponsaveisList.as_view(), name='areasresponsaveis'),
    path('areasresponsaveis/novo/', CriarAreasResponsaveis.as_view(), name='criar_areasresponsaveis'),
    path('areasresponsaveis/<int:pk>/visualizar/', VisualizarAreasResponsaveis.as_view(), name='visualizar_areasresponsaveis'),
    path('areasresponsaveis/<int:pk>/editar/', EditarAreasResponsaveis.as_view(), name='editar_areasresponsaveis'),
    path('areasresponsaveis/<int:pk>/excluir/', ExcluirAreasResponsaveis.as_view(), name='excluir_areasresponsaveis'),
    path('areasresponsaveis/importarcontatos/', ImportarContatosSeger.as_view(), name='importar_contatos_seger'),
    path('areasresponsaveis/<int:pk>/reativar/', ReativarAreasResponsaveis.as_view(), name='reativar_areasresponsaveis'),
    # Processos
    path('processos/', ProcessoView.as_view(), name='processos'),
    path('processo/novo/', CriarProcesso.as_view(), name='criar_processo'),
    path('processo/<int:pk>/visualizar/', VisualizarProcesso.as_view(), name='visualizar_processo'),
    path('processo/<int:pk>/editar/', EditarProcesso.as_view(), name='editar_processo'),
    path('processo/<int:pk>/excluir/', ExcluirProcesso.as_view(), name='excluir_processo'),
    path("processos/<int:pk>/concluir/", views.concluir_processo, name="concluir_processo"),
    # Endpoints - APIs
    # --> Classificação → Macro1
    path('api/classificacao_por_macro1/<int:macro1_id>/', classificacao_por_macro1, name='classificacao_por_macro1'),
    # --> Macro1 → Classificação
    path('api/macroprocessos_por_classificacao/<int:classificacao_id>/', macroprocessos_por_classificacao, name='macroprocessos_por_classificacao'),
    # --> Macro1 → Macro2
    path('api/macro2_por_macro1/<int:macro1_id>/', macro2_por_macro1, name='macro2_por_macro1'),
    # --> Macro2 → Macro1 + Classificação
    path('api/macro1_e_classificacao_por_macro2/<int:macro2_id>/', macro1_e_classificacao_por_macro2, name='macro1_e_classificacao_por_macro2'),
    # --> Macro1 → Tods
    path('api/macro1_todos/', macro1_todos, name='macro1_todos'),
    # --> Macro2 → Tods
    path('api/macro2_todos/', macro2_todos, name='macro2_todos'),
    # --> Todos Processos Pai
    path('api/processos_pai/', processos_pai, name='processos_pai'),
    # --> Utilitários
    path('utils/text-similarity/', verificar_similaridade, name='utils_text_similarity',),
    #
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
