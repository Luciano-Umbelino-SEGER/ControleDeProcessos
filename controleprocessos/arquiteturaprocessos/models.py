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
    nivel = models.IntegerField()

    def __str__(self):
        return str(f"{self.nome} - {self.nivel}")

class Norma(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(max_length=500)
    usuario_cadastro = models.ForeignKey("Usuario", related_name="normas_criadas", on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(default=timezone.now)

class Atualizacao_Norma(models.Model):
    norma = models.ForeignKey("Norma", related_name="atualizacoes", on_delete=models.CASCADE)
    usuario = models.ForeignKey("Usuario", null=True, blank=True, on_delete=models.SET_NULL)
    data_atualizacao = models.DateTimeField(default=timezone.now)
    versao = models.CharField(max_length=5)
    descricao = models.TextField(max_length=500)


class ArquiteturaProcesso(models.Model):
    classificacao = models.CharField(max_length=30, choices=LSTA_CLASSIFICACAO)
    macroprocesso_nivel1 = models.ForeignKey("Macroprocesso", related_name="arquiteturas_nivel1", null=True, blank=True,
                                             on_delete=models.SET_NULL)
    macroprocesso_nivel2 = models.ForeignKey("Macroprocesso", related_name="arquiteturas_nivel2", null=True, blank=True,
                                             on_delete=models.SET_NULL)
    processo = models.CharField(max_length=500)
    subprocesso = models.CharField(max_length=200)
    area_responsavel = models.CharField(max_length=100)
    gestor = models.CharField(max_length=300)
    email = models.CharField(max_length=300)
    ramal = models.IntegerField()
    norma = models.ForeignKey("Norma", related_name="arquiteturas", null=True, blank=True, on_delete=models.SET_NULL)
    objetivoprocesso = models.TextField(max_length=1500)
    versao = models.CharField(max_length=10)
    data_norma_revisao = models.DateField(default=timezone.now)
    link_norma_disponivel = models.CharField(max_length=500)
    observacao = models.TextField(max_length=1500)
    norma_autualizada = models.BooleanField(default=False) #(23-25 S/N)

class LogAtividade(models.Model):
    data_registro = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE)
    area = models.CharField(max_length=100)
    acao = models.CharField(max_length=100)  # Ex: "Criação", "Atualização", "Exclusão"
    descricao_acao = models.TextField(max_length=500)
    modelo_afetado = models.CharField(max_length=100, null=True, blank=True)  # Ex: "Norma", "Usuario"
    id_referencia = models.IntegerField(null=True, blank=True)  # ID do objeto afetado

