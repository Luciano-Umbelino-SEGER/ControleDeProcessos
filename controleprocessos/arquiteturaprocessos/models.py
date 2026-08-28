import unicodedata
import re
import os
import uuid
from uuid import uuid4
from datetime import datetime
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
# GERAÇÃO DO NOME DA IMAGEM DA CLASSIFICAÇÃO / MACROPROCESSO
# ============================================================
def nome_imagem_classificacao(instance, filename):
    """
    Gera o nome físico da imagem da Classificação.

    Formato:
        Nome_Normalizado_YYYYMMDD_HHMMSS.ext
    """
    nome = instance.nome.strip()

    # Remove acentos
    nome_normalizado = slugify(nome, allow_unicode=False)

    # Substitui hífens por underscore
    nome_normalizado = nome_normalizado.replace("-", "_")

    # Remove qualquer caractere que eventualmente tenha permanecido
    nome_normalizado = re.sub(
        r"[^a-zA-Z0-9_]",
        "",
        nome_normalizado
    )

    # Extensão original
    extensao = filename.rsplit(".", 1)[-1].lower()

    # Data e hora
    agora = datetime.now()

    data_hora = agora.strftime("%Y%m%d_%H%M%S")

    return (
        f"classificacoes/"
        f"{nome_normalizado}_{data_hora}.{extensao}"
    )

# ============================================================
# CLASSIFICAÇÃO / MACROPROCESSOS
# ============================================================
class Classificacao(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    imagem = models.ImageField(
        upload_to=nome_imagem_classificacao,
        max_length=500,
        blank=True,
        null=True,
    )
    imagem_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        editable=False,
    )

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
# SISTEMAS UECI
# ============================================================
class SistemasUECI(models.Model):

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    sigla_sistema = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Sigla'
    )

    nome_sistema = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Nome do Sistema'
    )

    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descrição'
    )

    class Meta:
        verbose_name = 'Sistema UECI'
        verbose_name_plural = 'Sistemas UECI'
        ordering = ['nome_sistema']

    @property
    def sistema_completo(self):
        if self.sigla_sistema:
            return f"{self.sigla_sistema} - {self.nome_sistema}"
        return self.nome_sistema

    def __str__(self):
        return self.sistema_completo

