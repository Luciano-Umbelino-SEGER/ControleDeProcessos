from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

LSTA_CLASSIFICACAO = (
    ("FINALISTICO", "Finalístico"),
    ("SUPORTE", "Suporte"),
    ("ESTRATEGICO", "Estratégico"),
)

# Create your models here.
class Perfil(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.nome)

class Telefone(models.Model):
    usuario = models.ForeignKey("Usuario", related_name="telefones", on_delete=models.CASCADE)
    ddd = models.IntegerField()
    numero = models.IntegerField()
    ramal = models.IntegerField()

class Usuario(AbstractUser):
    setor = models.CharField(max_length=100, null=False, blank=False)
    cargo = models.CharField(max_length=100, null=False, blank=False)
    funcao = models.CharField(max_length=100, null=False, blank=False)
    perfil = models.ForeignKey("Perfil", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.username} - {self.cargo}"

class Macroprocesso(models.Model):
    nome = models.CharField(max_length=200)
    nivel = models.IntegerField(max_length=1)

    def __str__(self):
        return str(f"{self.nome} - {self.nivel}")

class ArquiteturaProcesso(models.Model):
    classificacao = models.CharField(max_length=30, choices=LSTA_CLASSIFICACAO)
    macroprocesso_nivel1 = models.ForeignKey("Macroprocesso", on_delete=models.SET_NULL)
    macroprocesso_nivel2 = models.ForeignKey("Macroprocesso", on_delete=models.SET_NULL)
    processo = models.CharField(max_length=500)
    subprocesso = models.CharField(max_length=200)
    area_responsavel = models.CharField(max_length=100)
    gestor = models.CharField(max_length=300)
    email = models.CharField(max_length=300)
    ramal = models.IntegerField(max_length=4)
    nome_norma = models.CharField(max_length=500)
    objetivoprocesso = models.TextField(max_length=1500)
    versao = models.CharField(max_length=10)
    data_norma_revisao = models.DateField(default=timezone.now)
    link_norma_disponivel = models.CharField(max_length=500)
    observacao = models.TextField(max_length=1500)
    norma_autualizada = models.BooleanField(default=False) #(23-25 S/N)
