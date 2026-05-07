# ============================================================
# EXPORTAÇÃO GLOBAL DO SIGEMP
# ============================================================

import csv

from datetime import datetime

from django.http import HttpResponse


def gerar_nome_arquivo(nome_base, extensao):
    """
    Gera nome padronizado:
    <nome>_yyyymmddhhmmss.ext
    """

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    return f'{nome_base}_{timestamp}.{extensao}'


def csv_exporter(
    filename,
    headers,
    queryset,
    row_builder,
    delimiter=';'
):
    """
    Exportador CSV genérico do SIGEMP.
    """

    nome_arquivo = gerar_nome_arquivo(
        filename,
        'csv'
    )

    response = HttpResponse(
        content_type='text/csv; charset=utf-8'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{nome_arquivo}"'
    )

    # UTF-8 BOM para Excel
    response.write('\ufeff')

    writer = csv.writer(
        response,
        delimiter=delimiter
    )

    # Cabeçalhos
    writer.writerow(headers)

    # Dados
    for obj in queryset:
        writer.writerow(
            row_builder(obj)
        )

    return response