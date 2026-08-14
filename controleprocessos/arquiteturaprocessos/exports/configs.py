# ============================================================
# CONFIGURAÇÕES DE EXPORTAÇÃO DO SIGEMP
# ============================================================

from django.contrib import messages
from django.utils.dateparse import parse_date
from datetime import datetime, time
from urllib.parse import unquote

from arquiteturaprocessos.models import (ContatoAreaSeger, Usuario, Processo, ProcessoMapear,
                                         MacroprocessoNivel1, MacroprocessoNivel2,)
from auditoria.models import LogAcaoSistema
from arquiteturaprocessos.exports.registry import (register_export,)

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
                telefone
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

# -----------------------------------------------------#
# Exportação Processos a Mapear                        #
# -----------------------------------------------------#
class ProcessosMapearExportConfig:

    filename = 'processos_mapear'
    titulo_pdf = 'Processos a Mapear'

    headers = [
        'Nome',
        'Tipo',
        'Abrangência',
        'Classificação',
        'Macro N1',
        'Macro N2',
        'Área',
        'Criação',
        'Data Finalização',
        'Situação',
    ]

    pdf_col_widths = [
        120,  # Nome
        55,   # Tipo
        60,   # Abrangência
        70,   # Classificação
        82,   # Macro N1
        82,   # Macro N2
        70,   # Área
        50,   # Criação
        70,   # Data Finalização
        65,   # Situação
    ]

    pdf_center_columns = [2, 3, 8, 9, 10]

    # -------------------------------------------------
    # Queryset
    # -------------------------------------------------
    def get_queryset(self, request):

        req = request.GET

        queryset = (
            ProcessoMapear.objects
            .select_related(
                'classificacao',
                'macroprocesso_nivel1',
                'macroprocesso_nivel2',
                'parent',
                'area_responsavel',
            )
            .order_by('-data_criacao')
        )

        # =================================================
        # FILTROS
        # =================================================

        nome = req.get("nome", "").strip()
        tipo = req.get("tipo", "").strip()
        abrangencia = req.get("abrangencia", "").strip()
        classificacao = req.get("classificacao", "").strip()
        macro1 = req.get("macro1", "").strip()
        macro2 = req.get("macro2", "").strip()
        area = req.get("area", "").strip()

        cri_de_raw = req.get("criacao_de")
        cri_ate_raw = req.get("criacao_ate")

        cri_de = parse_date(cri_de_raw) if cri_de_raw else None
        cri_ate = parse_date(cri_ate_raw) if cri_ate_raw else None

        status = req.get("status", "ativo").strip()

        # =================================================
        # VALIDAÇÃO DO PERÍODO
        # =================================================
        if cri_de and cri_ate and cri_ate < cri_de:
            return ProcessoMapear.objects.none()

        # =================================================
        # NOME
        # =================================================
        if nome:
            queryset = queryset.filter(
                nome__icontains=nome
            )

        # =================================================
        # TIPO
        # =================================================
        if tipo in [
            "processo",
            "subprocesso",
            "outro",
        ]:
            queryset = queryset.filter(
                tipo=tipo
            )

        # =================================================
        # ABRANGÊNCIA
        # =================================================
        if abrangencia in [
            "GOVES",
            "SEGER",
            "OUTROS",
        ]:
            queryset = queryset.filter(
                abrangencia=abrangencia
            )

        # =================================================
        # CLASSIFICAÇÃO
        # =================================================
        if classificacao:
            queryset = queryset.filter(
                classificacao_id=classificacao
            )

        # =================================================
        # MACROPROCESSO NÍVEL 1
        # =================================================
        if macro1:
            queryset = queryset.filter(
                macroprocesso_nivel1__nome__icontains=macro1
            )

        # =================================================
        # MACROPROCESSO NÍVEL 2
        # =================================================
        if macro2:
            queryset = queryset.filter(
                macroprocesso_nivel2__nome__icontains=macro2
            )

        # =================================================
        # ÁREA RESPONSÁVEL
        # =================================================
        if area:
            queryset = queryset.filter(
                area_responsavel__nome_area__icontains=area
            )

        # =================================================
        # DATA DE CRIAÇÃO – INÍCIO
        # =================================================
        if cri_de:
            queryset = queryset.filter(
                data_criacao__gte=cri_de
            )

        # =================================================
        # DATA DE CRIAÇÃO – FIM
        # =================================================
        if cri_ate:

            fim_do_dia = datetime.combine(
                cri_ate,
                time.max
            )

            queryset = queryset.filter(
                data_criacao__lte=fim_do_dia
            )

        # =================================================
        # SITUAÇÃO
        # =================================================
        if status == "finalizado":

            queryset = queryset.filter(
                status="finalizado"
            )

        elif status == "todos":
            pass

        else:
            queryset = queryset.filter(
                status="ativo"
            )

        return queryset

    # -------------------------------------------------
    # Row Builder
    # -------------------------------------------------
    def row_builder(self, obj):

        # =================================================
        # TIPO
        # =================================================
        if obj.tipo == "processo":

            tipo = "Processo"

        elif obj.tipo == "subprocesso":

            tipo = "Subprocesso"

        else:

            tipo = "Outro"

        # =================================================
        # NOME
        # =================================================
        nome = (
            f"-> {obj.nome}"
            if obj.tipo == "subprocesso"
            else obj.nome
        )

        # =================================================
        # ABRANGÊNCIA
        # =================================================
        abrangencia = (
            obj.get_abrangencia_display()
            if obj.abrangencia
            else "----"
        )

        # =================================================
        # CLASSIFICAÇÃO
        # =================================================
        try:
            classificacao = (
                obj.classificacao.nome
                if obj.classificacao
                else "----"
            )
        except Exception:
            classificacao = "----"

        # =================================================
        # MACROPROCESSO NÍVEL 1
        # =================================================
        try:
            macro_n1 = (
                obj.macroprocesso_nivel1.nome
                if obj.macroprocesso_nivel1
                else "----"
            )
        except Exception:
            macro_n1 = "----"

        # =================================================
        # MACROPROCESSO NÍVEL 2
        # =================================================
        try:
            macro_n2 = (
                obj.macroprocesso_nivel2.nome
                if obj.macroprocesso_nivel2
                else "----"
            )
        except Exception:
            macro_n2 = "----"

        # =================================================
        # ÁREA RESPONSÁVEL
        # =================================================
        try:
            area_responsavel = (
                obj.area_responsavel.nome_area
                if obj.area_responsavel
                else "----"
            )
        except Exception:
            area_responsavel = "----"

        # =================================================
        # DATA DE CRIAÇÃO
        # =================================================
        data_criacao = (
            obj.data_criacao.strftime("%d/%m/%Y")
            if obj.data_criacao
            else "----"
        )

        # =================================================
        # DATA DE FINALIZAÇÃO
        # =================================================
        data_finalizacao = (
            obj.data_finalizacao.strftime("%d/%m/%Y")
            if obj.data_finalizacao
            else "----"
        )

        # =================================================
        # SITUAÇÃO
        # =================================================
        if obj.status == "finalizado":
            situacao = "Finalizado"
        else:
            situacao = "Ativo"

        return [
            nome or "----",
            tipo,
            abrangencia,
            classificacao,
            macro_n1,
            macro_n2,
            area_responsavel,
            data_criacao,
            data_finalizacao,
            situacao,
        ]

