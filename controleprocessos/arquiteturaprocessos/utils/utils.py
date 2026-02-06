import secrets
import string
from django.conf import settings
from django.core.mail import send_mail


# ============================================================
# Controle de acesso
# ============================================================
def usuario_tem_acesso_total(user):
    """
    Retorna True se o usuário tem acesso total ao sistema.
    Usuário Master SEMPRE tem acesso.
    """
    if not user.is_authenticated:
        return False

    if getattr(user, "is_master", False):
        return True

    if user.perfil and user.perfil.nome.casefold() == "administrador":
        return True

    return False


# ============================================================
# 🔐 Utilitário interno — geração de senha forte
# ============================================================
def _gerar_senha_forte(tamanho=12):
    caracteres = (
        string.ascii_uppercase +
        string.ascii_lowercase +
        string.digits +
        "!@#$%&*"
    )
    return "".join(secrets.choice(caracteres) for _ in range(tamanho))


# ============================================================
# 🔐 Função pública — definir senha e enviar e-mail
# ============================================================
def definir_senha_e_enviar_email(usuario, *, reset=False):
    """
    Gera senha temporária, aplica no usuário, força troca no
    próximo login e envia e-mail.

    Usada tanto no cadastro quanto no reset de senha.
    """

    senha_temporaria = _gerar_senha_forte()

    # 🔐 Aplica senha criptografada
    usuario.set_password(senha_temporaria)
    usuario.must_change_password = True
    usuario.save(update_fields=["password", "must_change_password"])

    # 📧 Conteúdo do e-mail
    assunto = "SIGEMP — Senha temporária de acesso"

    if reset:
        mensagem = f"""
                    Assunto: SIGEMP — Senha redefinida

                    Olá {{ nome_usuario }},
                    
                    Sua senha de acesso ao SIGEMP foi redefinida por um administrador do sistema.
                    
                    Segue abaixo sua nova senha temporária:
                    
                    Senha temporária: {{ senha }}
                    
                    ⚠️ Importante:
                    Ao acessar o sistema, será obrigatório criar uma nova senha.
                    Essa ação é necessária para garantir a segurança da sua conta.
                    
                    Se você não solicitou esta redefinição ou identificar qualquer comportamento incomum,
                    entre em contato com o administrador do sistema imediatamente.
                    
                    Atenciosamente,
                    SIGEMP - Sistema de Gestão de Monitoramento de Processos
                    """
    else:
        mensagem = f"""
                    Olá {usuario.get_full_name() or usuario.username},
                    
                    Assunto: SIGEMP — Acesso criado com sucesso

                    Olá {{ nome_usuario }},
                    
                    Seu acesso ao SIGEMP (Sistema de Gestão de Monitoramento de Processos) foi criado com sucesso.
                    
                    Abaixo estão suas credenciais iniciais de acesso:
                    
                    Usuário: {{ username }}
                    Senha temporária: {{ senha }}
                    
                    ⚠️ Importante:
                    No primeiro acesso ao sistema, será obrigatório criar uma nova senha de sua escolha.
                    Essa medida garante a segurança das suas informações.
                    
                    Caso você não reconheça este cadastro ou tenha qualquer dificuldade de acesso,
                    entre em contato com o administrador do sistema.
                    
                    Atenciosamente,
                    SIGEMP - Sistema de Gestão de Monitoramento de Processos
                    """

    send_mail(
        subject=assunto,
        message=mensagem.strip(),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )
