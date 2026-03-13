import re
import unicodedata


# Stopwords comuns em português que não agregam significado
STOPWORDS = {
    "de",
    "da",
    "das",
    "do",
    "dos",
    "e",
    "a",
    "as",
    "o",
    "os",
    "para",
    "por",
    "com",
    "sem",
    "na",
    "no",
    "nas",
    "nos",
}


def remover_acentos(texto: str) -> str:
    """
    Remove acentos e caracteres especiais.
    """
    if not texto:
        return ""

    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_texto(texto: str) -> str:
    """
    Normaliza um texto para facilitar comparação de similaridade.

    Etapas:
    - transforma em minúsculo
    - remove acentos
    - remove pontuação
    - remove stopwords
    - remove espaços duplicados
    """

    if not texto:
        return ""

    # minúsculo
    texto = texto.lower()

    # remover acentos
    texto = remover_acentos(texto)

    # remover pontuação
    texto = re.sub(r"[^\w\s]", " ", texto)

    # dividir em palavras
    palavras = texto.split()

    # remover stopwords
    palavras_filtradas = [
        p for p in palavras
        if p not in STOPWORDS
    ]

    # juntar novamente
    texto_normalizado = " ".join(palavras_filtradas)

    # remover espaços duplicados
    texto_normalizado = re.sub(r"\s+", " ", texto_normalizado).strip()

    return texto_normalizado