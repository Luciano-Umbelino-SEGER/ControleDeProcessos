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

        # Detecta substring forte
    if texto1 in texto2 or texto2 in texto1:
        return 1.0

    score_frase = SequenceMatcher(None, texto1, texto2).ratio()

    tokens1 = set(texto1.split())
    tokens2 = set(texto2.split())

    if not tokens1 or not tokens2:
        score_tokens = 0.0
    else:
        score_tokens = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))

    return max(score_frase, score_tokens)


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

    primeira_palavra = valor.split()[0]

    queryset = (
        Model.objects
        .filter(**{f"{campo}__icontains": primeira_palavra})
        .values("id", campo)
    )

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