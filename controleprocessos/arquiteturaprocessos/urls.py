from django.contrib import admin
from django.urls import path
from .views import HomePage, ArquiteruraProcessos, CadastroProcessos, Estatisticas, BackLog, CadastroUsuarios, Login

urlpatterns = [
    path('', HomePage.as_view(), name='homepage'),
    path('arquiteturaprocessos/', ArquiteruraProcessos.as_view(), name='arquiteturaprocessos'),
    #path('cadastroprocessos/<int:pk>', CadastroProcessos.as_view(), name='cadastroprocessos'),
    path('cadastroprocessos/', CadastroProcessos.as_view(), name='cadastroprocessos'),
    path('estatisticas/', Estatisticas.as_view(), name='estatisticas'),
    path('backlog/', BackLog.as_view(), name='backlog'),
    #path('cadastrousuarios/<int:pk>', CadastroUsuarios.as_view(), name='cadastrousuarios'),
    path('cadastrousuarios/', CadastroUsuarios.as_view(), name='cadastrousuarios'),
    #path('login/<int:pk>', Login.as_view(), name='login'),
    path('login/', Login.as_view(), name='login'),
]