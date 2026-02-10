# arquitetura_processos/middleware.py
from django.contrib.auth import logout

class ForceLogoutOnPasswordResetMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/senha/reset/"):
            if request.user.is_authenticated:
                logout(request)
        return self.get_response(request)
