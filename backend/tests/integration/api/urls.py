from django.urls import path

from tests.integration.api import views

urlpatterns = [
    path("probe/success/", views.success_probe, name="foundation-success-probe"),
    path("probe/validation/", views.validation_probe, name="foundation-validation-probe"),
    path("probe/csrf/", views.csrf_probe, name="foundation-csrf-probe"),
]
