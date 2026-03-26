from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


# ============================================================
# LOG de Ações Sistema
# ============================================================
class LogAcaoSistema(models.Model):

    class TipoAcao(models.TextChoices):
        CREATE = "CREATE", "Criação"
        UPDATE = "UPDATE", "Atualização"
        DELETE = "DELETE", "Exclusão"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        VIEW = "VIEW", "Visualização"
        ERROR = "ERROR", "Erro"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    acao = models.CharField(max_length=20, choices=TipoAcao.choices)

    modelo_afetado = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=50, null=True, blank=True)

    descricao = models.TextField()

    dados_antes = models.JSONField(null=True, blank=True)
    dados_depois = models.JSONField(null=True, blank=True)

    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    sucesso = models.BooleanField(default=True)

    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "log_acao_sistema"
        ordering = ["-data_registro"]

    def __str__(self):
        return f"{self.usuario} - {self.acao} - {self.modelo_afetado}"
