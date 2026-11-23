from django.core.serializers.json import DjangoJSONEncoder
import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.contrib.auth.signals import user_logged_in, user_logged_out

from .models import LogAcaoSistema
from auditoria.middleware import get_current_user
from .utils import gerar_diff, obter_usuario_log
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from arquiteturaprocessos.utils.cpf import mascarar_cpf

# 🔥 MODELOS QUE NÃO DEVEM SER LOGADOS
MODELOS_IGNORADOS = [
    "LogAcaoSistema",
    "Session",
]

# 🔐 CAMPOS QUE NUNCA SÃO GRAVADOS NOS LOGS
CAMPOS_REMOVIDOS_LOG = ("password",)

# Marcador usado quando o CPF muda, mas a máscara permanece igual
# (ex.: correção apenas dos dígitos verificadores)
MARCADOR_ALTERADO = " (alterado)"

# -----------------------------------------
# Verifica existencia da tabela
# -----------------------------------------
def tabela_existe(nome_tabela):
    return nome_tabela in connection.introspection.table_names()

# -----------------------------------------
# Obtém o usuário logado
# -----------------------------------------
def get_usuario_logado_seguro():
    user = get_current_user()

    if isinstance(user, AnonymousUser):
        return None

    return user

# -----------------------------------------
# SERIALIZAÇÃO
# -----------------------------------------
def serializar(instancia):
    """
    Serializa a instância para comparação e registro.

    O hash da senha (password) nunca é serializado. O CPF permanece
    completo aqui, para que a comparação antes/depois seja feita com os
    valores reais; a máscara é aplicada somente na gravação do log
    (ver proteger_dados_sensiveis).
    """
    try:
        dados = model_to_dict(instancia)
        for campo in CAMPOS_REMOVIDOS_LOG:
            dados.pop(campo, None)
        return json.loads(json.dumps(dados, cls=DjangoJSONEncoder))
    except Exception as e:
        return {"erro_serializacao": str(e)}


# -----------------------------------------
# PROTEÇÃO DE DADOS SENSÍVEIS (gravação do log)
# -----------------------------------------
def proteger_dados_sensiveis(dados_antes, dados_depois):
    """
    Prepara os dados para gravação no log, DEPOIS da comparação antes/depois.

    - Remove campos que nunca devem ser gravados (password).
    - Mascara o CPF (***.182.917-**).
    - Se o CPF mudou, mas as máscaras ficaram iguais (correção dos dígitos
      verificadores), marca o valor novo com "(alterado)".

    Trabalha com cópias: os dicionários recebidos não são modificados.
    Valores que não sejam dicionários são devolvidos sem alteração.
    """
    antes = dict(dados_antes) if isinstance(dados_antes, dict) else dados_antes
    depois = dict(dados_depois) if isinstance(dados_depois, dict) else dados_depois

    for dados in (antes, depois):
        if isinstance(dados, dict):
            for campo in CAMPOS_REMOVIDOS_LOG:
                dados.pop(campo, None)

    antes_tem_cpf = isinstance(antes, dict) and "cpf" in antes
    depois_tem_cpf = isinstance(depois, dict) and "cpf" in depois

    cpf_antes = antes.get("cpf") if antes_tem_cpf else None
    cpf_depois = depois.get("cpf") if depois_tem_cpf else None

    if antes_tem_cpf:
        antes["cpf"] = mascarar_cpf(cpf_antes)

    if depois_tem_cpf:
        depois["cpf"] = mascarar_cpf(cpf_depois)

        if (
            antes_tem_cpf
            and cpf_antes
            and cpf_depois
            and cpf_antes != cpf_depois
            and antes["cpf"] == depois["cpf"]
        ):
            depois["cpf"] = f"{depois['cpf']}{MARCADOR_ALTERADO}"

    return antes, depois


# -----------------------------------------
# CAPTURA ESTADO ANTES (UPDATE)
# -----------------------------------------
@receiver(pre_save)
def capturar_dados_antes(sender, instance, **kwargs):

    if sender.__name__ in MODELOS_IGNORADOS:
        return

    if not instance.pk:
        return

    try:
        antigo = sender.objects.get(pk=instance.pk)
        instance._dados_antes = serializar(antigo)
    except sender.DoesNotExist:
        instance._dados_antes = {}


# -----------------------------------------
# CREATE / UPDATE
# -----------------------------------------
@receiver(post_save)
def log_create_update(sender, instance, created, **kwargs):

    if sender.__name__ in MODELOS_IGNORADOS:
        return

    # 🚫 IGNORAR alteração de senha (tratada manualmente)
    if sender.__name__ == "Usuario" and not created:
        campos_ignorados = ["password", "last_login"]

        dados_antes = getattr(instance, "_dados_antes", {})
        dados_depois = serializar(instance)

        alteracoes = [
            k for k in dados_depois.keys()
            if dados_antes.get(k) != dados_depois.get(k)
        ]

        if all(campo in campos_ignorados for campo in alteracoes):
            return

    dados_depois = serializar(instance)
    dados_antes = getattr(instance, "_dados_antes", {})

    diff = gerar_diff(dados_antes, dados_depois)

    # 🔥 SEMPRE LOGA CREATE
    if not diff and not created:
        return

    acao = "CREATE" if created else "UPDATE"

    if sender.__name__ == "ContatoAreaSeger":
        descricao = f"Atualização de contatos SEGER | Área {'criada' if created else 'atualizada'}"
    else:
        descricao = f"{sender.__name__} {'criado' if created else 'atualizado'}"

    # 🔐 Máscara/remoção de dados sensíveis somente após a comparação
    dados_antes, dados_depois = proteger_dados_sensiveis(dados_antes, dados_depois)

    if tabela_existe("log_acao_sistema"):
        LogAcaoSistema.objects.create(
            usuario=get_usuario_logado_seguro(),
            acao=acao,
            modelo_afetado=sender.__name__,
            descricao=descricao,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
        )

# -----------------------------------------
# DELETE
# -----------------------------------------
@receiver(post_delete)
def log_delete(sender, instance, **kwargs):

    if sender.__name__ in MODELOS_IGNORADOS:
        return

    if sender.__name__ == "ContatoAreaSeger":
        descricao = "Atualização de contatos SEGER | Área excluída"
    else:
        descricao = f"{sender.__name__} excluído"

    if tabela_existe("log_acao_sistema"):
        dados_antes, _ = proteger_dados_sensiveis(serializar(instance), {})

        LogAcaoSistema.objects.create(
            usuario=get_usuario_logado_seguro(),
            acao="DELETE",
            modelo_afetado=sender.__name__,
            descricao=descricao,
            dados_antes=dados_antes,
            dados_depois={},
        )


# -----------------------------------------
# LOGIN
# -----------------------------------------
@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    if not tabela_existe("log_acao_sistema"):
        return

    LogAcaoSistema.objects.create(
        usuario=user,
        acao="LOGIN",
        modelo_afetado="Autenticação",
        descricao="Usuário autenticado no sistema",
        dados_antes={},
        dados_depois={
            "username": user.username,
            "nome": user.get_full_name()
        }
    )

# -----------------------------------------
# LOGOUT
# -----------------------------------------
@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if not tabela_existe("log_acao_sistema"):
        return

    LogAcaoSistema.objects.create(
        usuario=user,
        acao="LOGOUT",
        modelo_afetado="Autenticação",
        descricao="Saída do usuário do sistema",
        dados_antes={
            "username": user.username if user else None
        },
        dados_depois={}
    )