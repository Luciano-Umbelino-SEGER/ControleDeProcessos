from django.core.serializers.json import DjangoJSONEncoder
import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.contrib.auth.signals import user_logged_in, user_logged_out

from .models import LogAcaoSistema
from auditoria.middleware import get_current_user
from .utils import gerar_diff

# 🔥 MODELOS QUE NÃO DEVEM SER LOGADOS
MODELOS_IGNORADOS = [
    "LogAcaoSistema",
    "Session",
]


# -----------------------------------------
# SERIALIZAÇÃO
# -----------------------------------------
def serializar(instancia):
    try:
        dados = model_to_dict(instancia)
        return json.loads(json.dumps(dados, cls=DjangoJSONEncoder))
    except Exception as e:
        return {"erro_serializacao": str(e)}


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

    dados_depois = serializar(instance)
    dados_antes = getattr(instance, "_dados_antes", {})

    diff = gerar_diff(dados_antes, dados_depois)

    # 🔥 NÃO LOGA ALTERAÇÃO IRRELEVANTE
    if not diff:
        return

    acao = "CREATE" if created else "UPDATE"

    LogAcaoSistema.objects.create(
        usuario=get_current_user(),  # 🔥 CORRETO
        acao=acao,
        modelo_afetado=sender.__name__,
        descricao=f"{sender.__name__} {'criado' if created else 'atualizado'}",
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

    LogAcaoSistema.objects.create(
        usuario=get_current_user(),  # 🔥 CORRETO
        acao="DELETE",
        modelo_afetado=sender.__name__,
        descricao=f"{sender.__name__} excluído",
        dados_antes=serializar(instance),
        dados_depois={},
    )


# -----------------------------------------
# LOGIN
# -----------------------------------------
@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
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