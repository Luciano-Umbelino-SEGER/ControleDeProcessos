from django.db import migrations


def ajustar_ordem_funcionalidades_administracao(apps, schema_editor):
    Funcionalidade = apps.get_model(
        "arquiteturaprocessos",
        "Funcionalidade",
    )

    ordens = {
        "Perfis": 1,
        "Usuários": 2,
        "Logs": 3,
    }

    modulo = (
        apps.get_model("arquiteturaprocessos", "Modulo")
        .objects
        .get(nome="Administração")
    )

    for nome, ordem in ordens.items():
        Funcionalidade.objects.filter(
            modulo=modulo,
            nome=nome,
        ).update(
            ordem=ordem,
        )


def reverter_ordem_funcionalidades_administracao(apps, schema_editor):
    Funcionalidade = apps.get_model(
        "arquiteturaprocessos",
        "Funcionalidade",
    )

    ordens = {
        "Usuários": 1,
        "Logs": 2,
        "Perfis": 3,
    }

    modulo = (
        apps.get_model("arquiteturaprocessos", "Modulo")
        .objects
        .get(nome="Administração")
    )

    for nome, ordem in ordens.items():
        Funcionalidade.objects.filter(
            modulo=modulo,
            nome=nome,
        ).update(
            ordem=ordem,
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "arquiteturaprocessos",
            "0041_configura_permissoes_administrador",
        ),
    ]

    operations = [
        migrations.RunPython(
            ajustar_ordem_funcionalidades_administracao,
            reverter_ordem_funcionalidades_administracao,
        ),
    ]