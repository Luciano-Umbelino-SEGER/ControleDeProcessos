# ============================================================
# VIEWS GENÉRICAS DE EXPORTAÇÃO DO SIGEMP
# ============================================================

from django.http import Http404

from .registry import (get_export_config,)

from arquiteturaprocessos.utils.exportacao import (csv_exporter, txt_exporter, xlsx_exporter, pdf_exporter,)

EXPORTERS = {
    'csv': csv_exporter,
    'txt': txt_exporter,
    'xlsx': xlsx_exporter,
    'pdf': pdf_exporter,
}

def exportar_generico(
    request,
    resource,
    formato
):
    """
    Exportação genérica do SIGEMP.
    """

    # Busca configuração registrada
    config = get_export_config(resource)

    if not config:
        raise Http404(
            'Exportação não registrada.'
        )

    # Busca exporter
    exporter = EXPORTERS.get(formato)

    if not exporter:
        raise Http404(
            'Formato de exportação inválido.'
        )

    # Queryset
    queryset = config.get_queryset(request)

    # =====================================================
    # BUILD DAS LINHAS
    # Compatível com:
    # - row_builder()
    # - build_rows()
    # =====================================================

    if hasattr(config, 'build_rows'):

        rows = []

        for obj in queryset:
            rows.extend(
                config.build_rows(obj)
            )

    else:

        rows = [
            config.row_builder(obj)
            for obj in queryset
        ]

    # Parâmetros base
    export_kwargs = {
        'filename': config.filename,
        'headers': config.headers,
        'rows': rows,
    }

    # PDF possui parâmetros extras
    if formato == 'pdf':
        export_kwargs['titulo'] = (
            getattr(
                config,
                'titulo_pdf',
                config.filename
            )
        )

        export_kwargs['col_widths'] = (
            getattr(
                config,
                'pdf_col_widths',
                None
            )
        )

        export_kwargs['center_columns'] = (
            getattr(
                config,
                'pdf_center_columns',
                []
            )
        )

    return exporter(**export_kwargs)