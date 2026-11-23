"""
Utilitários para tratamento de CPF.

Funções reaproveitáveis no cadastro de usuários e na futura
integração com o Acesso Cidadão.
"""
import re


def somente_digitos(valor):
    """Retorna apenas os dígitos do valor informado ("" quando vazio)."""
    if not valor:
        return ""
    return re.sub(r"\D", "", str(valor))


def cpf_valido(cpf):
    """
    Verifica se o CPF é válido (aceita com ou sem máscara).

    Confere se possui 11 dígitos, recusa sequências repetidas
    (ex.: 111.111.111-11) e calcula os dois dígitos verificadores.
    """
    numeros = somente_digitos(cpf)

    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False

    for posicao in (9, 10):
        soma = sum(
            int(numeros[i]) * (posicao + 1 - i)
            for i in range(posicao)
        )
        digito = (soma * 10) % 11 % 10
        if digito != int(numeros[posicao]):
            return False

    return True


def formatar_cpf(cpf):
    """
    Formata o CPF como 000.000.000-00.

    Valores que não possuem 11 dígitos são devolvidos sem alteração.
    """
    numeros = somente_digitos(cpf)

    if len(numeros) != 11:
        return cpf or ""

    return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
