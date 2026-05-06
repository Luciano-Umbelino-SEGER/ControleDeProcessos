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

