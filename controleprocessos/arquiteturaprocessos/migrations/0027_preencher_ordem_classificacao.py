from django.db import migrations
from django.db.models import Max


def preencher_ordem_classificacao(apps, schema_editor):
    Classificacao = apps.get_model(
        "arquiteturaprocessos",
        "Classificacao"
    )

    # Ordem oficial das classificações existentes
    ordens = {
        "Estratégico": 1,
        "Finalístico": 2,
        "Suporte": 3,
        "Teste": 4,
        "Novo Teste": 5,
    }

    # Primeiro, aplica as ordens oficiais somente
    # aos registros que ainda não possuem ordem.
    for nome, ordem in ordens.items():
        Classificacao.objects.filter(
            nome=nome,
            ordem__isnull=True
        ).update(ordem=ordem)

    # Caso existam outras classificações sem ordem,
    # atribuímos números sequenciais após a maior ordem existente.
    maior_ordem = (
        Classificacao.objects.aggregate(
            maior=Max("ordem")
        )["maior"]
        or 0
    )

    classificacoes_sem_ordem = (
        Classificacao.objects
        .filter(ordem__isnull=True)
        .order_by("id")
    )

    for classificacao in classificacoes_sem_ordem:
        maior_ordem += 1
        classificacao.ordem = maior_ordem
        classificacao.save(update_fields=["ordem"])


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0026_classificacao_ordem"),
    ]

    operations = [
        migrations.RunPython(
            preencher_ordem_classificacao,
            migrations.RunPython.noop,
        ),
    ]