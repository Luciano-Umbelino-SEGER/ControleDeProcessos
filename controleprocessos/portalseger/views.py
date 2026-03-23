from django.shortcuts import render
from .models import Sistema


def portal_sistemas(request):
    sistemas = Sistema.objects.filter(ativo=True)

    return render(request, "portalseger/portal.html", {
        "sistemas": sistemas
    })