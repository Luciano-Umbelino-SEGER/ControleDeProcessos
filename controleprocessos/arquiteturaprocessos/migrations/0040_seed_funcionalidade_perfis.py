from django.db import migrations


RELACOES = [
    (
        "Administração",
        "Perfis",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
]


def criar_funcionalidade_perfis(apps, schema_editor):
    Modulo = apps.get_model(
        "arquiteturaprocessos",
        "Modulo",
    )
    Funcionalidade = apps.get_model(
        "arquiteturaprocessos",
        "Funcionalidade",
    )
    Acao = apps.get_model(
        "arquiteturaprocessos",
        "Acao",
    )
    FuncionalidadeAcao = apps.get_model(
        "arquiteturaprocessos",
        "FuncionalidadeAcao",
    )

    total_relacoes = 0

    for nome_modulo, nome_funcionalidade, nomes_acoes in RELACOES:
        modulo = Modulo.objects.get(
            nome=nome_modulo
        )

        funcionalidade, _ = Funcionalidade.objects.update_or_create(
            modulo=modulo,
            nome=nome_funcionalidade,
            defaults={
                "descricao": (
                    "Gerenciamento dos perfis de acesso "
                    "e suas permissões no SIGEMP."
                ),
                "ordem": 3,
                "ativo": True,
            },
        )

        for nome_acao in nomes_acoes:
            acao = Acao.objects.get(
                nome=nome_acao
            )

            FuncionalidadeAcao.objects.get_or_create(
                funcionalidade=funcionalidade,
                acao=acao,
            )

            total_relacoes += 1

    if total_relacoes != 4:
        raise RuntimeError(
            f"Quantidade inesperada de relações: {total_relacoes}. "
            "Era esperado um total de 4."
        )


def remover_funcionalidade_perfis(apps, schema_editor):
    Modulo = apps.get_model(
        "arquiteturaprocessos",
        "Modulo",
    )
    Funcionalidade = apps.get_model(
        "arquiteturaprocessos",
        "Funcionalidade",
    )

    modulo = Modulo.objects.filter(
        nome="Administração"
    ).first()

    if modulo:
        Funcionalidade.objects.filter(
            modulo=modulo,
            nome="Perfis",
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "arquiteturaprocessos",
            "0039_configura_perfil_administrador",
        ),
    ]

    operations = [
        migrations.RunPython(
            criar_funcionalidade_perfis,
            remover_funcionalidade_perfis,
        ),
    ]