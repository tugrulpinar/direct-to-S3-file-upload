from django.urls import path
from . import views

urlpatterns = [
    path("", views.uploader, name="uploader"),
    path(
        "conventional-uploader/",
        views.conventional_uploader,
        name="conventional_uploader",
    ),
]
