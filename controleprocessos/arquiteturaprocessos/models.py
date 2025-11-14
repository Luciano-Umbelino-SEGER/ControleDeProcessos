import os
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.urls import reverse

LSTA_CLASSIFICACAO = (
    ("FINALISTICO", "Finalístico"),
    ("SUPORTE", "Suporte"),
    ("ESTRATEGICO", "Estratégico"),
)

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
        """Retorna o telefone formatado no padrão brasileiro"""
        ramal_str = f" Ramal: {self.ramal}" if self.ramal else ""

        if len(self.numero) == 9:  # celular
            return f"({self.ddd}) {self.numero[:5]}-{self.numero[5:]}{ramal_str}"
        elif len(self.numero) == 8:  # fixo
            return f"({self.ddd}) {self.numero[:4]}-{self.numero[4:]}{ramal_str}"
        else:
            return f"({self.ddd}) {self.numero}{ramal_str}"

    def __str__(self):
        return f"{self.ddd} - {self.numero} - {self.ramal}"


class Usuario(AbstractUser):
    setor = models.CharField(max_length=100, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    funcao = models.CharField(max_length=100, null=True, blank=True)
    perfil = models.ForeignKey("Perfil", null=True, blank=True, on_delete=models.SET_NULL)
    data_ativacaodesativacao = models.DateTimeField(default=timezone.now)

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
    classificacao = models.ForeignKey(
        "Classificacao",
        on_delete=models.PROTECT,
        related_name="macroprocessos_nivel1"
    )

    def __str__(self):
        return f"{self.nome}"


class MacroprocessoNivel2(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(max_length=500)
    macroprocesso_nivel1 = models.ForeignKey(
        "MacroprocessoNivel1",
        on_delete=models.PROTECT,
        related_name="macroprocessos_nivel2",
        null=False,
        blank=False
    )

    def __str__(self):
        return f"{self.nome}"

# ============================================================
# Modelagem de Processos
# ============================================================
def mp_upload_to(instance, filename):
    """
    Gera um nome único para cada arquivo enviado.
    Evita sobrescrever e preserva a extensão original.
    """
    nome, ext = os.path.splitext(filename)
    ext = ext.lower()

    # Gera código único curto (8 chars)
    codigo = uuid.uuid4().hex[:8]

    # Normaliza o nome
    nome = nome.replace(" ", "_").replace("–", "-")

    novo_nome = f"{nome}_{codigo}{ext}"
    return f"modelagemprocessos/{novo_nome}"

class ModelagemProcesso(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    nome = models.CharField(max_length=200, verbose_name="Nome", default="NORMA DE PROCEDIMENTO")
    codigo = models.CharField(
        max_length=10,
        db_index=True,
        verbose_name="Código",
        validators=[RegexValidator(r"^[A-Za-z0-9.\-_/]+$", "Use apenas letras, números e . - _ /")],
        default="SRH"
    )
    sequencial = models.CharField(
        max_length=3,
        validators=[RegexValidator(r'^\d{1,3}$', message="Informe um número válido entre 1 e 999.")],
        verbose_name="Sequencial"
    )
    versao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        verbose_name="Versão"
    )
    tema = models.CharField(max_length=150, db_index=True, verbose_name="Tema")
    emitente = models.CharField(max_length=150, db_index=True, verbose_name="Emitente")
    sistema = models.CharField(max_length=100, db_index=True, verbose_name="Sistema")

    data_elaboracao = models.DateField(null=True, blank=True, verbose_name="Data de Elaboração")
    portaria_aprovacao = models.CharField(max_length=150, blank=True, verbose_name="Portaria de Aprovação")
    data_aprovacao = models.DateField(null=True, blank=True, verbose_name="Data de Aprovação")
    vigencia_inicio = models.DateField(null=True, blank=True, verbose_name="Início da Vigência")
    vigencia_fim = models.DateField(null=True, blank=True, verbose_name="Fim da Vigência")

    link_normaprocedimento = models.URLField(max_length=500, blank=True, null=True, verbose_name="Link Norma de Procedimento")

    documento_modelagem_processo = models.FileField(
        upload_to=mp_upload_to,
        max_length=500,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="Documento de Modelagem de Processo"
    )

    data_cadastro = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="Data de Cadastro")
    data_atualizacao = models.DateTimeField(auto_now=True, editable=False, verbose_name="Data de Atualização")

    usuario = models.ForeignKey(
        "Usuario",
        on_delete=models.PROTECT,
        related_name="modelagens_criadas",
        verbose_name="Usuário"
    )
    usuario_atualizacao = models.ForeignKey(
        "Usuario",
        related_name="modelagens_atualizadas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário (última atualização)"
    )

    class Meta:
        db_table = "arquiteturaprocessos_modelagem_processo"
        verbose_name = "Modelagem de Processo"
        verbose_name_plural = "Modelagens de Processo"
        ordering = ["nome", "codigo", "sequencial", "versao", "tema"]
        constraints = [
            models.UniqueConstraint(fields=["codigo", "sequencial", "versao"], name="uq_modelagem_codigo_seq_versao")
        ]
        indexes = [
            models.Index(fields=["nome"], name="idx_mp_nome"),
            models.Index(fields=["tema"], name="idx_mp_tema"),
            models.Index(fields=["sistema"], name="idx_mp_sistema"),
            models.Index(fields=["emitente"], name="idx_mp_emitente"),
        ]

    def save(self, *args, **kwargs):
        """
        Se o arquivo for alterado, remove o arquivo antigo do servidor.
        """

        # Detecta alteração do arquivo durante edição
        try:
            old = ModelagemProcesso.objects.get(pk=self.pk)
        except ModelagemProcesso.DoesNotExist:
            old = None

        super().save(*args, **kwargs)

        # Se não havia registro anterior, nada a deletar
        if not old:
            return

        # Se o arquivo foi trocado, apagar o antigo
        if old.documento_modelagem_processo and old.documento_modelagem_processo != self.documento_modelagem_processo:
            old_path = old.documento_modelagem_processo.path
            if os.path.isfile(old_path):
                os.remove(old_path)

    def delete(self, *args, **kwargs):
        """
        Ao excluir o registro, remove também o arquivo do servidor.
        """
        if self.documento_modelagem_processo:
            path = self.documento_modelagem_processo.path
            if os.path.isfile(path):
                os.remove(path)

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} - {self.codigo}-{self.sequencial} - V{self.versao} - {self.tema}"

