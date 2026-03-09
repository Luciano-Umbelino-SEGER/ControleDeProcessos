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


class MacroprocessoNivel1(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField()
    classificacao = models.ForeignKey("Classificacao", on_delete=models.PROTECT)

    def __str__(self):
        return self.nome


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
#Aqui 1
# ============================================================
# Processos a Mapear
# ============================================================
class ProcessoMapear(models.Model):

    TIPO_PROCESSO = "processo"
    TIPO_SUBPROCESSO = "subprocesso"

    TIPO_CHOICES = (
        (TIPO_PROCESSO, "Processo"),
        (TIPO_SUBPROCESSO, "Subprocesso"),
    )

    nome = models.CharField(max_length=100)

    gestor = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=200, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    objetivo = models.TextField()
    observacao = models.TextField(blank=True)

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(null=True, blank=True)

    area_responsavel = models.CharField(max_length=100)

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
        default=TIPO_PROCESSO
    )

    class Meta:
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['nome']),
            models.Index(fields=['data_criacao']),
            models.Index(fields=['tipo']),
            models.Index(fields=['tipo', 'macroprocesso_nivel1']),
            models.Index(fields=['tipo', 'macroprocesso_nivel2']),
        ]

    def validar_para_iniciar(self):
        erros = []

        if not self.nome or not self.nome.strip():
            erros.append("Nome do Processo/Subprocesso é obrigatório.")

        if not self.classificacao:
            erros.append("Classificação é obrigatória.")

        if self.macroprocesso_nivel2 and not self.macroprocesso_nivel1:
            erros.append("Macroprocesso Nível 1 é obrigatório quando Macroprocesso Nível 2 for informado.")

        if self.tipo not in dict(self.TIPO_CHOICES):
            erros.append("Tipo de processo inválido.")

        if self.tipo == self.TIPO_SUBPROCESSO and not self.parent:
            erros.append("Subprocesso deve estar vinculado a um Processo.")

        if not self.objetivo or not self.objetivo.strip():
            erros.append("Objetivo é obrigatório.")

        if not self.area_responsavel or not self.area_responsavel.strip():
            erros.append("Área Responsável é obrigatória.")

        if not self.gestor or not self.gestor.strip():
            erros.append("Gestor é obrigatório.")

        if not self.telefone or not self.telefone.strip():
            erros.append("Telefone é obrigatório.")

        if not self.email or not self.email.strip():
            erros.append("E-mail é obrigatório.")
        else:
            try:
                validate_email(self.email)
            except ValidationError:
                erros.append("E-mail inválido.")

        return erros

    def __str__(self):
        return self.nome

# ============================================================
# PROCESSO / SUBPROCESSO
# ============================================================
class Processo(models.Model):
    nome = models.CharField(max_length=200)
    gestor = models.CharField(max_length=150)
    email = models.EmailField(max_length=200, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
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

    area_responsavel = models.CharField(max_length=100, null=True, blank=True)

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

    versao_processo = models.CharField(
        "Versão do Processo",
        max_length=10,
        blank=True,
        null=True
    )

    data_conclusao = models.DateTimeField(
        "Data de Conclusão do Processo",
        blank=True,
        null=True
    )

    usuario_conclusao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos_concluidos",
        verbose_name="Usuário Conclusão"
    )

    @property
    def status(self):

        # 1️⃣ Processo concluído tem prioridade
        if self.data_conclusao:
            return "concluido"

        # 2️⃣ Processo ativo se tiver pelo menos um documento associado
        if self.documentos.exists():
            return "ativo"

        # 3️⃣ Caso contrário permanece iniciado
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

    @property
    def pode_concluir(self):

        for sub in self.subprocessos.all():
            if sub.status == "iniciado":
                return False

        return True

    class Meta:
        db_table = "arquiteturaprocessos_processo"
        ordering = ["nome"]
        verbose_name = "Processo"
        verbose_name_plural = "Processos"

    def __str__(self):
        return self.nome

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
