from django.conf import settings


def configuracoes(request):

    return {
        "HABILITAR_MODELAGEM_PROCESSOS":
            settings.HABILITAR_MODELAGEM_PROCESSOS,
    }