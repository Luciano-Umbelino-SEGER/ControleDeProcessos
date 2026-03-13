from django.http import JsonResponse
from .utils.text_similarity import buscar_similaridade


def verificar_similaridade(request):

    tabela = request.GET.get("tabela")
    campo = request.GET.get("campo")
    valor = request.GET.get("valor")

    resultado = buscar_similaridade(tabela, campo, valor)

    return JsonResponse(resultado)