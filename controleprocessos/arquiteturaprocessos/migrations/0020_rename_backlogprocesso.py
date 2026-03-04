from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('arquiteturaprocessos', '0019_alter_backlogprocesso_data_atualizacao'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BacklogProcesso',
            new_name='ProcessoMapear',
        ),
    ]