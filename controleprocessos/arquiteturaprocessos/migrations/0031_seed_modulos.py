from django.db import migrations


def criar_modulos(apps, schema_editor):
    Modulo = apps.get_model("arquiteturaprocessos", "Modulo")

    modulos = [
        {
            "nome": "Cadeia de Valor",
            "descricao": "Apresentação e gerenciamento da Cadeia de Valor",
            "ordem": 1,
        },
        {
            "nome": "Processos",
            "descricao": "Cadastro e gerenciamento dos processos",
            "ordem": 2,
        },
        {
            "nome": "Estatísticas",
            "descricao": "Consultas, indicadores e comparativos do sistema",
            "ordem": 3,
        },
        {
            "nome": "Estrutura de Documentos → Processos",
            "descricao": "Estrutura documental relacionada aos processos",
            "ordem": 4,
        },
        {
            "nome": "Estrutura de Documentos → Normas de Procedimento",
            "descricao": "Estrutura e gerenciamento das normas de procedimento",
            "ordem": 5,
        },
        {
            "nome": "Administração",
            "descricao": "Administração de usuários e registros do sistema",
            "ordem": 6,
        },
    ]

    for dados in modulos:
        Modulo.objects.update_or_create(
            nome=dados["nome"],
            defaults={
                "descricao": dados["descricao"],
                "ordem": dados["ordem"],
                "ativo": True,
            },
        )


def remover_modulos(apps, schema_editor):
    Modulo = apps.get_model("arquiteturaprocessos", "Modulo")

    nomes = [
        "Cadeia de Valor",
        "Processos",
        "Estatísticas",
        "Estrutura de Documentos → Processos",
        "Estrutura de Documentos → Normas de Procedimento",
        "Administração",
    ]

    Modulo.objects.filter(nome__in=nomes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0030_modulo"),
    ]

    operations = [
        migrations.RunPython(
            criar_modulos,
            remover_modulos,
        ),
    ]