# ============================================================
# TIPOS DE DOCUMENTOS
# ============================================================
class TiposDocumento(models.Model):
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome"
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name="Slug"
    )

    contexto = models.CharField(
        max_length=15,
        db_index=True,
        default="processo",
        verbose_name="Contexto"
    )

    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )

    class Meta:
        db_table = "arquiteturaprocessos_tiposdocumento"
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documento"

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
    # Compatibilidade histórica:
    # migrations/0001_initial.py referencia esta função, portanto esta função não pode ser
    # excluida por causa da referênncia na migrations/0001_initial.py
    # Não utilizada pela aplicação atual.
    """
    return filename

# ============================================================
# UPLOAD DE ARQUIVO DE NORMA DE PROCEDIMENTO
# ============================================================
def norma_procedimento_upload_to(instance, filename):
    """
    Gera caminho seguro para upload dos documentos de
    Norma de Procedimento.

    Regras:
    - Remove acentos;
    - Remove caracteres especiais;
    - Substitui espaços por "_";
    - Mantém a extensão em minúsculas;
    - Utiliza o UUID do próprio registro;
    - Mantém o nome original do arquivo para facilitar
      sua identificação pelo usuário.
    """

    # ========================================================
    # NOME E EXTENSÃO
    # ========================================================
    nome, ext = os.path.splitext(filename)

    ext = ext.lower()

    # ========================================================
    # REMOVE ACENTOS
    # ========================================================
    nome = (
        unicodedata
        .normalize("NFKD", nome)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    # ========================================================
    # REMOVE CARACTERES INVÁLIDOS
    # ========================================================
    nome = re.sub(
        r"[^\w\-_.]",
        "_",
        nome
    )

    if not nome:
        nome = "norma_procedimento"

    # ========================================================
    # NOME FINAL
    # ========================================================
    novo_nome = (
         f"{nome}_{instance.uuid.hex[:12]}{ext}"
    )

    # ========================================================
    # CAMINHO
    # ========================================================
    return (
        f"normas_procedimento/{novo_nome}"
    )

# ============================================================
# NORMA DE PROCEDIMENTO
# ============================================================
class NormaProcedimento(models.Model):
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
    nome_norma = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Nome da Norma",
    )

    sistema = models.ForeignKey(
        SistemasUECI,
        on_delete=models.PROTECT,
        related_name="normas_procedimento",
        db_column="id_sistema",
        db_index=True,
        verbose_name="Sistema",
    )

    codigo_norma = models.CharField(
        max_length=15,
        db_index=True,
        verbose_name="Código",
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
        max_length=255,
        db_index=True,
        verbose_name="Emitente",
    )

    # ========================================================
    # Datas
    # ========================================================
    data_elaboracao = models.DateField(
        verbose_name="Data Elaboração",
    )

    # ========================================================
    # APROVAÇÃO
    # ========================================================
    portaria_aprovacao = models.CharField(
        max_length=150,
        null=True,
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

    link_documento_norma = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Link Documento Norma de Procedimento",
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
            models.Index(fields=["nome_norma"],name="idx_norma_nome",),
            models.Index(fields=["sistema"],name="idx_norma_sistema",),
            models.Index(fields=["codigo_norma"],name="idx_norma_codigo",),
            models.Index(fields=["emitente"],name="idx_norma_emitente",),
        ]

        ordering = [
            "-data_atualizacao",
            "nome_norma",
            "codigo_norma",
            "versao",
        ]

    # ========================================================
    # SAVE
    # ========================================================
    def save(self, *args, **kwargs):

        old = None

        # ====================================================
        # RECUPERA O REGISTRO ANTIGO APENAS NA EDIÇÃO
        # ====================================================
        if self.pk:
            old = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .first()
            )

        super().save(*args, **kwargs)

        # ====================================================
        # REMOVE PDF ANTIGO
        # ====================================================
        if (
                old
                and old.documento_norma_procedimento
                and old.documento_norma_procedimento != self.documento_norma_procedimento
        ):

            old_path = old.documento_norma_procedimento.path

            if os.path.exists(old_path):

                try:
                    os.remove(old_path)

                except OSError:
                    pass

    # ========================================================
    # DELETE
    # ========================================================
    def delete(self, *args, **kwargs):

        arquivo = self.documento_norma_procedimento

        super().delete(*args, **kwargs)

        if arquivo:

            try:

                if hasattr(arquivo, "path") and os.path.isfile(arquivo.path):
                    os.remove(arquivo.path)

            except OSError:
                pass

    # ========================================================
    # STRING
    # ========================================================
    def __str__(self):

        numero = (
            self.codigo_norma
            or "---"
        )

        versao = (
            self.versao
            or "--"
        )

        return (
            f"{self.nome_norma} | "
            f"{self.sistema} | "
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
# ABRANGÊNCIA
# ============================================================
class AbrangenciaChoices(models.TextChoices):
    GOVES = "GOVES", "GOVES"
    SEGER = "SEGER", "SEGER"
    OUTROS = "OUTROS", "OUTROS"

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

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name="UUID"
    )

    abrangencia = models.CharField(
        max_length=10,
        choices=AbrangenciaChoices.choices,
        default=AbrangenciaChoices.GOVES,
        verbose_name="Abrangência"
    )

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

    usuario_finalizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="processosmapear_finalizados"
    )

    data_finalizacao = models.DateTimeField(
        blank=True,
        null=True
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

        # =========================================
        # NOME
        # =========================================
        if not self.nome or not self.nome.strip():
            erros.append(
                "Nome do Processo/Subprocesso é obrigatório."
            )

        # =========================================
        # ABRANGÊNCIA
        # =========================================
        if not self.abrangencia:
            erros.append(
                "Abrangência é obrigatória."
            )

        # =========================================
        # CLASSIFICAÇÃO
        # =========================================
        if not self.classificacao:
            erros.append(
                "Classificação é obrigatória."
            )

        # =========================================
        # MACROPROCESSO
        # =========================================
        if self.macroprocesso_nivel2:

            if not self.macroprocesso_nivel1:

                erros.append(
                    "Macroprocesso Nível 1 é obrigatório "
                    "quando Macroprocesso Nível 2 for informado."
                )

            elif (
                    self.macroprocesso_nivel2.macroprocesso_nivel1_id
                    != self.macroprocesso_nivel1_id
            ):

                erros.append(
                    "Macroprocesso Nível 2 não pertence "
                    "ao Macroprocesso Nível 1 informado."
                )

        # =========================================
        # TIPO
        # =========================================
        if self.tipo not in [
            c[0] for c in self.TIPO_CHOICES
        ]:
            erros.append("Tipo inválido.")

        # =========================================
        # SUBPROCESSO
        # =========================================
        if self.tipo == self.TIPO_SUBPROCESSO:

            if not self.parent:
                erros.append(
                    "Subprocesso deve estar vinculado a um Processo."
                )

            elif not Processo.objects.filter(
                    pk=self.parent_id
            ).exists():
                erros.append(
                    "O processo pai não existe mais."
                )

        # =========================================
        # OUTRO
        # =========================================
        elif self.tipo == self.TIPO_OUTRO:

            erros.append(
                "Tipo Outro não pode ser iniciado."
            )

        # =========================================
        # OBJETIVO
        # =========================================
        if not self.objetivo or not self.objetivo.strip():
            erros.append(
                "Objetivo é obrigatório."
            )

        # =========================================
        # ÁREA RESPONSÁVEL
        # =========================================
        if not self.area_responsavel:
            erros.append(
                "Área Responsável é obrigatória."
            )

        # =========================================
        # GESTOR
        # =========================================
        if not self.gestor or not self.gestor.strip():
            erros.append(
                "Gestor é obrigatório."
            )

        # =========================================
        # TELEFONE
        # =========================================
        if not self.telefone or not self.telefone.strip():
            erros.append(
                "Telefone é obrigatório."
            )

        # =========================================
        # E-MAIL
        # =========================================
        email = (self.email or "").strip()

        if not email:
            erros.append(
                "E-mail é obrigatório."
            )
        else:
            try:
                validate_email(email)
            except ValidationError:
                erros.append(
                    "E-mail inválido."
                )

        return erros

    def __str__(self):
        return self.nome

# ============================================================
# UPLOAD DE ARQUIVO DE MODELO DE PROCESSO
# ============================================================
def modelo_processo_upload_to(instance, filename):
    """
    Gera caminho seguro para upload dos documentos de
    Modelos de Processo.

    Regras:
    - Remove acentos;
    - Remove caracteres especiais;
    - Substitui espaços por "_";
    - Mantém a extensão em minúsculas;
    - Utiliza o UUID do próprio registro;
    - Mantém o nome original do arquivo para facilitar
      sua identificação pelo usuário.
    """

    # ========================================================
    # NOME E EXTENSÃO
    # ========================================================
    nome, ext = os.path.splitext(filename)

    ext = ext.lower()

    # ========================================================
    # REMOVE ACENTOS
    # ========================================================
    nome = (
        unicodedata
        .normalize("NFKD", nome)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    # ========================================================
    # REMOVE CARACTERES INVÁLIDOS
    # ========================================================
    nome = re.sub(
        r"[^\w\-_.]",
        "_",
        nome
    )

    if not nome:
        nome = "modelo_processo"

    # ========================================================
    # NOME FINAL
    # ========================================================
    novo_nome = (
         f"{nome}_{instance.uuid.hex[:12]}{ext}"
    )

    # ========================================================
    # CAMINHO
    # ========================================================
    return (
        f"modelos_processo/{novo_nome}"
    )

# ============================================================
# PROCESSO / SUBPROCESSO
# ============================================================
class Processo(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name="UUID",
    )

    nome = models.CharField(max_length=500, verbose_name="Nome")
    gestor = models.CharField(max_length=150, verbose_name="Gestor")
    email = models.EmailField(max_length=200, null=True, blank=True, verbose_name="Email")
    telefone = models.CharField(max_length=100, blank=True, verbose_name="Telefone")
    objetivo = models.TextField(verbose_name="Objetivo")

    abrangencia = models.CharField(
        max_length=10,
        choices=AbrangenciaChoices.choices,
        default=AbrangenciaChoices.GOVES,
        verbose_name="Abrangência"
    )

    data_elaboracao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Elaboração"
    )

    data_aprovacao = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Aprovação"
    )

    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")
    data_atualizacao = models.DateTimeField(null=True, blank=True, verbose_name="Data de Atualização")

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

    # ========================================================
    # ÁREA RESPONSÁVEL
    # ========================================================
    area_responsavel = models.ForeignKey(
        ContatoAreaSeger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos"
    )

    versao_processo = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
        blank=True,
        null=True,
        verbose_name="Versão"
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

    link_documento_modelo_processo = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Link Documento Modelo de Processo",
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

        if (
                self.documento_modelo_processo
                or self.link_documento_modelo_processo
                or ProcessoDocumento.objects.filter(processo=self).exists()
        ):
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

    @property
    def eh_processo(self):
        return self.parent_id is None

    @property
    def eh_subprocesso(self):
        return self.parent_id is not None

    def __str__(self):
        return self.nome

    @property
    def pode_concluir(self):

        for sub in self.subprocessos.all():
            if sub.status == "iniciado":
                return False

        return True

    # ========================================================
    # META
    # ========================================================
    class Meta:

        db_table = (
            "arquiteturaprocessos_processo"
        )
        verbose_name = (
            "Processo"
        )

        verbose_name_plural = (
            "Processos"
        )

        indexes = [
            models.Index(
                fields=["nome"],
                name="idx_processo_nome",
            ),
            models.Index(
                fields=["gestor"],
                name="idx_processo_gestor",
            ),
        ]

        ordering = [
            "-data_atualizacao",
            "-data_criacao",
            "nome",
        ]

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

    # ========================================================
    # AUXILIAR – Estrutura padronizada de erros
    # ========================================================
    def _erro(self, campo, label, mensagem):
        return {
            "campo": campo,
            "label": label,
            "mensagem": mensagem,
        }

    # ========================================================
    # VALIDAÇÃO PARA INICIAR
    # ========================================================
    def validar_para_iniciar(self):

        erros = []

        erros.extend(
            self._validar_identificacao()
        )

        erros.extend(
            self._validar_informacoes_processo()
        )

        return erros

    # ========================================================
    # IDENTIFICAÇÃO DO PROCESSO
    # ========================================================
    def _validar_identificacao(self):

        erros = []

        # =====================================================
        # PROCESSO / SUBPROCESSO
        # =====================================================
        if self.tipo == "subprocesso":

            # Processo Pai obrigatório
            if not self.parent_id:
                erros.append(
                    self._erro(
                        "parent",
                        "Processo Pai",
                        "Selecione o Processo ao qual este Subprocesso pertence."
                    )
                )

            # Processo Pai deve ser um Processo
            elif self.parent.parent_id:
                erros.append(
                    self._erro(
                        "parent",
                        "Processo Pai",
                        "Um Subprocesso somente pode possuir um Processo como pai."
                    )
                )

            # Nome do Subprocesso obrigatório
            if not (self.nome or "").strip():
                erros.append(
                    self._erro(
                        "nome",
                        "Nome do Subprocesso",
                        "Informe o nome do Subprocesso."
                    )
                )

        elif self.tipo == "processo":

            # Nome do Processo obrigatório
            if not (self.nome or "").strip():
                erros.append(
                    self._erro(
                        "nome",
                        "Nome do Processo",
                        "Informe o nome do Processo."
                    )
                )

        # =====================================================
        # DATA DE APROVAÇÃO
        # =====================================================
        if (self.data_elaboracao
            and self.data_aprovacao
            and self.data_aprovacao < self.data_elaboracao):
            erros.append(
                self._erro(
                    "data_aprovacao",
                    "Data de Aprovação",
                    "A Data de Aprovação não pode ser anterior à Data de Elaboração."
                )
            )


        # =====================================================
        # VERSÃO
        # =====================================================
        if self.versao_processo is None:
            erros.append(
                self._erro(
                    "versao_processo",
                    "Versão",
                    "Informe a versão do Processo."
                )
            )

        # =====================================================
        # CLASSIFICAÇÃO
        # =====================================================
        if not self.classificacao_id:
            erros.append(
                self._erro(
                    "classificacao",
                    "Classificação",
                    "Selecione a Classificação."
                )
            )

        # =====================================================
        # MACROPROCESSO NÍVEL 1
        # =====================================================
        if not self.macroprocesso_nivel1_id:
            erros.append(
                self._erro(
                    "macroprocesso_nivel1",
                    "Macroprocesso Nível 1",
                    "Selecione o Macroprocesso Nível 1."
                )
            )

        # =====================================================
        # MACROPROCESSO NÍVEL 2
        # =====================================================
        if (
                self.macroprocesso_nivel1
                and self.macroprocesso_nivel2
                and self.macroprocesso_nivel2.macroprocesso_nivel1_id != self.macroprocesso_nivel1_id
        ):
            erros.append(
                self._erro(
                    "macroprocesso_nivel2",
                    "Macroprocesso Nível 2",
                    "O Macroprocesso Nível 2 não pertence ao Macroprocesso Nível 1 informado."
                )
            )

        return erros

    # ========================================================
    # INFORMAÇÕES DO PROCESSO
    # ========================================================
    def _validar_informacoes_processo(self):

        erros = []

        # =====================================================
        # OBJETIVO
        # =====================================================
        if not (self.objetivo or "").strip():
            erros.append(
                self._erro(
                    "objetivo",
                    "Objetivo",
                    "Informe o Objetivo do Processo."
                )
            )

        # =====================================================
        # ÁREA RESPONSÁVEL
        # =====================================================
        if not self.area_responsavel_id:
            erros.append(
                self._erro(
                    "area_responsavel",
                    "Área Responsável",
                    "Selecione a Área Responsável."
                )
            )

        # =====================================================
        # GESTOR
        # =====================================================
        if not (self.gestor or "").strip():
            erros.append(
                self._erro(
                    "gestor",
                    "Gestor",
                    "Informe o Gestor."
                )
            )

        # =====================================================
        # TELEFONE
        # =====================================================
        if not (self.telefone or "").strip():
            erros.append(
                self._erro(
                    "telefone",
                    "Telefone",
                    "Informe o Telefone."
                )
            )

        # =====================================================
        # E-MAIL
        # =====================================================
        email = (self.email or "").strip()

        if not email:
            erros.append(
                self._erro(
                    "email",
                    "E-mail",
                    "Informe o E-mail."
                )
            )
        else:
            try:
                validate_email(email)
            except ValidationError:
                erros.append(
                    self._erro(
                        "email",
                        "E-mail",
                        "Informe um E-mail válido."
                    )
                )

        return erros

    def save(self, *args, **kwargs):

        old = None

        if self.pk:
            old = Processo.objects.filter(pk=self.pk).first()

        self.full_clean()
        super().save(*args, **kwargs)

        # ====================================================
        # REMOVE PDF ANTIGO
        # ====================================================
        if (
                old
                and old.documento_modelo_processo
                and old.documento_modelo_processo != self.documento_modelo_processo
        ):

            old_path = old.documento_modelo_processo.path

            if os.path.exists(old_path):

                try:
                    os.remove(old_path)

                except OSError:
                    pass

# ============================================================
# PROCESSO – NORMA DE PROCEDIMENTO
# (Relaciona um Processo a uma ou mais Normas de Procedimento)
# ============================================================
class ProcessoDocumento(models.Model):

    processo = models.ForeignKey(
        "Processo",
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Processo",
    )

    norma_procedimento = models.ForeignKey(
        "NormaProcedimento",
        on_delete=models.PROTECT,
        related_name="processos",
        verbose_name="Norma de Procedimento",
    )

    class Meta:

        db_table = "arquiteturaprocessos_processodocumento"

        verbose_name = "Norma de Procedimento do Processo"

        verbose_name_plural = "Normas de Procedimento do Processo"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "processo",
                    "norma_procedimento",
                ],
                name="unique_norma_por_processo",
            )
        ]

    def __str__(self):
        return (
            f"{self.processo} - {self.norma_procedimento}"
        )

