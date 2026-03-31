from django.contrib.auth.models import AnonymousUser
from auditoria.middleware import get_current_user
from auditoria.models import LogAcaoSistema

# --------------------------------#
# 🔍 Função para gerar diferenças #
# --------------------------------#
def gerar_diff(antes, depois):

    IGNORAR_CAMPOS = [
        "session_data",
        "session_key",
        "last_login",
    ]

    if not antes or not depois:
        return []

    diff = []

    chaves = set(antes.keys()) | set(depois.keys())

    for chave in chaves:

        if chave in IGNORAR_CAMPOS:
            continue

        valor_antes = antes.get(chave)
        valor_depois = depois.get(chave)

        # 🔥 Normaliza listas (evita falso diff)
        if isinstance(valor_antes, list) and isinstance(valor_depois, list):
            if sorted(valor_antes) == sorted(valor_depois):
                continue

        # 🔥 Evita lixo técnico gigante
        if isinstance(valor_antes, str) and len(valor_antes) > 500:
            valor_antes = "[conteúdo muito grande]"
        if isinstance(valor_depois, str) and len(valor_depois) > 500:
            valor_depois = "[conteúdo muito grande]"

        if valor_antes != valor_depois:
            diff.append({
                "campo": formatar_nome_campo(chave),
                "antes": valor_antes,
                "depois": valor_depois,
            })

    return diff

# --------------------------------#
# 🧠 Formata nome do campo bonito #
# --------------------------------#
def formatar_nome_campo(nome):
    return nome.replace("_", " ").capitalize()


# ----------------------------------#
# 🎯 Função para Obter Usuário alvo #
# ----------------------------------#

def obter_usuario_log(instance=None, user_override=None):
    """
    Retorna o usuário correto para log:

    Prioridade:
    1. user_override (usado em casos especiais, ex: reset de senha)
    2. instance.usuario_atualizacao
    3. usuário do middleware
    4. None (se for Anonymous)
    """

    # 🔥 1. CASO EXPLÍCITO (RESET DE SENHA, ETC)
    if user_override:
        return user_override

    # 🔥 2. INSTANCE
    if instance and hasattr(instance, "usuario_atualizacao"):
        if instance.usuario_atualizacao:
            return instance.usuario_atualizacao

    # 🔥 3. MIDDLEWARE
    user = get_current_user()

    if isinstance(user, AnonymousUser) or not user:
        return None

    return user

# -----------------------------------#
# Função para Registro Manual de Log #
# -----------------------------------#
def registrar_log(usuario=None, acao=None, modelo=None, descricao=None,
                  dados_antes=None, dados_depois=None):

    if isinstance(usuario, AnonymousUser):
        usuario = None

    LogAcaoSistema.objects.create(
        usuario=usuario,
        acao=acao,
        modelo_afetado=modelo,
        descricao=descricao,
        dados_antes=dados_antes or {},
        dados_depois=dados_depois or {},
    )