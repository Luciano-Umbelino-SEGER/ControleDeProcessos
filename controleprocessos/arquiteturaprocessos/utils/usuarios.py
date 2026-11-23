"""
Utilitários para o cadastro de usuários.
"""
import re
import unicodedata

from django.contrib.auth import get_user_model

# Termos de parentesco desconsiderados quando aparecem no fim do sobrenome.
# Ex.: "Pedro" + "Silva Filho" -> "pedro.silva"
SUFIXOS_PARENTESCO = {
    "filho", "filha", "neto", "neta",
    "junior", "jr", "sobrinho", "sobrinha",
}


def _normalizar_termo(texto):
    """Remove acentos, espaços e caracteres especiais, em minúsculas."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def gerar_base_username(first_name, last_name):
    """
    Monta o nome de usuário no formato nome.sobrenome.

    Usa o primeiro termo do nome e o último termo do sobrenome,
    sem acentos e em minúsculas. Termos de parentesco no fim do
    sobrenome (Filho, Júnior, Neto...) são desconsiderados.
    Ex.: "Cláudio Paiva" + "Silva Campos" -> "claudio.campos"
         "Pedro" + "Silva Filho"           -> "pedro.silva"

    Retorna "" quando não for possível montar o nome de usuário.
    """
    nomes = (first_name or "").split()
    sobrenomes = (last_name or "").split()

    if not nomes or not sobrenomes:
        return ""

    termos_sobrenome = [_normalizar_termo(s) for s in sobrenomes]
    termos_sobrenome = [s for s in termos_sobrenome if s]
    while len(termos_sobrenome) > 1 and termos_sobrenome[-1] in SUFIXOS_PARENTESCO:
        termos_sobrenome.pop()

    nome = _normalizar_termo(nomes[0])
    sobrenome = termos_sobrenome[-1] if termos_sobrenome else ""

    if not nome or not sobrenome:
        return ""

    return f"{nome}.{sobrenome}"


def gerar_username_unico(first_name, last_name):
    """
    Gera um nome de usuário sem duplicidade.

    Se nome.sobrenome já existir (inclusive em usuários inativos e sem
    diferenciar maiúsculas/minúsculas), acrescenta um número sequencial:
    claudio.campos, claudio.campos2, claudio.campos3...
    """
    base = gerar_base_username(first_name, last_name)
    if not base:
        return ""

    Usuario = get_user_model()
    candidato = base
    sequencial = 2

    while Usuario.objects.filter(username__iexact=candidato).exists():
        candidato = f"{base}{sequencial}"
        sequencial += 1

    return candidato
