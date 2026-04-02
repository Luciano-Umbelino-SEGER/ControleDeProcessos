from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from dateutil.relativedelta import relativedelta

from auditoria.models import LogAcaoSistema
from auditoria.utils import registrar_log


class Command(BaseCommand):
    help = "Remove logs antigos (mais de 6 meses)"

    def handle(self, *args, **kwargs):
        hoje = timezone.now()
        limite = hoje - relativedelta(months=6)

        try:
            with transaction.atomic():
                logs_antigos = LogAcaoSistema.objects.filter(data_registro__lt=limite)
                total = logs_antigos.count()

                logs_antigos.delete()

                # 🔥 REGISTRA A LIMPEZA
                registrar_log(
                    usuario=None,  # Sistema
                    acao="DELETE",
                    modelo="LogAcaoSistema",
                    descricao=f"Limpeza automática de logs executada. {total} registros removidos.",
                    dados_depois={
                        "quantidade_removida": total,
                        "data_execucao": hoje.strftime("%d/%m/%Y %H:%M"),
                        "limite_utilizado": limite.strftime("%d/%m/%Y %H:%M"),
                    }
                )

            self.stdout.write(
                self.style.SUCCESS(f"{total} logs removidos com sucesso.")
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Erro ao executar limpeza de logs: {str(e)}")
            )