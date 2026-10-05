import secrets
import string
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from datetime import datetime
from arquiteturaprocessos.models import (PerfilPermissao,)

# ============================================================
# Controle de acesso
# ============================================================
def tem_permissao(usuario, modulo_nome, funcionalidade_nome, acao_nome):
    """
    Retorna True se o usuário possui a permissão informada.

    Regras:
    - Usuário não autenticado não possui permissão.
    - Usuário Master possui acesso total.
    - A permissão é verificada no perfil do usuário.
    - Módulo e funcionalidade precisam estar ativos.
    - A ação precisa estar vinculada à funcionalidade.
    - Na ausência da permissão, o acesso é negado.
    """

    if not usuario.is_authenticated:
        return False

    # Usuário Master possui acesso total.
    if getattr(usuario, "is_master", False):
        return True

    # Usuário sem perfil não possui permissão.
    if not usuario.perfil_id:
        return False

    return PerfilPermissao.objects.filter(
        perfil_id=usuario.perfil_id,
        funcionalidade_acao__funcionalidade__modulo__nome=modulo_nome,
        funcionalidade_acao__funcionalidade__nome=funcionalidade_nome,
        funcionalidade_acao__acao__nome=acao_nome,
        funcionalidade_acao__funcionalidade__modulo__ativo=True,
        funcionalidade_acao__funcionalidade__ativo=True,
    ).exists()

# ============================================================
# 🔐 Função pública — definir senha e enviar e-mail
# ============================================================
def definir_senha_e_enviar_email(usuario, *, reset=False):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)

    link = settings.SITE_URL + reverse(
        "arquiteturaprocessos:password_reset_confirm",
        kwargs={"uidb64": uid, "token": token},
    )

    nome = usuario.get_full_name() or usuario.username

    if reset:
        assunto = "SIGEMP - Sistema de Gestão de Monitoramento de Processos — Redefinição de senha"
        mensagem = f"""
    Olá {nome},

    Recebemos uma solicitação para redefinição da sua senha no SIGEMP - Sistema de Gestão de Monitoramento de Processos.

    Dados da conta:
    Usuário: {usuario.username}
    Perfil : {usuario.perfil}

    Para criar uma nova senha, acesse o link abaixo:
    {link}

    Atenção:
    Este link deve ser acessado a partir do navegador da máquina
    onde o sistema SIGEMP está em execução (ambiente interno - máquina virtual).

    Caso esteja acessando de outra máquina, copie o link e abra
    no navegador da máquina virtual.

    Se você não solicitou essa ação, ignore este e-mail.
    """
    else:
        assunto = "SIGEMP - Sistema de Gestão de Monitoramento de Processos — Acesso criado com sucesso"
        mensagem = f"""
Olá {nome},

Seu acesso ao SIGEMP - Sistema de Gestão de Monitoramento de Processos, foi criado com sucesso.

Usuário: {usuario.username}
Setor  : {usuario.setor}
Cargo  : {usuario.cargo}
Função : {usuario.funcao}
Perfil : {usuario.perfil}

Para definir sua senha de acesso, clique no link abaixo:
{link}

Atenção:
Este link deve ser acessado a partir do navegador da máquina
onde o sistema SIGEMP está em execução (ambiente interno - máquina virtual).

Caso esteja acessando de outra máquina, copie o link e abra
no navegador da máquina virtual.
"""

    send_mail(
        subject=assunto,
        message=mensagem.strip(),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )

# -----------------------------------------------------------
# Função utilitária para conversão segura de datas (filtros)
# -----------------------------------------------------------
# Converte uma string no formato 'YYYY-MM-DD' (padrão enviado
# por inputs HTML do tipo <input type="date">) para um objeto
# datetime.date do Python.
#
# Caso o valor esteja vazio ou em formato inválido, a função
# retorna None em vez de gerar exceção. Isso evita que filtros
# de data nas views quebrem a execução da aplicação.
#
# Uso típico nas views:
#
#     data = parse_date(request.GET.get("criacao_de"))
#     if data:
#         queryset = queryset.filter(data_criacao__date__gte=data)
#
# Essa função foi criada para reutilização em múltiplas views
# que utilizam filtros por intervalo de datas.
# -----------------------------------------------------------
def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None