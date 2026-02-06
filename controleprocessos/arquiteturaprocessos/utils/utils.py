import secrets
import string

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

def gerar_senha_temporaria_e_aplicar(usuario, *, commit=True):
    """
    Gera uma senha temporária forte, aplica no usuário e
    força a troca no próximo login.

    - NÃO salva senha em texto plano
    - Retorna a senha apenas para envio por e-mail
    - Pode ser usada tanto na criação quanto no reset de senha

    :param usuario: instância do model Usuario
    :param commit: se True, salva o usuário no banco
    :return: senha temporária em texto plano
    """

    # 🔐 Configuração da senha
    tamanho = 12
    caracteres = (
        string.ascii_uppercase +
        string.ascii_lowercase +
        string.digits +
        "!@#$%&*"
    )

    # Gera senha segura
    senha_temporaria = "".join(
        secrets.choice(caracteres) for _ in range(tamanho)
    )

    # Aplica no usuário
    usuario.set_password(senha_temporaria)
    usuario.must_change_password = True

    if commit:
        usuario.save(update_fields=["password", "must_change_password"])

    return senha_temporaria

