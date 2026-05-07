# ============================================================
# EXPORTAÇÃO GLOBAL DO SIGEMP
# ============================================================

import csv
from datetime import datetime
from django.http import HttpResponse


# ---------------------------------------------------
# Normalização do Nome dos Arquivos
# ---------------------------------------------------
def gerar_nome_arquivo(nome_base, extensao):
    """
    Gera nome padronizado:
    <nome>_yyyymmddhhmmss.ext
    """

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    return f'{nome_base}_{timestamp}.{extensao}'

# ---------------------------------------------------
# Exportação para arquivo .CSV
# ---------------------------------------------------
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

# ---------------------------------------------------
# Exportação para Arquivos .TXT
# ---------------------------------------------------
def txt_exporter(
    filename,
    headers,
    queryset,
    row_builder,
    delimiter=' | '
):
    """
    Exportador TXT genérico do SIGEMP.
    """

    nome_arquivo = gerar_nome_arquivo(
        filename,
        'txt'
    )

    response = HttpResponse(
        content_type='text/plain; charset=utf-8'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{nome_arquivo}"'
    )

    # UTF-8 BOM
    response.write('\ufeff')

    # Cabeçalhos
    response.write(
        delimiter.join(headers) + '\n'
    )

    # Dados
    for obj in queryset:

        linha = [
            str(valor)
            for valor in row_builder(obj)
        ]

        response.write(
            delimiter.join(linha) + '\n'
        )

    return response