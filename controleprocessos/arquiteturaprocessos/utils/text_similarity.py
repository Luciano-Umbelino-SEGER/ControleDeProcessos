from difflib import SequenceMatcher
from django.apps import apps

from .text_normalizer import normalizar_texto


def calcular_similaridade(texto1: str, texto2: str) -> float:
    """
    Calcula similaridade entre dois textos normalizados.
    Retorna valor entre 0 e 1.
    """
    if not texto1 or not texto2:
        return 0.0

    return SequenceMatcher(None, texto1, texto2).ratio()


def buscar_similares(
    tabela: str,
    campo: str,
    valor: str,
    ignorar_id: int | None = None,
    app_label: str = "arquiteturaprocessos",
    limite: float = 0.8,
    max_resultados: int = 5,
):
    """
    Busca registros similares em qualquer tabela do Django.

    Parâmetros:
    tabela : nome do Model
    campo  : campo textual a ser comparado
    valor  : texto digitado pelo usuário
    limite : percentual mínimo de similaridade
    """

    Model = apps.get_model(app_label, tabela)

    if not Model:
        return []

    texto_base = normalizar_texto(valor)

    resultados = []

    queryset = Model.objects.filter(**{f"{campo}__icontains": valor}).values("id", campo)

    for registro in queryset:

        if ignorar_id and registro["id"] == int(ignorar_id):
            continue

        valor_banco = registro.get(campo)

        if not valor_banco:
            continue

        texto_banco = normalizar_texto(valor_banco)

        score = calcular_similaridade(texto_base, texto_banco)

        if score >= limite:
            resultados.append({
                "id": registro["id"],
                "texto": valor_banco,
                "score": round(score, 3),
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)

    return resultados[:max_resultados]