from django.core.management.base import BaseCommand
from arquiteturaprocessos.services.contatos_seger import atualizar_contatos_seger


class Command(BaseCommand):
    help = "Atualiza contatos da SEGER"

    def handle(self, *args, **kwargs):
        total = atualizar_contatos_seger()
        self.stdout.write(self.style.SUCCESS(f"{total} registros processados"))