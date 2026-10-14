from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "specialization",
        "user",
    )
    fields = (
        "name",
        "specialization",
        "consultation_fee",
        "is_available",
        "user",
    )