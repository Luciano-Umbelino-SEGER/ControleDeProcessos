def contar_documentos_associados(processo):
    """
    Retorna a quantidade de documentos associados diretamente
    a um Processo ou Subprocesso.

    Regras:
    - PDF do Modelo de Processo: +1
    - URL do Modelo de Processo: +1
    - Cada Norma de Procedimento associada: +1
    - Documentos internos da Norma de Procedimento não são
      contabilizados.
    """

    total = 0

    # -------------------------------------------------
    # Modelo de Processo
    # -------------------------------------------------

    if processo.documento_modelo_processo:
        total += 1

    if processo.link_documento_modelo_processo:
        total += 1

    # -------------------------------------------------
    # Normas de Procedimento
    # Cada norma associada vale 1 documento
    # -------------------------------------------------

    total += processo.documentos.count()

    return total