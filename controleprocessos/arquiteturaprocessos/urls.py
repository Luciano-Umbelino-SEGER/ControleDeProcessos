
from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', homepage, name='homepage'),
    path('cadastroprocessos/', cadastroprocessos, name='cadastroprocessos'),
    path('estatisticas/', estatisticas, name='estatisticas'),
    path('backlog/', backlog, name='backlog'),
    path('cadastrousuarios/', cadastrousuarios, name='cadastrousuarios'),
    path('login/', login, name='login'),
]