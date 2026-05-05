from django.db.models import Func
import unicodedata


class Unaccent(Func):
    function = "unaccent"


def remover_acentos(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )