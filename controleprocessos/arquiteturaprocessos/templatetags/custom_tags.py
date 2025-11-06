import os
from django import template
from urllib.parse import urlparse, unquote

register = template.Library()

@register.filter
def filename(value):
    """Retorna o nome do arquivo decodificado a partir de um caminho ou URL"""
    try:
        # Se for FieldFile, pega o nome
        if hasattr(value, 'name'):
            value = value.name
        # Extrai o path da URL ou caminho
        parsed = urlparse(value)
        # Decodifica os caracteres especiais
        decoded_path = unquote(parsed.path)
        return os.path.basename(decoded_path)
    except Exception:
        return value