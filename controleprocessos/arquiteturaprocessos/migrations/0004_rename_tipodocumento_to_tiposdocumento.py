# -*- coding: utf-8 -*-
from django.db import migrations, models


def atualizar_contenttype(apps, schema_editor):
    """
    Atualiza o nome do ContentType do Django para refletir a renomeação
    do modelo TipoDocumento → TiposDocumento.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="arquiteturaprocessos", model="tipodocumento").first()
    if ct:
        ct.model = "tiposdocumento"
        ct.save(update_fields=["model"])


def atualizar_permissoes(apps, schema_editor):
    """
    Ajusta permissões que referenciam tipodocumento → tiposdocumento
    """
    Permission = apps.get_model("auth", "Permission")
    for perm in Permission.objects.filter(codename__icontains="tipodocumento"):
        perm.codename = perm.codename.replace("tipodocumento", "tiposdocumento")
        perm.name = perm.name.replace("Tipo documento", "Tipos documento")
        perm.save(update_fields=["codename", "name"])


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0003_alter_modelagemprocesso_options_and_more"),
    ]

    operations = [
        # 1) Renomeia a tabela física
        migrations.AlterModelTable(
            name="tipodocumento",
            table="arquiteturaprocessos_tiposdocumento",
        ),

        # 2) Renomeia o modelo dentro do Django
        migrations.RenameModel(
            old_name="TipoDocumento",
            new_name="TiposDocumento",
        ),

        # 3) Adiciona novo campo
        migrations.AddField(
            model_name="tiposdocumento",
            name="descricao",
            field=models.TextField(null=True, blank=True),
        ),

        # 4) Atualiza ContentType
        migrations.RunPython(atualizar_contenttype, migrations.RunPython.noop),

        # 5) Atualiza permissões
        migrations.RunPython(atualizar_permissoes, migrations.RunPython.noop),
    ]
