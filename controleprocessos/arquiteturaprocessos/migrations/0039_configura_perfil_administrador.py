from django.db import migrations


def configurar_perfil_administrador(apps, schema_editor):
    Perfil = apps.get_model("arquiteturaprocessos", "Perfil")

    perfil = Perfil.objects.filter(nome="Administrador").first()

    if perfil:
        perfil.codigo = "ADMINISTRADOR"
        perfil.protegido = True
        perfil.save(update_fields=["codigo", "protegido"])


def reverter_perfil_administrador(apps, schema_editor):
    Perfil = apps.get_model("arquiteturaprocessos", "Perfil")

    perfil = Perfil.objects.filter(codigo="ADMINISTRADOR").first()

    if perfil:
        perfil.codigo = None
        perfil.protegido = False
        perfil.save(update_fields=["codigo", "protegido"])


class Migration(migrations.Migration):

    dependencies = [
        ("arquiteturaprocessos", "0038_perfil_codigo_perfil_protegido"),
    ]

    operations = [
        migrations.RunPython(
            configurar_perfil_administrador,
            reverter_perfil_administrador,
        ),
    ]