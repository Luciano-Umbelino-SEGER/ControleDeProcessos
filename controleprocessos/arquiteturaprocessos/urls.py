from django.urls import path
from .views import *

urlpatterns = [
    path('', homepage, name='homepage'),
    path('cadastroprocessos/', cadastroprocessos, name='cadastroprocessos'),
    path('estatisticas/', estatisticas, name='estatisticas'),
    path('backlog/', backlog, name='backlog'),
    path('login/', login, name='login'),
]