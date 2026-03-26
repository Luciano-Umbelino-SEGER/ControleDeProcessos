from django.urls import path
from .views import LogAcaoListView, LogAcaoDetailView

app_name = "auditoria"

urlpatterns = [
    path("log-acoes/", LogAcaoListView.as_view(), name="log_list"),
    path("log-acoes/<int:pk>/", LogAcaoDetailView.as_view(), name="log_detail"),
]