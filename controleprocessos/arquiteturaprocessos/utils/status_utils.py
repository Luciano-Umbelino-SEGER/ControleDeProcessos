def normalizar_status(status):
    if not status:
        return ""
    return (
        status.lower()
        .replace("á", "a")
        .replace("ã", "a")
        .replace("ç", "c")
    )


def contar_status(processos):

    from collections import Counter

    contador = Counter(
        normalizar_status(p.status) for p in processos
    )

    return {
        "iniciado": contador.get("iniciado", 0),
        "ativo": contador.get("ativo", 0),
        "concluido": contador.get("concluido", 0),
        "total": sum(contador.values())
    }