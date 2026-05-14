# ============================================================
# CONFIGURAÇÕES DE EXPORTAÇÃO DO SIGEMP
# ============================================================

from django.contrib import messages
from django.utils.dateparse import parse_date
from datetime import datetime, time
from urllib.parse import unquote

from arquiteturaprocessos.models import (ModelagemProcesso, ContatoAreaSeger, Usuario, Processo,)
from auditoria.models import LogAcaoSistema
from arquiteturaprocessos.exports.registry import (register_export,)

# -----------------------------------------------------#
# Exportação da Listagem de Modelagem de Processos     #
# -----------------------------------------------------#
class ModelagemProcessosExportConfig:

    filename = 'modelagem_processos'

    titulo_pdf = 'Modelagem de Processos'

    pdf_col_widths = [
        58,  # Tipo
        90,  # Título
        72,  # Tema
        102,  # Modelo Processo
        102,  # Norma Procedimento
        82,  # Emitente
        82,  # Sistema
        48,  # Portaria
        46,  # Data Aprovação
        46,  # Início Vigência
        46,  # Fim Vigência
    ]

    headers = [
        'Tipo',
        'Título',
        'Tema',
        'Modelo de Processo',
        'Norma de Procedimento',
        'Emitente',
        'Sistema',
        'Portaria',
        'Data Aprovação',
        'Início Vigência',
        'Fim Vigência',
    ]

    def get_queryset(self, request):

        return (
            ModelagemProcesso.objects
            .select_related('tipo_documento')
            .all()
        )

    def row_builder(self, obj):

        # Tipo
        tipo_nome = (
            obj.tipo_documento.nome
            .strip()
            .lower()
        )

        if tipo_nome == 'modelo de processo':
            tipo = 'Modelo de Processo'

        elif tipo_nome == 'norma de procedimento':
            tipo = 'Norma de Procedimento'

        else:
            tipo = obj.tipo_documento.nome

        # Sistema
        if obj.codigo or obj.sistema:

            sistema = (
                f'{obj.codigo or ""}'
            )

            if obj.codigo and obj.sistema:
                sistema += ' - '

            sistema += f'{obj.sistema or ""}'

        else:
            sistema = '----'

        return [
            tipo,
            obj.titulo,
            obj.tema or '----',

            (
                unquote(
                    obj.documento_modelagem_processo.name.split('/')[-1]
                )
                if obj.documento_modelagem_processo
                else '----'
            ),

            (
                unquote(
                    obj.link_normaprocedimento.split('/')[-1]
                )
                if obj.link_normaprocedimento
                else '----'
            ),

            obj.emitente or '----',

            sistema,

            obj.portaria_aprovacao or '----',

            (
                obj.data_aprovacao.strftime('%d/%m/%Y')
                if obj.data_aprovacao
                else ''
            ),

            (
                obj.vigencia_inicio.strftime('%d/%m/%Y')
                if obj.vigencia_inicio
                else ''
            ),

            (
                obj.vigencia_fim.strftime('%d/%m/%Y')
                if obj.vigencia_fim
                else ''
            ),
        ]

# -----------------------------------------------------#
# Exportação da Listagem de Áreas Responsáveis         #
# -----------------------------------------------------#
class AreasResponsaveisExportConfig:

    filename = 'areas_responsaveis'

    titulo_pdf = 'Áreas Responsáveis'

    pdf_col_widths = [

        140,  # Área
        130,  # Titular
        155,  # E-mail
        95,  # Telefone/Ramal
        65,  # Origem
        42,  # Estado
        67,  # Criado
        67,  # Atualizado
    ]

    headers = [
        'Área',
        'Titular',
        'E-mail',
        'Telefone/Ramal',
        'Origem',
        'Estado',
        'Criado',
        'Atualizado',
    ]

    def get_queryset(self, request):

        queryset = (
            ContatoAreaSeger.objects
            .all()
            .order_by('nome_area')
        )

        # ===== FILTROS =====
        nome_area = request.GET.get(
            "nome_area",
            ""
        ).strip()

        titular = request.GET.get(
            "titular",
            ""
        ).strip()

        email = request.GET.get(
            "email",
            ""
        ).strip()

        ativo = request.GET.get(
            "ativo",
            ""
        ).strip()

        origem = request.GET.get(
            "origem",
            ""
        ).strip()

        # 🔍 FILTROS
        if nome_area:

            queryset = queryset.filter(
                nome_area__icontains=nome_area
            )

        if titular:

            queryset = queryset.filter(
                titular__icontains=titular
            )

        if email:

            queryset = queryset.filter(
                email__icontains=email
            )

        if ativo in ["True", "False"]:

            queryset = queryset.filter(
                ativo=(ativo == "True")
            )

        if origem:

            queryset = queryset.filter(
                origem=origem
            )

        return queryset

    def row_builder(self, obj):

        return [
            obj.nome_area,

            obj.titular or '----',

            obj.email or '----',

            (
                obj.telefone
                .replace('|', '<br/>')
                if obj.telefone
                else '----'
            ),

            obj.get_origem_display(),

            'Ativo' if obj.ativo else 'Inativo',

            (
                obj.criado_em.strftime(
                    '%d/%m/%Y %H:%M'
                )
                if obj.criado_em
                else '----'
            ),

            (
                obj.atualizado_em.strftime(
                    '%d/%m/%Y %H:%M'
                )
                if obj.atualizado_em
                else '----'
            ),
        ]

