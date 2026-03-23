from django.db import models


class Sistema(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True)

    url = models.CharField(max_length=255, blank=True, null=True)
    rota = models.CharField(max_length=255, blank=True, null=True)

    icone = models.CharField(max_length=50, default="fa-cube")
    cor = models.CharField(max_length=20, default="#2563eb")

    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)

    # 🔮 FUTURO: controle de acesso (DESLIGADO por enquanto)
    # perfis = models.ManyToManyField("arquiteturaprocessos.Perfil", blank=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ["ordem", "nome"]