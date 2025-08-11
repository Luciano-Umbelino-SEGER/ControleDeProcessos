from django.shortcuts import render

# Create your views here.
def homepage(request):
    return render(request, 'homepage.html')

def cadastroprocessos(request):
    return render(request, 'cadastroprocessos.html')

def estatisticas(request):
    return render(request, 'estatisticas.html')

def backlog(request):
    return render(request, 'backlog.html')

def cadastrousuarios(request):
    return render(request, 'usuario/cadastrousuarios.html')

def login(request):
    return render(request, 'usuario/login.html')