# -----------------------------------------------------#
# Exportação da Listagem Usuários                      #
# -----------------------------------------------------#
class UsuariosExportConfig:

    filename = 'usuarios'

    titulo_pdf = 'Cadastro de Usuários'

    headers = [
        'Usuário',
        'Nome',
        'Setor',
        'Cargo',
        'Perfil',
        'Estado',
        'Telefone',
        'E-mail',
    ]

    pdf_col_widths = [
        75,   # Usuário
        120,  # Nome
        110,  # Setor
        105,  # Cargo
        65,   # Perfil
        45,   # Estado
        95,   # Telefone
        150,  # E-mail
    ]

    def get_queryset(self, request):

        return (
            Usuario.objects
            .select_related('perfil')
            .prefetch_related('telefones')
            .all()
            .order_by('username')
        )

    def row_builder(self, obj):

        telefones = ' | '.join(
            telefone.numero_formatado
            for telefone in obj.telefones.all()
        )

        return [

            obj.username or '----',

            (
                f'{obj.first_name} {obj.last_name}'.strip()
                or '----'
            ),

            obj.setor or '----',

            obj.cargo or '----',

            (
                obj.perfil.nome
                if obj.perfil
                else '----'
            ),

            (
                'Ativo'
                if obj.is_active
                else 'Inativo'
            ),

            (
                telefones
                if telefones
                else '----'
            ),

            obj.email or '----',
        ]

# -----------------------------------------------------#
# Exportação da Listagem de Log de Ações               #
# -----------------------------------------------------#
class LogAcoesExportConfig:

    filename = 'log_acoes'

    titulo_pdf = 'Log de Ações'

    headers = [
        'Data/Hora',
        'Usuário',
        'Perfil',
        'Ação',
        'Modelo',
        'Descrição',
    ]

    pdf_col_widths = [
        78,   # Data/Hora
        95,   # Usuário
        60,   # Perfil
        55,   # Ação
        90,   # Modelo
        300,  # Descrição
    ]

    def get_queryset(self, request):

        queryset = (
            LogAcaoSistema.objects
            .select_related(
                'usuario',
                'usuario__perfil',
            )
            .order_by('-data_registro')
        )

        # FILTROS
        usuario = request.GET.get('usuario')
        perfil = request.GET.get('perfil')
        acao = request.GET.get('acao')
        modelo = request.GET.get('modelo')
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')

        from django.db.models import Q, Value
        from django.db.models.functions import Concat

        if usuario:

            queryset = queryset.annotate(
                nome_completo=Concat(
                    'usuario__first_name',
                    Value(' '),
                    'usuario__last_name',
                )
            ).filter(
                Q(usuario__username__icontains=usuario)
                |
                Q(nome_completo__icontains=usuario)
            )

        if perfil:

            queryset = queryset.filter(
                usuario__perfil__nome__icontains=perfil
            )

        if acao:

            queryset = queryset.filter(
                acao=acao
            )

        if modelo:

            queryset = queryset.filter(
                modelo_afetado__icontains=modelo
            )

        if data_inicio:

            queryset = queryset.filter(
                data_registro__date__gte=data_inicio
            )

        if data_fim:

            queryset = queryset.filter(
                data_registro__date__lte=data_fim
            )

        return queryset

    def row_builder(self, obj):

        return [

            (
                obj.data_registro.strftime(
                    '%d/%m/%Y %H:%M:%S'
                )
                if obj.data_registro
                else '----'
            ),

            (
                obj.usuario.get_full_name()
                or obj.usuario.username
            )
            if obj.usuario
            else 'Sistema',

            (
                obj.usuario.perfil.nome
                if (
                    obj.usuario
                    and obj.usuario.perfil
                )
                else '----'
            ),

            obj.acao or '----',

            obj.modelo_afetado or '----',

            obj.descricao or '----',
        ]

