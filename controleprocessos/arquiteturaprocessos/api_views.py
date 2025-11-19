# controleprocessos/arquiteturaprocessos/api_views.py

from django.http import JsonResponse
from .models import (MacroprocessoNivel1, MacroprocessoNivel2,)

# ======================
#  Endpoints - APIs
# ======================

def classificacao_por_macro1(request, macro1_id):
    try:
        macro1 = MacroprocessoNivel1.objects.get(id=macro1_id)
        return JsonResponse({
            'classificacao_id': macro1.classificacao.id,
            'classificacao_nome': macro1.classificacao.nome
        })
    except MacroprocessoNivel1.DoesNotExist:
        return JsonResponse({
            'classificacao_id': None,
            'classificacao_nome': ''
        })



def macroprocessos_por_classificacao(request, classificacao_id):
    """
    Retorna Macroprocessos de Nivel 1 associados a uma Classificação.
    """
    macroprocessos = MacroprocessoNivel1.objects.filter(classificacao_id=classificacao_id)
    data = [{'id': m.id, 'nome': m.nome} for m in macroprocessos]
    return JsonResponse({'macroprocessos': data})


def macro2_por_macro1(request, macro1_id):
    """
    Retorna Macroprocessos de Nivel 2 associados a um Macroprocesso Nivel 1.
    """
    macro2_list = MacroprocessoNivel2.objects.filter(
        macroprocesso_nivel1_id=macro1_id
    ).values("id", "nome")
    return JsonResponse({"macro2": list(macro2_list)})


def macro1_e_classificacao_por_macro2(request, macro2_id):
    """
    Retorna o Macroprocesso Nivel 1 e Classificação associados a um Macroprocesso Nivel 2.
    """
    try:
        macro2 = MacroprocessoNivel2.objects.select_related(
            "macroprocesso_nivel1__classificacao"
        ).get(id=macro2_id)

        macro1 = macro2.macroprocesso_nivel1
        classificacao = macro1.classificacao

        return JsonResponse({
            "macroprocesso_nivel1": {"id": macro1.id, "nome": macro1.nome},
            "classificacao": {"id": classificacao.id, "nome": classificacao.nome}
        })

    except MacroprocessoNivel2.DoesNotExist:
        return JsonResponse({"error": "Macroprocesso Nível 2 não encontrado."}, status=404)


def macro1_todos(request):
    """
    Retorna todos os Macroprocessos Nivel 1.
    """
    items = MacroprocessoNivel1.objects.values("id", "nome")
    return JsonResponse({"macro1": list(items)})


def macro2_todos(request):
    """
    Retorna todos os Macroprocessos Nivel 2.
    """
    items = MacroprocessoNivel2.objects.values("id", "nome")
    return JsonResponse({"macro2": list(items)})
