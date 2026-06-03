import unicodedata
import re
import os
import uuid
from uuid import uuid4
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, FileExtensionValidator, validate_email
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


# ============================================================
# Usuários
# ============================================================
class Usuario(AbstractUser):
    """
    Modelo de usuário customizado baseado em AbstractUser,
    mantendo username, password, first_name, last_name, email etc.
    """

    setor = models.CharField(max_length=100, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    funcao = models.CharField(max_length=100, null=True, blank=True)
    perfil = models.ForeignKey(
        "Perfil",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    data_ativacaodesativacao = models.DateTimeField(default=timezone.now)

    # 🔐 FLAG DE SISTEMA
    is_master = models.BooleanField(
        default=False,
        help_text="Usuário Master do sistema (invisível e não excluível)"
    )

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        perfil_nome = self.perfil.nome if self.perfil else "Sem perfil"
        cargo_nome = self.cargo if self.cargo else "Sem cargo"
        return f"{self.username} - {cargo_nome} - {perfil_nome}"

    # ========================================================
    # 🛡️ CAMADA 3 — BLINDAGEM NO MODEL
    # ========================================================

    def save(self, *args, **kwargs):
        """
        Impede alterações críticas no Usuário Master:
        - não pode ser desativado
        - não pode perder status de master
        """
        if self.pk:
            original = Usuario.objects.get(pk=self.pk)

            # 🔒 Master não pode ser desativado
            if original.is_master and not self.is_active:
                raise ValidationError(
                    "Usuário master não pode ser desativado."
                )

            # 🔒 Master não pode perder status
            if original.is_master and not self.is_master:
                raise ValidationError(
                    "Não é permitido remover o status de usuário master."
                )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Impede exclusão do Usuário Master em qualquer cenário
        (views, admin, shell, scripts)
        """
        if self.is_master:
            raise ValidationError(
                "Usuário master é protegido pelo sistema e não pode ser excluído."
            )
        super().delete(*args, **kwargs)


# ============================================================
# CLASSIFICAÇÃO / MACROPROCESSOS
# ============================================================
class Classificacao(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()

    def __str__(self):
        return self.nome

# ============================================================
# Macroprocesso Nível 1
# ============================================================
class MacroprocessoNivel1(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField()
    classificacao = models.ForeignKey("Classificacao", on_delete=models.PROTECT)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['nome']

# ============================================================
# Macroprocesso Nível 2
# ============================================================
class MacroprocessoNivel2(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField()
    macroprocesso_nivel1 = models.ForeignKey("MacroprocessoNivel1", on_delete=models.PROTECT)

    def __str__(self):
        return self.nome

# ============================================================
# TIPOS DE DOCUMENTOS
# ============================================================
class TiposDocumento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    descricao = models.TextField(blank=True)

    class Meta:
        db_table = "arquiteturaprocessos_tiposdocumento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

# ==================================================================
# Função para normalização de strings - retirar caracter especiais
# ==================================================================
def mp_upload_to(instance, filename):
    """
    Gera caminho seguro para upload de documentos de modelagem de processo.

    - Remove acentos
    - Remove caracteres especiais
    - Substitui espaços por _
    - Mantém extensão em minúsculo
    - Garante unicidade com UUID
    """

    nome, ext = os.path.splitext(filename)
    ext = ext.lower()

    # Normaliza (remove acentos)
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")

    # Substitui caracteres inválidos por _
    nome = re.sub(r"[^\w\-_.]", "_", nome)

    # Evita nomes vazios
    if not nome:
        nome = "documento"

    # Garante unicidade
    novo_nome = f"{nome}_{uuid4().hex[:8]}{ext}"

    return f"modelagemprocessos/{novo_nome}"

# ============================================================
# MODELAGEM DE PROCESSO
# ============================================================
class ModelagemProcesso(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    tipo_documento = models.ForeignKey(
        "TiposDocumento",
        on_delete=models.PROTECT,
        related_name="modelagens"
    )

    # 🔹 SEMPRE obrigatório
    titulo = models.CharField(max_length=255)

    # 🔹 Opcionais para Modelo de Processo
    codigo = models.CharField(
        max_length=10,
        db_index=True,
        validators=[RegexValidator(r"^[A-Z0-9.\-_/]+$")],
        null=True,
        blank=True,
    )

    sequencial = models.CharField(
        max_length=4,
        validators=[RegexValidator(r"^\d{1,4}$")],
        null=True,
        blank=True,
    )

    versao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
        null=True,
        blank=True,
    )

    tema = models.CharField(
        max_length=150,
        db_index=True,
        null=True,
        blank=True,
    )

    emitente = models.CharField(
        max_length=150,
        db_index=True,
        null=True,
        blank=True,
    )

    sistema = models.CharField(
        max_length=100,
        db_index=True,
        null=True,
        blank=True,
    )

    # 🔹 Datas opcionais
    data_elaboracao = models.DateField(null=True, blank=True)

    portaria_aprovacao = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    data_aprovacao = models.DateField(null=True, blank=True)

    vigencia_inicio = models.DateField(null=True, blank=True)

    vigencia_fim = models.DateField(null=True, blank=True)

    # 🔹 Link opcional
    link_normaprocedimento = models.URLField(
        max_length=500,
        null=True,
        blank=True,
    )

    # 🔹 PDF opcional
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
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelagens_criadas"
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

        ordering = [
            "titulo",
            "codigo",
            "sequencial",
            "versao",
            "tema",
        ]

    def save(self, *args, **kwargs):
        try:
            old = ModelagemProcesso.objects.get(pk=self.pk)

        except ModelagemProcesso.DoesNotExist:
            old = None

        super().save(*args, **kwargs)

        # 🔹 Remove PDF antigo após substituição
        if (
            old
            and old.documento_modelagem_processo
            and old.documento_modelagem_processo != self.documento_modelagem_processo
        ):
            old_path = old.documento_modelagem_processo.path

            if os.path.isfile(old_path):
                os.remove(old_path)

    def __str__(self):
        codigo = self.codigo or "---"
        sequencial = self.sequencial or "---"
        versao = self.versao or "--"

        return f"{self.titulo} - {codigo}-{sequencial} - V{versao}"

# ============================================================
# UPLOAD DE ARQUIVO DE MODELO DE PROCESSO
# ============================================================
def modelo_processo_upload_to(instance, filename):
    """
    Gera caminho seguro para upload de documentos de Modelo de Processo.

    - Remove acentos
    - Remove caracteres especiais
    - Substitui espaços por _
    - Mantém extensão minúscula
    - Garante unicidade com UUID
    """

    nome, ext = os.path.splitext(filename)

    ext = ext.lower()

    # Remove acentos
    nome = (
        unicodedata
        .normalize("NFKD", nome)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    # Remove caracteres inválidos
    nome = re.sub(
        r"[^\w\-_.]",
        "_",
        nome
    )

    # Evita nome vazio
    if not nome:
        nome = "modelo_processo"

    # UUID curto
    novo_nome = (
        f"{nome}_{uuid4().hex[:8]}{ext}"
    )

    return (
        f"modelosprocesso/{novo_nome}"
    )

# ============================================================
# MODELO DE PROCESSO
# ============================================================
class ModeloProcesso(models.Model):
    # ============================================================
    # STATUS
    # ============================================================
    STATUS_ELABORADO = "ELABORADO"
    STATUS_REVISADO = "REVISADO"
    STATUS_APROVADO = "APROVADO"

    STATUS_CHOICES = [
        ("ELABORADO", "Elaborado"),
        ("REVISADO", "Revisado"),
        ("APROVADO", "Aprovado"),
    ]

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # ========================================================
    # IDENTIFICAÇÃO DO DOCUMENTO
    # ========================================================
    titulo = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Título",
    )

    codigo = models.CharField(
        max_length=20,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9.\-_/]+$",
                message="Utilize apenas letras maiúsculas, números e . - _ /",
            )
        ],
        verbose_name="Código",
    )

    numero_modelo = models.CharField(
        max_length=8,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r"^\d{3}/\d{4}$",
                message="Informe no formato 001/2025.",
            )
        ],
        verbose_name="Número do Modelo",
    )

    versao = models.CharField(
        max_length=4,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r"^(?!0000)\d{4}$",
                message="Informe a versão no formato 0001.",
            )
        ],
        default="0001",
        verbose_name="Versão",
    )

    estado = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ELABORADO,
        db_index=True,
        verbose_name="Estado",
    )

    # ========================================================
    # DADOS DO PROCESSO
    # ========================================================
    setor = models.CharField(
        max_length=150,
        verbose_name="Setor",
    )

    unidades_envolvidas = models.TextField(
        blank=True,
        verbose_name="Unidades Envolvidas",
    )

    objetivo_processo = models.TextField(
        verbose_name="Objetivo do Processo",
    )

    abrangencia = models.TextField(
        blank=True,
        verbose_name="Abrangência",
    )

    fundamentacao_definicoes = models.TextField(
        blank=True,
        verbose_name="Fundamentação / Definições",
    )

    envolvidos_externos = models.TextField(
        blank=True,
        verbose_name="Envolvidos Externos",
    )

    observacao = models.TextField(
        blank=True,
        verbose_name="Observação",
    )

    # ========================================================
    # DOCUMENTAÇÃO
    # ========================================================
    documento_modelo_processo = models.FileField(
        upload_to=modelo_processo_upload_to,
        max_length=500,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(["pdf"])
        ],
        verbose_name="Documento Modelo de Processo",
    )

    link_documento_externo = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Link Documento Externo",
    )

    # ========================================================
    # ELABORAÇÃO
    # ========================================================
    data_elaboracao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Elaboração",
    )

    usuario_elaboracao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelos_processo_elaborados",
        verbose_name="Usuário Elaboração",
    )

    # ========================================================
    # REVISÃO
    # ========================================================
    data_revisao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Revisão",
    )

    usuario_revisao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelos_processo_revisados",
        null=True,
        blank=True,
        verbose_name="Usuário Revisão",
    )

    # ========================================================
    # APROVAÇÃO
    # ========================================================
    data_aprovacao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Aprovação",
    )

    usuario_aprovacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelos_processo_aprovados",
        null=True,
        blank=True,
        verbose_name="Usuário Aprovação",
    )

    # ========================================================
    # AUDITORIA
    # ========================================================
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data Cadastro",
    )

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelos_processo_cadastrados",
        verbose_name="Usuário Cadastro",
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Data Atualização",
    )

    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelos_processo_atualizados",
        null=True,
        blank=True,
        verbose_name="Usuário Atualização",
    )

    # ========================================================
    # METADADOS
    # ========================================================
    class Meta:

        db_table = "arquiteturaprocessos_modelo_processo"

        verbose_name = "Modelo de Processo"

        verbose_name_plural = "Modelos de Processo"

        indexes = [
            models.Index(fields=["titulo"]),
            models.Index(fields=["codigo"]),
            models.Index(fields=["numero_modelo"]),
            models.Index(fields=["estado"]),
        ]

        ordering = [
            "-data_atualizacao",
            "titulo",
            "numero_modelo",
            "versao",
        ]

    # ========================================================
    # SAVE
    # ========================================================
    def save(self, *args, **kwargs):

        try:
            old = ModeloProcesso.objects.get(pk=self.pk)

        except ModeloProcesso.DoesNotExist:
            old = None

        super().save(*args, **kwargs)

        # ====================================================
        # REMOVE PDF ANTIGO
        # ====================================================
        if (
                old
                and old.documento_modelo_processo
                and old.documento_modelo_processo != self.documento_modelo_processo
        ):
            if hasattr(old.documento_modelo_processo, "path"):
                old_path = old.documento_modelo_processo.path
                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass

    # ========================================================
    # STRING
    # ========================================================
    def __str__(self):

        codigo = self.codigo or "---"

        numero = self.numero_modelo or "---"

        versao = self.versao or "--"

        return f"{self.titulo} | {codigo} | {numero} | {versao}"

# ============================================================
# UPLOAD DE ARQUIVO DE NORMA DE PROCEDIMENTO
# ============================================================
def norma_procedimento_upload_to(instance, filename):
    """
    Gera caminho seguro para upload de documentos
    de Norma de Procedimento.

    - Remove acentos
    - Remove caracteres especiais
    - Substitui espaços por _
    - Mantém extensão minúscula
    - Garante unicidade com UUID
    """

    nome, ext = os.path.splitext(filename)

    ext = ext.lower()

    nome = (
        unicodedata
        .normalize("NFKD", nome)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    nome = re.sub(
        r"[^\w\-_.]",
        "_",
        nome
    )

    if not nome:
        nome = "norma_procedimento"

    novo_nome = (
        f"{nome}_{uuid4().hex[:8]}{ext}"
    )

    return (
        f"normaprocedimento/{novo_nome}"
    )


# ============================================================
# NORMA DE PROCEDIMENTO
# ============================================================
class NormaProcedimento(models.Model):

    # ========================================================
    # STATUS
    # ========================================================
    STATUS_ELABORADO = "ELABORADO"
    STATUS_REVISADO = "REVISADO"
    STATUS_APROVADO = "APROVADO"
    STATUS_PRESCRITO = "PRESCRITO"

    STATUS_CHOICES = [
        (STATUS_ELABORADO, "Elaborado"),
        (STATUS_REVISADO, "Revisado"),
        (STATUS_APROVADO, "Aprovado"),
        (STATUS_PRESCRITO, "Prescrito"),
    ]

    # ========================================================
    # UUID
    # ========================================================
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # ========================================================
    # IDENTIFICAÇÃO
    # ========================================================
    titulo = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Título",
    )

    sistema = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Sistema",
    )

    sigla_sistema = models.CharField(
        max_length=20,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9.\-_/]+$",
                message=(
                    "Utilize apenas letras "
                    "maiúsculas, números e . - _ /"
                ),
            )
        ],
        verbose_name="Sigla Sistema",
    )

    numero_norma = models.CharField(
        max_length=4,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r"^(?!0000)\d{4}$",
                message="Informe no formato 0001.",
            )
        ],
        verbose_name="Nr. Norma",
    )

    versao = models.CharField(
        max_length=4,
        db_index=True,
        default="0001",
        validators=[
            RegexValidator(
                regex=r"^(?!0000)\d{4}$",
                message="Informe a versão no formato 0001.",
            )
        ],
        verbose_name="Versão",
    )

    emitente = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Emitente",
    )

    tema = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Tema",
    )

    estado = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ELABORADO,
        db_index=True,
        verbose_name="Estado",
    )

    # ========================================================
    # ELABORAÇÃO
    # ========================================================
    data_elaboracao = models.DateField(
        verbose_name="Data Elaboração",
    )

    # ========================================================
    # APROVAÇÃO
    # ========================================================
    portaria_aprovacao = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Portaria Aprovação",
    )

    data_aprovacao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Aprovação",
    )

    # ========================================================
    # VIGÊNCIA
    # ========================================================
    vigencia_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name="Início Vigência",
    )

    vigencia_fim = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fim Vigência",
    )

    # ========================================================
    # DOCUMENTAÇÃO
    # ========================================================
    documento_norma_procedimento = models.FileField(
        upload_to=norma_procedimento_upload_to,
        max_length=500,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                ["pdf"]
            )
        ],
        verbose_name="Documento Norma de Procedimento",
    )

    link_documento_externo = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Link Documento Externo",
    )

    # ========================================================
    # ELABORAÇÃO
    # ========================================================
    usuario_elaboracao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="normas_elaboradas",
        verbose_name="Usuário Elaboração",
    )

    # ========================================================
    # REVISÃO
    # ========================================================
    data_revisao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Revisão",
    )

    usuario_revisao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="normas_revisadas",
        null=True,
        blank=True,
        verbose_name="Usuário Revisão",
    )

    # ========================================================
    # APROVAÇÃO
    # ========================================================
    usuario_aprovacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="normas_aprovadas",
        null=True,
        blank=True,
        verbose_name="Usuário Aprovação",
    )

    # ========================================================
    # AUDITORIA
    # ========================================================
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data Cadastro",
    )

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="normas_criadas",
        verbose_name="Usuário Cadastro",
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Data Atualização",
    )

    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="normas_atualizadas",
        null=True,
        blank=True,
        verbose_name="Usuário Atualização",
    )

    # ========================================================
    # META
    # ========================================================
    class Meta:

        db_table = (
            "arquiteturaprocessos_norma_procedimento"
        )

        verbose_name = (
            "Norma de Procedimento"
        )

        verbose_name_plural = (
            "Normas de Procedimento"
        )

        indexes = [
            models.Index(fields=["titulo"]),
            models.Index(fields=["sistema"]),
            models.Index(fields=["sigla_sistema"]),
            models.Index(fields=["numero_norma"]),
            models.Index(fields=["tema"]),
            models.Index(fields=["estado"]),
        ]

        ordering = [
            "-data_atualizacao",
            "titulo",
            "numero_norma",
            "versao",
        ]

    # ========================================================
    # SAVE
    # ========================================================
    def save(self, *args, **kwargs):

        try:
            old = (
                NormaProcedimento.objects
                .get(pk=self.pk)
            )

        except NormaProcedimento.DoesNotExist:
            old = None

        super().save(*args, **kwargs)

        # ====================================================
        # REMOVE PDF ANTIGO
        # ====================================================
        if (
            old
            and old.documento_norma_procedimento
            and old.documento_norma_procedimento
            != self.documento_norma_procedimento
        ):
            if hasattr(
                old.documento_norma_procedimento,
                "path"
            ):
                old_path = (
                    old
                    .documento_norma_procedimento
                    .path
                )

                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)

                    except OSError:
                        pass

    # ========================================================
    # STRING
    # ========================================================
    def __str__(self):

        numero = (
            self.numero_norma
            or "---"
        )

        versao = (
            self.versao
            or "--"
        )

        return (
            f"{self.titulo} | "
            f"{self.sigla_sistema} | "
            f"{numero} | "
            f"{versao}"
        )

# ============================================================
# Contatos Seger - Area Responsável
# ============================================================
class ContatoAreaSeger(models.Model):

    ORIGEM_CHOICES = [
        ("SEGER_SITE", "Importação SEGER"),
        ("MANUAL", "Cadastro Manual"),
    ]

    nome_area = models.CharField("Nome da Área", max_length=255, unique=True)
    titular = models.CharField("Titular", max_length=255, blank=True, null=True)
    telefone = models.CharField("Telefone(s)", max_length=255, blank=True, null=True)
    email = models.EmailField("E-mail", blank=True, null=True)

    ativo = models.BooleanField(default=True)

    origem = models.CharField(
        "Origem dos dados",
        max_length=20,
        choices=ORIGEM_CHOICES,
        default="SEGER_SITE"
    )

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='areasresponsaveis_criados',
        null=True,  # 👈 IMPORTANTE PRA MIGRATION
        blank=True
    )

    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='areasresponsaveis_atualizados',
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", null=True, blank=True)

    class Meta:
        verbose_name = "Contato Área SEGER"
        verbose_name_plural = "Contatos Área SEGER"
        ordering = ["nome_area"]

    def __str__(self):
        return self.nome_area or "Área sem nome"

    def __repr__(self):
        return f"<ContatoAreaSeger nome_area={self.nome_area}>"

# ============================================================
# Processos a Mapear
# ============================================================
class ProcessoMapear(models.Model):

    TIPO_PROCESSO = "processo"
    TIPO_SUBPROCESSO = "subprocesso"
    TIPO_OUTRO = "outro"

    TIPO_CHOICES = (
        (TIPO_PROCESSO, "Processo"),
        (TIPO_SUBPROCESSO, "Subprocesso"),
        (TIPO_OUTRO, "Outro"),
    )

    STATUS_ATIVO = "ativo"
    STATUS_FINALIZADO = "finalizado"

    STATUS_CHOICES = [
        (STATUS_ATIVO, "Ativo"),
        (STATUS_FINALIZADO, "Finalizado"),
    ]

    nome = models.CharField(max_length=500)

    gestor = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=200, blank=True)
    telefone = models.CharField(max_length=100, blank=True)

    objetivo = models.TextField()
    observacao = models.TextField(blank=True)

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(null=True, blank=True)

    # 🔥 FK USANDO COLUNA EXISTENTE (NÃO PERDE DADOS)
    area_responsavel = models.ForeignKey(
        ContatoAreaSeger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos_mapear"
    )

    classificacao = models.ForeignKey(
        'Classificacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    macroprocesso_nivel1 = models.ForeignKey(
        'MacroprocessoNivel1',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    macroprocesso_nivel2 = models.ForeignKey(
        'MacroprocessoNivel2',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    parent = models.ForeignKey(
        'Processo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subprocessos_processomapear'
    )

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='processosmapear_criados'
    )

    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='processosmapear_atualizados',
        null=True,
        blank=True
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_PROCESSO,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ATIVO
    )

    class Meta:
        ordering = ['-data_criacao']

    def validar_para_iniciar(self):
        erros = []

        if not self.nome or not self.nome.strip():
            erros.append("Nome do Processo/Subprocesso/Outro é obrigatório.")

        if not self.classificacao:
            erros.append("Classificação é obrigatória.")

        # 🔥 MACROPROCESSO
        if self.macroprocesso_nivel2:
            if not self.macroprocesso_nivel1:
                erros.append("Macroprocesso Nível 1 é obrigatório quando Macroprocesso Nível 2 for informado.")
            elif self.macroprocesso_nivel2.macroprocesso_nivel1_id != self.macroprocesso_nivel1_id:
                erros.append("Macroprocesso Nível 2 não pertence ao Macroprocesso Nível 1 informado.")

        # 🔥 TIPO
        if self.tipo not in [c[0] for c in self.TIPO_CHOICES]:
            erros.append("Tipo inválido.")

        # 🔥 SUBPROCESSO
        if self.tipo == self.TIPO_SUBPROCESSO:
            if not self.parent:
                erros.append("Subprocesso deve estar vinculado a um Processo.")
            elif not Processo.objects.filter(pk=self.parent_id).exists():
                erros.append("O processo pai não existe mais.")

        if not self.objetivo or not self.objetivo.strip():
            erros.append("Objetivo é obrigatório.")

        # 🔥 FK
        if not self.area_responsavel:
            erros.append("Área Responsável é obrigatória.")

        if not self.gestor or not self.gestor.strip():
            erros.append("Gestor é obrigatório.")

        if not self.telefone or not self.telefone.strip():
            erros.append("Telefone é obrigatório.")

        # 🔥 EMAIL
        email = (self.email or "").strip()

        if not email:
            erros.append("E-mail é obrigatório.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                erros.append("E-mail inválido.")

        return erros

    def __str__(self):
        return self.nome

# ============================================================
# PROCESSO / SUBPROCESSO
# ============================================================
class Processo(models.Model):

    nome = models.CharField(max_length=500)
    gestor = models.CharField(max_length=150)
    email = models.EmailField(max_length=200, null=True, blank=True)
    telefone = models.CharField(max_length=100, blank=True)
    objetivo = models.TextField()
    observacao = models.TextField(null=True, blank=True)

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(null=True, blank=True)

    classificacao = models.ForeignKey(
        "Classificacao",
        on_delete=models.PROTECT,
        related_name="processos"
    )

    macroprocesso_nivel1 = models.ForeignKey(
        "MacroprocessoNivel1",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="macro_nivel1"
    )

    macroprocesso_nivel2 = models.ForeignKey(
        "MacroprocessoNivel2",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="macro_nivel2"
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="subprocessos"
    )

    # 🔥 FK USANDO COLUNA EXISTENTE
    area_responsavel = models.ForeignKey(
        ContatoAreaSeger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos"
    )

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="processos_cadastrados"
    )

    usuario_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="processos_atualizados"
    )

    versao_processo = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
        blank=True,
        null=True
    )

    data_conclusao = models.DateTimeField(blank=True, null=True)

    usuario_conclusao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos_concluidos"
    )

    @property
    def status(self):
        if self.data_conclusao:
            return "concluido"

        if self.documentos.exists():
            return "ativo"

        return "iniciado"

    @property
    def status_label(self):
        return {
            "iniciado": "Iniciado",
            "ativo": "Ativo",
            "concluido": "Concluído"
        }.get(self.status)

    @property
    def status_css(self):
        return {
            "iniciado": "bg-orange-200 text-orange-900",
            "ativo": "bg-green-200 text-green-900",
            "concluido": "bg-red-200 text-red-900"
        }.get(self.status, "")

    def __str__(self):
        return self.nome

    def clean(self):
        # 🔥 ÁREA
        if self.area_responsavel and not self.area_responsavel.ativo:
            raise ValidationError("Área Responsável inválida ou inativa.")

        # 🔥 HIERARQUIA
        if self.parent:
            if self.parent == self:
                raise ValidationError("Processo não pode ser pai de si mesmo.")

            if self.parent.parent_id:
                raise ValidationError("Subprocesso não pode ter outro subprocesso como pai.")

        # 🔥 MACROPROCESSO
        if self.macroprocesso_nivel2 and self.macroprocesso_nivel1:
            if self.macroprocesso_nivel2.macroprocesso_nivel1_id != self.macroprocesso_nivel1_id:
                raise ValidationError("Macroprocesso Nível 2 não pertence ao Macroprocesso Nível 1.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# ============================================================
# PROCESSO – DOCUMENTO (1 Processo → N Modelagens)
# ============================================================
class ProcessoDocumento(models.Model):
    processo = models.ForeignKey(
        "Processo",
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Processo"
    )

    modelagem_processo = models.ForeignKey(
        "ModelagemProcesso",
        on_delete=models.PROTECT,
        related_name="processo_documentos",
        verbose_name="Modelagem de Processo"
    )

    class Meta:
        db_table = "arquiteturaprocessos_processodocumento"
        verbose_name = "Documento do Processo"
        verbose_name_plural = "Documentos do Processo"
        ordering = ["modelagem_processo__tipo_documento", "modelagem_processo__titulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["processo", "modelagem_processo"],
                name="unique_modelagem_por_processo"
            )
        ]

    def __str__(self):
        mp = self.modelagem_processo
        return f"{mp.tipo_documento.nome if mp else 'Documento'} – {mp.titulo if mp else ''}"

