from django.db import models
from django.contrib.auth.models import User


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    age = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("Confirmed", "Confirmed"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments"
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments"
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Scheduled"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "doctor",
                    "appointment_date",
                    "appointment_time",
                ],
                condition=~models.Q(status="Cancelled"),
                name="unique_active_doctor_appointment_slot",
            )
        ]

    def __str__(self):
        return f"{self.patient.name} - {self.doctor.name}"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("Cash", "Cash"),
        ("UPI", "UPI"),
        ("Card", "Card"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    ]

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payment"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="Pending"
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Payment for appointment {self.appointment_id}"