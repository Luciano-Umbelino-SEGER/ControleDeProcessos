# ============================================================
# EXPORTAÇÃO GLOBAL DO SIGEMP
# ============================================================

import csv
from datetime import datetime
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle


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

# ---------------------------------------------------
# Exportação para arquivo .XLSX
# ---------------------------------------------------
def xlsx_exporter(
    filename,
    headers,
    queryset,
    row_builder
):
    """
    Exportador XLSX genérico do SIGEMP.
    """

    nome_arquivo = gerar_nome_arquivo(
        filename,
        'xlsx'
    )

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{nome_arquivo}"'
    )

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = 'Dados'

    # Cabeçalhos
    worksheet.append(headers)

    # Negrito no cabeçalho
    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    # Dados
    for obj in queryset:

        worksheet.append(
            row_builder(obj)
        )

    # Ajustar largura automática
    for column_cells in worksheet.columns:

        max_length = 0

        column_letter = column_cells[0].column_letter

        for cell in column_cells:

            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))

            except Exception:
                pass

        adjusted_width = min(max_length + 2, 60)

        worksheet.column_dimensions[
            column_letter
        ].width = adjusted_width

    workbook.save(response)

    return response

# ---------------------------------------------------
# Exportação para arquivo .PDF
# ---------------------------------------------------
def pdf_exporter(
    filename,
    headers,
    queryset,
    row_builder,
    titulo='Relatório',
    col_widths=None,
):
    """
    Exportador PDF genérico do SIGEMP.
    """

    nome_arquivo = gerar_nome_arquivo(
        filename,
        'pdf'
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{nome_arquivo}"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=5,
        rightMargin=5,
        topMargin=20,
        bottomMargin=20,
    )

    elementos = []

    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        name='Titulo',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=20,
    )

    estilo_celula = ParagraphStyle(
        name='Celula',
        parent=styles['BodyText'],
        fontSize=6,
        leading=7,
    )

    estilo_header = ParagraphStyle(
        name='Header',
        parent=styles['BodyText'],
        fontSize=6,
        leading=7,
        alignment=TA_CENTER,
    )

    elementos.append(
        Paragraph(titulo, estilo_titulo)
    )

    # Dados da tabela
    dados = [[

        Paragraph(
            str(header),

            ParagraphStyle(
                'header_centralizado',
                parent=estilo_celula,
                alignment=TA_CENTER,
            )

            if index >= 8 else estilo_celula

        )

        for index, header in enumerate(headers)

    ]]

    for obj in queryset:
        linha = [
            Paragraph(
                str(valor).replace('|', '<br/>'),
                estilo_celula
            )
            for valor in row_builder(obj)
        ]

        dados.append(linha)

    tabela = Table(
        dados,
        repeatRows=1,
        colWidths=col_widths,
    )

    tabela.setStyle(TableStyle([

        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6),

        # Corpo
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),

        # Zebrado linhas
        ('ROWBACKGROUNDS',
         (0, 1),
         (-1, -1),
         [
             colors.white,
             colors.HexColor('#eff6ff')
         ]),

        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

        # Espaçamento
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),

        # Alinhamento
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Centralizar datas
        ('ALIGN', (8, 1), (10, -1), 'CENTER'),

        # Quebra linha
        ('WORDWRAP', (0, 0), (-1, -1), True),

    ]))

    elementos.append(tabela)

    doc.build(elementos)

    return response