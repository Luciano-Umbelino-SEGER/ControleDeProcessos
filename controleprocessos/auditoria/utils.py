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