# -----------------------------------------------------#
# Exportação da Arquitetura de Processos               #
# -----------------------------------------------------#
class ArquiteturaProcessosExportConfig:

    filename = 'arquitetura_processos'

    titulo_pdf = 'Arquitetura de Processos'

    headers = [
        'Processo / Subprocesso',
        'Objetivo',
        'Classificação',
        'Macro N1',
        'Macro N2',
        'Área Responsável',
        'Gestor',
        'Telefone',
        'Versão',
        'Criado em',
        'Documentos Associados',
    ]

    pdf_col_widths = [
        120,  # Processo/Subprocesso
        110,  # Objetivo
        60,   # Classificação
        80,   # Macro N1
        80,   # Macro N2
        67,   # Área
        67,   # Gestor
        64,   # Telefone
        35,   # Versão
        53,   # Criado em
        47,   # Docs
    ]

    pdf_center_columns = [8, 9, 10]

    # -------------------------------------------------
    # Queryset
    # -------------------------------------------------
    def get_queryset(self, request):

        req = request.GET

        nome = req.get("nome", "").strip()
        classificacao = req.get("classificacao", "").strip()
        macro1 = req.get("macro1", "").strip()
        macro2 = req.get("macro2", "").strip()
        area = req.get("area", "").strip()

        cri_de_raw = req.get("criacao_de")
        cri_ate_raw = req.get("criacao_ate")

        cri_de = parse_date(cri_de_raw) if cri_de_raw else None
        cri_ate = parse_date(cri_ate_raw) if cri_ate_raw else None

        # 🔥 Validação
        if cri_de and cri_ate and cri_ate < cri_de:
            return Processo.objects.none()

        qs = (
            Processo.objects
            .filter(parent__isnull=True)
            .select_related(
                "classificacao",
                "macroprocesso_nivel1",
                "macroprocesso_nivel2",
                "area_responsavel",
            )
            .prefetch_related(
                "documentos__modelagem_processo__tipo_documento",
                "subprocessos__documentos__modelagem_processo__tipo_documento",
                "subprocessos",
            )
            .order_by("id")
        )

        # --------------------
        # Filtros
        # --------------------
        if nome:
            qs = qs.filter(nome__icontains=nome)

        if classificacao:
            qs = qs.filter(classificacao_id=classificacao)

        if macro1:
            qs = qs.filter(
                macroprocesso_nivel1__nome__icontains=macro1
            )

        if macro2:
            qs = qs.filter(
                macroprocesso_nivel2__nome__icontains=macro2
            )

        if area:
            qs = qs.filter(
                area_responsavel__nome_area__icontains=area
            )

        if cri_de:
            qs = qs.filter(data_criacao__gte=cri_de)

        if cri_ate:
            fim_do_dia = datetime.combine(
                cri_ate,
                time.max
            )

            qs = qs.filter(
                data_criacao__lte=fim_do_dia
            )

        return qs

    # -------------------------------------------------
    # Linha individual
    # -------------------------------------------------
    def build_row(self, obj, is_subprocesso=False):

        telefone = obj.telefone or ''

        nome = (
            f'-> {obj.nome}'
            if is_subprocesso
            else obj.nome
        )

        docs_count = obj.documentos.count()

        # -------------------------------------------------
        # Blindagem contra FK órfã
        # -------------------------------------------------

        try:
            macro_n1 = (
                obj.macroprocesso_nivel1.nome
                if obj.macroprocesso_nivel1
                else '----'
            )

        except Exception:
            macro_n1 = '----'

        try:
            macro_n2 = (
                obj.macroprocesso_nivel2.nome
                if obj.macroprocesso_nivel2
                else '----'
            )

        except Exception:
            macro_n2 = '----'

        try:
            classificacao = (
                obj.classificacao.nome
                if obj.classificacao
                else '----'
            )

        except Exception:
            classificacao = '----'

        try:
            area_responsavel = (
                obj.area_responsavel.nome_area
                if obj.area_responsavel
                else '----'
            )

        except Exception:
            area_responsavel = '----'

        return [

            nome or '----',

            obj.objetivo or '----',

            classificacao,

            macro_n1,

            macro_n2,

            area_responsavel,

            obj.gestor or '----',

            (
                telefone.replace('|', '<br/>')
                if telefone
                else '----'
            ),

            (
                obj.versao_processo
                if obj.versao_processo
                else '—'
            ),

            (
                obj.data_criacao.strftime('%d/%m/%Y')
                if obj.data_criacao
                else '----'
            ),

            f'({docs_count})',
        ]

    # -------------------------------------------------
    # Construção hierárquica
    # -------------------------------------------------
    def build_rows(self, obj):

        linhas = []

        # Processo pai
        linhas.append(
            self.build_row(obj)
        )

        # Subprocessos
        for sub in obj.subprocessos.all():

            linhas.append(
                self.build_row(
                    sub,
                    is_subprocesso=True
                )
            )

        return linhas

# ============================================================
# REGISTRO DA EXPORTAÇÃO
# ============================================================
register_export(
    key='modelagemprocessos',
    config=ModelagemProcessosExportConfig(),
)

register_export(
    key='areasresponsaveis',
    config=AreasResponsaveisExportConfig(),
)

register_export(
    key='usuarios',
    config=UsuariosExportConfig(),
)

register_export(
    key='logacoes',
    config=LogAcoesExportConfig(),
)

register_export(
    key='arquiteturaprocessos',
    config=ArquiteturaProcessosExportConfig(),
)