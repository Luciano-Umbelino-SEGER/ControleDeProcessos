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
