from .models import LogAcaoSistema


def get_client_ip(request):
    """Captura IP real do usuário"""
    if not request:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')


def registrar_log(
    request=None,
    acao=None,
    modelo=None,
    objeto_id=None,
    descricao="",
    dados_antes=None,
    dados_depois=None,
    sucesso=True,
    usuario=None,
):
    """
    Função robusta:
    - aceita request (padrão)
    - ou aceita usuario direto (fallback)
    """

    user = None

    # 🔥 PRIORIDADE 1 → request
    if request and hasattr(request, "user"):
        user = request.user if request.user.is_authenticated else None

    # 🔥 PRIORIDADE 2 → usuario manual
    elif usuario:
        user = usuario

    try:
        LogAcaoSistema.objects.create(
            usuario=user,
            acao=acao,
            modelo_afetado=modelo,
            objeto_id=objeto_id,
            descricao=descricao,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            ip=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None,
            sucesso=sucesso
        )

    except Exception as e:
        # ⚠️ Log nunca pode quebrar o sistema
        print(f"Erro ao registrar log: {e}")