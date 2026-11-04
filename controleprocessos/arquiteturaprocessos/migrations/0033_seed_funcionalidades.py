from django.db import migrations


def criar_funcionalidades(apps, schema_editor):
    Modulo = apps.get_model("arquiteturaprocessos", "Modulo")
    Funcionalidade = apps.get_model("arquiteturaprocessos", "Funcionalidade")

    funcionalidades = [
        # ========================================================
        # CADEIA DE VALOR
        # ========================================================
        {
            "modulo": "Cadeia de Valor",
            "nome": "Definição",
            "descricao": "Gerenciamento das definições utilizadas na Cadeia de Valor.",
            "ordem": 1,
        },
        {
            "modulo": "Cadeia de Valor",
            "nome": "Imagens",
            "descricao": "Gerenciamento das imagens utilizadas na apresentação da Cadeia de Valor.",
            "ordem": 2,
        },

        # ========================================================
        # PROCESSOS
        # ========================================================
        {
            "modulo": "Processos",
            "nome": "Cadastro de Processos",
            "descricao": "Gerenciamento dos processos cadastrados no SIGEMP.",
            "ordem": 1,
        },
        {
            "modulo": "Processos",
            "nome": "Processos a Mapear",
            "descricao": "Gerenciamento dos processos identificados para mapeamento.",
            "ordem": 2,
        },

        # ========================================================
        # ESTATÍSTICAS
        # ========================================================
        {
            "modulo": "Estatísticas",
            "nome": "Consultas e Indicadores",
            "descricao": "Consulta das informações, indicadores e representações gráficas disponibilizadas pelo SIGEMP.",
            "ordem": 1,
        },

        # ========================================================
        # ESTRUTURA DE DOCUMENTOS → PROCESSOS
        # ========================================================
        {
            "modulo": "Estrutura de Documentos → Processos",
            "nome": "Definição",
            "descricao": "Gerenciamento das definições de Macroprocesso e Modelo de Processo.",
            "ordem": 1,
        },
        {
            "modulo": "Estrutura de Documentos → Processos",
            "nome": "Classificação de Macroprocessos",
            "descricao": "Gerenciamento das classificações utilizadas para os Macroprocessos.",
            "ordem": 2,
        },
        {
            "modulo": "Estrutura de Documentos → Processos",
            "nome": "Macroprocesso N1",
            "descricao": "Gerenciamento dos Macroprocessos de nível 1.",
            "ordem": 3,
        },
        {
            "modulo": "Estrutura de Documentos → Processos",
            "nome": "Macroprocesso N2",
            "descricao": "Gerenciamento dos Macroprocessos de nível 2.",
            "ordem": 4,
        },
        {
            "modulo": "Estrutura de Documentos → Processos",
            "nome": "Áreas Responsáveis",
            "descricao": "Gerenciamento das áreas responsáveis pelos processos e demais estruturas relacionadas.",
            "ordem": 5,
        },

        # ========================================================
        # ESTRUTURA DE DOCUMENTOS → NORMAS DE PROCEDIMENTO
        # ========================================================
        {
            "modulo": "Estrutura de Documentos → Normas de Procedimento",
            "nome": "Definição",
            "descricao": "Gerenciamento das definições utilizadas nas Normas de Procedimento.",
            "ordem": 1,
        },
        {
            "modulo": "Estrutura de Documentos → Normas de Procedimento",
            "nome": "Sistemas",
            "descricao": "Gerenciamento dos sistemas relacionados às Normas de Procedimento.",
            "ordem": 2,
        },
        {
            "modulo": "Estrutura de Documentos → Normas de Procedimento",
            "nome": "Normas",
            "descricao": "Gerenciamento das Normas de Procedimento cadastradas no SIGEMP.",
            "ordem": 3,
        },

        # ========================================================
        # ADMINISTRAÇÃO
        # ========================================================
        {
            "modulo": "Administração",
            "nome": "Usuários",
            "descricao": "Gerenciamento dos usuários, seus perfis e demais informações de acesso ao SIGEMP.",
            "ordem": 1,
        },
        {
            "modulo": "Administração",
            "nome": "Logs",
            "descricao": "Consulta dos registros de atividades e eventos registrados pelo SIGEMP.",
            "ordem": 2,
        },
    ]

    for dados in funcionalidades:
        modulo = Modulo.objects.get(nome=dados["modulo"])

        Funcionalidade.objects.update_or_create(
            modulo=modulo,
            nome=dados["nome"],
            defaults={
                "descricao": dados["descricao"],
                "ordem": dados["ordem"],
                "ativo": True,
            },
        )


def remover_funcionalidades(apps, schema_editor):
    Modulo = apps.get_model("arquiteturaprocessos", "Modulo")
    Funcionalidade = apps.get_model("arquiteturaprocessos", "Funcionalidade")

    funcionalidades = [
        ("Cadeia de Valor", "Definição"),
        ("Cadeia de Valor", "Imagens"),

        ("Processos", "Cadastro de Processos"),
        ("Processos", "Processos a Mapear"),

        ("Estatísticas", "Consultas e Indicadores"),

        ("Estrutura de Documentos → Processos", "Definição"),
        ("Estrutura de Documentos → Processos", "Classificação de Macroprocessos"),
        ("Estrutura de Documentos → Processos", "Macroprocesso N1"),
        ("Estrutura de Documentos → Processos", "Macroprocesso N2"),
        ("Estrutura de Documentos → Processos", "Áreas Responsáveis"),

        ("Estrutura de Documentos → Normas de Procedimento", "Definição"),
        ("Estrutura de Documentos → Normas de Procedimento", "Sistemas"),
        ("Estrutura de Documentos → Normas de Procedimento", "Normas"),

        ("Administração", "Usuários"),
        ("Administração", "Logs"),
    ]

    for nome_modulo, nome_funcionalidade in funcionalidades:
        modulo = Modulo.objects.filter(nome=nome_modulo).first()

        if modulo:
            Funcionalidade.objects.filter(
                modulo=modulo,
                nome=nome_funcionalidade,
            ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0032_funcionalidade"),
    ]

    operations = [
        migrations.RunPython(
            criar_funcionalidades,
            remover_funcionalidades,
        ),
    ]