from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from auditoria.models import LogAcaoSistema
from auditoria.utils import registrar_log


class Command(BaseCommand):
    help = "Remove logs antigos (mais de 6 meses)"

    def handle(self, *args, **kwargs):
        hoje = timezone.now()
        limite = hoje - timedelta(days=180)

        logs_antigos = LogAcaoSistema.objects.filter(data_registro__lt=limite)
        total = logs_antigos.count()

        logs_antigos.delete()

        # 🔥 REGISTRA A LIMPEZA
        registrar_log(
            usuario=None,  # 🔥 sistema
            acao="DELETE",
            modelo="Auditoria",
            descricao=f"Limpeza automática de logs executada. {total} registros removidos.",
            dados_depois={
                "quantidade_removida": total,
                "data_execucao": hoje.strftime("%d/%m/%Y %H:%M")
            }
        )

        self.stdout.write(self.style.SUCCESS(f"{total} logs removidos com sucesso."))