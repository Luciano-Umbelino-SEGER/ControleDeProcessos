from django.views.static import serve
from django.utils.decorators import decorator_from_middleware
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.http import HttpResponse


def media_serve_allow_iframe(request, path, document_root=None, show_indexes=False):
    """
    View segura para servir arquivos de mídia (PDFs, imagens, etc.)
    permitindo exibição em iframe.
    """
    response = serve(request, path, document_root=document_root, show_indexes=show_indexes)

    # Remove o cabeçalho que bloqueia iframe
    if isinstance(response, HttpResponse):
        response.headers.pop("X-Frame-Options", None)

    # Adiciona SAMEORIGIN explicitamente
    response["X-Frame-Options"] = "SAMEORIGIN"

    return response
