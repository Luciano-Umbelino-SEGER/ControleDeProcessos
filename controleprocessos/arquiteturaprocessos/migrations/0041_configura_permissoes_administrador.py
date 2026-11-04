from django.db import migrations


def configurar_permissoes_administrador(apps, schema_editor):
    Perfil = apps.get_model(
        "arquiteturaprocessos",
        "Perfil",
    )
    FuncionalidadeAcao = apps.get_model(
        "arquiteturaprocessos",
        "FuncionalidadeAcao",
    )
    PerfilPermissao = apps.get_model(
        "arquiteturaprocessos",
        "PerfilPermissao",
    )

    perfil_administrador = Perfil.objects.filter(
        codigo="ADMINISTRADOR",
    ).first()

    if not perfil_administrador:
        raise RuntimeError(
            "Perfil Administrador não encontrado."
        )

    total_permissoes = 0

    for funcionalidade_acao in FuncionalidadeAcao.objects.all():
        PerfilPermissao.objects.get_or_create(
            perfil=perfil_administrador,
            funcionalidade_acao=funcionalidade_acao,
        )

        total_permissoes += 1

    if total_permissoes != 58:
        raise RuntimeError(
            f"Quantidade inesperada de permissões: "
            f"{total_permissoes}. "
            "Era esperado um total de 58."
        )


def remover_permissoes_administrador(apps, schema_editor):
    Perfil = apps.get_model(
        "arquiteturaprocessos",
        "Perfil",
    )
    PerfilPermissao = apps.get_model(
        "arquiteturaprocessos",
        "PerfilPermissao",
    )

    perfil_administrador = Perfil.objects.filter(
        codigo="ADMINISTRADOR",
    ).first()

    if perfil_administrador:
        PerfilPermissao.objects.filter(
            perfil=perfil_administrador,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "arquiteturaprocessos",
            "0040_seed_funcionalidade_perfis",
        ),
    ]

    operations = [
        migrations.RunPython(
            configurar_permissoes_administrador,
            remover_permissoes_administrador,
        ),
    ]