# ============================================================
# PROCESSO / SUBPROCESSO
# ============================================================

class Processo(models.Model):
    classificacao = models.ForeignKey(
        "Classificacao",
        on_delete=models.PROTECT,
        related_name="processos"
    )

    macroprocesso_nivel1 = models.ForeignKey(
        "MacroprocessoNivel1",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    macroprocesso_nivel2 = models.ForeignKey(
        "MacroprocessoNivel2",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    nome = models.CharField(
        max_length=100,
        verbose_name="Nome do Processo/Subprocesso"
    )

    usuario_cadastro = models.ForeignKey(
        "Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processos_cadastrados",
        verbose_name="Usuário que efetuou o cadastro"
    )

    area_responsavel = models.CharField(
        max_length=100,
        null = True,
        blank = True,
        verbose_name="Área Responsável"
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subprocessos",
        verbose_name="Processo Pai"
    )

    gestor = models.CharField(
        max_length=150,
        verbose_name="Gestor"
    )

    email = models.EmailField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="E-mail do Gestor"
    )

    telefone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Telefone/Ramal"
    )

    modelagem_processo = models.ForeignKey(
        "ModelagemProcesso",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Modelagem de Processo"
    )

    objetivo = models.TextField(
        verbose_name="Objetivo do Processo"
    )

    observacao = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observações"
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Data de Atualização"
    )

    class Meta:
        db_table = "arquiteturaprocessos_processo"
        verbose_name = "Processo / Subprocesso"
        verbose_name_plural = "Processos / Subprocessos"
        ordering = ["nome"]

    def __str__(self):
        # Exibe hierarquia se for subprocesso
        return f"{self.nome}" if not self.parent else f"{self.parent.nome} > {self.nome}"

# ============================================================
# ARQUITETURA / LOG
# ============================================================

class ArquiteturaProcesso(models.Model):
    macroprocesso_nivel1 = models.ForeignKey("MacroprocessoNivel1", related_name="arquiteturas_nivel1", null=True, blank=True, on_delete=models.SET_NULL)
    macroprocesso_nivel2 = models.ForeignKey("MacroprocessoNivel2", related_name="arquiteturas_nivel2", null=True, blank=True, on_delete=models.SET_NULL)


class LogAcoes(models.Model):
    data_registro = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE)
    area = models.CharField(max_length=100)
    acao = models.CharField(max_length=100)
    descricao_acao = models.TextField(max_length=500)
    modelo_afetado = models.CharField(max_length=100, null=True, blank=True)
    id_referencia = models.IntegerField(null=True, blank=True)
