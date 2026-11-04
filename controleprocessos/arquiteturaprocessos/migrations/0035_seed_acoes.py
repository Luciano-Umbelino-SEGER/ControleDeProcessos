from django.db import migrations


ACOES = [
    {
        "nome": "Cadastrar",
        "descricao": "Permite incluir novos registros na funcionalidade.",
        "ordem": 1,
    },
    {
        "nome": "Visualizar",
        "descricao": "Permite consultar e visualizar registros da funcionalidade.",
        "ordem": 2,
    },
    {
        "nome": "Editar",
        "descricao": (
            "Permite alterar registros e executar operações vinculadas "
            "à edição, conforme as regras da funcionalidade."
        ),
        "ordem": 3,
    },
    {
        "nome": "Excluir",
        "descricao": (
            "Permite remover ou inativar registros conforme a regra "
            "de negócio da funcionalidade."
        ),
        "ordem": 4,
    },
    {
        "nome": "Atualizar Contatos",
        "descricao": "Permite atualizar os contatos associados à funcionalidade.",
        "ordem": 5,
    },
]


def criar_acoes(apps, schema_editor):
    Acao = apps.get_model("arquiteturaprocessos", "Acao")

    for acao in ACOES:
        Acao.objects.update_or_create(
            nome=acao["nome"],
            defaults={
                "descricao": acao["descricao"],
                "ordem": acao["ordem"],
            },
        )


def remover_acoes(apps, schema_editor):
    Acao = apps.get_model("arquiteturaprocessos", "Acao")

    nomes = [acao["nome"] for acao in ACOES]

    Acao.objects.filter(nome__in=nomes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0034_acao_funcionalidadeacao"),
    ]

    operations = [
        migrations.RunPython(
            criar_acoes,
            remover_acoes,
        ),
    ]