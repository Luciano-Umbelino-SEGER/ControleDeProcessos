from .models import LogAcaoSistema


def get_client_ip(request):
    """Captura IP real do usuário"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')


def registrar_log(
    request,
    acao,
    modelo,
    objeto_id=None,
    descricao="",
    dados_antes=None,
    dados_depois=None,
    sucesso=True
):
    try:
        LogAcaoSistema.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            acao=acao,
            modelo_afetado=modelo,
            objeto_id=objeto_id,
            descricao=descricao,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            sucesso=sucesso
        )
    except Exception as e:
        # ⚠️ Log nunca pode quebrar o sistema
        print(f"Erro ao registrar log: {e}")