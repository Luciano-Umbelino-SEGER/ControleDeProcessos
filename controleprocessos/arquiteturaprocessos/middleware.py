from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            user = request.user

            # URLs liberadas mesmo com senha pendente
            allowed_paths = [
                reverse("arquiteturaprocessos:alterar_senha"),
                reverse("arquiteturaprocessos:logout"),
            ]

            if (
                getattr(user, "must_change_password", False)
                and request.path not in allowed_paths
            ):
                return redirect("arquiteturaprocessos:alterar_senha")

        return self.get_response(request)
