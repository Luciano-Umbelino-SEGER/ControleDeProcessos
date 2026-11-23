"""
Migration de dados: protege informações sensíveis nos logs já gravados.

- Remove a chave "password" (hash da senha) de dados_antes e dados_depois.
- Mascara CPFs completos no formato ***.182.917-**.

Os demais dados dos registros são preservados integralmente.
Registros com estruturas diferentes (nulos, listas, textos) são ignorados.
A operação não tem reversão: o hash removido não deve ser restaurado.
"""
import re

from django.db import migrations
from django.db.models import Q


def _mascarar_cpf(valor):
    """Cópia local da regra de máscara (migrations não dependem do código atual)."""
    if valor is None or valor == "":
        return valor

    texto = str(valor)
    if "*" in texto:
        return texto

    numeros = re.sub(r"\D", "", texto)
    if len(numeros) != 11:
        return "***"

    return f"***.{numeros[3:6]}.{numeros[6:9]}-**"


def _limpar(dados):
    """Retorna (dados_protegidos, houve_alteracao). Só trata dicionários."""
    if not isinstance(dados, dict):
        return dados, False

    novos = dict(dados)
    alterou = False

    if "password" in novos:
        novos.pop("password")
        alterou = True

    if "cpf" in novos:
        mascarado = _mascarar_cpf(novos["cpf"])
        if mascarado != novos["cpf"]:
            novos["cpf"] = mascarado
            alterou = True

    return novos, alterou


def proteger_logs_existentes(apps, schema_editor):
    LogAcaoSistema = apps.get_model("auditoria", "LogAcaoSistema")

    candidatos = LogAcaoSistema.objects.filter(
        Q(dados_antes__has_key="password")
        | Q(dados_depois__has_key="password")
        | Q(dados_antes__has_key="cpf")
        | Q(dados_depois__has_key="cpf")
    ).only("pk", "dados_antes", "dados_depois")

    for log in candidatos.iterator(chunk_size=500):
        antes, alterou_antes = _limpar(log.dados_antes)
        depois, alterou_depois = _limpar(log.dados_depois)

        if alterou_antes or alterou_depois:
            # update() grava só os dois campos e não dispara signals
            LogAcaoSistema.objects.filter(pk=log.pk).update(
                dados_antes=antes,
                dados_depois=depois,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_alter_logacaosistema_acao"),
    ]

    operations = [
        migrations.RunPython(proteger_logs_existentes, migrations.RunPython.noop),
    ]
