from django.db import migrations


RELACOES = [
    (
        "Cadeia de Valor",
        "Definição",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Cadeia de Valor",
        "Imagens",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
        ],
    ),
    (
        "Processos",
        "Cadastro de Processos",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Processos",
        "Processos a Mapear",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estatísticas",
        "Consultas e Indicadores",
        [
            "Visualizar",
        ],
    ),
    (
        "Estrutura de Documentos → Processos",
        "Definição",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estrutura de Documentos → Processos",
        "Classificação de Macroprocessos",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estrutura de Documentos → Processos",
        "Macroprocesso N1",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estrutura de Documentos → Processos",
        "Macroprocesso N2",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estrutura de Documentos → Processos",
        "Áreas Responsáveis",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
            "Atualizar Contatos",
        ],
    ),
    (
        "Estrutura de Documentos → Normas de Procedimento",
        "Definição",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estrutura de Documentos → Normas de Procedimento",
        "Sistemas",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Estrutura de Documentos → Normas de Procedimento",
        "Normas",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Administração",
        "Usuários",
        [
            "Cadastrar",
            "Visualizar",
            "Editar",
            "Excluir",
        ],
    ),
    (
        "Administração",
        "Logs",
        [
            "Visualizar",
        ],
    ),
]


def criar_relacoes(apps, schema_editor):
    Modulo = apps.get_model("arquiteturaprocessos", "Modulo")
    Funcionalidade = apps.get_model("arquiteturaprocessos", "Funcionalidade")
    Acao = apps.get_model("arquiteturaprocessos", "Acao")
    FuncionalidadeAcao = apps.get_model(
        "arquiteturaprocessos",
        "FuncionalidadeAcao",
    )

    total_relacoes = 0

    for nome_modulo, nome_funcionalidade, nomes_acoes in RELACOES:
        modulo = Modulo.objects.get(nome=nome_modulo)

        funcionalidade = Funcionalidade.objects.get(
            modulo=modulo,
            nome=nome_funcionalidade,
        )

        for nome_acao in nomes_acoes:
            acao = Acao.objects.get(nome=nome_acao)

            FuncionalidadeAcao.objects.get_or_create(
                funcionalidade=funcionalidade,
                acao=acao,
            )

            total_relacoes += 1

    if total_relacoes != 54:
        raise RuntimeError(
            f"Quantidade inesperada de relações: {total_relacoes}. "
            "Era esperado um total de 54."
        )


def remover_relacoes(apps, schema_editor):
    FuncionalidadeAcao = apps.get_model(
        "arquiteturaprocessos",
        "FuncionalidadeAcao",
    )

    FuncionalidadeAcao.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0035_seed_acoes"),
    ]

    operations = [
        migrations.RunPython(
            criar_relacoes,
            remover_relacoes,
        ),
    ]