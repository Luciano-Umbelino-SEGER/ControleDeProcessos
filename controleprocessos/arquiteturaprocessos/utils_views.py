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

        tabela = data.get("tabela")
        campo = data.get("campo")
        valor = data.get("valor")
        registro_id = int(data.get("id")) if data.get("id") else None

        if not tabela or not campo or not valor:
            return JsonResponse(
                {"erro": "Parâmetros inválidos"},
                status=400
            )

        similares = buscar_similares(
            tabela=tabela,
            campo=campo,
            valor=valor,
            ignorar_id=registro_id
        )

        return JsonResponse({
            "similar_encontrado": len(similares) > 0,
            "resultados": similares
        })

    except Exception as e:
        return JsonResponse(
            {"erro": str(e)},
            status=500
        )