import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .utils.text_similarity import buscar_similares


@require_POST
@csrf_exempt
def verificar_similaridade(request):
    """
    Endpoint genérico para verificar similaridade textual.
    Recebe:
        tabela
        campo
        valor
    """

    try:
        data = json.loads(request.body)

        tabelas = data.get("tabelas") or [data.get("tabela")]
        campo = data.get("campo")
        valor = data.get("valor")

        id_valor = data.get("id")
        if id_valor in (None, "", "None"):
            registro_id = None
        else:
            try:
                registro_id = int(id_valor)
            except (ValueError, TypeError):
                registro_id = None

        if not tabelas or not campo or not valor:
            return JsonResponse(
                {"erro": "Parâmetros inválidos"},
                status=400
            )
        resultados = {}

        for tabela in tabelas:
            resultados[tabela] = buscar_similares(
                tabela=tabela,
                campo=campo,
                valor=valor,
                ignorar_id=registro_id
            )

        return JsonResponse({
            "similar_encontrado": any(resultados.values()),
            "resultados": resultados
        })

    except Exception as e:
        return JsonResponse(
            {"erro": str(e)},
            status=500
        )