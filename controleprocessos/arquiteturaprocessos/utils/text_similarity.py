from difflib import SequenceMatcher
from django.apps import apps


def calcular_similaridade(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def buscar_similaridade(model_name, field_name, valor, limite=0.9):

    Model = apps.get_model(model_name)

    registros = Model.objects.values_list(field_name, flat=True)

    melhor_match = None
    maior_percentual = 0

    for registro in registros:
        similaridade = calcular_similaridade(valor, registro)

        if similaridade > maior_percentual:
            maior_percentual = similaridade
            melhor_match = registro

    if maior_percentual >= limite:
        return {
            "encontrado": True,
            "percentual": round(maior_percentual * 100, 2),
            "valor": melhor_match
        }

    return {"encontrado": False}