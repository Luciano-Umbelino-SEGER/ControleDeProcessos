import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.urls import reverse

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
    ddd = models.CharField(max_length=3, null=True, blank=True)
    numero = models.CharField(max_length=9, null=True, blank=True)
    ramal = models.CharField(max_length=5, null=True, blank=True)

    @property
    def numero_formatado(self):
        """
        Retorna o telefone formatado no padrão brasileiro:
        - Fixo (8 dígitos): (DD) XXXX-XXXX
        - Celular (9 dígitos): (DD) XXXXX-XXXX
        """
        ramal_str = f" Ramal: {self.ramal}" if self.ramal else ""

        if len(self.numero) == 9:  # celular
            return f"({self.ddd}) {self.numero[:5]}-{self.numero[5:]}{ramal_str}"
        elif len(self.numero) == 8:  # fixo
            return f"({self.ddd}) {self.numero[:4]}-{self.numero[4:]}{ramal_str}"
        else:
            return f"({self.ddd}) {self.numero}{ramal_str}"  # caso número inválido

    def __str__(self):
        return str(f"{self.ddd} - {self.numero} - {self.ramal}")

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

class Classificacao(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(max_length=500)

    def __str__(self):
        return self.nome

class MacroprocessoNivel1(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(max_length=500)
    classificacao = models.ForeignKey(
        Classificacao,
        on_delete=models.PROTECT,  # Impede exclusão se houver Macroprocessos associados
        related_name='macroprocessos_nivel1'
    )

    def __str__(self):
        return f"{self.nome}"


class MacroprocessoNivel2(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(max_length=500)
    macroprocesso_nivel1 = models.ForeignKey(
        MacroprocessoNivel1,
        on_delete=models.PROTECT,
        related_name='macroprocessos_nivel2',
        null=False,
        blank=False
    )

    def __str__(self):
        return f"{self.nome}"

class NormaProcedimento(models.Model):
    # PK padrão (BigAutoField) é criada automaticamente
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    # --- Campos que compõem a identificação ---
    nome = models.CharField(
        max_length=200,
        verbose_name="Nome",
        default="NORMA DE PROCEDIMENTO"
    )

    codigo = models.CharField(
        max_length=10,
        db_index=True,
        verbose_name="Código",
        validators=[RegexValidator(r"^[A-Za-z0-9.\-_/]+$", "Use apenas letras, números e . - _ /")],
        default="SRH"
    )

    sequencial = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        verbose_name="Sequencial",
        help_text="Número sequencial (1 a 999)."
    )

    versao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        verbose_name="Versão",
        help_text="Versão (1 a 99)."
    )

    tema = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Tema"
    )

    # --- Demais campos do cadastro ---
    emitente = models.CharField(max_length=150, db_index=True, verbose_name="Emitente")
    sistema = models.CharField(max_length=100, db_index=True, verbose_name="Sistema")

    data_elaboracao = models.DateField(null=True, blank=True, verbose_name="Data de Elaboração")
    portaria_aprovacao = models.CharField(max_length=150, blank=True, verbose_name="Portaria de Aprovação")
    data_aprovacao = models.DateField(null=True, blank=True, verbose_name="Data de Aprovação")
    vigencia_inicio = models.DateField(null=True, blank=True, verbose_name="Início da Vigência")
    vigencia_fim = models.DateField(null=True, blank=True, verbose_name="Fim da Vigência")

    link = models.URLField(max_length=500, blank=True, verbose_name="Link")

    data_cadastro = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="Data de Cadastro")
    data_atualizacao = models.DateTimeField(auto_now=True, editable=False, verbose_name="Data de Atualização")

    usuario = models.ForeignKey(
        "Usuario",
        on_delete=models.PROTECT,
        related_name="normas_procedimento_criadas",
        verbose_name="Usuário"
    )

    usuario_atualizacao = models.ForeignKey(
        "Usuario",
        related_name="normas_procedimento_atualizadas",
        on_delete=models.SET_NULL,  # trocado de PROTECT para SET_NULL
        null=True,
        blank=True,
        verbose_name="Usuário (última atualização)"
    )

    class Meta:
        db_table = "arquiteturaprocessos_norma_procedimento"
        managed = True
        verbose_name = "Norma de Procedimento"
        verbose_name_plural = "Normas de Procedimento"
        # Ordenação coerente com a "identificação interna"
        ordering = ["nome", "codigo", "sequencial", "versao", "tema"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo", "sequencial", "versao"],
                name="uq_norma_proc_codigo_seq_versao"
            ),
            # (Opcional) Checks no BD — defesa em profundidade:
            # models.CheckConstraint(check=models.Q(sequencial__gte=1, sequencial__lte=999), name="ck_np_seq_range"),
            # models.CheckConstraint(check=models.Q(versao__gte=1, versao__lte=99), name="ck_np_versao_range"),
        ]
        indexes = [
            models.Index(fields=["nome"], name="idx_np_nome"),
            models.Index(fields=["tema"], name="idx_np_tema"),
            models.Index(fields=["sistema"], name="idx_np_sistema"),
            models.Index(fields=["emitente"], name="idx_np_emitente"),  # adicionado
        ]

    # ===== Helpers de formatação com zero à esquerda =====
    def sequencial_fmt(self) -> str:
        return f"{self.sequencial:03d}"  # 1 -> "001"

    def versao_fmt(self) -> str:
        return f"{self.versao:02d}"      # 2 -> "02"

    @property
    def identificacao_ext(self) -> str:
        """
        Ex.: "SRH Nr001 - Versão 01 - Concessão de Diárias"
        """
        return f"{self.codigo} Nr{self.sequencial_fmt()} - Versão {self.versao_fmt()} - {self.tema}"

    @property
    def identificacao_int(self) -> str:
        """
        Ex.: "NORMA DE PROCEDIMENTO - SRH-001 - Versão 01 - Concessão de Diárias"
        """
        return f"{self.nome} - {self.codigo}-{self.sequencial_fmt()} - Versão {self.versao_fmt()} - {self.tema}"

    def __str__(self):
        # Mantenha curto para admin/logs
        return self.identificacao_int

    # def get_absolute_url(self):
    #     # Ajuste o namespace conforme suas urls.py
    #     return reverse("arquiteturaprocessos:detalhar_norma_procedimento", args=[self.pk])

    # Validações de datas
    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.vigencia_inicio and self.vigencia_fim and self.vigencia_fim < self.vigencia_inicio:
            errors["vigencia_fim"] = "Fim da vigência não pode ser anterior ao início."

        if self.data_elaboracao and self.data_aprovacao and self.data_aprovacao < self.data_elaboracao:
            errors["data_aprovacao"] = "A aprovação não pode ser anterior à elaboração."

        # Se realmente quiser forçar que a última atualização não seja antes da elaboração:
        if self.data_elaboracao and self.data_atualizacao and self.data_atualizacao < self.data_elaboracao:
            errors["data_atualizacao"] = "A atualização não pode ser anterior à elaboração."

        if self.vigencia_fim and self.data_atualizacao and self.data_atualizacao > self.vigencia_fim:
            errors["data_atualizacao"] = "A atualização não pode ser posterior ao fim da vigência."

        if errors:
            raise ValidationError(errors)

    # Normalizações leves (opcional)
    def save(self, *args, **kwargs):
        if self.codigo:
            self.codigo = self.codigo.strip().upper()
        if self.emitente:
            self.emitente = self.emitente.strip()
        if self.sistema:
            self.sistema = self.sistema.strip()
        if self.tema:
            self.tema = self.tema.strip()
        super().save(*args, **kwargs)

    # Helper útil
    def is_vigente(self, on_date=None) -> bool:
        ref = on_date or timezone.localdate()
        if not self.vigencia_inicio and not self.vigencia_fim:
            return False
        if self.vigencia_inicio and ref < self.vigencia_inicio:
            return False
        if self.vigencia_fim and ref > self.vigencia_fim:
            return False
        return True

class ArquiteturaProcesso(models.Model):
    #classificacao = models.CharField(max_length=30, choices=LSTA_CLASSIFICACAO)
    macroprocesso_nivel1 = models.ForeignKey("MacroprocessoNivel1", related_name="arquiteturas_nivel1", null=True, blank=True,
                                             on_delete=models.SET_NULL)
    macroprocesso_nivel2 = models.ForeignKey("MacroprocessoNivel2", related_name="arquiteturas_nivel2", null=True, blank=True,
                                             on_delete=models.SET_NULL)


class LogAcoes(models.Model):
    data_registro = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE)
    area = models.CharField(max_length=100)
    acao = models.CharField(max_length=100)  # Ex: "Criação", "Atualização", "Exclusão"
    descricao_acao = models.TextField(max_length=500)
    modelo_afetado = models.CharField(max_length=100, null=True, blank=True)  # Ex: "Norma", "Usuario"
    id_referencia = models.IntegerField(null=True, blank=True)  # ID do objeto afetado