# -----------------------------------------------------#
# Exportação Processos                                 #
# -----------------------------------------------------#
class ProcessosExportConfig:

    filename = 'processos'

    titulo_pdf = 'Processos'

    headers = [
        'Processo / Subprocesso',
        'Versão',
        'Estado',
        'Classificação',
        'Macro N1',
        'Macro N2',
        'Área',
        'Gestor',
        'Criação',
        'Conclusão',
    ]

    pdf_col_widths = [

        138,  # Processo/Subprocesso
        38,  # Versão
        50,  # Estado
        62,  # Classificação
        100,  # Macro N1
        100,  # Macro N2
        78,  # Área
        84,  # Gestor
        48,  # Criação
        48,  # Conclusão
    ]

    pdf_center_columns = [1, 2, 8, 9]

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
        estado = req.get("estado", "").strip().lower()

        cri_de_raw = req.get("criacao_de")
        cri_ate_raw = req.get("criacao_ate")

        con_de_raw = req.get("conclusao_de")
        con_ate_raw = req.get("conclusao_ate")

        cri_de = parse_date(cri_de_raw) if cri_de_raw else None
        cri_ate = parse_date(cri_ate_raw) if cri_ate_raw else None

        con_de = parse_date(con_de_raw) if con_de_raw else None
        con_ate = parse_date(con_ate_raw) if con_ate_raw else None

        # -------------------------------------------------
        # Validação
        # -------------------------------------------------

        if cri_de and cri_ate and cri_ate < cri_de:
            return Processo.objects.none()

        if con_de and con_ate and con_ate < con_de:
            return Processo.objects.none()

        # -------------------------------------------------
        # Query base
        # -------------------------------------------------

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
                "documentos",
                "subprocessos",
                "subprocessos__documentos",
                "subprocessos__classificacao",
                "subprocessos__macroprocesso_nivel1",
                "subprocessos__macroprocesso_nivel2",
                "subprocessos__area_responsavel",
            )
            .order_by("id")
        )

        # -------------------------------------------------
        # Filtros
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Estado
        # -------------------------------------------------

        if estado == "concluido":

            qs = qs.filter(
                data_conclusao__isnull=False
            )

        elif estado == "ativo":

            qs = qs.filter(
                data_conclusao__isnull=True,
                documentos__isnull=False
            ).distinct()

        elif estado == "iniciado":

            qs = qs.filter(
                data_conclusao__isnull=True,
                documentos__isnull=True
            )

        # -------------------------------------------------
        # Datas criação
        # -------------------------------------------------

        if cri_de:
            qs = qs.filter(
                data_criacao__gte=cri_de
            )

        if cri_ate:
            fim = datetime.combine(
                cri_ate,
                time.max
            )

            qs = qs.filter(
                data_criacao__lte=fim
            )

        # -------------------------------------------------
        # Datas conclusão
        # -------------------------------------------------

        if con_de:
            qs = qs.filter(
                data_conclusao__date__gte=con_de
            )

        if con_ate:
            qs = qs.filter(
                data_conclusao__date__lte=con_ate
            )

        return qs

    # -------------------------------------------------
    # Linha individual
    # -------------------------------------------------
    def build_row(self, obj, is_subprocesso=False):

        # -------------------------------------------------
        # Nome hierárquico
        # -------------------------------------------------

        nome = (
            f'-> {obj.nome}'
            if is_subprocesso
            else obj.nome
        )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        if obj.status == 'concluido':
            status = 'Concluído'

        elif obj.status == 'ativo':
            status = 'Ativo'

        else:
            status = 'Iniciado'

        # -------------------------------------------------
        # Blindagem FK órfã
        # -------------------------------------------------

        try:
            classificacao = (
                obj.classificacao.nome
                if obj.classificacao
                else '----'
            )

        except Exception:
            classificacao = '----'

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
            area_responsavel = (
                obj.area_responsavel.nome_area
                if obj.area_responsavel
                else '----'
            )

        except Exception:
            area_responsavel = '----'

        # -------------------------------------------------
        # Linha
        # -------------------------------------------------

        return [

            nome or '----',

            (
                obj.versao_processo
                if obj.versao_processo
                else '—'
            ),

            status,

            classificacao,

            macro_n1,

            macro_n2,

            area_responsavel,

            obj.gestor or '----',

            (
                obj.data_criacao.strftime('%d/%m/%Y')
                if obj.data_criacao
                else '----'
            ),

            (
                obj.data_conclusao.strftime('%d/%m/%Y')
                if obj.data_conclusao
                else '----'
            ),
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

# -----------------------------------------------------#
# Exportação Macroprocesso Nível 1                     #
# -----------------------------------------------------#
class MacroprocessoNivel1ExportConfig:

    filename = 'macroprocesso_nivel1'

    titulo_pdf = 'Macroprocesso Nível 1'

    headers = [
        'Classificação',
        'Nome',
        'Descrição',
    ]

    pdf_col_widths = [
        120,  # Classificação
        180,  # Nome
        420,  # Descrição
    ]

    # -------------------------------------------------
    # Queryset
    # -------------------------------------------------
    def get_queryset(self, request):

        req = request.GET

        queryset = (
            MacroprocessoNivel1.objects
            .select_related('classificacao')
        )

        # -------------------------------------------------
        # Filtros
        # -------------------------------------------------

        classificacao = req.get(
            "classificacao",
            ""
        ).strip()

        nome = req.get(
            "nome",
            ""
        ).strip()

        if classificacao:

            queryset = queryset.filter(
                classificacao__nome__icontains=classificacao
            )

        if nome:

            queryset = queryset.filter(
                nome__icontains=nome
            )

        # -------------------------------------------------
        # Ordenação
        # -------------------------------------------------

        queryset = queryset.order_by(
            'classificacao__nome',
            'nome'
        )

        return queryset

    # -------------------------------------------------
    # Row Builder
    # -------------------------------------------------
    def row_builder(self, obj):

        return [

            (
                obj.classificacao.nome
                if obj.classificacao
                else '----'
            ),

            obj.nome or '----',

            obj.descricao or '----',
        ]

# -----------------------------------------------------#
# Exportação Macroprocesso Nível 2                     #
# -----------------------------------------------------#
class MacroprocessoNivel2ExportConfig:

    filename = 'macroprocesso_nivel2'

    titulo_pdf = 'Macroprocesso Nível 2'

    headers = [
        'Classificação',
        'Macroprocesso Nível 1',
        'Nome',
        'Descrição',
    ]

    pdf_col_widths = [
        120,  # Classificação
        180,  # Macro N1
        180,  # Nome
        320,  # Descrição
    ]

    # -------------------------------------------------
    # Queryset
    # -------------------------------------------------
    def get_queryset(self, request):

        req = request.GET

        queryset = (
            MacroprocessoNivel2.objects
            .select_related(
                'macroprocesso_nivel1',
                'macroprocesso_nivel1__classificacao'
            )
        )

        # -------------------------------------------------
        # Filtros
        # -------------------------------------------------

        classificacao = req.get(
            "classificacao",
            ""
        ).strip()

        macro_n1 = req.get(
            "macro_n1",
            ""
        ).strip()

        nome = req.get(
            "nome",
            ""
        ).strip()

        if classificacao:

            queryset = queryset.filter(
                macroprocesso_nivel1__classificacao__nome__icontains=classificacao
            )

        if macro_n1:

            queryset = queryset.filter(
                macroprocesso_nivel1__nome__icontains=macro_n1
            )

        if nome:

            queryset = queryset.filter(
                nome__icontains=nome
            )

        # -------------------------------------------------
        # Ordenação
        # -------------------------------------------------

        queryset = queryset.order_by(
            "macroprocesso_nivel1__classificacao__nome",
            "macroprocesso_nivel1__nome",
            "nome"
        )

        return queryset

    # -------------------------------------------------
    # Row Builder
    # -------------------------------------------------
    def row_builder(self, obj):

        try:
            classificacao = (
                obj.macroprocesso_nivel1.classificacao.nome
                if (
                    obj.macroprocesso_nivel1
                    and obj.macroprocesso_nivel1.classificacao
                )
                else '----'
            )

        except Exception:
            classificacao = '----'

        try:
            macro_n1 = (
                obj.macroprocesso_nivel1.nome
                if obj.macroprocesso_nivel1
                else '----'
            )

        except Exception:
            macro_n1 = '----'

        return [

            classificacao,

            macro_n1,

            obj.nome or '----',

            obj.descricao or '----',
        ]

# ============================================================
# REGISTRO DA EXPORTAÇÃO
# ============================================================
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

register_export(
    key='processosmapear',
    config=ProcessosMapearExportConfig(),
)

register_export(
    key='processos',
    config=ProcessosExportConfig(),
)

register_export(
    key='macroprocessonivel1',
    config=MacroprocessoNivel1ExportConfig(),
)

register_export(
    key='macroprocessonivel2',
    config=MacroprocessoNivel2ExportConfig(),
)