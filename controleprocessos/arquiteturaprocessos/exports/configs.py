# ============================================================
# CONFIGURAÇÕES DE EXPORTAÇÃO DO SIGEMP
# ============================================================

from urllib.parse import unquote

from arquiteturaprocessos.models import (ModelagemProcesso,)
from arquiteturaprocessos.exports.registry import (register_export,)

class ModelagemProcessosExportConfig:

    filename = 'modelagem_processos'

    titulo_pdf = 'Modelagem de Processos'

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

# ============================================================
# REGISTRO DA EXPORTAÇÃO
# ============================================================
register_export(
    key='modelagemprocessos',
    config=ModelagemProcessosExportConfig(),
)