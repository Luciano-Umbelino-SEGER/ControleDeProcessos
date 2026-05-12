# ============================================================
# REGISTRY GLOBAL DE EXPORTAÇÕES DO SIGEMP
# ============================================================

EXPORT_REGISTRY = {}


def register_export(key, config):
    """
    Registra uma configuração de exportação.
    """

    EXPORT_REGISTRY[key] = config


def get_export_config(key):
    """
    Retorna configuração registrada.
    """

    return EXPORT_REGISTRY.get(key)