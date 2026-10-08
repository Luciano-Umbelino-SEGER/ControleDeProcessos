from collections import OrderedDict

from arquiteturaprocessos.utils.utils import obter_funcionalidades_permitidas


def permissoes_menu(request):
    funcionalidades = obter_funcionalidades_permitidas(request.user)

    modulos_permitidos = OrderedDict()

    for funcionalidade in funcionalidades:
        modulo = funcionalidade.modulo

        if modulo not in modulos_permitidos:
            modulos_permitidos[modulo] = []

        modulos_permitidos[modulo].append(funcionalidade)

    modulos_permitidos_nomes = {
        modulo.nome
        for modulo in modulos_permitidos
    }

    return {
        "funcionalidades_permitidas": funcionalidades,
        "modulos_permitidos": modulos_permitidos,
        "modulos_permitidos_nomes": modulos_permitidos_nomes,
    }