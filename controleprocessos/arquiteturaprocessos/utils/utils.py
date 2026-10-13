import secrets
import string

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse

from datetime import datetime

from arquiteturaprocessos.models import (PerfilPermissao, Funcionalidade,FuncionalidadeAcao, UsuarioPermissao,)

# ============================================================
# Controle de acesso
# ============================================================

def tem_permissao(usuario, modulo_nome, funcionalidade_nome, acao_nome):
    """
    Retorna True se o usuário possui a permissão informada.

    Precedência:
    1. Usuário Master possui acesso total.
    2. Decisão individual explícita prevalece sobre o perfil.
    3. Na ausência de exceção individual, consulta o perfil.
    4. Na ausência de autorização, nega o acesso.
    """
    if not usuario.is_authenticated:
        return False

    # Usuário Master possui acesso total.
    if getattr(usuario, "is_master", False):
        return True

    # Identifica a ação da funcionalidade solicitada,
    # garantindo que módulo e funcionalidade estejam ativos.
    funcionalidade_acao = FuncionalidadeAcao.objects.filter(
        funcionalidade__modulo__nome=modulo_nome,
        funcionalidade__nome=funcionalidade_nome,
        acao__nome=acao_nome,
        funcionalidade__modulo__ativo=True,
        funcionalidade__ativo=True,
    ).first()

    if not funcionalidade_acao:
        return False

    # 1. Verifica primeiro a exceção individual.
    permissao_individual = UsuarioPermissao.objects.filter(
        usuario=usuario,
        funcionalidade_acao=funcionalidade_acao,
    ).first()

    if permissao_individual:
        return (
            permissao_individual.decisao
            == UsuarioPermissao.Decisao.PERMITIR
        )

    # 2. Sem exceção individual, consulta o perfil.
    if not usuario.perfil_id:
        return False

    return PerfilPermissao.objects.filter(
        perfil_id=usuario.perfil_id,
        funcionalidade_acao=funcionalidade_acao,
    ).exists()


def obter_funcionalidades_permitidas(usuario):
    """
    Retorna as funcionalidades que o usuário pode acessar.

    Regras:
    - Usuário não autenticado não possui funcionalidades.
    - Usuário Master visualiza todas as funcionalidades ativas.
    - Demais usuários visualizam funcionalidades que tenham
      pelo menos uma ação efetivamente autorizada.
    - A permissão individual prevalece sobre a permissão do perfil.
    - Sem decisão individual, utiliza a permissão do perfil.
    - Módulo e funcionalidade precisam estar ativos.
    """
    if not usuario.is_authenticated:
        return Funcionalidade.objects.none()

    # Usuário Master visualiza todas as funcionalidades ativas.
    if getattr(usuario, "is_master", False):
        return (
            Funcionalidade.objects
            .filter(
                ativo=True,
                modulo__ativo=True,
            )
            .select_related("modulo")
            .order_by(
                "modulo__ordem",
                "modulo__id",
                "ordem",
                "id",
            )
        )

    funcionalidades = (
        Funcionalidade.objects
        .filter(
            ativo=True,
            modulo__ativo=True,
        )
        .select_related("modulo")
        .prefetch_related("acoes__acao")
        .order_by(
            "modulo__ordem",
            "modulo__id",
            "ordem",
            "id",
        )
    )

    ids_permitidos = []

    for funcionalidade in funcionalidades:
        for vinculo in funcionalidade.acoes.all():
            if tem_permissao(
                usuario,
                funcionalidade.modulo.nome,
                funcionalidade.nome,
                vinculo.acao.nome,
            ):
                ids_permitidos.append(funcionalidade.pk)
                break

    return funcionalidades.filter(pk__in=ids_permitidos)

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
        assunto = (
            "SIGEMP - Sistema de Gestão de Monitoramento de Processos "
            "— Redefinição de senha"
        )
        mensagem = f"""
Olá {nome},

Recebemos uma solicitação para redefinição da sua senha no SIGEMP -
Sistema de Gestão de Monitoramento de Processos.

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
        assunto = (
            "SIGEMP - Sistema de Gestão de Monitoramento de Processos "
            "— Acesso criado com sucesso"
        )
        mensagem = f"""
Olá {nome},

Seu acesso ao SIGEMP - Sistema de Gestão de Monitoramento de Processos,
foi criado com sucesso.

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