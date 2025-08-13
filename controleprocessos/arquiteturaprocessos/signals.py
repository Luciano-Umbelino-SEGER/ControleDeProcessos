from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Norma, Atualizacao_Norma

@receiver(post_save, sender=Norma)
def criar_primeira_atualizacao(sender, instance, created, **kwargs):
    if created:
        Atualizacao_Norma.objects.create(
            norma=instance,
            usuario=instance.usuario_cadastro,
            versao="1.0",
            descricao="Criação da Norma"
        )
