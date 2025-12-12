import os
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import (
    RegexValidator,
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator,
)
from django.core.exceptions import ValidationError


# ============================================================
# PERFIL / USUÁRIO / TELEFONE
# ============================================================

class Perfil(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.nome)


class Telefone(models.Model):
    usuario = models.ForeignKey("Usuario", related_name="telefones", on_delete=models.CASCADE)
    ddd = models.CharField(max_length=3, null=True, blank=True)
    numero = models.CharField(max_length=9, null=True, blank=True)
    ramal = models.CharField(max_length=5, null=True, blank=True)

    @property
    def numero_formatado(self):
        ramal_str = f" Ramal: {self.ramal}" if self.ramal else ""
        if len(self.numero) == 9:
            return f"({self.ddd}) {self.numero[:5]}-{self.numero[5:]}{ramal_str}"
        elif len(self.numero) == 8:
            return f"({self.ddd}) {self.numero[:4]}-{self.numero[4:]}{ramal_str}"
        return f"({self.ddd}) {self.numero}{ramal_str}"

    def __str__(self):
        return f"{self.ddd} - {self.numero} - {self.ramal}"

class Usuario(AbstractUser):
    """
    Modelo de usuário customizado baseado em AbstractUser,
    mantendo username, password, first_name, last_name, email etc.
    """

    setor = models.CharField(max_length=100, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    funcao = models.CharField(max_length=100, null=True, blank=True)
    perfil = models.ForeignKey("Perfil", null=True, blank=True, on_delete=models.SET_NULL)
    data_ativacaodesativacao = models.DateTimeField(default=timezone.now)

    # campos obrigatórios além de USERNAME_FIELD
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        perfil_nome = self.perfil.nome if self.perfil else "Sem perfil"
        cargo_nome = self.cargo if self.cargo else "Sem cargo"
        return f"{self.username} - {cargo_nome} - {perfil_nome}"



# ============================================================
# CLASSIFICAÇÃO / MACROPROCESSOS
# ============================================================

class Classificacao(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(max_length=500)

    def __str__(self):
        return self.nome


class MacroprocessoNivel1(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(max_length=500)
    classificacao = models.ForeignKey("Classificacao", on_delete=models.PROTECT)

    def __str__(self):
        return self.nome


class MacroprocessoNivel2(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(max_length=500)
    macroprocesso_nivel1 = models.ForeignKey("MacroprocessoNivel1", on_delete=models.PROTECT)

    def __str__(self):
        return self.nome

# ============================================================
# TIPOS DE DOCUMENTOS
# ============================================================
class TiposDocumento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    descricao = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "arquiteturaprocessos_tiposdocumento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)



# ============================================================
# MODELAGEM DE PROCESSO
# ============================================================

def mp_upload_to(instance, filename):
    titulo, ext = os.path.splitext(filename)
    ext = ext.lower()
    codigo = uuid.uuid4().hex[:8]
    titulo = titulo.replace(" ", "_").replace("–", "-")
    return f"modelagemprocessos/{titulo}_{codigo}{ext}"


class ModelagemProcesso(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    tipo_documento = models.ForeignKey(
        "TiposDocumento", on_delete=models.PROTECT, related_name="modelagens"
    )

    titulo = models.CharField(max_length=255, null=True, blank=True)
    codigo = models.CharField(
        max_length=10,
        db_index=True,
        validators=[RegexValidator(r"^[A-Za-z0-9.\-_/]+$")],
        default="SRH",
    )
    sequencial = models.CharField(
        max_length=3,
        validators=[RegexValidator(r"^\d{1,3}$")],
    )
    versao = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(99)])
    tema = models.CharField(max_length=150, db_index=True)
    emitente = models.CharField(max_length=150, db_index=True)
    sistema = models.CharField(max_length=100, db_index=True)

    data_elaboracao = models.DateField(null=True, blank=True)
    portaria_aprovacao = models.CharField(max_length=150, blank=True)
    data_aprovacao = models.DateField(null=True, blank=True)
    vigencia_inicio = models.DateField(null=True, blank=True)
    vigencia_fim = models.DateField(null=True, blank=True)

    link_normaprocedimento = models.URLField(max_length=500, null=True, blank=True)

    documento_modelagem_processo = models.FileField(
        upload_to=mp_upload_to,
        max_length=500,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["pdf"])],
    )

    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="modelagens_criadas"
    )
    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modelagens_atualizadas",
    )

    class Meta:
        db_table = "arquiteturaprocessos_modelagem_processo"
        ordering = ["titulo", "codigo", "sequencial", "versao", "tema"]

    def save(self, *args, **kwargs):
        try:
            old = ModelagemProcesso.objects.get(pk=self.pk)
        except ModelagemProcesso.DoesNotExist:
            old = None

        super().save(*args, **kwargs)

        if old and old.documento_modelagem_processo and old.documento_modelagem_processo != self.documento_modelagem_processo:
            old_path = old.documento_modelagem_processo.path
            if os.path.isfile(old_path):
                os.remove(old_path)

    def __str__(self):
        return f"{self.titulo} - {self.codigo}-{self.sequencial} - V{self.versao}"


# ============================================================
# PROCESSO / SUBPROCESSO
# ============================================================

class Processo(models.Model):
    nome = models.CharField(max_length=100)
    gestor = models.CharField(max_length=150)
    email = models.EmailField(max_length=200, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    objetivo = models.TextField()
    observacao = models.TextField(null=True, blank=True)

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(null=True, blank=True)

    classificacao = models.ForeignKey("Classificacao", on_delete=models.PROTECT)

    macroprocesso_nivel1 = models.ForeignKey("MacroprocessoNivel1", on_delete=models.SET_NULL, null=True, blank=True)
    macroprocesso_nivel2 = models.ForeignKey("MacroprocessoNivel2", on_delete=models.SET_NULL, null=True, blank=True)

    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="subprocessos")

    area_responsavel = models.CharField(max_length=100, null=True, blank=True)

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="processos_cadastrados"
    )
    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="processos_atualizados"
    )

    class Meta:
        db_table = "arquiteturaprocessos_processo"
        ordering = ["nome"]

    def __str__(self):
        return self.nome if not self.parent else f"{self.parent.nome} > {self.nome}"

    def clean(self):
        if self.parent and self.parent_id == self.id:
            raise ValidationError({"parent": "O processo pai não pode ser o próprio processo."})


# ============================================================
# PROCESSO–DOCUMENTO (1 processo → N documentos)
# ============================================================

class ProcessoDocumento(models.Model):
    processo = models.ForeignKey(
        "Processo",
        on_delete=models.CASCADE,
        related_name="documentos"  # facilita uso: processo.documentos.all()
    )
    # Relação direta com a modelagem que contém o PDF / link / tipo
    modelagem_processo = models.ForeignKey(
        "ModelagemProcesso",
        on_delete=models.PROTECT,
        related_name="processo_documentos"
    )

    class Meta:
        db_table = "arquiteturaprocessos_processodocumento"

    def __str__(self):
        mp = self.modelagem_processo
        return f"Doc {mp.codigo if mp else 'N/A'} → Processo {self.processo_id}"

# ============================================================
# LOG
# ============================================================

class LogAcoes(models.Model):
    data_registro = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE)
    area = models.CharField(max_length=100)
    acao = models.CharField(max_length=100)
    descricao_acao = models.TextField(max_length=500)
    modelo_afetado = models.CharField(max_length=100, null=True, blank=True)
    id_referencia = models.IntegerField(null=True, blank=True)
