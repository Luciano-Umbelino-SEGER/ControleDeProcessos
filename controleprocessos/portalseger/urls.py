from django.urls import path
from .views import portal_sistemas

app_name = "portalseger"

urlpatterns = [
    path("", portal_sistemas, name="portal"),
]