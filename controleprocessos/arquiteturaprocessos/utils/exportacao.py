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
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth


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
    rows,
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
    for row in rows:
        writer.writerow(row)

    return response

# ---------------------------------------------------
# Exportação para Arquivos .TXT
# ---------------------------------------------------
def txt_exporter(
        filename,
        headers,
        rows,
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
    for row in rows:
        linha = [
            str(valor)
            for index, valor in enumerate(row)
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
    rows
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
    for row in rows:
        worksheet.append(row)

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
# Rodapé global PDF
# ---------------------------------------------------
def adicionar_rodape(canvas, doc):

    canvas.saveState()

    largura, altura = landscape(A4)

    texto_esquerda = (
        'SIGEMP – Sistema de Gestão de Monitoramento de Processos '
    )

    texto_centro = (
        f'Página {canvas.getPageNumber()}'
    )

    texto_direita = (
        f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
    )

    # Fonte
    canvas.setFont(
        'Helvetica-Oblique',
        7
    )

    # Esquerda
    canvas.drawString(
        10,
        10,
        texto_esquerda
    )

    # Centro
    largura_texto = stringWidth(
        texto_centro,
        'Helvetica-Oblique',
        7
    )

    canvas.drawString(
        (largura / 2) - (largura_texto / 2),
        10,
        texto_centro
    )

    # Direita
    largura_direita = stringWidth(
        texto_direita,
        'Helvetica-Oblique',
        7
    )

    canvas.drawString(
        largura - largura_direita - 10,
        10,
        texto_direita
    )

    canvas.restoreState()

# ---------------------------------------------------
# Exportação para arquivo .PDF
# ---------------------------------------------------
def pdf_exporter(
    filename,
    headers,
    queryset=None,
    row_builder=None,
    titulo='Relatório',
    col_widths=None,
    center_columns=None,
    rows=None,
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

    estilo_celula_centralizado = ParagraphStyle(
        name='CelulaCentralizada',
        parent=estilo_celula,
        alignment=TA_CENTER,
    )

    elementos.append(
        Paragraph(titulo, estilo_titulo)
    )

    # ---------------------------------------------------
    # Colunas centralizadas
    # Retrocompatibilidade:
    # se nenhuma config for enviada,
    # mantém padrão antigo (8,9,10)
    # ---------------------------------------------------

    if center_columns is None:
        center_columns = [8, 9, 10]

    # Dados da tabela
    dados = [[

        Paragraph(
            str(header).replace(
                'Documentos Associados',
                'Documentos<br/>Associados'
            ),

            ParagraphStyle(
                'header_centralizado',
                parent=estilo_celula,
                alignment=TA_CENTER,
            )

            if index in center_columns else estilo_celula

        )

        for index, header in enumerate(headers)

    ]]

    # ---------------------------------------------------
    # Dados da tabela
    # Suporta:
    # - modo tradicional (queryset + row_builder)
    # - modo avançado (rows prontas)
    # ---------------------------------------------------

    if rows:

        for row in rows:
            linha = [
                Paragraph(
                    str(valor).replace('|', '<br/>'),
                    (
                        estilo_celula_centralizado
                        if index in center_columns
                        else estilo_celula
                    )
                )
                for index, valor in enumerate(row)
            ]

            dados.append(linha)

    else:

        for obj in queryset:
            linha = [
                Paragraph(
                    str(valor).replace('|', '<br/>'),
                    (
                        estilo_celula_centralizado
                        if index in center_columns
                        else estilo_celula
                    )
                )
                for index, valor in enumerate(row_builder(obj))
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

        # Centralização configurável
        *[
            ('ALIGN', (col, 0), (col, -1), 'CENTER')
            for col in center_columns
        ],

        # Quebra linha
        ('WORDWRAP', (0, 0), (-1, -1), True),

    ]))

    elementos.append(tabela)

    doc.build(
        elementos,
        onFirstPage=adicionar_rodape,
        onLaterPages=adicionar_rodape,
    )

    return response