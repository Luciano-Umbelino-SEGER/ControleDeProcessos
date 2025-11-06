"""
URL configuration for controleprocessos project.

O `urlpatterns` abaixo foi ajustado para permitir que arquivos PDF armazenados
em /media/ possam ser exibidos em iframes dentro do próprio sistema,
sem gerar o erro:
"Refused to display because it set 'X-Frame-Options' to 'DENY'"
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from django.views.decorators.clickjacking import xframe_options_sameorigin
from arquiteturaprocessos.utils.media_serve_safe import media_serve_allow_iframe

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('arquiteturaprocessos.urls', namespace='arquiteturaprocessos')),
]

# --- Servindo arquivos de mídia em modo DEBUG com permissão para iframe ---
if settings.DEBUG:
    urlpatterns += [
        path(
            'media/<path:path>',
            media_serve_allow_iframe,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
