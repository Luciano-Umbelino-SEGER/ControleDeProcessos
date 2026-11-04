# controleprocessos/arquiteturaprocessos/api_views.py

from django.http import JsonResponse
from .models import MacroprocessoNivel1, Processo

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

def processos_pai(request):
    """
    Retorna processos que são pais (parent is null).
    """
    items = Processo.objects.filter(parent__isnull=True).order_by('nome').values('id', 'nome')
    return JsonResponse({"processos_pai": list(items)})
